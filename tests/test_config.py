from src.config import Settings, settings

def test_settings_load_defaults():
    s = Settings()
    assert s.POSTGRES_PORT == 5432
    assert s.POSTGRES_DB == "gis_intelligence"
    assert s.POSTGRES_HOST == "localhost"

def test_settings_singleton_instance():
    assert settings.POSTGRES_PORT == 5432
    assert settings.POSTGRES_DB == "gis_intelligence"
