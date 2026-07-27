-- Schema do Gerador de Notas Explicativas
-- Aplicação sem autenticação: não existe tabela de usuários.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Empresas (cadastro de clientes com configuração de timbrado e sócios)
CREATE TABLE IF NOT EXISTS empresas (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                 VARCHAR(500) NOT NULL,
    cnpj                 VARCHAR(18) NOT NULL,
    endereco             TEXT,
    -- Ex: [{"nome": "Fulano", "participacao": "R$ 50.000,00", "cpf": "657...", "cargo": "Sócio Administrador"}]
    socios               JSONB NOT NULL DEFAULT '[]',
    contador_nome        VARCHAR(255),
    contador_crc         VARCHAR(50),
    contador_cpf         VARCHAR(14),
    timbrado_header_path TEXT,
    timbrado_footer_path TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at           TIMESTAMPTZ
);

-- Jobs de geração (rastreabilidade de cada execução)
CREATE TABLE IF NOT EXISTS jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id      UUID REFERENCES empresas(id),
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- 'pending' | 'processing' | 'done' | 'error'
    ano_exercicio   INTEGER NOT NULL,
    data_aprovacao  VARCHAR(100),
    balanco_path    TEXT,
    dre_path        TEXT,
    -- Exercícios comparativos: [{"ano": 2025, "balanco_path": ..., "dre_path": ...}]
    exercicios      JSONB NOT NULL DEFAULT '[]',
    output_path     TEXT,
    dados_extraidos JSONB,
    error_message   TEXT,
    progresso       INTEGER NOT NULL DEFAULT 0,
    etapa_atual     VARCHAR(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ
);

-- Log de auditoria (rastreio de ações sem necessidade de identificar usuário)
CREATE TABLE IF NOT EXISTS audit_log (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action     VARCHAR(100) NOT NULL,  -- 'upload', 'generate', 'download'
    job_id     UUID REFERENCES jobs(id),
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_jobs_empresa    ON jobs(empresa_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status     ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created    ON jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_job       ON audit_log(job_id);
CREATE INDEX IF NOT EXISTS idx_empresas_ativas ON empresas(deleted_at);
