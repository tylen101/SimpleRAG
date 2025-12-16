import json
from typing import Any, cast
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings
from sqlalchemy import text

# SQLAlchemy Oracle dialect using python-oracledb:
# oracle+oracledb://user:pass@dsn
DATABASE_URL = f"oracle+oracledb://{settings.ORACLE_USER}:{settings.ORACLE_PASSWORD}@{settings.ORACLE_DSN}"
# "oracle+oracledb://app_user:4432@192.168.0.99:1521/?service_name=freepdb1"

connection_url = "oracle+oracledb://app_user:4432@127.0.0.1:1521/?service_name=freepdb1"


engine = create_engine(
    connection_url,
    pool_pre_ping=True,
    future=True,
)
print("db stuff:", connection_url)


def safe_json_deserializer(v):
    # Already decoded by the driver/dialect
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return v
    # bytes -> str
    if isinstance(v, (bytes, bytearray)):
        v = v.decode("utf-8")
    # str -> python
    if isinstance(v, str):
        v = v.strip()
        if v == "":
            return None
        return json.loads(v)
    # anything else: return as-is (or raise if you prefer)
    return v


def safe_json_serializer(obj):
    if obj is None:
        return None
    return json.dumps(obj, ensure_ascii=False)


# Cast dialect to Any to avoid static typing errors when attaching custom JSON handlers
# dialect_any._json_serializer = lambda obj: json.dumps(obj, ensure_ascii=False)
# dialect_any._json_deserializer = lambda s: json.loads(s)
# dialect_any = cast(Any, engine.dialect)


engine.dialect._json_serializer = safe_json_serializer
engine.dialect._json_deserializer = safe_json_deserializer
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


# with engine.connect() as connection:
#     result = connection.execute(text("SELECT * FROM app_users"))
#     for row in result:
#         print(row)


def get_db():
    print("-------------------getting db--------------------")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
