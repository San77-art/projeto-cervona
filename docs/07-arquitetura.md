# Arquitetura — E-Cernova Livro Caixa Rural

**Última atualização:** 2026-07-14
**Status:** Reflete o código como ele existe hoje na branch `master` (não o plano original — veja a nota de divergência abaixo).

---

## ⚠️ Nota de divergência em relação a `01-decisoes-arquitetura.md`

`docs/01-decisoes-arquitetura.md` e `docs/02-roadmap-detalhado.md` foram escritos em 2026-07-09, no dia da estrutura inicial, e descrevem um plano assumindo **Azure** (Container Apps, Key Vault, PostgreSQL Flexible Server, Blob Storage, Entra ID) com IaC em **Bicep** (`infra/main.bicep` + `infra/modules/`).

Desde então o projeto seguiu um caminho diferente:

- A infraestrutura que efetivamente existe e é mantida é **Terraform para AWS** (`infra/terraform/`): EC2 + RDS Postgres + S3 + Secrets Manager + IAM. Veja `docs/05-deployment.md`.
- O Bicep/Azure (`infra/main.bicep`, `infra/modules/*.bicep`, `infra/README.md`) permanece no repositório mas **não é usado** — trate como legado/histórico até uma decisão explícita de reativá-lo ou removê-lo.
- Autenticação Entra ID, Key Vault, Blob Storage, rate limiting e middleware de auditoria descritos no plano original **não foram implementados**. Não existe `src/api/middleware/`.

Este documento descreve a arquitetura **real**. Onde o plano original diverge de forma relevante, isso é sinalizado.

---

## 1. Visão geral

```
                         ┌─────────────────────────┐
                         │   frontend/index.html    │
                         │  (React via CDN, single  │
                         │   arquivo, sem build)    │
                         └────────────┬─────────────┘
                                      │ fetch() JSON
                                      │ /api/v1/*
                                      ▼
┌───────────────────────────────────────────────────────────────┐
│                         FastAPI (src/api)                       │
│  main.py → routers: health / xml_capture / extraction           │
└───────────┬───────────────────────────────┬─────────────────────┘
            │                               │
            ▼                               ▼
┌────────────────────────┐      ┌────────────────────────────────┐
│  src/sefaz/parser.py     │      │   src/agent/extractor.py         │
│  Parsing determinístico  │      │   Claude (Anthropic) extrai      │
│  de NCM/CFOP/CST via lxml│      │   quantidade, valores, confiança │
└────────────┬────────────┘      └────────────────┬─────────────────┘
             │                                     │
             └───────────────┬─────────────────────┘
                              ▼
                  ┌───────────────────────┐
                  │  SQLAlchemy async ORM  │
                  │  XMLDocument            │
                  │  ExtractedItem          │
                  └───────────┬─────────────┘
                              ▼
                  ┌───────────────────────┐
                  │  PostgreSQL             │
                  │  (docker-compose local  │
                  │   ou RDS em produção)   │
                  └───────────────────────┘
```

## 2. Componentes

### 2.1 API (`src/api/`)

- **`main.py`** — cria a `FastAPI` app, registra CORS, monta os três routers sob o prefixo `/api/v1`, e roda `init_db()` (cria as tabelas via `Base.metadata.create_all`, não há migrations Alembic apesar de `alembic` estar em `requirements.txt`) no lifespan de startup.
- **`routes/health.py`** — `/health`, `/health/deep` (checks ainda não implementados, retorna `"unknown"` para todas as dependências), `/ready`.
- **`routes/xml_capture.py`** — upload de XML, persistência, orquestra parser determinístico + extractor Claude.
- **`routes/extraction.py`** — leitura dos itens extraídos e resumo agregado (`/dashboard`).
- **`routes/auth.py`** — `POST /auth/login`, autentica contra o único usuário admin (`ADMIN_USERNAME`/`ADMIN_PASSWORD_HASH` em `settings.py`) e devolve um JWT.
- **`middleware/auth.py`** — hash/verificação de senha (bcrypt puro, não `passlib` — ver nota abaixo), criação/validação de JWT (`python-jose`), e a dependency `get_current_user` usada para proteger rotas.
- Todas as rotas de `xml_capture.py` e `extraction.py` exigem `Authorization: Bearer <token>` (aplicado via `APIRouter(dependencies=[Depends(get_current_user)])` em cada um dos dois routers). `health.py` e `auth.py` ficam públicos.
- Ainda sem audit trail nem rate limiting, apesar de `RATE_LIMIT_ENABLED` existir em `settings.py` — essa config não é consumida em nenhum lugar do código ainda. Também não há tabela de usuários, refresh token, logout/revogação de token, nem múltiplos papéis — é um único login compartilhado.

