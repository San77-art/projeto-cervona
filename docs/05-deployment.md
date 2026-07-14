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

### 2.4 O que o `user_data` da EC2 faz

O script de bootstrap embutido em `aws_instance.app.user_data` (main.tf):

1. Atualiza pacotes e instala `python3.11`, `git`, `jq`, `docker`; habilita e inicia o serviço `docker`.
2. Busca `{prefix}/app-secrets` e `{prefix}/db-credentials` do Secrets Manager e monta `/etc/cernova-app.env` (inclui `DATABASE_URL` já montada a partir das credenciais do RDS) — este arquivo vira o `--env-file` do container da API.
3. Busca `{prefix}/ghcr-credentials` e monta `/etc/cernova-ghcr.env`, separado do arquivo acima de propósito: só o script de deploy usa essas credenciais para `docker login`, a API não deveria ver o PAT do GHCR no seu próprio ambiente.
4. Escreve `/usr/local/bin/cernova-deploy.sh` — o script que o pipeline de CI/CD invoca a cada deploy (ver 4.1): faz `docker login`, `docker pull` da imagem indicada, para/remove o container `cernova-api` anterior, sobe o novo com `--restart unless-stopped`, espera `GET /api/v1/health` responder, e faz `docker image prune` de imagens não usadas há mais de 24h.

A instância registra-se automaticamente no AWS Systems Manager (o agente SSM já vem pré-instalado nas AMIs Amazon Linux 2023; a permissão para isso é a managed policy `AmazonSSMManagedInstanceCore` anexada à role da EC2) — é assim que o GitHub Actions consegue rodar `cernova-deploy.sh` sem precisar de acesso SSH.

### 2.5 Destruir

```bash
terraform destroy
```

Em `environment = "production"`, `deletion_protection` do RDS bloqueia a destruição até você desligar essa proteção manualmente (via console/CLI ou mudando `environment` e reaplicando antes de destruir).

## 3. Infraestrutura Azure (Bicep) — legado, não usado

`infra/main.bicep` + `infra/modules/*.bicep` implementam o plano original: Key Vault, PostgreSQL Flexible Server, Storage Account, Managed Identity, Application Insights, RBAC, Budget. Instruções completas em `infra/README.md`. Mantido no repositório por histórico; não há pipeline nem instância ativa rodando a partir dele hoje.

## 4. CI/CD

`.github/workflows/ci.yml` ("CI/CD Pipeline") tem três jobs:

1. **`test`** — em todo push (`develop`/`staging`/`main`) e PR para `develop`: `flake8`, `black --check`, `mypy`, `pytest` com cobertura, contra um Postgres de serviço.
2. **`docker-build-push`** — só em push para `main` e só se `test` passar. Builda a imagem (`Dockerfile` da raiz) e publica em `ghcr.io/<owner>/<repo>` com duas tags: o SHA do commit e `latest`. Autentica com o `GITHUB_TOKEN` embutido — nenhum segredo novo necessário para este job.
3. **`deploy`** — assume uma role AWS via OIDC (sem chaves de longa duração salvas no GitHub), localiza a instância EC2 pela tag `Name` e dispara `/usr/local/bin/cernova-deploy.sh <imagem>` nela via `aws ssm send-command`, depois espera o resultado e falha o workflow se o comando não terminar com `Success`.

### 4.1 Setup único antes do primeiro deploy automático

1. Aplique o Terraform com as novas variáveis (`github_repository`, `ghcr_username`, `ghcr_pat` — ver `terraform.tfvars.example`). Isso cria, além do que já existia: o secret `{prefix}/ghcr-credentials`, a role `{prefix}-gha-deploy` (assumível só pelo branch `main` do repo indicado em `github_repository`, via OIDC), e anexa `AmazonSSMManagedInstanceCore` à role da EC2.
2. No GitHub, em Settings → Secrets and variables → Actions → **Variables** (não Secrets — nenhum destes é sensível), crie:
   - `AWS_DEPLOY_ROLE_ARN` = saída `github_actions_deploy_role_arn` do Terraform
   - `AWS_REGION` = a mesma região do `aws_region` usado no apply
   - `EC2_NAME_TAG` = saída `ec2_name_tag` do Terraform (por padrão `cernova-production-app`)
3. Gere um GitHub PAT clássico com escopo `read:packages` (usado pela instância EC2 para `docker pull` de `ghcr.io`, não pelo GitHub Actions) e passe-o como `TF_VAR_ghcr_pat` ao aplicar o Terraform — não commite em `terraform.tfvars`.
4. A partir daí, todo push em `main` que passar em `test` builda, publica e faz deploy automaticamente. Para forçar um redeploy sem mudar código, re-rode o job `deploy` do último workflow run pela UI do GitHub.

Este pipeline ainda não foi executado contra a infraestrutura real (requer credenciais AWS e um repositório com Actions habilitado) — a lógica do `user_data`/deploy script foi validada renderizando o heredoc do Terraform e checando a sintaxe do bash resultante (`bash -n`), não rodando de ponta a ponta em uma EC2 de verdade. Valide o primeiro deploy observando os logs do job e `docker logs cernova-api` na instância.

## 5. Checklist antes de apontar produção para dados reais

- [ ] `terraform.tfvars` **não** commitado (`git status` limpo)
- [ ] `ANTHROPIC_API_KEY`, `jwt_secret_key` e `ghcr_pat` passados via `TF_VAR_*`, não hardcoded
- [ ] `allowed_ssh_cidr` restrito ao seu IP, não `0.0.0.0/0`
- [ ] Variáveis do GitHub Actions configuradas (`AWS_DEPLOY_ROLE_ARN`, `AWS_REGION`, `EC2_NAME_TAG` — ver 4.1) e um deploy de teste executado com sucesso
- [ ] `environment = "production"` no `.tfvars` antes do apply final, para ativar `deletion_protection` do RDS
- [ ] Rotina de backup/teste de restore do RDS validada (retention está em 7 dias por padrão)
