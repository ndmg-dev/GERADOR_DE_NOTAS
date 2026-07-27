from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação, lidas do ambiente / arquivo .env."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Banco
    database_url: str = "postgresql+asyncpg://notas_user:notas@db:5432/notas_db"

    # Ambiente
    environment: str = "development"
    frontend_url: str = "http://localhost:5173"

    # Armazenamento
    storage_path: Path = Path("/app/storage")

    # Uploads
    max_upload_size_mb: int = 50
    max_files_per_request: int = 2

    # Retenção
    file_retention_days: int = 30
    upload_retention_hours: int = 24
    # O scheduler roda dentro do processo da API. Com mais de uma réplica do
    # backend, mantenha-o ativo em apenas uma para não duplicar as limpezas.
    enable_scheduler: bool = True

    # OCR
    tesseract_cmd: str = "/usr/bin/tesseract"

    @property
    def uploads_dir(self) -> Path:
        return self.storage_path / "uploads"

    @property
    def outputs_dir(self) -> Path:
        return self.storage_path / "outputs"

    @property
    def timbrados_dir(self) -> Path:
        return self.storage_path / "timbrados"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def ensure_directories(self) -> None:
        for directory in (self.uploads_dir, self.outputs_dir, self.timbrados_dir):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
