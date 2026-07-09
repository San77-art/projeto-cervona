# Infraestrutura como Código (IaC) — Bicep

Todos os recursos Azure estão definidos como código (Infrastructure as Code) usando **Bicep**.

---

## 📋 Estrutura

```
infra/
├── main.bicep           ← Orquestrador principal
├── main.bicepparam      ← Parâmetros (dev)
├── deploy.sh            ← Script automático de deploy
├── validate.sh          ← Validação pré-deploy
├── modules/
│   ├── key-vault.bicep
│   ├── postgresql.bicep
│   ├── storage.bicep
│   ├── managed-identity.bicep
│   ├── app-insights.bicep
│   ├── budget.bicep
│   └── rbac.bicep
└── README.md (este arquivo)
```

---

## 🚀 Quick Start

### 1️⃣ Validar sintaxe Bicep

```bash
az bicep build -f infra/main.bicep
# Sucesso se não houver erros
```

### 2️⃣ Validar antes de deploy (what-if)

```bash
# Gerar variável de ambiente com senha (NUNCA em código!)
export PG_ADMIN_PASSWORD="SuaSenhaSegura123!@#"

az deployment group what-if \
  -g rg-livcx-dev \
  -f infra/main.bicep \
  -p infra/main.bicepparam \
  --parameters postgresAdminPassword="$PG_ADMIN_PASSWORD"
```

### 3️⃣ Deploy (criar recursos)

```bash
az deployment group create \
  -g rg-livcx-dev \
  -f infra/main.bicep \
  -p infra/main.bicepparam \
  --parameters postgresAdminPassword="$PG_ADMIN_PASSWORD"
```

### 4️⃣ Cleanup (remover recursos)

```bash
az group delete -n rg-livcx-dev --yes
```

---

## 🔐 Segurança: Gerenciar Senhas

### ❌ NUNCA faça:

```bash
# ERRADO! Expõe senha em histórico
param postgresAdminPassword = 'MinhaS3nh@'

# ERRADO! Expõe em processo histórico
az deployment group create ... --parameters postgresAdminPassword=MinhaS3nh@
```

### ✅ CORRETO: Use variável de ambiente

```bash
# 1. Gerar senha segura
PASSWORD=$(openssl rand -base64 32)
echo "Salve esta senha em lugar seguro: $PASSWORD"

# 2. Usar via variável de ambiente (não aparece em histórico)
export PG_PASSWORD="$PASSWORD"

# 3. Passar para Bicep
az deployment group create ... --parameters postgresAdminPassword="$PG_PASSWORD"

# 4. Depois que deploy terminar, senha está no Key Vault
# REMOVA a variável de ambiente
unset PG_PASSWORD
```

---

## 📝 Módulos Bicep

Cada recurso é um módulo separado:

### Key Vault (`key-vault.bicep`)
- Modo RBAC ativado
- Soft-delete ativado
- Sem acesso público (firewall)
- Saída: ID, Nome

### PostgreSQL (`postgresql.bicep`)
- Flexible Server (gerenciado, não VM)
- Tier: B1ms (dev) → D2s (prod)
- Banco `junior` criado automaticamente
- Sem acesso público
- Backup: 7-35 dias conforme env
- Saída: Nome servidor, database

### Storage (`storage.bicep`)
- Blob Storage (armazenar XMLs)
- `allowBlobPublicAccess = false` (privado)
- `allowSharedKeyAccess = false` (apenas Managed Identity)
- TLS1.2 enforced
- Versionamento ligado
- Container `xml-acervo` criado
- Saída: Nome storage

### Managed Identity (`managed-identity.bicep`)
- Identity para serviços acessarem recursos sem senha
- Saída: Principal ID (para RBAC)

### Application Insights (`app-insights.bicep`)
- Monitoring + Logging centralizado
- Log Analytics Workspace
- Saída: Chave de instrumentação

### RBAC (`rbac.bicep`)
- 3 role assignments:
  1. Identity → Key Vault Secrets User
  2. Identity → Key Vault Certificates User
  3. Identity → Storage Blob Data Contributor

