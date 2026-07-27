import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.rate_limit import LIMITE_ESCRITA, limiter
from app.models import AuditLog, Empresa, Job
from app.schemas import (
    GerarRequest,
    GerarResponse,
    HistoricoResponse,
    JobOut,
    PreviewResponse,
    ProcessarResponse,
    StatusResponse,
)
from app.services.docx_generator import DocxGeneratorService
from app.services.notas_builder import NotasBuilderService
from app.services.pdf_parser import PdfParserService
from app.services.storage import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notas", tags=["notas"])

ALLOWED_EXTENSIONS = {".pdf"}
PDF_MAGIC = b"%PDF"


# --------------------------------------------------------------------------- #
# Auxiliares
# --------------------------------------------------------------------------- #


async def _registrar_auditoria(
    db: AsyncSession, action: str, job_id: uuid.UUID | None, request: Request
) -> None:
    db.add(
        AuditLog(
            action=action,
            job_id=job_id,
            ip_address=request.client.host if request.client else None,
        )
    )
    await db.commit()


async def _validar_pdf(arquivo: UploadFile, rotulo: str) -> bytes:
    """Valida extensão, content-type, magic bytes e tamanho do upload."""
    nome = arquivo.filename or ""
    if Path(nome).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, detail=f"O arquivo de {rotulo} deve ter extensão .pdf"
        )

    if arquivo.content_type not in (None, "application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=400,
            detail=f"Content-Type inválido para o arquivo de {rotulo}",
        )

    conteudo = await arquivo.read()

    if not conteudo:
        raise HTTPException(status_code=400, detail=f"Arquivo de {rotulo} vazio")
    if len(conteudo) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"O arquivo de {rotulo} excede o limite de "
                f"{settings.max_upload_size_mb} MB"
            ),
        )
    if not conteudo.startswith(PDF_MAGIC):
        raise HTTPException(
            status_code=400, detail=f"O arquivo de {rotulo} não é um PDF válido"
        )

    return conteudo


def _empresa_para_dict(empresa: Empresa | None) -> dict[str, Any]:
    if empresa is None:
        return {"nome": "", "cnpj": "", "endereco": "", "socios": []}
    return {
        "id": str(empresa.id),
        "nome": empresa.nome,
        "cnpj": empresa.cnpj,
        "endereco": empresa.endereco or "",
        "socios": empresa.socios or [],
        "contador_nome": empresa.contador_nome,
        "contador_crc": empresa.contador_crc,
        "contador_cpf": empresa.contador_cpf,
        "timbrado_header_path": empresa.timbrado_header_path,
        "timbrado_footer_path": empresa.timbrado_footer_path,
    }


