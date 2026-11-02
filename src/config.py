from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_DB: str = Field(default="gis_intelligence")
    POSTGRES_USER: str = Field(default="postgres")
    POSTGRES_PASSWORD: str = Field(default="postgres_secret")

    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    EMBEDDING_MODEL_NAME: str = Field(default="BAAI/bge-m3")
    RERANKER_MODEL_NAME: str = Field(default="BAAI/bge-reranker-v2-m3")

    RAW_DATA_DIR: Path = Field(default=Path("./data_raw"))
    PROCESSED_DATA_DIR: Path = Field(default=Path("./data_processed"))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