### Budget (`budget.bicep`)
- Alert de custo na subscription
- Email quando atingir threshold

---

## 🔄 Deploy em Outros Ambientes

### Para Staging:

1. Criar `staging.bicepparam`
```bicepparam
using './main.bicep'

param environment = 'staging'
param location = 'brazilsouth'
param projectName = 'livcx'
param budgetAlertThreshold = 2000
```

2. Deploy:
```bash
az group create -n rg-livcx-staging -l brazilsouth

az deployment group create \
  -g rg-livcx-staging \
  -f infra/main.bicep \
  -p infra/staging.bicepparam \
  --parameters postgresAdminPassword="$STAGING_PG_PASSWORD"
```

### Para Production:

Similar, mas com:
- Tier DB: D2s (escalável)
- Budget: R$ 5000+
- Private Endpoints: Sim
- Geo-redundancy: GRS/ZRS
- PITR: 35 dias

---

## ✅ Checklist de Validação

Depois de deploy, validar:

- [ ] Resource Group `rg-livcx-dev` existe em `brazilsouth`
- [ ] Key Vault criado, modo RBAC, sem secrets ainda
- [ ] PostgreSQL rodando, banco `junior` criado
  ```bash
  PGPASSWORD="$PG_PASSWORD" psql \
    -h livcx-pg-dev.postgres.database.azure.com \
    -U azureuser@livcx-pg-dev \
    -d junior \
    -c "SELECT version();"
  ```
- [ ] Storage criado, container `xml-acervo` existe
- [ ] Managed Identity tem 3 roles atribuídos
- [ ] App Insights coletando dados
- [ ] Budget + alerta funcionando
- [ ] Nenhum segredo em outputs
- [ ] Health check: Identity lê segredo de teste do Key Vault

---

## 🐛 Troubleshooting

### Erro: "Resource group not found"

```bash
# Criar antes de fazer deployment
az group create -n rg-livcx-dev -l brazilsouth
```

### Erro: "Insufficient quota"

Sua subscription pode ter limite baixo. Contate Azure support.

### Erro: "The property allowBlobPublicAccess is not allowed"

Versão antiga do Azure SDK. Atualize:
```bash
az upgrade
```

### PostgreSQL não conecta

```bash
# Validar firewall
az postgres flexible-server firewall-rule list \
  -g rg-livcx-dev \
  -n livcx-pg-dev

# Adicionar IP local (temporário para teste)
az postgres flexible-server firewall-rule create \
  -g rg-livcx-dev \
  -n livcx-pg-dev \
  -r AllowLocalDev \
  --start-ip-address YOUR_LOCAL_IP \
  --end-ip-address YOUR_LOCAL_IP
```

### Key Vault retorna "Access Denied"

Validar RBAC assignments:
```bash
az role assignment list \
  --scope /subscriptions/SUB_ID/resourceGroups/rg-livcx-dev/providers/Microsoft.KeyVault/vaults/livcx-kv-dev
```

---

## 📦 Exportar Template (Backup)

Se precisar ver o template gerado (ARM JSON):

```bash
az bicep build -f infra/main.bicep -o main.json
# Arquivo main.json terá o template ARM equivalente
```

---

## 🔄 Atualizar Recursos

Se precisar alterar algo (ex: aumentar tier PostgreSQL):

```bash
# 1. Editar main.bicep ou módulo
# 2. Validar
az deployment group what-if ...

# 3. Deploy (Azure atualiza apenas o que mudou)
az deployment group create ...
```

---

## 📊 Monitorar Custos

```bash
# Ver atual spend
az billing invoice list --subscription

# Ver por recurso
az resource show -g rg-livcx-dev -n livcx-pg-dev --resource-type Microsoft.DBforPostgreSQL/flexibleServers
```

---

## 🔗 Referências

- [Bicep Docs](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/)
- [Azure Bicep Best Practices](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/best-practices)
- [PostgreSQL Flexible Server](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/)
- [Key Vault Security](https://learn.microsoft.com/en-us/azure/key-vault/general/overview)

---

**Versão:** 1.0  
**Última atualização:** 2026-07-09
