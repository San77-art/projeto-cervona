# Instalação — Ambiente Local

**Última atualização:** 2026-07-14

Guia para rodar a API, o worker de extração e o frontend localmente. Para build de imagem Docker e deploy em nuvem, veja `docs/05-deployment.md`.

---

## 1. Pré-requisitos

| Ferramenta | Versão | Obrigatório? |
|---|---|---|
| Python | 3.11+ | Sim |
| Docker Desktop | qualquer recente | Sim, para o PostgreSQL local (a menos que você já tenha um Postgres rodando em outro lugar) |
| Git | qualquer | Sim |
| Chave de API Anthropic | — | Só para testar o fluxo de extração via Claude; a API sobe e os testes passam sem ela |

## 2. Clonar e criar o ambiente virtual

```bash
git clone <url-do-repo>
cd projeto-cernova-completo

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

## 3. Variáveis de ambiente

```bash
cp .env.example .env
```

Edite `.env`. Para desenvolvimento local, os únicos valores que normalmente precisam mudar são:

- `ANTHROPIC_API_KEY` — necessária para que `POST /api/v1/xml/upload` funcione de ponta a ponta (o upload cria o registro e roda o parser determinístico mesmo sem a chave, mas a chamada ao Claude falha e o documento fica com status `failed`).
- `CLAUDE_MODEL` — o `.env.example` traz `claude-3-5-sonnet-20241022`; o valor padrão em `settings.py` é `claude-sonnet-5`. Ajuste conforme o modelo ao qual sua chave tem acesso.
- `DATABASE_URL` — só mude se não for usar o `docker-compose.yml` deste repo (ele já sobe um Postgres com essas credenciais).

Todas as variáveis `AZURE_*` e `ENTRA_*` existem em `settings.py` mas não são lidas por nenhum código ainda — pode deixá-las em branco.

`ADMIN_PASSWORD_HASH` fica em branco no `.env.example` — sem ela, o login sempre falha com 401. Gere um hash bcrypt e cole em `.env`:

```bash
python -c "from src.api.middleware.auth import hash_password; print(hash_password('sua-senha'))"
```

## 4. Subir o banco local

```bash
docker-compose up -d
```

Isso sobe três serviços:

| Serviço | Porta | Uso |
|---|---|---|
| `postgres` (16-alpine) | `localhost:5432` | banco `cernova_dev`, usuário `cernova` / senha `cernova123` |
| `pgadmin` | `localhost:5050` | UI opcional para inspecionar o banco (login `admin@cernova.local` / `admin123`) |
| `redis` (7-alpine) | `localhost:6379` | provisionado para uso futuro — nenhum código do projeto usa Redis hoje |

Confirme que o Postgres está saudável:

```bash
docker-compose ps
```

## 5. Rodar a API

A partir da **raiz do projeto** (não de dentro de `src/` — os imports são absolutos, `from src.config...`):

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

ou, equivalente:

```bash
python -m src.api.main
```

No startup, `init_db()` cria as tabelas no Postgres automaticamente (não há migrations Alembic para rodar, apesar de `alembic` estar entre as dependências).

Verifique:

- `http://localhost:8000/` — informação básica da API
- `http://localhost:8000/api/v1/health` — health check
- `http://localhost:8000/docs` — Swagger UI (OpenAPI gerado automaticamente pelo FastAPI)

## 6. Rodar o frontend

`frontend/index.html` é um arquivo único (React + Babel carregados via CDN, sem build). Basta abrir no navegador:

```bash
# Windows
start frontend/index.html
# macOS
open frontend/index.html
# ou sirva como estático:
python -m http.server 3000 --directory frontend
```

Ele assume a API em `http://localhost:8000/api/v1` por padrão — esse valor fica editável no topo da página e é salvo em `localStorage`. Requer conexão com a internet mesmo em uso local, pois React/Babel vêm de `unpkg.com`.

## 7. Testar o fluxo de upload manualmente

`/xml/*`, `/extracted/*` e `/dashboard` exigem um token (ver `docs/06-api.md`, seção "Autenticação"):

```bash
curl http://localhost:8000/api/v1/health

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin" -d "password=sua-senha" | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

curl -X POST -H "Authorization: Bearer $TOKEN" \
  -F "file=@tests/data/sample-nfe.xml" \
  http://localhost:8000/api/v1/xml/upload
```

> Se `tests/data/sample-nfe.xml` não existir no seu checkout, use `src/sefaz/mock.py::MockSEFAZClient.mock_nfe()["xml"]` como XML de exemplo, ou qualquer NFe real anonimizada.

## 8. Rodar os testes

```bash
pytest
```

Os testes usam um SQLite in-memory (criado por teste, via `tests/conftest.py`) e um `StubExtractor` no lugar do Claude real — **não precisam** do `docker-compose` rodando nem de uma `ANTHROPIC_API_KEY` válida.

Cobertura HTML é gerada automaticamente (config em `pyproject.toml`, saída em `htmlcov/`).

## 9. Ferramentas de desenvolvimento

```bash
black src/ tests/       # formatação
isort src/ tests/       # ordenação de imports
flake8 src/ tests/      # lint
mypy src/                # type checking
```

## 10. Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `ModuleNotFoundError: No module named 'src'` | Rodando `uvicorn` de dentro de `src/` | Rode da raiz do projeto |
| Upload retorna `status: failed` | `ANTHROPIC_API_KEY` ausente/inválida, ou `CLAUDE_MODEL` incorreto | Confirme `.env`, veja os logs da API |
| `docker-compose up` falha na porta 5432 | Já existe um Postgres local rodando nessa porta | Pare o outro serviço ou mude a porta mapeada no `docker-compose.yml` e em `DATABASE_URL` |
| `POST /auth/login` sempre retorna 401 | `ADMIN_PASSWORD_HASH` vazio/não configurado no `.env` | Gere o hash (passo 3) e reinicie a API |
| Endpoints de `/xml`, `/extracted`, `/dashboard` retornam 401 | Faltou `Authorization: Bearer <token>` ou o token expirou (`JWT_EXPIRATION_HOURS`) | Faça login de novo em `/auth/login` |
| Frontend mostra "Não foi possível conectar à API" | API não está rodando, ou CORS bloqueando | Confirme que a API está em `http://localhost:8000`; em `ENVIRONMENT=development` o CORS já libera `*` |
