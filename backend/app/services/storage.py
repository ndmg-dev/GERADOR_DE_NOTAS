import logging
import shutil
import time
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Gerencia o armazenamento em disco e a retenção automática de arquivos."""

    _scheduler: AsyncIOScheduler | None = None

    def __init__(self) -> None:
        self.uploads_dir = settings.uploads_dir
        self.outputs_dir = settings.outputs_dir
        self.timbrados_dir = settings.timbrados_dir

    # ------------------------------------------------------------------ IO

    def ensure_dir(self, path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_bytes(self, directory: Path, filename: str, content: bytes) -> Path:
        self.ensure_dir(directory)
        destino = directory / filename
        destino.write_bytes(content)
        return destino

    def job_upload_dir(self, job_id: str) -> Path:
        return self.ensure_dir(self.uploads_dir / job_id)

    def output_path(self, job_id: str, filename: str) -> Path:
        self.ensure_dir(self.outputs_dir)
        return self.outputs_dir / f"{job_id}_{filename}"

    # ----------------------------------------------------------- Retenção

    def limpar_uploads_antigos(self) -> int:
        """Remove diretórios de upload com mais de UPLOAD_RETENTION_HOURS horas."""
        limite_segundos = settings.upload_retention_hours * 3600
        removidos = self._remover_antigos(
            self.uploads_dir, limite_segundos, apenas_diretorios=True
        )
        if removidos:
            logger.info(
                "Retenção: %d diretório(s) de upload removido(s) (> %dh)",
                removidos,
                settings.upload_retention_hours,
            )
        return removidos

    def limpar_outputs_antigos(self) -> int:
        """Remove .docx gerados com mais de FILE_RETENTION_DAYS dias."""
        limite_segundos = settings.file_retention_days * 86400
        removidos = self._remover_antigos(
            self.outputs_dir, limite_segundos, sufixo=".docx"
        )
        if removidos:
            logger.info(
                "Retenção: %d arquivo(s) .docx removido(s) (> %d dias)",
                removidos,
                settings.file_retention_days,
            )
        return removidos

    def _remover_antigos(
        self,
        base: Path,
        limite_segundos: int,
        *,
        sufixo: str | None = None,
        apenas_diretorios: bool = False,
    ) -> int:
        if not base.exists():
            return 0

        agora = time.time()
        removidos = 0

        for item in base.iterdir():
            try:
                idade = agora - item.stat().st_mtime
                if idade <= limite_segundos:
                    continue
                if apenas_diretorios:
                    if not item.is_dir():
                        continue
                    shutil.rmtree(item)
                else:
                    if not item.is_file():
                        continue
                    if sufixo and item.suffix.lower() != sufixo:
                        continue
                    item.unlink()
                removidos += 1
                logger.info("Retenção: removido %s", item)
            except OSError:
                logger.warning("Retenção: falha ao remover %s", item, exc_info=True)

        return removidos

    # ---------------------------------------------------------- Scheduler

    def start_scheduler(self) -> None:
        if StorageService._scheduler is not None:
            return

        scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")
        scheduler.add_job(
            self.limpar_uploads_antigos,
            trigger="interval",
            hours=1,
            id="limpeza_uploads",
            replace_existing=True,
        )
        scheduler.add_job(
            self.limpar_outputs_antigos,
            trigger="interval",
            days=1,
            id="limpeza_outputs",
            replace_existing=True,
        )
        scheduler.start()
        StorageService._scheduler = scheduler
        logger.info(
            "Scheduler de retenção iniciado (uploads: %dh, outputs: %d dias)",
            settings.upload_retention_hours,
            settings.file_retention_days,
        )

    def shutdown_scheduler(self) -> None:
        if StorageService._scheduler is not None:
            StorageService._scheduler.shutdown(wait=False)
            StorageService._scheduler = None
            logger.info("Scheduler de retenção encerrado")
