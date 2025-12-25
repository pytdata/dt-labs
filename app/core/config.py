from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App
    APP_NAME: str = "DT-Labs LIS"
    ENV: str = "dev"
    SECRET_KEY: str = "5791628bb0huuce0c676dfde280ba245"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    DEFAULT_ADMIN_PASSWORD: str = "ChangeMe123!"

    # DB
    DATABASE_URL: str = "postgresql+asyncpg://postgres:cN7JmVQE9yztzyX3do@localhost:5432/dt_labs"


    # Integration
    INGEST_TOKEN: str = "dev-ingest-token"
    LIS_BASE_URL: str = "http://127.0.0.1:8000"

    # Web / Templates
    TEMPLATES_DIR: str = "app/web/templates"
    STATIC_DIR: str = "app/web/static"

    @property
    def TEMPLATES_PATH(self) -> Path:
        return Path(self.TEMPLATES_DIR)

    @property
    def STATIC_PATH(self) -> Path:
        return Path(self.STATIC_DIR)


    # Integration
    ASTM_SERVICE_API_URL: str = "http://127.0.0.1:8000/api/v1/integration/astm/results"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