def _job_para_out(job: Job) -> JobOut:
    return JobOut(
        id=job.id,
        empresa_id=job.empresa_id,
        empresa_nome=job.empresa.nome if job.empresa else None,
        status=job.status,
        ano_exercicio=job.ano_exercicio,
        data_aprovacao=job.data_aprovacao,
        progresso=job.progresso,
        etapa_atual=job.etapa_atual,
        error_message=job.error_message,
        output_disponivel=bool(job.output_path and Path(job.output_path).exists()),
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


def _nome_arquivo_saida(job: Job) -> str:
    return f"Notas_Explicativas_{job.ano_exercicio}.docx"


# --------------------------------------------------------------------------- #
# Processamento em background
# --------------------------------------------------------------------------- #


async def processar_job(job_id: uuid.UUID) -> None:
    """Extrai os dados dos PDFs e monta a estrutura das notas."""
    async with AsyncSessionLocal() as db:
        job = await db.get(Job, job_id)
        if job is None:
            logger.error("Job %s não encontrado para processamento", job_id)
            return

        try:
            parser = PdfParserService()

            entradas = job.exercicios or [
                {
                    "ano": job.ano_exercicio,
                    "balanco_path": job.balanco_path,
                    "dre_path": job.dre_path,
                }
            ]

            exercicios: list[dict[str, Any]] = []
            for indice, entrada in enumerate(entradas):
                ano = entrada.get("ano")
                job.etapa_atual = f"Lendo demonstrativos de {ano}"
                job.progresso = 10 + int(70 * indice / max(len(entradas), 1))
                await db.commit()

                exercicios.append(
                    {
                        "ano": ano,
                        "balanco": parser.parse_balanco(entrada["balanco_path"]),
                        "dre": parser.parse_dre(entrada["dre_path"]),
                    }
                )

            job.etapa_atual = "Montando notas explicativas"
            job.progresso = 80
            await db.commit()

            empresa = _empresa_para_dict(job.empresa)
            config = {"ano": job.ano_exercicio, "data_aprovacao": job.data_aprovacao}
            notas = NotasBuilderService().build_all(exercicios, empresa, config)

            job.dados_extraidos = {
                "exercicios": exercicios,
                "empresa": empresa,
                "config": config,
                "notas": [nota.to_dict() for nota in notas],
            }
            job.status = "done"
            job.progresso = 100
            job.etapa_atual = "Dados extraídos — aguardando revisão"
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("Job %s processado: %d notas", job_id, len(notas))

        except Exception as exc:  # noqa: BLE001 - o erro é persistido no job
            logger.exception("Falha ao processar job %s", job_id)
            job.status = "error"
            job.error_message = str(exc)[:2000]
            job.etapa_atual = "Erro no processamento"
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #


@router.post(
    "/processar",
    response_model=ProcessarResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(LIMITE_ESCRITA)
async def processar(
    request: Request,
    background_tasks: BackgroundTasks,
    balanco_pdf: UploadFile = File(...),
    dre_pdf: UploadFile = File(...),
    empresa_id: uuid.UUID = Form(...),
    ano: int = Form(..., ge=1900, le=2999),
    data_aprovacao: str | None = Form(default=None),
    # Exercícios anteriores (opcionais), para as tabelas comparativas.
    balanco_pdf_ant1: UploadFile | None = File(default=None),
    dre_pdf_ant1: UploadFile | None = File(default=None),
    balanco_pdf_ant2: UploadFile | None = File(default=None),
    dre_pdf_ant2: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_db),
) -> ProcessarResponse:
    result = await db.execute(
        select(Empresa).where(Empresa.id == empresa_id, Empresa.deleted_at.is_(None))
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    job_id = uuid.uuid4()
    storage = StorageService()
    destino = storage.job_upload_dir(str(job_id))

    async def salvar(arquivo: UploadFile, rotulo: str) -> str:
        conteudo = await _validar_pdf(arquivo, rotulo)
        # Nome gerado pelo servidor — o nome original nunca é usado.
        return str(storage.save_bytes(destino, f"{uuid.uuid4()}.pdf", conteudo))

    balanco_path = await salvar(balanco_pdf, "Balanço Patrimonial")
    dre_path = await salvar(dre_pdf, "DRE")

    exercicios: list[dict[str, Any]] = [
        {"ano": ano, "balanco_path": balanco_path, "dre_path": dre_path}
    ]

    anteriores = (
        (balanco_pdf_ant1, dre_pdf_ant1, ano - 1),
        (balanco_pdf_ant2, dre_pdf_ant2, ano - 2),
    )
    for balanco_ant, dre_ant, ano_ant in anteriores:
        if balanco_ant is None and dre_ant is None:
            continue
        if balanco_ant is None or dre_ant is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Envie o Balanço e a DRE do exercício de {ano_ant}, "
                    "ou nenhum dos dois"
                ),
            )
        exercicios.append(
            {
                "ano": ano_ant,
                "balanco_path": await salvar(
                    balanco_ant, f"Balanço Patrimonial de {ano_ant}"
                ),
                "dre_path": await salvar(dre_ant, f"DRE de {ano_ant}"),
            }
        )

    job = Job(
        id=job_id,
        empresa_id=empresa_id,
        status="processing",
        ano_exercicio=ano,
        data_aprovacao=data_aprovacao,
        balanco_path=balanco_path,
        dre_path=dre_path,
        exercicios=exercicios,
        progresso=0,
        etapa_atual="Processamento iniciado",
    )
    db.add(job)
    await db.commit()

    await _registrar_auditoria(db, "upload", job_id, request)
    background_tasks.add_task(processar_job, job_id)

    return ProcessarResponse(
        job_id=job_id, status="processing", message="Processamento iniciado"
    )


