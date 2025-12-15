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
