# Deploy em produção (Coolify)

Guia para publicar o Gerador de Notas Explicativas em uma VPS com
[Coolify](https://coolify.io).

---

## ⚠️ Antes de tudo: proteja o acesso

**A aplicação não tem autenticação.** Isso foi uma decisão de projeto (spec §1.3):
a segurança de acesso é responsabilidade da infraestrutura de rede.

Numa VPS com domínio público, essa premissa deixa de valer sozinha. Sem uma
camada de proteção na frente, **qualquer pessoa que descobrir a URL** pode:

- listar e baixar as Notas Explicativas de todos os clientes;
- ver razão social, CNPJ, endereço, sócios e CPFs no cadastro de empresas;
- enviar arquivos e consumir recursos do servidor;
- remover empresas cadastradas.

Escolha **uma** destas proteções antes de expor o domínio:

| Opção | Como | Quando usar |
|---|---|---|
| **Restrição por IP** | Middleware `IPAllowList` do Traefik, liberando o IP fixo do escritório | Melhor opção se o escritório tem IP fixo |
| **Basic Auth no proxy** | Middleware `BasicAuth` do Traefik | Simples, funciona de qualquer lugar |
| **VPN / Tailscale** | Publicar só na rede privada | Mais seguro; exige VPN em cada máquina |
| **Cloudflare Access** | Zero Trust na frente do domínio | Bom com login corporativo (Google Workspace) |

No Coolify, middlewares do Traefik são adicionados em
**Configuration → Advanced → Custom Labels** do recurso.

Exemplo de Basic Auth (gere o hash com `htpasswd -nbB usuario senha`):

```
traefik.http.middlewares.notas-auth.basicauth.users=usuario:$2y$05$HASH_AQUI
traefik.http.routers.<nome-do-router>.middlewares=notas-auth
```

> O `$` precisa ser escapado como `$$` em arquivos compose, mas **não** no
> campo de labels do Coolify.

---

## 1. Pré-requisitos

- Coolify instalado e funcionando na VPS.
- Um domínio (ou subdomínio) apontando para o IP da VPS.
- Este repositório acessível pelo Coolify (GitHub, GitLab ou Git privado).

Dimensionamento: o parsing de PDF e a geração do `.docx` são operações de CPU
e memória modestas, mas o OCR (usado só em PDFs escaneados) é pesado.
**2 vCPU e 2 GB de RAM** atendem com folga o uso do escritório.

---

## 2. Criar o recurso no Coolify

1. **+ New** → **Resource** → **Docker Compose**.
2. Aponte para o repositório e o branch (`main`).
3. Em **Docker Compose Location**, informe:
   ```
   docker-compose.prod.yml
   ```
   Este é o passo mais fácil de esquecer — sem ele o Coolify usa o
   `docker-compose.yml`, que é o de **desenvolvimento** (com `--reload`,
   porta do banco publicada e sem build da SPA).

---

## 3. Variáveis de ambiente

Em **Environment Variables**, cadastre:

| Variável | Obrigatória | Observação |
|---|---|---|
| `POSTGRES_PASSWORD` | ✅ | Use o gerador do Coolify. O stack não sobe sem ela. |
| `MAX_UPLOAD_SIZE_MB` | — | Padrão `50`. Se aumentar, ajuste `client_max_body_size` em `nginx/nginx.conf`. |
| `FILE_RETENTION_DAYS` | — | Padrão `30`. |
| `UPLOAD_RETENTION_HOURS` | — | Padrão `24`. |
| `ENABLE_SCHEDULER` | — | Padrão `true`. Só mexa se rodar mais de uma réplica do backend. |

O arquivo [`.env.production.example`](.env.production.example) lista todas elas.

---

## 4. Domínio

O serviço `frontend` é o único ponto de entrada: o nginx serve a SPA e faz
proxy de `/api` para o backend. Banco e backend ficam apenas na rede interna,
sem portas publicadas.

Configure o domínio **no serviço `frontend`, porta 80**. O Coolify emite o
certificado TLS via Let's Encrypt automaticamente.

---

## 5. Deploy

Clique em **Deploy**. O Coolify vai:

1. clonar o repositório;
2. construir a imagem do backend (Python + tesseract) e a do frontend
   (build da SPA + nginx);
3. subir o Postgres e criar o schema a partir de `db/init.sql`;
4. aguardar os healthchecks e rotear o domínio.

A primeira subida demora alguns minutos por causa do tesseract. As seguintes
aproveitam o cache de camadas.

Para conferir, acesse `https://SEU-DOMINIO/health` — deve responder
`{"status":"ok"}`.

---

## 6. Depois do primeiro deploy

1. Acesse o domínio e vá em **Empresas**.
2. Cadastre cada cliente com razão social, CNPJ, endereço, quadro societário
   e dados do contador.
3. Envie os PNGs do **papel timbrado** (cabeçalho e rodapé) de cada empresa.
   As artes precisam manter a proporção das originais — veja a seção
   "Papel timbrado" do [README](README.md).
4. Peça ao time contábil para revisar os textos das 20 notas em
   `backend/app/templates/notas/`. São arquivos `.txt`; qualquer alteração
   exige um novo deploy para entrar no ar.

---

## Operação

### Backup

Dois volumes guardam estado e **precisam entrar na rotina de backup**:

| Volume | Conteúdo | Criticidade |
|---|---|---|
| `postgres_data` | Empresas, jobs e auditoria | **Alta** — cadastro não se recupera |
| `storage_data` | PDFs enviados, `.docx` gerados e timbrados | Média — timbrados não se recuperam |

O Coolify tem backup agendado para bancos em **Databases → Backups**. Como o
Postgres aqui faz parte de um Compose (e não é um recurso de banco do
Coolify), agende um dump por cron na VPS:

```bash
docker exec <container-do-db> pg_dump -U notas_user notas_db | gzip > /backup/notas_$(date +%F).sql.gz
```

Os timbrados também merecem uma cópia — são a única parte de `storage_data`
que não se regenera.

### Atualizar a aplicação

`git push` no branch configurado. Com **Automatic Deployment** ligado, o
Coolify reconstrói e sobe sozinho.

### Alterações no schema do banco

`db/init.sql` roda **apenas na primeira subida**, com o volume vazio. Mudanças
posteriores no schema não são aplicadas automaticamente — hoje precisam de SQL
manual:

```bash
docker exec -i <container-do-db> psql -U notas_user -d notas_db < migracao.sql
```

O Alembic já está nas dependências, mas as migrations ainda não foram
escritas (Fase 3 da spec). Enquanto isso, toda alteração de schema precisa de
um `ALTER TABLE` aplicado à mão.

### Logs

Em **Logs**, no recurso do Coolify. O backend loga em texto com nível INFO;
o nginx loga em JSON, com IP real do cliente, rota, status e duração.

### Migrar uma instalação anterior a esta versão

O backend passou a rodar como usuário sem privilégios (`notas`, uid 1000).
Volumes de `storage` criados por versões anteriores pertencem ao root e
precisam de um ajuste único:

```bash
docker compose -f docker-compose.prod.yml run --rm --user root backend \
  chown -R notas:notas /app/storage
```

Deploys novos não precisam disso.

---

## Decisões desta configuração

- **Nenhuma porta publicada no host.** Só o `frontend` é alcançável, pelo
  proxy do Coolify. O Postgres não fica exposto na internet.
- **Um único domínio.** O nginx serve a SPA e faz proxy de `/api`, então não
  há CORS nem segundo certificado para manter.
- **Documentação da API fechada em produção.** `/docs`, `/redoc` e
  `/openapi.json` respondem 404 quando `ENVIRONMENT=production`, para não
  publicar a superfície de uma API sem autenticação.
- **Backend sem root**, com healthcheck e `--proxy-headers`, para que o IP
  real do cliente chegue ao rate limiting e ao `audit_log`.
- **Um worker do uvicorn.** O scheduler de retenção roda no processo da API;
  com várias réplicas, as limpezas rodariam duplicadas. Se precisar escalar,
  suba réplicas com `ENABLE_SCHEDULER=false` e mantenha uma com `true`.
- **Cache agressivo nos assets** (têm hash no nome) e `no-store` no
  `index.html`, para que um deploy novo apareça imediatamente.
