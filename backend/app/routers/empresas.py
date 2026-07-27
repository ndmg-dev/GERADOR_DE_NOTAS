import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import Empresa
from app.schemas import EmpresaCreate, EmpresaOut, EmpresaUpdate, TimbradoOut
from app.services.storage import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/empresas", tags=["empresas"])

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_TIMBRADO_BYTES = 5 * 1024 * 1024


async def _get_empresa_ativa(db: AsyncSession, empresa_id: uuid.UUID) -> Empresa:
    result = await db.execute(
        select(Empresa).where(Empresa.id == empresa_id, Empresa.deleted_at.is_(None))
    )
    empresa = result.scalar_one_or_none()
    if empresa is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa


@router.get("", response_model=list[EmpresaOut])
async def listar_empresas(db: AsyncSession = Depends(get_db)) -> list[Empresa]:
    result = await db.execute(
        select(Empresa).where(Empresa.deleted_at.is_(None)).order_by(Empresa.nome)
    )
    return list(result.scalars().all())


@router.post("", response_model=EmpresaOut, status_code=status.HTTP_201_CREATED)
async def criar_empresa(
    payload: EmpresaCreate, db: AsyncSession = Depends(get_db)
) -> Empresa:
    empresa = Empresa(
        nome=payload.nome,
        cnpj=payload.cnpj,
        endereco=payload.endereco,
        socios=[s.model_dump() for s in payload.socios],
        contador_nome=payload.contador_nome,
        contador_crc=payload.contador_crc,
        contador_cpf=payload.contador_cpf,
    )
    db.add(empresa)
    await db.commit()
    await db.refresh(empresa)
    logger.info("Empresa criada: %s (%s)", empresa.nome, empresa.id)
    return empresa


@router.get("/{empresa_id}", response_model=EmpresaOut)
async def detalhar_empresa(
    empresa_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Empresa:
    return await _get_empresa_ativa(db, empresa_id)


@router.put("/{empresa_id}", response_model=EmpresaOut)
async def atualizar_empresa(
    empresa_id: uuid.UUID,
    payload: EmpresaUpdate,
    db: AsyncSession = Depends(get_db),
) -> Empresa:
    empresa = await _get_empresa_ativa(db, empresa_id)

    dados = payload.model_dump(exclude_unset=True)
    if "socios" in dados and dados["socios"] is not None:
        dados["socios"] = [s.model_dump() for s in payload.socios or []]

    for campo, valor in dados.items():
        setattr(empresa, campo, valor)

    await db.commit()
    await db.refresh(empresa)
    logger.info("Empresa atualizada: %s", empresa.id)
    return empresa


@router.post("/{empresa_id}/timbrado", response_model=TimbradoOut)
async def upload_timbrado(
    request: Request,
    empresa_id: uuid.UUID,
    header: UploadFile | None = File(default=None),
    footer: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_db),
) -> TimbradoOut:
    empresa = await _get_empresa_ativa(db, empresa_id)

    if header is None and footer is None:
        raise HTTPException(
            status_code=400, detail="Envie ao menos uma imagem (header ou footer)"
        )

    storage = StorageService()
    destino = settings.timbrados_dir / str(empresa_id)

    for nome_campo, arquivo in (("header", header), ("footer", footer)):
        if arquivo is None:
            continue
        conteudo = await arquivo.read()
        _validar_png(conteudo, nome_campo)
        caminho = storage.save_bytes(destino, f"{nome_campo}.png", conteudo)
        if nome_campo == "header":
            empresa.timbrado_header_path = str(caminho)
        else:
            empresa.timbrado_footer_path = str(caminho)

    await db.commit()
    await db.refresh(empresa)
    logger.info("Timbrado atualizado para empresa %s", empresa_id)

    return TimbradoOut(
        empresa_id=empresa.id,
        timbrado_header_path=empresa.timbrado_header_path,
        timbrado_footer_path=empresa.timbrado_footer_path,
    )


@router.delete("/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_empresa(
    empresa_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    empresa = await _get_empresa_ativa(db, empresa_id)
    empresa.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info("Empresa removida (soft delete): %s", empresa_id)


def _validar_png(conteudo: bytes, campo: str) -> None:
    if not conteudo:
        raise HTTPException(status_code=400, detail=f"Arquivo '{campo}' vazio")
    if len(conteudo) > MAX_TIMBRADO_BYTES:
        raise HTTPException(
            status_code=413, detail=f"Arquivo '{campo}' excede 5 MB"
        )
    if not conteudo.startswith(PNG_MAGIC):
        raise HTTPException(
            status_code=400, detail=f"Arquivo '{campo}' não é um PNG válido"
        )
