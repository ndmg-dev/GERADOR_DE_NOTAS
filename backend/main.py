import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.core.rate_limit import limiter

# Importado pelo efeito colateral de registrar os models em Base.metadata,
# do qual depende a criação do schema em preparar_schema().
from app.models import AuditLog, Empresa, Job  # noqa: F401
from app.routers import empresas, notas
from app.services.storage import StorageService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("notas")

# X-Frame-Options não suporta múltiplas origens, então o controle de quem
# pode embutir a aplicação em iframe fica no frame-ancestors do CSP (ver
# nginx/security-headers.conf para o mesmo ajuste no frontend).
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Content-Security-Policy": (
        "default-src 'self'; frame-ancestors 'self' https://crmmg.mendoncagalvao.com.br"
    ),
    "Referrer-Policy": "no-referrer",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona os headers de segurança da spec seção 8.3 a toda resposta."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response


# Erros de autenticação do asyncpg, identificados pelo nome para não acoplar
# este módulo ao driver.
ERROS_DE_CREDENCIAL = frozenset(
    {"InvalidPasswordError", "InvalidAuthorizationSpecificationError"}
)

AJUDA_CREDENCIAL = (
    "Falha de autenticação no banco. O Postgres só aplica POSTGRES_PASSWORD "
    "quando inicializa o volume pela primeira vez: se o volume já existia, ele "
    "mantém a senha antiga e alterar a variável não tem efeito. Para alinhar a "
    "senha do banco à do ambiente, sem perder dados, rode no servidor: "
    "docker exec <container-do-db> psql -U notas_user -d notas_db "
    "-c \"ALTER USER notas_user WITH PASSWORD '<a senha de POSTGRES_PASSWORD>';\""
)


def _e_erro_de_credencial(exc: BaseException) -> bool:
    """Percorre a cadeia de causas procurando uma falha de autenticação."""
    atual: BaseException | None = exc
    while atual is not None:
        if type(atual).__name__ in ERROS_DE_CREDENCIAL:
            return True
        atual = atual.__cause__
    return False


async def preparar_schema(tentativas: int = 10, espera: float = 3.0) -> None:
    """Cria as tabelas que ainda não existem no banco.

    O `db/init.sql` só é executado pelo Postgres no primeiro boot, com o volume
    ainda vazio, e depende do bind mount ter funcionado. Quando isso falha, o
    schema nunca é criado e a aplicação sobe normalmente, quebrando só na
    primeira escrita — por isso a criação é garantida aqui, no startup.

    `create_all` usa checkfirst: tabelas existentes são deixadas intactas, e
    nenhuma coluna é alterada. Instalações antigas seguem inalteradas.

    A espera entre tentativas cobre o banco ainda subindo. Senha errada não é
    transitória: nesse caso o erro sobe na hora, com a orientação de correção.
    """
    for tentativa in range(1, tentativas + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Schema do banco verificado")
            return
        except Exception as exc:
            if _e_erro_de_credencial(exc):
                logger.error(AJUDA_CREDENCIAL)
                raise
            if tentativa == tentativas:
                raise
            logger.warning(
                "Banco indisponível (tentativa %d/%d): %s",
                tentativa,
                tentativas,
                exc,
            )
            await asyncio.sleep(espera)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings.ensure_directories()
    await preparar_schema()
    storage = StorageService()
    if settings.enable_scheduler:
        storage.start_scheduler()
    else:
        logger.info("Scheduler de retenção desabilitado nesta réplica")
    logger.info("Aplicação iniciada (ambiente=%s)", settings.environment)
    try:
        yield
    finally:
        storage.shutdown_scheduler()
        logger.info("Aplicação encerrada")


app = FastAPI(
    title="Gerador de Notas Explicativas",
    description=(
        "API interna para geração de Notas Explicativas às Demonstrações "
        "Contábeis a partir de PDFs do sistema Domínio. Sem autenticação — "
        "acesso restrito pela rede interna."
    ),
    version="1.1.0",
    lifespan=lifespan,
    # Como a API não tem autenticação, a documentação interativa fica
    # disponível apenas fora de produção, para não expor a superfície da API.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

cors_origins = [settings.frontend_url]
if settings.cors_origins:
    cors_origins.extend([o.strip() for o in settings.cors_origins.split(",")])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(notas.router)
app.include_router(empresas.router)


@app.get("/api/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor"},
    )
