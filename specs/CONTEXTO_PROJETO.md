# Contexto do Projeto — Gerador de Notas Explicativas

> Documento de contexto gerado em 2026-07-28, cobrindo tudo o que foi construído,
> alterado e decidido desde o início do desenvolvimento. Complementa (não substitui)
> [`SPEC_NotasExplicativas_App.md`](SPEC_NotasExplicativas_App.md), que é a especificação
> original. Este arquivo registra o histórico de decisões, ajustes de referência e o
> estado atual do sistema.

---

## 1. O que é a aplicação

Sistema interno que recebe os PDFs de **Balanço Patrimonial** e **DRE** gerados pelo
sistema contábil **Domínio**, extrai os dados automaticamente e produz o `.docx` das
**Notas Explicativas às Demonstrações Contábeis**, dentro do papel timbrado real da
Mendonça Galvão Contadores Associados, pronto para assinatura.

**Decisão fundamental de projeto: sem autenticação.** Não existe login, JWT, tabela de
usuários ou middleware de autorização. A segurança de acesso é responsabilidade da
infraestrutura de rede (VPN, firewall, VLAN interna) — isso está documentado com
destaque em [`DEPLOY.md`](../DEPLOY.md) e no [`README.md`](../README.md), pois é
crítico antes de expor a aplicação publicamente.

Stack: React 18 + Vite + TypeScript + Tailwind (frontend) · Python 3.12 + FastAPI
assíncrono (backend) · PostgreSQL 16 via SQLAlchemy async · python-docx · pdfplumber +
pytesseract (fallback OCR) · Docker + Docker Compose.

---

## 2. Linha do tempo das decisões

### 2.1 Construção inicial
Implementação seguindo as 10 fases ordenadas da spec original, com commits atômicos em
português a cada etapa.

### 2.2 Alinhamento com documentos de referência reais
Após o usuário adicionar arquivos reais em `random_files/` (Balanço e DRE da Soberana
2025, Notas Explicativas da Soberana 2020–2022, e o papel timbrado real em `.docx`), foi
feita uma auditoria completa comparando a estrutura da aplicação com esses documentos.
Decisões tomadas pelo usuário nesse momento:

- **Comparativo de 3 exercícios**: as tabelas das notas passaram a suportar até 3 anos
  lado a lado (atual + 2 anteriores opcionais).
- **Alinhar 100% ao modelo**: a lista de 20 notas, sua ordem e nomenclatura foram
  reescritas para bater exatamente com o modelo de referência da Soberana (ver lista
  completa na seção 4).
- **Nota 08 (Imobilizado) com movimentação editável**: em vez de um valor único, a nota
  passou a ser uma tabela de movimentação (`saldo anterior · aquisições · baixas ·
  depreciação · saldo atual`), com aquisições/baixas/depreciação digitáveis na revisão —
  confirmado pelo usuário: *"Ela pode ser digitada na revisão."*
- **Provisões duplicada de propósito**: Provisões aparece tanto aninhada dentro do total
  de Obrigações Trabalhistas quanto como nota própria — comportamento intencional,
  confirmado pelo usuário: *"Sim, é assim."*
- **Papel timbrado é o arquivo real de produção**: o `.docx` enviado pelo usuário não é
  um mockup — é o timbrado oficial. Isso levou ao ajuste fino da geometria (ver seção 5),
  não das margens de texto (que já estavam corretas).

### 2.3 Checagem de completude
Pergunta do usuário — *"Tá pronto ou tem mais alguma coisa pra alterar?"* — levou à
descoberta de que a Nota 08 tinha sido **anunciada como editável mas não estava de
fato**: os campos de aquisições/baixas/depreciação estavam zerados e hardcoded, com
apenas um comentário no código dizendo "editável". Foi corrigida de verdade, com campo
`movimentacao_imobilizado` persistido, endpoint atualizado e UI de edição por grupo no
frontend.

Nesse mesmo ciclo, foi encontrado e corrigido um bug real de `UnicodeEncodeError` →
HTTP 500 na geração do `.docx`, quando um caractere de controle/substituto inválido
chegava ao `python-docx`.

### 2.4 Tema visual
O usuário compartilhou um print de um dashboard de referência ("FiscalMatch") para a
"Mendonça Galvão Contadores Associados", em modo escuro com destaque dourado, e pediu
que a mesma paleta fosse aplicada a toda a aplicação. Foi feita a migração completa do
frontend (todas as páginas e componentes) do tema neutro/cinza para o tema
escuro + dourado.

