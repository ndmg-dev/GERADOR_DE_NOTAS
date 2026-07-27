# Gerador de Notas Explicativas

Aplicação web interna que recebe os PDFs de **Balanço Patrimonial** e **DRE** gerados pelo
sistema contábil **Domínio**, extrai os dados automaticamente e produz o arquivo `.docx` das
**Notas Explicativas às Demonstrações Contábeis**, formatado dentro do papel timbrado da
empresa e pronto para assinatura.

> **Sem autenticação.** É um sistema de uso interno: qualquer pessoa com acesso à rede onde
> ele estiver hospedado pode utilizá-lo. A segurança de acesso é responsabilidade da
> infraestrutura de rede (VPN, firewall, VLAN interna).

---

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS |
| Backend | Python 3.12 + FastAPI (assíncrono) |
| Banco | PostgreSQL 16 via SQLAlchemy async |
| Documentos | python-docx |
| PDF | pdfplumber + pytesseract (fallback OCR) |
| Infra | Docker + Docker Compose |

---

## Subindo o projeto

Pré-requisitos: Docker e Docker Compose.

```bash
cp .env.example .env      # ajuste POSTGRES_PASSWORD antes de subir
docker compose up --build
```

Os três serviços sobem juntos:

| Serviço | URL | Descrição |
|---|---|---|
| `frontend` | http://localhost:5173 | SPA React (Vite dev server) |
| `backend` | http://localhost:8000 | API FastAPI — docs em `/docs` |
| `db` | `localhost:5432` | PostgreSQL 16 |

Verificação rápida:

```bash
curl http://localhost:8000/api/health   # {"status":"ok"}
```

O schema do banco é criado automaticamente na primeira subida, a partir de
[`db/init.sql`](db/init.sql). Para recriá-lo do zero:

```bash
docker compose down -v && docker compose up --build
```

### Produção

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

O frontend é servido como build estático pelo Nginx ([`nginx/nginx.conf`](nginx/nginx.conf)),
que também faz o proxy de `/api/*` para o backend e aplica rate limiting.

---

## Como usar

1. **Empresas** — cadastre a empresa (razão social, CNPJ, endereço), o quadro societário e os
   dados do contador. Envie as imagens PNG do **header** e do **footer** do papel timbrado.
2. **Gerar Notas** — fluxo de 3 passos:
   - **Passo 1:** envie o PDF do Balanço e o da DRE, escolha a empresa, o ano do exercício e a
     data de aprovação (ex.: `20 de julho de 2026`).
   - **Passo 2:** revise os valores extraídos e corrija o que for necessário.
   - **Passo 3:** baixe o `.docx` gerado.
3. **Histórico** — consulte todas as gerações, com filtro por empresa e ano, e rebaixe os
   arquivos ainda dentro do prazo de retenção.

---

## Estrutura

```
├── backend/            FastAPI + serviços de parsing e geração
│   ├── app/
│   │   ├── core/       config, database, rate limiting
│   │   ├── models/     ORM (empresas, jobs, audit_log)
│   │   ├── routers/    notas, empresas
│   │   ├── schemas/    Pydantic
│   │   ├── services/   pdf_parser, ocr, notas_builder, docx_generator, storage
│   │   └── templates/  textos das 20 notas (.txt editáveis)
│   └── tests/
├── frontend/           React + Vite + TypeScript
├── db/init.sql         Schema PostgreSQL
├── nginx/nginx.conf    Proxy reverso (produção)
└── specs/              Especificação técnica
```

### Textos das notas

Os textos descritivos ficam em [`backend/app/templates/notas/`](backend/app/templates/notas/),
um arquivo `.txt` por nota. O time contábil pode editá-los sem alterar código. Os parâmetros
dinâmicos usam a sintaxe `{empresa.nome}`, `{config.ano}`, `{config.data_aprovacao}`, além dos
valores calculados de cada nota (`{total}`, `{capital}`, `{lucro}` etc.). Parágrafos são
separados por uma linha em branco.

---

## API

Todos os endpoints são públicos dentro da rede. Documentação interativa em `/docs`.

### Notas

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/notas/processar` | Upload dos PDFs — responde `202` com o `job_id` |
| `GET` | `/api/notas/status/{job_id}` | Status, progresso e etapa atual |
| `GET` | `/api/notas/preview/{job_id}` | Dados extraídos para revisão |
| `POST` | `/api/notas/gerar/{job_id}` | Gera o `.docx` (aceita dados corrigidos) |
| `GET` | `/api/notas/download/{job_id}` | Baixa o `.docx` |
| `GET` | `/api/notas/historico` | Lista paginada, com filtros |

### Empresas

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/empresas` | Lista as empresas ativas |
| `POST` | `/api/empresas` | Cria empresa |
| `GET` | `/api/empresas/{id}` | Detalhe |
| `PUT` | `/api/empresas/{id}` | Atualiza dados e sócios |
| `POST` | `/api/empresas/{id}/timbrado` | Upload dos PNGs de header/footer |
| `DELETE` | `/api/empresas/{id}` | Remove (soft delete) |

---

## Segurança

- Uploads validados por extensão, `Content-Type`, magic bytes (`%PDF`) e tamanho (50 MB).
- Arquivos salvos com nome UUID gerado pelo servidor, em `/app/storage` — fora do webroot.
  O acesso se dá exclusivamente pelo endpoint `/api/notas/download/{job_id}`.
- Rate limiting por IP: `10/minute` nos endpoints de escrita, `60/minute` nos demais.
- Headers `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection` e `Content-Security-Policy`.
- Senha do banco somente via variável de ambiente.

### Retenção de arquivos

Um scheduler (`apscheduler`) roda dentro do próprio processo FastAPI:

- **A cada hora:** remove os PDFs de upload com mais de `UPLOAD_RETENTION_HOURS` (padrão 24h).
- **A cada dia:** remove os `.docx` gerados com mais de `FILE_RETENTION_DAYS` (padrão 30 dias).

Todas as deleções são registradas no log da aplicação.

---

## Variáveis de ambiente

Veja [`.env.example`](.env.example).

| Variável | Padrão | Descrição |
|---|---|---|
| `POSTGRES_PASSWORD` | — | Senha do PostgreSQL (obrigatória) |
| `FRONTEND_URL` | `http://localhost:5173` | Origem liberada no CORS |
| `STORAGE_PATH` | `/app/storage` | Raiz do armazenamento |
| `MAX_UPLOAD_SIZE_MB` | `50` | Tamanho máximo por PDF |
| `FILE_RETENTION_DAYS` | `30` | Retenção dos `.docx` gerados |
| `UPLOAD_RETENTION_HOURS` | `24` | Retenção dos PDFs de entrada |
| `ENVIRONMENT` | `development` | `development` ou `production` |
| `VITE_API_URL` | `http://localhost:8000` | URL da API para o frontend |

---

## Testes

```bash
# Backend
cd backend && python -m pytest tests/ -v

# Frontend (checagem de tipos e build)
cd frontend && npm run lint && npm run build
```