@router.get("/historico", response_model=HistoricoResponse)
async def historico(
    empresa_id: uuid.UUID | None = Query(default=None),
    ano: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> HistoricoResponse:
    filtros = []
    if empresa_id is not None:
        filtros.append(Job.empresa_id == empresa_id)
    if ano is not None:
        filtros.append(Job.ano_exercicio == ano)

    total = await db.scalar(select(func.count(Job.id)).where(*filtros)) or 0

    result = await db.execute(
        select(Job)
        .where(*filtros)
        .order_by(Job.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    jobs = result.unique().scalars().all()

    return HistoricoResponse(
        items=[_job_para_out(job) for job in jobs],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/status/{job_id}", response_model=StatusResponse)
async def status_job(
    job_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> StatusResponse:
    job = await _obter_job(db, job_id)
    return StatusResponse(
        job_id=job.id,
        status=job.status,
        progresso=job.progresso,
        etapa_atual=job.etapa_atual,
        output_disponivel=bool(job.output_path and Path(job.output_path).exists()),
        error_message=job.error_message,
    )


@router.get("/preview/{job_id}", response_model=PreviewResponse)
async def preview(
    job_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> PreviewResponse:
    job = await _obter_job(db, job_id)
    if not job.dados_extraidos:
        raise HTTPException(
            status_code=409, detail="Os dados ainda não foram extraídos deste job"
        )
    return PreviewResponse(job_id=job.id, dados=job.dados_extraidos)


@router.post("/gerar/{job_id}", response_model=GerarResponse)
@limiter.limit(LIMITE_ESCRITA)
async def gerar(
    request: Request,
    job_id: uuid.UUID,
    payload: GerarRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> GerarResponse:
    job = await _obter_job(db, job_id)

    dados = dict(job.dados_extraidos or {})
    if payload and payload.dados_editados:
        dados.update(payload.dados_editados)

    if not dados.get("exercicios"):
        raise HTTPException(
            status_code=409,
            detail="Não há dados extraídos para gerar o documento",
        )

    empresa = dados.get("empresa") or _empresa_para_dict(job.empresa)
    config = dados.get("config") or {
        "ano": job.ano_exercicio,
        "data_aprovacao": job.data_aprovacao,
    }

    try:
        job.status = "processing"
        job.etapa_atual = "Gerando documento Word"
        job.progresso = 90
        await db.commit()

        notas = NotasBuilderService().build_all(
            dados.get("exercicios") or [], empresa, config
        )

        storage = StorageService()
        destino = storage.output_path(str(job.id), _nome_arquivo_saida(job))
        DocxGeneratorService().generate(notas, empresa, config, destino)

        job.dados_extraidos = {**dados, "notas": [n.to_dict() for n in notas]}
        job.output_path = str(destino)
        job.status = "done"
        job.progresso = 100
        job.etapa_atual = "Documento gerado"
        job.error_message = None
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()

    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - o erro é persistido no job
        logger.exception("Falha ao gerar documento do job %s", job_id)
        job.status = "error"
        job.error_message = str(exc)[:2000]
        job.etapa_atual = "Erro na geração do documento"
        await db.commit()
        raise HTTPException(
            status_code=500, detail="Falha ao gerar o documento"
        ) from exc

    await _registrar_auditoria(db, "generate", job_id, request)

    return GerarResponse(
        job_id=job.id, output_path=str(job.output_path), status=job.status
    )


@router.get("/download/{job_id}")
async def download(
    request: Request, job_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> FileResponse:
    job = await _obter_job(db, job_id)

    if not job.output_path:
        raise HTTPException(
            status_code=409, detail="O documento deste job ainda não foi gerado"
        )

    caminho = Path(job.output_path)
    if not caminho.exists():
        raise HTTPException(
            status_code=410,
            detail="O documento não está mais disponível (prazo de retenção expirado)",
        )

    await _registrar_auditoria(db, "download", job_id, request)

    return FileResponse(
        path=str(caminho),
        filename=_nome_arquivo_saida(job),
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )


async def _obter_job(db: AsyncSession, job_id: uuid.UUID) -> Job:
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job