### 2.5 Preparação para produção
Pedido: *"Vamos preparar a aplicação pra produção. Colocarei-a no coolify que está
hospedado na minha vps."* Isso resultou em:

- Reescrita completa de `docker-compose.prod.yml` para convenções do Coolify (sem
  portas publicadas no host, variáveis mágicas `SERVICE_FQDN_*`/`SERVICE_URL_*`).
- `backend/Dockerfile` de produção com usuário não-root, healthcheck e dependências
  de sistema (tesseract-ocr, poppler-utils).
- `frontend/Dockerfile.prod` multi-stage (build da SPA + nginx).
- `nginx/nginx.conf` com rate limiting, gzip, headers de segurança, proxy para o
  backend.
- Documentação completa em [`DEPLOY.md`](../DEPLOY.md), incluindo aviso proeminente de
  que a aplicação sem autenticação **precisa** de uma camada de proteção de rede antes
  de qualquer domínio público (IP allowlist, Basic Auth, VPN ou Cloudflare Access).

### 2.6 Push para o GitHub e questão de segurança de dados reais
Pedido: subir o repositório para `https://github.com/ndmg-dev/GERADOR_DE_NOTAS`.

Durante a auditoria pré-push, foi descoberto que `backend/tests/test_notas_builder.py`
continha **dados pessoais reais** (CNPJ real, nome e CPF reais de um sócio, nome/CPF/CRC
reais de um contador) — extraídos verbatim do bloco de assinatura do DRE de referência
da Soberana durante o trabalho de alinhamento. Confirmado via API do GitHub que o
repositório de destino é **público**.

O usuário foi consultado explicitamente sobre como proceder e escolheu
**"Publicar como está"** — ou seja, decidiu conscientemente **não reescrever o
histórico do git** para remover os dados reais já commitados, aceitando que essas
informações (CPFs, nome do cliente, valores financeiros) permaneceriam permanentemente
públicas nos commits já existentes (a partir de `42ba739`).

Como correção **daqui para frente** (sem alterar histórico), o fixture de teste foi
trocado para dados fictícios: empresa "Instituição de Ensino Exemplo Ltda", sócios "Ana
Paula Ribeiro de Souza" e "Carlos Eduardo Nunes", contadora "Marina Alves Pereira",
todos com CPF/CNPJ fabricados. Commit: *"Usa dados fictícios nos fixtures de teste"*.
Todos os 62 testes do backend continuam passando.

> **Importante para o futuro**: essa foi uma decisão explícita e consciente do usuário.
> Não reescrever o histórico do git nem tentar "corrigir" isso retroativamente sem o
> usuário pedir de novo.

### 2.7 Bloqueio de push (pendência em aberto)
`git push -u origin main` falhou com **403** — a credencial local do Git (via Windows
Credential Manager) está autenticada como `monteiro-lab`, que não tem permissão de
escrita em `ndmg-dev/GERADOR_DE_NOTAS`. O repositório remoto está vazio (seria um push
inicial, sem sobrescrever nada).

Caminhos de resolução propostos ao usuário:
1. Adicionar `monteiro-lab` como colaborador em `ndmg-dev/GERADOR_DE_NOTAS`
   (Settings → Collaborators), ou
2. Trocar a credencial usada localmente por uma com acesso de escrita ao repositório
   (ex.: token pessoal da própria conta `ndmg-dev`).

**Status: ainda não resolvido.** Assim que resolvido, retomar com
`git push -u origin main`.

---

## 3. Bugs reais encontrados e corrigidos