> **Nota — passlib evitado de propósito:** a primeira versão desta feature usou `passlib[bcrypt]`, já presente em `requirements.txt`. `passlib` está sem release desde 2020 e sua rotina de autodetecção de backend quebra contra `bcrypt` >= 4.1 (`AttributeError` na leitura de versão, seguido de `ValueError: password cannot be longer than 72 bytes` no autoteste interno do passlib, não relacionado a nenhuma senha real). A correção foi trocar para a API do pacote `bcrypt` diretamente (`bcrypt.hashpw`/`bcrypt.checkpw`) e remover `passlib` de `requirements.txt`.

### 2.2 Extração determinística (`src/sefaz/parser.py`)

`parse_nfe_items()` faz parsing de um XML de NFe com `lxml`, ignorando namespace, e para cada `<det>` extrai `NCM`, `CFOP` e `CST`/`CSOSN` (procurando dentro de qualquer variante de regime ICMS: `ICMS00`, `ICMS60`, `ICMSSN101`, etc.). Esses três campos são estruturados e não ambíguos — não faz sentido pedir para o modelo "adivinhar" um código que já está no XML, então o parser determinístico tem prioridade sobre o que o Claude retornar para esses campos (ver `xml_capture.py`, linhas 62-71: `parsed.get("ncm") or item.get("ncm")`).

### 2.3 Agente de extração (`src/agent/`)

- **`extractor.py`** — `XMLExtractor` envia o XML cru para o Claude (`AsyncAnthropic`) com um prompt de sistema fixo, espera JSON de volta, tolera cercas de código markdown (```json ... ```) na resposta. É instanciado como singleton (`extractor = XMLExtractor()`) e exposto via `get_extractor()` para injeção de dependência — os testes sobrescrevem essa dependência com um `StubExtractor` (`tests/conftest.py`) para não bater na API real do Anthropic.
- **`prompts.py`** — prompt de sistema e template de extração. Pede NCM, CFOP, CST, quantidade, valores, confiança (0-1) e warnings por item.
- Claude é responsável por quantidade, valores e confiança; NCM/CFOP/CST vêm do parser determinístico quando disponível (ver 2.2).
- Modelo configurado: `CLAUDE_MODEL` em `settings.py` (default `"claude-sonnet-5"`; `.env.example` ainda referencia o nome antigo `claude-3-5-sonnet-20241022` — vale alinhar ao configurar um ambiente novo).

### 2.4 SEFAZ (`src/sefaz/`)

- **`mock.py`** — `MockSEFAZClient` simula respostas da SEFAZ (NFe mock, `query_xml`, `manifest`) para desenvolvimento sem certificado A1 nem acesso real à SEFAZ.
- **Não existe `client.py`** (cliente real da SEFAZ com certificado A1, NSU, retentativas) nem `src/utils/keyvault.py`, `src/utils/storage.py`, `src/utils/retry.py`. `SEFAZ_MODE=real` não tem implementação por trás — apenas a variável existe em `settings.py`.

### 2.5 Modelos de dados (`src/models/`)

SQLAlchemy 2.0, engine assíncrono (`asyncpg` para Postgres, `aiosqlite` em testes).

```python
XMLDocument
  id: str (uuid4)
  filename: str
  status: enum (pending | processing | processed | failed)
  confidence_score: float | None
  uploaded_at: datetime
  items: list[ExtractedItem]  (cascade delete)

ExtractedItem
  id: int (autoincrement)
  xml_document_id: FK -> XMLDocument.id
  ncm: str(8)
  cfop: str(4)
  cst: str(3)
  quantity: float
  value: float
```

Não existem as tabelas `clients` ou `audit_logs` mencionadas no roadmap original — só estas duas.

### 2.6 Frontend (`frontend/index.html`)

Um único arquivo HTML: React 18 + Babel standalone carregados via CDN (`unpkg.com`), sem etapa de build, sem `package.json`. Isso significa:

