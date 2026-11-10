from pathlib import Path
import pytest
from src.config import Settings, settings

DEFAULT_POSTGRES_PORT = 5432
CUSTOM_POSTGRES_PORT = 5433
DEFAULT_POSTGRES_DB = "gis_intelligence"
DEFAULT_POSTGRES_HOST = "localhost"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"
DEFAULT_RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


def test_should_load_default_database_and_model_settings() -> None:
    # Arrange & Act
    cfg = Settings()

    # Assert
    assert cfg.POSTGRES_PORT == DEFAULT_POSTGRES_PORT
    assert cfg.POSTGRES_DB == DEFAULT_POSTGRES_DB
    assert cfg.POSTGRES_HOST == DEFAULT_POSTGRES_HOST
    assert cfg.EMBEDDING_MODEL_NAME == DEFAULT_EMBEDDING_MODEL
    assert cfg.RERANKER_MODEL_NAME == DEFAULT_RERANKER_MODEL


def test_should_expose_configured_singleton_instance() -> None:
    # Arrange & Act
    active_port = settings.POSTGRES_PORT
    active_db = settings.POSTGRES_DB

    # Assert
    assert active_port == DEFAULT_POSTGRES_PORT
    assert active_db == DEFAULT_POSTGRES_DB


def test_should_override_settings_from_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    monkeypatch.setenv("POSTGRES_HOST", "db.internal")
    monkeypatch.setenv("POSTGRES_PORT", str(CUSTOM_POSTGRES_PORT))
    monkeypatch.setenv("OLLAMA_MODEL", "bielik-11b")

    # Act
    cfg = Settings()

    # Assert
    assert cfg.POSTGRES_HOST == "db.internal"
    assert cfg.POSTGRES_PORT == CUSTOM_POSTGRES_PORT
    assert cfg.OLLAMA_MODEL == "bielik-11b"


def test_should_resolve_data_directories_as_path_objects() -> None:
    # Arrange & Act
    cfg = Settings()

    # Assert
    assert isinstance(cfg.RAW_DATA_DIR, Path)
    assert isinstance(cfg.PROCESSED_DATA_DIR, Path)
