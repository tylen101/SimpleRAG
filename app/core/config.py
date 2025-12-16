from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

# TODO: fix the env dummy

print("env load: ", os.getenv("SECRET_KEY"))


class Settings(BaseModel):
    ORACLE_DSN: str = os.getenv("ORACLE_DSN", "localhost/orclpdb1")
    ORACLE_USER: str = os.getenv("ORACLE_USER", "app_user")
    ORACLE_PASSWORD: str = os.getenv("ORACLE_PASSWORD", "4432")

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "qwen3-embedding")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "4096"))

    DEFAULT_CHAT_MODEL: str = os.getenv("DEFAULT_CHAT_MODEL", "gpt-oss:20b")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "itsasecret")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")


settings = Settings()
