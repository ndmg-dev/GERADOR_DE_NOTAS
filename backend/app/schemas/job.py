import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProcessarResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    message: str


class StatusResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    progresso: int
    etapa_atual: str | None = None
    output_disponivel: bool
    error_message: str | None = None


class PreviewResponse(BaseModel):
    job_id: uuid.UUID
    dados: dict[str, Any]


class GerarRequest(BaseModel):
    dados_editados: dict[str, Any] | None = None


class GerarResponse(BaseModel):
    job_id: uuid.UUID
    output_path: str
    status: str


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    empresa_id: uuid.UUID | None
    empresa_nome: str | None = None
    status: str
    ano_exercicio: int
    data_aprovacao: str | None
    progresso: int
    etapa_atual: str | None
    error_message: str | None
    output_disponivel: bool = False
    created_at: datetime
    finished_at: datetime | None


class HistoricoResponse(BaseModel):
    items: list[JobOut]
    total: int
    page: int
    limit: int


class ConfigNotas(BaseModel):
    """Configuração de um job usada pelos templates das notas."""

    ano: int = Field(ge=1900, le=2999)
    data_aprovacao: str | None = None

    @property
    def ano_anterior(self) -> int:
        return self.ano - 1
