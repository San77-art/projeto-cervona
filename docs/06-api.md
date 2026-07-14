# API — Referência de Endpoints

**Última atualização:** 2026-07-14
**Base URL local:** `http://localhost:8000`
**Swagger/OpenAPI interativo:** `http://localhost:8000/docs` (ReDoc em `/redoc`, spec crua em `/openapi.json`)

Todos os endpoints de negócio ficam sob o prefixo `/api/v1`. Os endpoints de `/xml` e `/extracted`/`/dashboard` exigem um JWT (`Authorization: Bearer <token>`), obtido em `POST /api/v1/auth/login`. `/health*`, `/ready` e `/auth/login` não exigem token. Não há tabela de usuários — autenticação é contra um único usuário admin configurado via `.env` (ver seção "Autenticação" abaixo e `docs/07-arquitetura.md`).

---

## `GET /`

Informação básica da API. Não tem prefixo `/api/v1`.

```json
{
  "title": "E-Cernova Livro Caixa Rural",
  "version": "0.1.0",
  "environment": "development",
  "docs": "/docs"
}
```

## `GET /api/v1/health`

Health check simples, sempre `healthy` se o processo está de pé.

```json
{
  "status": "healthy",
  "timestamp": "2026-07-14T12:00:00.000000",
  "environment": "development",
  "version": "0.1.0"
}
```

## `GET /api/v1/health/deep`

Pensado para checar dependências (banco, Key Vault, Anthropic, storage), mas as checagens ainda não estão implementadas — sempre retorna `"unknown"` para todos os itens. Não trate como sinal real de saúde de dependências ainda.

```json
{
  "status": "checking",
  "timestamp": "2026-07-14T12:00:00.000000",
  "checks": {
    "api": "ok",
    "database": "unknown",
    "key_vault": "unknown",
    "anthropic": "unknown",
    "storage": "unknown"
  }
}
```

## `GET /api/v1/ready`

Probe de prontidão estilo Kubernetes. Sempre `{"ready": true}` — não valida nada de fato.

---

## Autenticação

### `POST /api/v1/auth/login`

Não exige token. Corpo `application/x-www-form-urlencoded` (padrão OAuth2 password flow — os mesmos campos que o botão "Authorize" do Swagger UI em `/docs` já usa), não JSON.

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin" -d "password=sua-senha"
```

**Resposta 200:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**401** se o usuário/senha não baterem com `ADMIN_USERNAME`/`ADMIN_PASSWORD_HASH`, ou se `ADMIN_PASSWORD_HASH` não estiver configurado no `.env` (login sempre falha nesse caso — não há fallback).

O token expira em `JWT_EXPIRATION_HOURS` horas (padrão 24). Não há endpoint de refresh — depois de expirar, faça login de novo.

Use o token nas chamadas protegidas:

```bash
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." http://localhost:8000/api/v1/xml
```

No Swagger UI (`/docs`), clique em **Authorize** e informe usuário/senha — ele chama `/auth/login` e injeta o token automaticamente nas chamadas seguintes.

---

## `POST /api/v1/xml/upload` 🔒

Requer `Authorization: Bearer <token>`. Envia um XML de NFe para processamento. `multipart/form-data`, campo `file`.

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -F "file=@nota.xml" http://localhost:8000/api/v1/xml/upload
```

O que acontece internamente (detalhado em `docs/07-arquitetura.md`, seção 3):
1. Valida que o nome do arquivo termina em `.xml` (400 se não).
2. Cria o `XMLDocument` com status `pending`.
3. Roda o parser determinístico (`src/sefaz/parser.py`) para NCM/CFOP/CST.
4. Chama o Claude para extrair quantidade, valores e confiança.
5. Persiste os itens e marca o documento como `processed` ou `failed`.

**Resposta 200:**

```json
{
  "filename": "nota.xml",
  "size": 4821,
  "status": "processed",
  "id": "3f9a2b1c-...-uuid"
}
```

`status` pode vir `failed` mesmo com HTTP 200 — a falha de extração do Claude não vira erro HTTP, só marca o documento. Cheque o campo `status` na resposta, não apenas o código HTTP.

**Erros:**
- `400` — arquivo não termina em `.xml`.
- `500` — exceção não tratada durante upload/parsing/persistência (detalhe da exceção vai no corpo, o que é aceitável em dev mas vale revisar antes de expor em produção — pode vazar detalhes internos).

## `GET /api/v1/xml/{xml_id}` 🔒

Metadados de um XML enviado.

```json
{
  "id": "3f9a2b1c-...-uuid",
  "filename": "nota.xml",
  "uploaded_at": "2026-07-14T12:00:00Z",
  "status": "processed"
}
```

`404` se `xml_id` não existir.

## `GET /api/v1/xml?skip=0&limit=10` 🔒

Lista paginada dos XMLs enviados, mais recentes primeiro. `skip`/`limit` são inteiros opcionais (padrão `skip=0`, `limit=10`).

```json
{
  "total": 42,
  "items": [
    {
      "id": "3f9a2b1c-...-uuid",
      "filename": "nota.xml",
      "uploaded_at": "2026-07-14T12:00:00Z",
      "status": "processed"
    }
  ]
}
```

---

## `GET /api/v1/extracted/{xml_id}` 🔒

Itens extraídos (NCM/CFOP/CST/quantidade/valor) de um XML específico, mais a confiança geral atribuída pelo Claude.

```json
{
  "xml_id": "3f9a2b1c-...-uuid",
  "items": [
    {
      "ncm": "12345678",
      "cfop": "5102",
      "cst": "00",
      "quantity": 10.0,
      "value": 1000.0
    }
  ],
  "confidence_score": 0.95
}
```

`404` se `xml_id` não existir.

## `GET /api/v1/dashboard` 🔒

Resumo agregado de todos os XMLs processados até agora — usado pelo frontend para os cartões de estatística.

```json
{
  "total_xmls": 42,
  "processed": 38,
  "pending": 1,
  "failed": 3,
  "avg_confidence": 0.9123
}
```

`avg_confidence` é a média de `confidence_score` entre todos os documentos (não só os processados); vem `0.0` se nenhum documento tiver confiança registrada.

---

## Formato de erro padrão

Qualquer `HTTPException` levantada é serializada pelo handler global (`src/api/main.py`):

```json
{
  "error": "mensagem do detail",
  "status_code": 404
}
```

## O que não existe ainda (não assuma que está implementado)

- Múltiplos usuários / tabela de usuários — um único login admin via `.env`, sem registro, sem troca de senha, sem Entra ID.
- Refresh token / logout / revogação — o JWT é válido até expirar (`JWT_EXPIRATION_HOURS`); não há como invalidar um token antes disso.
- Rate limiting — `RATE_LIMIT_ENABLED` existe em `settings.py` mas não é lido em lugar nenhum.
- Endpoints de admin (`src/api/routes/admin.py` do plano original não existe).
- Upload para armazenamento externo (S3/Blob) — o conteúdo do XML é lido em memória e descartado após o parsing; não fica persistido em disco nem em object storage.