| Bug | Causa raiz | Correção |
|---|---|---|
| Contas com nomes longos somem da extração | Regex `_LINE_RE` exigia 2+ espaços entre descrição e valor; PDFs reais colapsam para 1 espaço | Regex ajustada para `\s+` |
| Depreciação em dobro (2.328.449,24 em vez de 1.164.224,62) | Hierarquia do Domínio não é confiável por indentação — linhas sintéticas e analíticas caem na mesma coluna, causando contagem dupla | `_agrupar_por_soma()`: reconstrução aritmética (pai = soma dos filhos) + `_analiticas_no_mesmo_nivel()` para subgrupos no mesmo nível do pai (caso Provisões) |
| Nota "Obrigações Trabalhistas" ausente inteira | Parser só reconhecia a forma plural; o relatório real do Domínio usa "OBRIGACOES TRABALHISTA E PREVIDENCIARIA" (singular) | Variante singular adicionada ao conjunto de rótulos |
| Nota 08 "editável" só no nome | Campos de movimentação hardcoded em `0.0`, com comentário dizendo "editável" mas sem campo real nem UI | `movimentacao_imobilizado` implementado de ponta a ponta (modelo, endpoint, UI) |
| `UnicodeEncodeError` → HTTP 500 na geração do `.docx` | Caractere de controle/substituto inválido quebrava a serialização XML do python-docx | `texto_seguro()` sanitiza todo texto antes de `add_run()` |
| HMR do Vite não funciona no Docker (Windows) | Bind mounts do Windows não propagam eventos de mudança de arquivo para dentro do contêiner | `usePolling: true` em `vite.config.ts` quando `IN_DOCKER=true` |
| Headers de segurança ausentes em `/` e `/index.html` | `add_header` do nginx não herda entre blocos `location` aninhados — qualquer `location` com seu próprio `add_header` descarta os do `server{}` pai | Headers extraídos para `nginx/security-headers.conf`, incluído via `include` em cada `location` que declara `add_header` |
| `Cache-Control` duplicado em `/assets/*` | `expires 1y;` + `add_header Cache-Control` explícito geravam dois headers | Removido `expires`, mantido só o `add_header` |
| Permissão negada ao escrever em `/app/storage` (dev) | Volume `storage_data` pré-existente era dono do `root`; novo Dockerfile roda como usuário `notas` (uid 1000) | `chown -R notas:notas /app/storage` uma única vez; documentado em `DEPLOY.md` para migração de instalações antigas |
| Push 403 para `ndmg-dev/GERADOR_DE_NOTAS` | Credencial local (`monteiro-lab`) sem permissão de escrita no repo de destino | **Em aberto** — depende de ação do usuário (colaborador ou troca de credencial) |

---

## 4. As 20 notas (ordem final, alinhada à referência da Soberana)

| # | Nota | # | Nota |
|---|---|---|---|
| 01 | Contexto operacional | 11 | Obrigações Trabalhistas |
| 02 | Apresentação das Demonstrações Contábeis | 12 | Obrigações Fiscais |
| 03 | Sumário das principais práticas contábeis | 13 | Adiantamento de Clientes |
| 04 | Caixa e equivalentes de Caixa | 14 | Outras Obrigações |
| 05 | Contas a receber de clientes | 15 | Provisões |
| 06 | Créditos | 16 | Capital Social |
| 07 | Realizável a Longo Prazo | 17 | Receita Operacional Líquida |
| 08 | Imobilizado | 18 | Natureza das Despesas e Custos |
| 09 | Fornecedores | 19 | Resultado Financeiro |
| 10 | Empréstimos e Financiamentos | 20 | Aprovação das Demonstrações Financeiras |

Notas removidas na fase de alinhamento (não existem no modelo de referência como notas
separadas): **Patrimônio Líquido** e **Resultado do Exercício** — o Intangível foi
incorporado à nota de Imobilizado. Notas cujos grupos não existem no balanço são
omitidas automaticamente e as demais renumeradas em sequência.

**Nota 08 (Imobilizado)**: tabela de movimentação `saldo anterior · aquisições · baixas
· depreciação · saldo atual`. Saldo anterior vem do balanço do exercício precedente
(quando enviado); aquisições, baixas e depreciação do período não constam do balanço do
Domínio e são digitadas por grupo no passo de revisão. Sem preenchimento, a depreciação
cai para a variação entre exercícios.

**Nota 16 (Capital Social)**: o quadro societário mostra apenas `Sócio | Participação`
— sem CPF na tabela (o CPF ainda aparece no bloco de assinatura, formato
`REPRESENTANTE LEGAL` / `CONTADOR - CRC Nº <crc>`).

**Nota 18 (Natureza das Despesas e Custos)**: matriz por exercício (Custo do Serviço
Prestado / Serviços de Terceiros / Depreciações / Outros Custos e Despesas, cruzando
Custos vs. Despesas Gerais e Administrativas). A DRE do Domínio só informa o total das
despesas operacionais sem abrir os componentes — por isso os 4 campos são editáveis por
exercício no passo de revisão; o padrão inicial usa o que a DRE fornece e joga o
restante em "Outros".

---

## 5. Papel timbrado — geometria de referência

O `.docx` enviado pelo usuário é o **timbrado real de produção**. A imagem é ancorada à
página como floating image (`wp:anchor`, `behindDoc=1`, `wp:wrapNone`), atrás do texto,
para se repetir em todas as páginas.

