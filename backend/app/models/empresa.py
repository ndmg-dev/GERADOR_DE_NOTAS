import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(String(500), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(18), nullable=False)
    endereco: Mapped[str | None] = mapped_column(Text)

    # [{"nome": ..., "participacao": ..., "cpf": ..., "cargo": ...}]
    socios: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    contador_nome: Mapped[str | None] = mapped_column(String(255))
    contador_crc: Mapped[str | None] = mapped_column(String(50))
    contador_cpf: Mapped[str | None] = mapped_column(String(14))

    timbrado_header_path: Mapped[str | None] = mapped_column(Text)
    timbrado_footer_path: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:  # pragma: no cover - apoio a debug
        return f"<Empresa {self.id} {self.nome!r}>"