- **Requer internet** para carregar os scripts do CDN, mesmo rodando localmente.
- Aponta para a API via um campo configurável (padrão `http://localhost:8000/api/v1`), persistido em `localStorage`.
- Dashboard com contagem por status, upload por drag-and-drop, tabela de XMLs enviados, drawer lateral com os itens extraídos de um XML selecionado.
- Faz polling da API a cada 15s (`setInterval(refresh, 15000)`), mas só enquanto houver um token — sem login, `refresh()` retorna cedo em vez de bater em endpoints protegidos.
- **Login:** um modal (`LoginModal`) cobre a tela inteira sempre que não há token em `localStorage` (chave `cernova_token`). Ele faz `POST /auth/login` (form-urlencoded) direto contra `apiBase` e guarda o `access_token` retornado.
- **Todas as chamadas passam por `fetchJson()`**, que anexa `Authorization: Bearer <token>` quando há token. Uma resposta `401` limpa o token do estado/`localStorage` e lança um erro marcado (`isAuthError`), o que faz o modal de login reaparecer automaticamente — não existe um endpoint de logout no backend; o botão "Sair" só descarta o token local.

Não há roteamento client-side nem state management além de hooks do React puro.

### 2.7 Configuração (`src/config/`)

- **`settings.py`** — `pydantic-settings`, lê `.env`. Contém muitas variáveis para features Azure/Entra/rate-limiting que não são usadas em código ainda (ver seção 2.1). Trate como "reservadas para quando as features existirem", não como configuração ativa.
- **`database.py`** — engine assíncrono, `get_db()` (dependency injection), `init_db()`.
- **`logging.py`** — setup de logging (JSON ou plaintext via `LOG_FORMAT`).

## 3. Fluxo de dados: upload de um XML

1. Cliente (frontend ou `curl`) envia `POST /api/v1/xml/upload` com o arquivo.
2. API valida extensão `.xml`, cria um `XMLDocument` com status `pending` e salva no banco.
3. `parse_nfe_items()` roda sobre o conteúdo cru — se o XML for inválido, loga um warning e segue com lista vazia (não falha o upload).
4. `XMLExtractor.extract()` chama o Claude com o XML completo.
5. Se o Claude retornar erro (JSON inválido, exceção da API), o documento vira `failed`.
6. Caso contrário, para cada item retornado pelo Claude: NCM/CFOP/CST vêm do parser determinístico quando disponíveis (por índice posicional — assume que a ordem dos `<det>` no XML bate com a ordem dos itens retornados pelo Claude), quantidade/valor vêm do Claude. Documento vira `processed`, com `confidence_score` = confiança geral do Claude.
7. Resposta: `{filename, size, status, id}`.

**Nota de design a observar:** o pareamento entre item do parser e item do Claude é por índice (`parsed_items[index]`), não por chave de negócio. Se o Claude retornar itens em ordem diferente do XML original (juntar/quebrar itens, pular um item ambíguo), o NCM/CFOP/CST atribuído pode ficar desalinhado com a quantidade/valor daquele item.

## 4. Infraestrutura

Ver `docs/05-deployment.md` para o guia operacional completo. Resumo:

| Camada | Local (dev) | Produção (implementado) | Produção (legado, não usado) |
|---|---|---|---|
| Compute | `uvicorn` direto ou Docker | EC2 (`t3.small`, Amazon Linux 2023) | Azure Container Apps (Bicep) |
| Banco | Postgres via `docker-compose` | RDS Postgres (`db.t3.micro`) | Azure PostgreSQL Flexible Server |
| Storage de arquivos | — (XMLs não persistidos em disco/blob) | S3 (bucket privado, versionado, criptografado) | Azure Blob Storage |
| Segredos | `.env` local | AWS Secrets Manager | Azure Key Vault |
| IaC | — | Terraform (`infra/terraform/`) | Bicep (`infra/*.bicep`) |

## 5. Testes

- `pytest` com fixtures em `tests/conftest.py`: banco SQLite in-memory por teste (`sqlite+aiosqlite://`, `StaticPool`), `StubExtractor` no lugar do Claude real via override de `get_extractor`.
- Apenas testes unitários existem (`tests/unit/`); a pasta `tests/integration/` mencionada no README original não existe.
- Cobertura configurada em `pyproject.toml` (`pytest-cov`, relatório HTML) e roda automaticamente via `addopts` do pytest.
