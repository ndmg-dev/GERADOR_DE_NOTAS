
# Especificação Técnica — Gerador de Notas Explicativas
**Versão:** 1.1  
**Data:** Julho 2026  
**Origem:** Chamado #501 — Siler Rodrigues / Setor Contábil  
**Responsável TI:** Arthur Monteiro  

---

## 1. Visão Geral do Produto

### 1.1 O que é

Uma aplicação web interna que recebe os arquivos de **Balanço Patrimonial** e **DRE** em PDF (gerados pelo sistema contábil Domínio), extrai os dados automaticamente via OCR + parsing estruturado, e gera um arquivo `.docx` profissional das **Notas Explicativas às Demonstrações Contábeis**, formatado dentro do papel timbrado da empresa, pronto para assinatura.

### 1.2 O que faz (fluxo em 4 etapas)

```
Upload PDF (Balanço + DRE)
        ↓
Extração e estruturação de dados (OCR + parser Python)
        ↓
Geração do .docx com papel timbrado (python-docx)
        ↓
Download do arquivo final pelo usuário
```

### 1.3 Acesso à aplicação

A aplicação é de **uso interno, sem autenticação**. Qualquer usuário com acesso à rede onde ela estiver hospedada pode utilizá-la. A segurança de acesso é responsabilidade da infraestrutura de rede (VPN, firewall, VLAN interna), não da aplicação em si.

> **Consequência direta:** não há tabela de usuários, não há JWT, não há rotas de login, não há middleware de autorização. Todo endpoint da API é público dentro da rede.

### 1.4 Por que Python no backend (e não Java)

O coração do sistema é a **geração de documentos Word** e o **parsing de PDFs contábeis**.

- `python-docx` é a biblioteca mais madura e completa para gerar `.docx` programaticamente com controle fino de tabelas, bordas, imagens flutuantes (cabeçalho/rodapé timbrado), espaçamentos e estilos — exatamente o que este caso exige. A equivalente em Java (Apache POI) é notoriamente mais verbosa e menos confiável para layouts complexos.
- `pdfplumber` e `pytesseract` têm ecossistema muito superior para extração de dados de PDFs contábeis em PT-BR.
- O backend Python pode ser encapsulado em um contêiner leve (FastAPI + Uvicorn), mantendo a arquitetura Docker com o mesmo nível de isolamento que o Java teria.

**Decisão de stack final:**

| Camada | Tecnologia |
|---|---|
| Frontend | React 18 + Vite + TypeScript |
| Backend API | Python 3.12 + FastAPI |
| Geração de documentos | python-docx |
| Parsing PDF | pdfplumber + pytesseract |
| Banco de dados | PostgreSQL 16 |
| Containerização | Docker + Docker Compose |
| Proxy reverso | Nginx (produção) |

---

## 2. Arquitetura do Sistema

### 2.1 Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTE (Browser)                    │
│                React + Vite (SPA)                          │
│  - Upload de PDFs                                          │
│  - Formulário de configuração (empresa, período, sócios)   │
│  - Preview das notas antes de gerar                        │
│  - Download do .docx                                       │
└───────────────────┬─────────────────────────────────────────┘
                    │ HTTP / REST JSON (rede interna)
