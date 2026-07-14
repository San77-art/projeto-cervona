# Deployment

**Última atualização:** 2026-07-14

A infraestrutura ativa e mantida deste projeto é **Terraform + AWS** (`infra/terraform/`). O Bicep/Azure (`infra/main.bicep`, `infra/modules/`, `infra/README.md`) reflete a decisão de arquitetura original (`docs/01-decisoes-arquitetura.md`) e **não está em uso** — não faça deploy a partir dele sem antes confirmar com o time que a direção mudou de volta para Azure.

---

## 1. Imagem Docker

`Dockerfile` faz build multi-stage (compila dependências com `gcc`/`libpq-dev`, depois copia só o necessário para a imagem final baseada em `python:3.11-slim`).

```bash
docker build -t cernova-api .

docker run --rm -p 8000:8000 --env-file .env cernova-api
```

O `CMD` da imagem é `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`. O healthcheck embutido bate em `GET /api/v1/health`.

`docker-compose.yml` neste repo sobe **apenas** Postgres + pgAdmin + Redis — ele não inclui um serviço para a API. Para testar a imagem junto com o Postgres do compose, rode a API separadamente apontando `DATABASE_URL` para `localhost:5432`, ou adicione um serviço `api` ao compose se for útil para o seu fluxo.

## 2. Infraestrutura AWS (Terraform) — caminho atual

`infra/terraform/main.tf` provisiona:

| Recurso | Detalhe |
|---|---|
| EC2 (`aws_instance.app`) | Amazon Linux 2023, tipo configurável (`var.instance_type`, default `t3.small`), na VPC/subnet default da conta |
| RDS Postgres (`aws_db_instance.app`) | `postgres` 16.3, `db.t3.micro` por padrão, `publicly_accessible = false`, storage criptografado, backup retention 7 dias, `deletion_protection` ligado automaticamente se `environment == "production"` |
| S3 (`aws_s3_bucket.app`) | Versionado, criptografia SSE-S3 (AES256), bloqueio total de acesso público |
| Secrets Manager | Dois secrets: `{prefix}/db-credentials` (usuário/senha/host/porta/dbname do RDS, gerado automaticamente) e `{prefix}/app-secrets` (`anthropic_api_key`, `jwt_secret_key`, passados por você) |
| Security Groups | `app` (SSH restrito a `var.allowed_ssh_cidr`, 8000 e 443 abertos); `db` (5432 só a partir do SG `app`) |
| IAM | Role/instance profile da EC2 com permissão só para ler os dois secrets acima e ler/gravar no bucket S3 do projeto |

### 2.1 Pré-requisitos

- Terraform >= 1.5
- Credenciais AWS configuradas (`aws configure` ou variáveis `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`)
- Um key pair EC2 já existente na região de destino (`var.key_name`)
- Seu IP público, para restringir SSH (`var.allowed_ssh_cidr`, ex.: `203.0.113.4/32`)

### 2.2 Configurar variáveis

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edite `aws_region`, `project_name`, `environment`, `allowed_ssh_cidr`, `key_name` conforme necessário. **Não** coloque `anthropic_api_key` nem `jwt_secret_key` no `terraform.tfvars` — passe por variável de ambiente, que não fica gravada em nenhum arquivo do repo:

```bash
export TF_VAR_anthropic_api_key="sk-ant-..."
export TF_VAR_jwt_secret_key="$(openssl rand -base64 48)"
```

`*.tfvars`, `*.tfstate` e `.terraform/` já estão no `.gitignore` — confirme com `git status` que nada disso aparece como novo arquivo antes de commitar.

### 2.3 Deploy

```bash
terraform init
terraform plan
terraform apply
```

Outputs relevantes: `ec2_public_ip`, `ec2_instance_id`, `rds_endpoint`, `s3_bucket_name`, `secrets_manager_arn`, `app_secrets_manager_arn`.

### 2.4 O que o `user_data` da EC2 faz — e o que NÃO faz

O script de bootstrap embutido em `aws_instance.app.user_data` (main.tf, linhas ~315-334):

1. Atualiza pacotes e instala `python3.11`, `git`, `jq`.
2. Busca os dois secrets do Secrets Manager e monta `/etc/cernova-app.env` com as variáveis da app (incluindo `DATABASE_URL` já montada a partir das credenciais do RDS).

Ele **não** clona o repositório, não instala `requirements.txt`, não faz `docker build`/`docker run`, e não inicia a API como serviço (`systemd`, etc.). Depois de `terraform apply`, a instância está pronta com `/etc/cernova-app.env` populado, mas **o deploy da aplicação em si ainda é manual**: você precisa entrar na instância (SSH), trazer o código (git clone ou `scp` da imagem Docker), instalar dependências e subir a API — ou estender o `user_data`/adicionar um pipeline de CI/CD que faça isso. Trate isso como a próxima peça em aberto, não como algo já automatizado.

### 2.5 Destruir

```bash
terraform destroy
```

Em `environment = "production"`, `deletion_protection` do RDS bloqueia a destruição até você desligar essa proteção manualmente (via console/CLI ou mudando `environment` e reaplicando antes de destruir).

## 3. Infraestrutura Azure (Bicep) — legado, não usado

`infra/main.bicep` + `infra/modules/*.bicep` implementam o plano original: Key Vault, PostgreSQL Flexible Server, Storage Account, Managed Identity, Application Insights, RBAC, Budget. Instruções completas em `infra/README.md`. Mantido no repositório por histórico; não há pipeline nem instância ativa rodando a partir dele hoje.

## 4. CI/CD

`.github/workflows/ci.yml` existe e roda lint/type-check/testes no push — não há workflow de deploy (`deploy.yml` mencionado no README original não existe). Deploy para AWS é manual pelos passos acima até que isso mude.

## 5. Checklist antes de apontar produção para dados reais

- [ ] `terraform.tfvars` **não** commitado (`git status` limpo)
- [ ] `ANTHROPIC_API_KEY` e `jwt_secret_key` passados via `TF_VAR_*`, não hardcoded
- [ ] `allowed_ssh_cidr` restrito ao seu IP, não `0.0.0.0/0`
- [ ] Deploy da aplicação na EC2 automatizado ou documentado passo a passo pela pessoa que o fizer manualmente (ver 2.4)
- [ ] `environment = "production"` no `.tfvars` antes do apply final, para ativar `deletion_protection` do RDS
- [ ] Rotina de backup/teste de restore do RDS validada (retention está em 7 dias por padrão)