| | Largura | Altura | Posição |
|---|---|---|---|
| Página | 11910 twips | 16840 twips | — |
| Cabeçalho | 11397 twips | proporcional à imagem enviada | topo, centralizado |
| Rodapé | 11477 twips | proporcional à imagem enviada | pé da página, centralizado |

A altura é derivada da proporção real da imagem enviada — por isso as artes de cada
empresa precisam manter a mesma proporção das originais (cabeçalho ~2371×447 px,
rodapé ~2391×299 px). As margens de texto (2750 twips no topo, 1700 no pé) já estavam
corretas na spec original e **não** precisaram de ajuste — apenas as dimensões de
página e a largura/posicionamento da arte precisaram ser corrigidos para bater com o
arquivo real. Há testes (`test_docx_generator.py`) que garantem que o corpo do texto
não colide com a arte do timbrado.

---

## 6. Tema visual (paleta escura + dourado)

Aplicado em `frontend/tailwind.config.js` como tokens semânticos:

| Token | Cor | Uso |
|---|---|---|
| `fundo` / `fundo-alt` | `#0f0c09` / `#0a0806` | Fundo da aplicação |
| `superficie` / `superficie-alt` | `#17120d` / `#1e1811` | Cards, painéis |
| `borda` / `borda-clara` | `#2a2119` / `#3d3124` | Bordas |
| `ouro` / `claro` / `escuro` | `#c9a961` / `#e2cd93` / `#a1823f` | Destaque, botões primários |
| `texto` / `texto-suave` / `texto-fraco` | `#f2ece1` / `#a89a86` / `#6f6558` | Hierarquia de texto |
| `sucesso` / `erro` | `#4ade80` / `#f87171` | Estados |

Classes reutilizáveis em `frontend/src/index.css`: `.cartao`, `.cartao-destaque`,
`.btn-ouro`, `.btn-neutro`, `.campo`, `.rotulo`, `.rotulo-mini`. Todas as páginas e
componentes (`Dashboard`, `HistoricoTable`, `UploadZone`, `Toast`, `EmpresaForm`,
`Historico`, `Empresas`, `NotasPreview`) foram migrados do tema neutro/cinza original
para esta paleta.

---

## 7. Estado atual da infraestrutura de produção

- `docker-compose.prod.yml`: sem portas publicadas no host; apenas o `frontend` é
  ponto de entrada, roteado pelo proxy do Coolify via `SERVICE_FQDN_FRONTEND_80`.
- Backend roda como usuário não-root (`notas`, uid 1000), com healthcheck e
  `--proxy-headers --forwarded-allow-ips '*'` para que o IP real do cliente chegue ao
  rate limiting e ao `audit_log`.
- Documentação de API (`/docs`, `/redoc`, `/openapi.json`) desabilitada quando
  `ENVIRONMENT=production`.
- Nginx com rate limiting (`api_zone` 60r/min, `upload_zone` 10r/min), `client_max_body_size
  110M`, headers de segurança centralizados em `nginx/security-headers.conf`, cache
  agressivo em `/assets/` (hash no nome) e `no-store` em `index.html`.
- Alembic está nas dependências mas **ainda não há migrations escritas** — alterações
  de schema em produção hoje exigem `ALTER TABLE` manual (documentado em `DEPLOY.md`).
- Guia completo de deploy em [`DEPLOY.md`](../DEPLOY.md), incluindo aviso de segurança
  proeminente sobre a ausência de autenticação.

---

## 8. Pendências em aberto

1. **Bloqueador atual**: resolver o erro 403 de push para
   `ndmg-dev/GERADOR_DE_NOTAS` — depende do usuário adicionar `monteiro-lab` como
   colaborador, ou trocar a credencial local do Git por uma com acesso de escrita a
   esse repositório. Assim que resolvido, retomar com `git push -u origin main`.
2. Escrever as migrations do Alembic (mencionado como possível próximo passo, não
   solicitado formalmente pelo usuário).
3. Confirmar se o layout de navegação lateral do dashboard de referência ("FiscalMatch")
   deveria substituir a barra superior atual — só a paleta de cores foi pedida até
   agora, não a estrutura de navegação.
4. Adicionar o logo real da Mendonça Galvão como asset, caso o usuário forneça.

Nenhum desses itens 2–4 foi solicitado explicitamente pelo usuário — são apenas
observações registradas para referência futura, não devem ser executados sem pedido
explícito.
