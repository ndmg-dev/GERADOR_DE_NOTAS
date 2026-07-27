import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

CNPJ_RE = re.compile(r"^\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}$")


class Socio(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    participacao: str | None = Field(default=None, max_length=100)
    cpf: str | None = Field(default=None, max_length=14)
    cargo: str | None = Field(default=None, max_length=100)


class EmpresaBase(BaseModel):
    nome: str = Field(min_length=1, max_length=500)
    cnpj: str = Field(min_length=14, max_length=18)
    endereco: str | None = None
    socios: list[Socio] = Field(default_factory=list)
    contador_nome: str | None = Field(default=None, max_length=255)
    contador_crc: str | None = Field(default=None, max_length=50)
    contador_cpf: str | None = Field(default=None, max_length=14)

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj(cls, v: str) -> str:
        if not CNPJ_RE.match(v.strip()):
            raise ValueError("CNPJ inválido. Use o formato 00.000.000/0000-00")
        return v.strip()


class EmpresaCreate(EmpresaBase):
    pass


class EmpresaUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=500)
    cnpj: str | None = Field(default=None, min_length=14, max_length=18)
    endereco: str | None = None
    socios: list[Socio] | None = None
    contador_nome: str | None = Field(default=None, max_length=255)
    contador_crc: str | None = Field(default=None, max_length=50)
    contador_cpf: str | None = Field(default=None, max_length=14)

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not CNPJ_RE.match(v.strip()):
            raise ValueError("CNPJ inválido. Use o formato 00.000.000/0000-00")
        return v.strip()


class EmpresaOut(EmpresaBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    timbrado_header_path: str | None = None
    timbrado_footer_path: str | None = None
    created_at: datetime
    updated_at: datetime


class TimbradoOut(BaseModel):
    empresa_id: uuid.UUID
    timbrado_header_path: str | None
    timbrado_footer_path: str | None
