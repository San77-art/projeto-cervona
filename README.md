# E-Cernova Livro Caixa Rural

Automação de captura e processamento de XMLs fiscais (NFe) com IA para extração de dados estruturados (NCM, CFOP, CST).

**Tech Stack real:** Python 3.11 + FastAPI + PostgreSQL (SQLAlchemy async) + Claude (Anthropic) + React (arquivo único, sem build) + Terraform/AWS.

> Este README descreve o estado **atual** do código. Os documentos `docs/01-*` e `docs/02-*` registram o plano original (2026-07-09, Azure/Bicep) — parte dele foi implementado de forma diferente do planejado, parte não foi implementada ainda. Veja `docs/07-arquitetura.md` para a lista completa de divergências.

---

## Documentação

| Documento | Conteúdo |
|---|---|
| [`docs/04-instalacao.md`](docs/04-instalacao.md) | Rodar a API, o banco e o frontend localmente |
| [`docs/05-deployment.md`](docs/05-deployment.md) | Build da imagem Docker e deploy em AWS via Terraform |
| [`docs/06-api.md`](docs/06-api.md) | Referência de todos os endpoints |
| [`docs/07-arquitetura.md`](docs/07-arquitetura.md) | Componentes, fluxo de dados, e onde o código diverge do plano original |
| [`docs/01-decisoes-arquitetura.md`](docs/01-decisoes-arquitetura.md) | Plano original (Azure) — histórico |
| [`docs/02-roadmap-detalhado.md`](docs/02-roadmap-detalhado.md) | Roadmap original por fases — histórico |
| [`docs/03-seguranca-lgpd.md`](docs/03-seguranca-lgpd.md) | Checklist de compliance LGPD |
| [`infra/README.md`](infra/README.md) | IaC Bicep/Azure — **legado, não usado** (ver nota abaixo) |

---

## Quickstart

```bash
git clone <url-do-repo>
cd projeto-cernova-completo

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
cp .env.example .env           # edite ANTHROPIC_API_KEY se for testar extração

docker-compose up -d           # PostgreSQL + pgAdmin + Redis

uvicorn src.api.main:app --reload --port 8000
```

- API: `http://localhost:8000` · Swagger: `http://localhost:8000/docs`
- Frontend: abra `frontend/index.html` no navegador (é um arquivo único, sem build)
- Testes: `pytest` (não precisa do Docker rodando — usa SQLite in-memory + stub do Claude)

Guia completo, incluindo troubleshooting: [`docs/04-instalacao.md`](docs/04-instalacao.md).

---

## Estrutura do projeto

```
projeto-cernova-completo/
├── src/
│   ├── api/
│   │   ├── main.py               ← FastAPI app + lifespan/startup
│   │   └── routes/
│   │       ├── health.py         ← /health, /health/deep, /ready
│   │       ├── xml_capture.py    ← upload + persistência
│   │       ├── extraction.py     ← leitura de itens extraídos + dashboard
│   │       └── sefaz.py          ← POST /sefaz/sync (real ou mock, conforme SEFAZ_MODE)
│   ├── agent/
│   │   ├── extractor.py          ← XMLExtractor (Claude)
│   │   └── prompts.py            ← prompts de extração
│   ├── sefaz/
│   │   ├── parser.py             ← parsing determinístico NCM/CFOP/CST (lxml)
│   │   ├── client.py             ← SEFAZClient real (Distribuição de DFe, mTLS + NSU)
│   │   ├── service.py            ← sync_documents(): escolhe real/mock e persiste
│   │   └── mock.py               ← MockSEFAZClient para dev
│   ├── services/
│   │   └── xml_pipeline.py       ← parser + extração Claude, compartilhado entre upload e sync
│   ├── models/
│   │   ├── base.py               ← declarative base SQLAlchemy
│   │   ├── xml_document.py       ← XMLDocument (+ enum XMLStatus)
│   │   ├── extracted_item.py     ← ExtractedItem
│   │   └── sefaz_sync_state.py   ← cursor de NSU da última sincronização
│   └── config/
│       ├── settings.py           ← pydantic-settings
│       ├── database.py           ← engine async + init_db()
│       └── logging.py
│
├── frontend/
│   └── index.html                ← dashboard React (CDN, sem build)
│
├── tests/
│   ├── conftest.py               ← fixtures (SQLite in-memory, stub extractor)
│   └── unit/                     ← toda a suíte de testes vive aqui
│
├── infra/
│   ├── terraform/                ← IaC AWS ativa (EC2 + RDS + S3 + Secrets Manager)
│   └── main.bicep, modules/      ← IaC Azure — legado, não usado
│
├── docs/                         ← ver tabela acima
├── docker-compose.yml            ← Postgres + pgAdmin + Redis locais
├── Dockerfile                    ← build multi-stage da API
└── requirements.txt
```

O que **não** existe apesar de aparecer em documentação antiga ou em `requirements.txt`: `src/api/middleware/` (auth/audit), `src/sefaz/client.py` (SEFAZ real), `src/utils/` (Key Vault, Blob Storage, retry), migrations Alembic, `tests/integration/`. Ver `docs/07-arquitetura.md` para a lista completa.

---

## O que já funciona

- Upload de XML → parsing determinístico (NCM/CFOP/CST) + extração via Claude (quantidade/valores/confiança) → persistência em Postgres.
- Endpoints de consulta (`GET /xml`, `GET /xml/{id}`, `GET /extracted/{id}`, `GET /dashboard`), protegidos por JWT.
- Login (`POST /auth/login`) contra um único usuário admin configurado via `.env` — ver `docs/06-api.md`.
- Frontend funcional para upload e visualização, com modal de login: guarda o JWT em `localStorage`, envia `Authorization: Bearer` em toda chamada, e volta a pedir login se o token expirar ou for revogado (401).
- Testes unitários com banco isolado, Claude mockado e fluxo de auth cobertos (não fazem chamadas reais).
- Deploy em AWS via Terraform (EC2 + RDS + S3 + Secrets Manager), com CI/CD completo: `.github/workflows/ci.yml` roda lint/testes, builda a imagem Docker, publica em ghcr.io e faz deploy na EC2 via SSM a cada push em `main` (ver `docs/05-deployment.md`, seções 2.4 e 4).
- Cliente SEFAZ real (`src/sefaz/client.py`, Distribuição de DFe com mTLS + NSU) além do mock, com `POST /api/v1/sefaz/sync` para disparar a sincronização (real ou mock, conforme `SEFAZ_MODE`).

## O que ainda não existe

- Múltiplos usuários / tabela de usuários, refresh token, logout no servidor (o botão "Sair" do frontend só limpa o token local) ou revogação — um único login admin, token válido até expirar.
- Upload de XML bruto para storage externo (S3/Blob) — hoje o conteúdo é processado em memória e descartado.
- Rate limiting, apesar da configuração existir.
- Sincronização automática/agendada com a SEFAZ — `/sefaz/sync` existe, mas só roda quando chamado (sem scheduler/cron).

---

**Licença:** Proprietária.