┌───────────────────▼─────────────────────────────────────────┐
│                   NGINX (reverse proxy)                     │
│  - Serve o build estático do frontend                      │
│  - Proxy /api/* → FastAPI                                  │
│  - Rate limiting (proteção contra uso acidental excessivo) │
└───────────────────┬─────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────┐
│               BACKEND — FastAPI (Python)                   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Routers (todos públicos — sem autenticação)         │  │
│  │  POST /api/notas/processar   ← upload PDFs           │  │
│  │  GET  /api/notas/status/{id}                         │  │
│  │  GET  /api/notas/preview/{id}                        │  │
│  │  POST /api/notas/gerar/{id}                          │  │
│  │  GET  /api/notas/download/{id}                       │  │
│  │  GET  /api/notas/historico                           │  │
│  │  GET  /api/empresas                                  │  │
│  │  POST /api/empresas                                  │  │
│  │  GET  /api/empresas/{id}                             │  │
│  │  PUT  /api/empresas/{id}                             │  │
│  │  POST /api/empresas/{id}/timbrado                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Services                                            │  │
│  │  PdfParserService   → extrai dados do Balanço/DRE   │  │
│  │  OcrService         → OCR via pytesseract           │  │
│  │  NotasBuilderService→ monta estrutura de notas      │  │
│  │  DocxGeneratorService → gera o .docx final          │  │
│  │  StorageService     → gerencia arquivos             │  │
│  └──────────────────────────────────────────────────────┘  │
└──────┬──────────────────────────────┬───────────────────────┘
       │                              │
┌──────▼──────┐               ┌──────▼──────────────────────┐
│ PostgreSQL  │               │  Volume Docker: /app/storage│
│             │               │  /uploads   ← PDFs entrada  │
│ - empresas  │               │  /outputs   ← .docx gerados │
│ - jobs      │               │  /timbrados ← logos/headers │
│ - audit_log │               └─────────────────────────────┘
└─────────────┘
```

### 2.2 Estrutura de Diretórios do Projeto

```
notas-explicativas/
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── README.md
│
├── frontend/
│   ├── Dockerfile
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/               ← axios clients
│       ├── components/
│       │   ├── UploadZone.tsx
│       │   ├── NotasPreview.tsx
│       │   ├── EmpresaForm.tsx
│       │   └── HistoricoTable.tsx
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── GerarNotas.tsx
│       │   ├── Historico.tsx
│       │   └── Empresas.tsx
│       ├── store/             ← Zustand
│       └── types/
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── app/
│       ├── core/
│       │   ├── config.py      ← settings via pydantic-settings
│       │   └── database.py    ← SQLAlchemy async
│       ├── models/
│       │   ├── empresa.py
│       │   └── job.py
│       ├── schemas/           ← Pydantic schemas
│       ├── routers/
│       │   ├── notas.py
│       │   └── empresas.py
│       ├── services/
│       │   ├── pdf_parser.py
│       │   ├── ocr_service.py
│       │   ├── notas_builder.py
│       │   ├── docx_generator.py
│       │   └── storage.py
│       └── templates/
│           └── notas/         ← templates de texto das notas por seção
│
├── nginx/
│   └── nginx.conf
│
└── db/
    └── init.sql
```

---

## 3. Modelo de Dados (PostgreSQL)

```sql
-- Empresas (cadastro de clientes com configuração de timbrado e sócios)
CREATE TABLE empresas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome            VARCHAR(500) NOT NULL,
    cnpj            VARCHAR(18) NOT NULL,
    endereco        TEXT,
    -- Sócios para o quadro societário
    socios          JSONB NOT NULL DEFAULT '[]',
    -- Ex: [{"nome": "Albert Mario...", "participacao": "R$ 50.000,00", "cpf": "657..."}]
    contador_nome   VARCHAR(255),
    contador_crc    VARCHAR(50),
    contador_cpf    VARCHAR(14),
    -- Paths das imagens do papel timbrado
    timbrado_header_path TEXT,
    timbrado_footer_path TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Jobs de geração (rastreabilidade de cada execução)
CREATE TABLE jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id      UUID REFERENCES empresas(id),
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
    -- 'pending' | 'processing' | 'done' | 'error'
    ano_exercicio   INTEGER NOT NULL,
    data_aprovacao  VARCHAR(100),
    -- Paths dos arquivos
    balanco_path    TEXT,   -- PDF do balanço (input)
    dre_path        TEXT,   -- PDF da DRE (input)
    output_path     TEXT,   -- .docx gerado (output)
    -- Dados extraídos (para auditoria e reprocessamento sem re-upload)
    dados_extraidos JSONB,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    finished_at     TIMESTAMPTZ
);

-- Log de auditoria (rastreio de ações sem necessidade de identificar usuário)
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action      VARCHAR(100) NOT NULL,  -- 'upload', 'generate', 'download'
    job_id      UUID REFERENCES jobs(id),
    ip_address  INET,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_jobs_empresa ON jobs(empresa_id);
CREATE INDEX idx_jobs_status  ON jobs(status);
CREATE INDEX idx_jobs_created ON jobs(created_at DESC);
CREATE INDEX idx_audit_job    ON audit_log(job_id);
```

---

## 4. Especificação da API (FastAPI)

> Todos os endpoints são públicos. Nenhum header de autorização é necessário.

### 4.1 Endpoints de Notas

```
POST /api/notas/processar
Content-Type: multipart/form-data
Campos:
  - balanco_pdf:    File   (obrigatório)
  - dre_pdf:        File   (obrigatório)
  - empresa_id:     string UUID (obrigatório)
  - ano:            integer (obrigatório, ex: 2025)
  - data_aprovacao: string (ex: "20 de julho de 2026")

Response 202:
{
  "job_id": "uuid",
  "status": "processing",
  "message": "Processamento iniciado"
}

──────────────────────────────────────────

GET /api/notas/status/{job_id}
Response:
{
  "job_id": "uuid",
  "status": "done",
  "progresso": 100,
  "etapa_atual": "Gerando documento Word",
  "output_disponivel": true
}

──────────────────────────────────────────

GET /api/notas/preview/{job_id}
Response:
{
  "job_id": "uuid",
  "dados": {
    "empresa": { ... },
    "notas": [
      { "numero": 4, "titulo": "Caixa e equivalentes de Caixa",
        "tabelas": [...], "textos": [...] },
      ...
    ]
  }
}

──────────────────────────────────────────

POST /api/notas/gerar/{job_id}
Body: { "dados_editados": { ... } }  // opcional: dados corrigidos pelo usuário
Response 200: { "output_path": "/outputs/uuid.docx", "status": "done" }

──────────────────────────────────────────

GET /api/notas/download/{job_id}
Response: FileResponse (.docx)
Headers: Content-Disposition: attachment; filename="Notas_Explicativas_2025.docx"

──────────────────────────────────────────

GET /api/notas/historico?empresa_id=&ano=&page=&limit=
Response: { "items": [...], "total": int, "page": int }
```

### 4.2 Endpoints de Empresas

```
GET    /api/empresas              → lista todas
POST   /api/empresas              → cria empresa
GET    /api/empresas/{id}         → detalhe
PUT    /api/empresas/{id}         → atualiza dados/sócios
POST   /api/empresas/{id}/timbrado → upload header/footer PNG do timbrado
DELETE /api/empresas/{id}         → remove empresa (soft delete)
```

---

## 5. Serviços Python — Lógica de Negócio

### 5.1 `PdfParserService` — Extração de Dados

```python
class PdfParserService:
    def parse_balanco(self, pdf_path: str) -> dict:
        """
        Retorna estrutura:
        {
          "ativo": {
            "circulante": {
              "caixa_equivalentes": { "total": 315540.60, "itens": [...] },
              "clientes": { "total": ..., "itens": [...] },
              "outros_creditos": { ... }
            },
            "nao_circulante": {
              "outros_creditos": { ... },
              "imobilizado": {
                "grupos": [ {"nome": "Edifícios", "custo": ..., "depreciacao": ..., "liquido": ...} ],
                "depreciacao_total": ...,
                "total_liquido": ...
              },
              "intangivel": { ... }
            }
          },
          "passivo": {
            "circulante": {
              "fornecedores": { "total": ... },
              "obrigacoes_tributarias": { "total": ..., "itens": [...] },
              "obrigacoes_trabalhistas": { "total": ..., "itens": [...] },
              "outras_obrigacoes": { ... }
            }
          },
          "patrimonio_liquido": {
            "capital_social": ...,
            "reservas": ...,
            "ajustes": ...,
            "total": ...
          },
          "total_ativo": ...,
          "total_passivo_pl": ...
        }
        """

    def parse_dre(self, pdf_path: str) -> dict:
        """
        Retorna estrutura:
        {
          "receita_bruta": ...,
          "deducoes": ...,
          "receita_liquida": ...,
          "custos": { "custos_aplicados": ..., "mao_obra_direta": ... },
          "lucro_bruto": ...,
          "despesas_operacionais": {
            "total": ...,
            "despesas_pessoal": ...,
            "impostos_taxas": ...,
            "despesas_gerais": ...
          },
          "resultado_financeiro": {
            "receitas_financeiras": ...,
            "despesas_financeiras": ...,
            "liquido": ...
          },
          "outras_receitas": ...,
          "resultado_operacional": ...,
          "lucro_liquido": ...
        }
        """

    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """Extração nativa — PDFs do Domínio têm camada de texto."""

    def _extract_with_ocr(self, pdf_path: str) -> str:
        """Fallback: rasteriza com pdf2image e aplica tesseract pt+eng."""

    def _parse_value(self, text: str) -> float:
        """Converte '1.566.336,51D' → 1566336.51 (D=débito, C=crédito negativo)."""

    def detect_extraction_method(self, pdf_path: str) -> str:
        """Retorna 'native' se há texto suficiente, senão 'ocr'."""
        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""
            return "native" if len(text.strip()) > 100 else "ocr"
```

### 5.2 `NotasBuilderService` — Estruturação das Notas

```python
class NotasBuilderService:
    """
    Recebe os dicts do parser e monta a lista ordenada de notas.
    Cada nota é um objeto:
    {
      "numero": int,
      "titulo": str,
      "tipo": "texto" | "tabela" | "misto",
      "conteudo": [ ... blocos de parágrafo e tabela em ordem ]
    }
    Notas cujos grupos não existem no balanço (ex: intangível zerado)
    são automaticamente omitidas.
    """

    def build_all(self, balanco: dict, dre: dict, empresa: dict, config: dict) -> list[Nota]:
        notas = [
            self.nota_contexto_operacional(empresa),
            self.nota_apresentacao(config),
            self.nota_praticas_contabeis(balanco),
            self.nota_caixa(balanco),
            self.nota_clientes(balanco),
            self.nota_outros_creditos(balanco),
            self.nota_realizavel_lp(balanco),
            self.nota_imobilizado(balanco),
            self.nota_intangivel(balanco),
            self.nota_fornecedores(balanco),
            self.nota_obrigacoes_tributarias(balanco),
            self.nota_obrigacoes_trabalhistas(balanco),
            self.nota_outras_obrigacoes(balanco),
            self.nota_capital_social(balanco, empresa),
            self.nota_patrimonio_liquido(balanco),
            self.nota_receita(dre),
            self.nota_custos_despesas(dre),
            self.nota_resultado_financeiro(dre),
            self.nota_resultado_exercicio(dre),
            self.nota_aprovacao(empresa, config),
        ]
        return [n for n in notas if n is not None]
```

### 5.3 `DocxGeneratorService` — Geração do .docx

```python
class DocxGeneratorService:
    def generate(self, notas: list[Nota], empresa: Empresa, output_path: str) -> str:
        doc = Document()
        self._apply_page_setup(doc)
        self._set_default_header(doc, empresa)
        self._set_default_footer(doc, empresa)
        self._add_title_block(doc, notas[0].config)
        for nota in notas:
            self._add_nota(doc, nota)
        self._add_signature_block(doc, empresa)
        doc.save(output_path)
        return output_path
```

**Parâmetros de layout (padrão já aprovado e validado):**

```python
PAGE_SETUP = {
    "width_twips":  11906,   # A4
    "height_twips": 16838,
    "margin_top":    2750,   # espaço para o header timbrado
    "margin_bottom": 1700,
    "margin_left":   1134,
    "margin_right":  1134,
}

TABLE_STYLE = {
    "header_fill":    "A6A6A6",
    "total_fill":     "A6A6A6",
    "border_size":    6,
    "font":           "Arial",
    "font_size_body": 22,    # 11pt (half-points)
    "font_size_table":18,    # 9pt
}
```

---

## 6. Frontend React — Telas e Componentes

### 6.1 Telas

| Rota | Componente | Descrição |
|---|---|---|
| `/` | `Dashboard.tsx` | Visão geral: últimos jobs, atalhos rápidos |
| `/gerar` | `GerarNotas.tsx` | Fluxo principal (upload → preview → download) |
| `/historico` | `Historico.tsx` | Tabela de todos os jobs com filtros |
| `/empresas` | `Empresas.tsx` | CRUD de empresas e timbrados |

### 6.2 Fluxo Principal (`GerarNotas.tsx`) — 3 Steps

```
Step 1: Upload e configuração
  ├─ Dropzone para balanco.pdf
  ├─ Dropzone para dre.pdf
  ├─ Select empresa (carregado da API)
  ├─ Input ano do exercício
  └─ Input data de aprovação

Step 2: Revisão dos dados extraídos
  ├─ Exibe os valores extraídos do Balanço
  ├─ Exibe os valores extraídos da DRE
  ├─ Campos editáveis para corrigir valores incorretos
  └─ Botão "Confirmar e Gerar"

Step 3: Download
  ├─ Barra de progresso (polling GET /api/notas/status/{job_id})
  └─ Botão "Baixar .docx" ao concluir
```

### 6.3 Dependências Frontend

```json
{
  "dependencies": {
    "react": "^18.3",
    "react-router-dom": "^6",
    "axios": "^1.7",
    "zustand": "^4",
    "@tanstack/react-query": "^5",
    "react-dropzone": "^14",
    "react-hook-form": "^7",
    "zod": "^3",
    "@radix-ui/react-select": "latest",
    "@radix-ui/react-dialog": "latest",
    "@radix-ui/react-progress": "latest",
    "@radix-ui/react-toast": "latest",
    "tailwindcss": "^3",
    "lucide-react": "latest"
  }
}
```

---

## 7. Docker Compose

### 7.1 `docker-compose.yml` (desenvolvimento)

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: notas_db
      POSTGRES_USER: notas_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U notas_user"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql+asyncpg://notas_user:${POSTGRES_PASSWORD}@db:5432/notas_db
      STORAGE_PATH: /app/storage
      TESSERACT_CMD: /usr/bin/tesseract
      ENVIRONMENT: development
      FRONTEND_URL: http://localhost:5173
    volumes:
      - ./backend:/app
      - storage_data:/app/storage
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      VITE_API_URL: http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "5173:5173"
    command: npm run dev

volumes:
  postgres_data:
  storage_data:
```

### 7.2 `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    tesseract-ocr-eng \
    poppler-utils \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 7.3 `backend/requirements.txt`

```
fastapi==0.111.0
uvicorn[standard]==0.30.0
python-multipart==0.0.9
sqlalchemy[asyncio]==2.0.31
asyncpg==0.29.0
alembic==1.13.2
pydantic==2.8.0
pydantic-settings==2.3.4
python-docx==1.1.2
pdfplumber==0.11.2
pytesseract==0.3.13
Pillow==10.4.0
pdf2image==1.17.0
slowapi==0.1.9
httpx==0.27.0
```

---

## 8. Segurança

A aplicação não tem autenticação. A segurança de acesso é garantida pela rede (VPN / firewall corporativo). As proteções implementadas na própria aplicação são:

### 8.1 Validação de Upload de Arquivos

```python
ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE_MB = 50
MAX_FILES_PER_REQUEST = 2

# Validações obrigatórias no backend:
# 1. Verificar magic bytes: arquivo deve começar com b'%PDF'
# 2. Rejeitar se Content-Type não for application/pdf
# 3. Salvar com nome UUID gerado pelo servidor (nunca usar o nome original)
# 4. Armazenar em /app/storage (fora do webroot, inacessível diretamente)
# 5. Rejeitar PDFs corrompidos (pdfplumber lança exceção ao abrir)
```

### 8.2 Rate Limiting (proteção contra uso acidental excessivo)

```python
# slowapi — limites por IP
@limiter.limit("10/minute")   # POST /processar e POST /gerar
@limiter.limit("60/minute")   # GETs em geral
```

### 8.3 Headers HTTP de Segurança

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
```

### 8.4 Banco de Dados

- Usuário do banco com permissões mínimas (SELECT, INSERT, UPDATE — sem DDL)
- Queries via SQLAlchemy ORM (proteção automática contra SQL injection)
- Senha do banco somente via variável de ambiente (nunca hardcoded)

### 8.5 Retenção de Arquivos

- PDFs de entrada são deletados automaticamente após 24 horas
- `.docx` gerados são deletados após 30 dias (configurável via `FILE_RETENTION_DAYS`)
- Implementar via `apscheduler` rodando no próprio processo FastAPI

---

## 9. Lógica de Parsing — Detalhes Críticos

### 9.1 Formato dos PDFs do Sistema Domínio

Os PDFs do Domínio têm camada de texto nativa e seguem padrão fixo:

```
Descrição              Saldo Atual
CONTA PRINCIPAL        9.999.999,99D
  subconta nivel 1     1.111,11D
    subconta nivel 2   222,22C
```

Onde `D` = débito (natureza devedora) e `C` = crédito (natureza credora).

```python
SECTION_MARKERS = {
    "ativo_circulante":      "ATIVO CIRCULANTE",
    "ativo_nao_circulante":  "ATIVO NÃO-CIRCULANTE",
    "passivo_circulante":    "PASSIVO CIRCULANTE",
    "patrimonio_liquido":    "PATRIMÔNIO LÍQUIDO",
}

ACCOUNT_PATTERNS = {
    "caixa_total":           r"CAIXA E EQUIVALENTE DE CAIXA\s+([\d.,]+)[DC]",
    "clientes_total":        r"CLIENTES\s+([\d.,]+)[DC]",
    "imobilizado_total":     r"IMOBILIZADO\s+([\d.,]+)[DC]",
    "depreciacao_acumulada": r"\(-\) DEPRECIA[ÇC][ÕO]ES.*?\s+([\d.,]+)[DC]",
    "fornecedores":          r"FORNECEDORES\s+([\d.,]+)[DC]",
    "patrimonio_liquido":    r"PATRIMÔNIO LÍQUIDO\s+([\d.,]+)[DC]",
}
```

### 9.2 Templates de Texto das Notas

Criar arquivos em `backend/app/templates/notas/` para cada nota. Isso permite que o time contábil edite os textos padrão sem alterar código:

```
nota_01_contexto.txt       → {empresa.nome}, {empresa.endereco}
nota_02_apresentacao.txt   → {config.data_aprovacao}, {config.ano}
nota_04_caixa.txt          → texto fixo + tabela gerada dinamicamente
nota_05_clientes.txt       → texto fixo + tabela
...
```

---

## 10. Roadmap de Implementação

### Fase 1 — MVP (2–3 semanas)
- [ ] Docker Compose funcionando (db + backend + frontend)
- [ ] CRUD de empresas + upload de timbrado
- [ ] Parser de Balanço e DRE para PDFs Domínio (extração nativa)
- [ ] Gerador `.docx` com papel timbrado
- [ ] Endpoint de download
- [ ] Tela de upload → progresso → download

### Fase 2 — Robustez (1–2 semanas)
- [ ] Fallback OCR para PDFs escaneados
- [ ] Step de revisão/edição dos dados extraídos
- [ ] Histórico de jobs com filtros
- [ ] Relatório de campos não encontrados no parsing

### Fase 3 — Produção (1 semana)
- [ ] Nginx + certificado TLS (rede interna)
- [ ] Alembic migrations
- [ ] Logs estruturados em JSON
- [ ] Backup automático do volume PostgreSQL
- [ ] Testes automatizados (pytest + Vitest)

### Fase 4 — Evolução (backlog)
- [ ] Notas comparativas (2 exercícios lado a lado)
- [ ] Suporte a outros sistemas contábeis além do Domínio
- [ ] Edição inline das notas no browser antes de exportar
- [ ] API webhook para fechar o chamado no sistema de tickets automaticamente

---

## 11. Variáveis de Ambiente (`.env.example`)

```env
# PostgreSQL
POSTGRES_PASSWORD=troque_em_producao

# Backend
FRONTEND_URL=http://localhost:5173
STORAGE_PATH=/app/storage
MAX_UPLOAD_SIZE_MB=50
FILE_RETENTION_DAYS=30
ENVIRONMENT=development

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## 12. Testes de Aceitação

O sistema será considerado funcional quando, dado o upload do Balanço e DRE da Soberana 2025:

1. Todas as notas estiverem presentes no `.docx` gerado no mesmo padrão do documento de referência
2. Os valores das tabelas baterem 100% com os do Balanço/DRE fonte
3. O papel timbrado (header/footer) aparecer corretamente em todas as páginas
4. O bloco de assinaturas estiver no final com nome, cargo e CPF dos signatários
5. O processo completo (upload → download) ocorrer em menos de 30 segundos para PDFs de até 10 páginas

---

*Documento gerado por Mendonça Galvão Contadores Associados — TI*  
*Referência: Chamado #501 — 24/07/2026*  
*Versão 1.1 — Autenticação removida conforme decisão de projeto*
