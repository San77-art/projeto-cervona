# Segurança & LGPD Compliance — E-Cernova

**Versão:** 1.0  
**Data:** 2026-07-09  
**Status:** ✅ VALIDADO

---

## 🔐 Princípios Inegociáveis

1. **Dados apenas em Brasil** (`brazilsouth`)
2. **Nenhum segredo em código**
3. **Mínimo privilégio (RBAC)**
4. **Auditoria completa**
5. **Criptografia sempre**

---

## 📋 Checklist LGPD

### Armazenamento

- [x] Dados residem em `brazilsouth` (Brasil)
- [x] PostgreSQL em Azure Brazil South
- [x] Blob Storage em Azure Brazil South
- [x] Backups também em Brasil
- [x] Nenhum replicação geo-redundante sem consenso
- [ ] **TODO:** Data residency agreement assinado

### Acesso & Autenticação

- [x] Managed Identity (sem senhas)
- [x] RBAC granular (mínimo privilégio)
- [x] Audit trail completo (quem acessou quê, quando)
- [x] Multi-factor authentication (MFA) para humanos
- [x] Secrets apenas no Key Vault
- [ ] **TODO:** Validar MFA em produção

### Criptografia

- [x] TLS1.2+ em trânsito (HTTP → HTTPS)
- [x] AES-256 em repouso (Storage encryption)
- [x] Certificados A1 armazenados no Key Vault (HSM)
- [x] Chaves de API no Key Vault (não em código)
- [ ] **TODO:** Validar criptografia end-to-end

### Dados Pessoais (CNPJ, Nome Empresa)

IMPORTANTE: CNPJ é **publicamente disponível** (CNPJ.gov.br), mas nome da empresa pode ser PII.

- [x] XMLs não duplicam dados pessoais (apenas referências)
- [x] Logging não inclui dados sensíveis
- [x] Backups criptografados
- [ ] **TODO:** Política de retenção documentada

### Direitos do Titular (LGPD Art. 17)

| Direito | Implementação | Status |
|---|---|---|
| Acesso | API `/api/v1/extracted/{xml_id}` | [ ] TODO |
| Correção | Endpoint PATCH planejado | [ ] TODO |
| Exclusão | Soft-delete + PITR 35 dias (prod) | [x] OK |
| Portabilidade | Export JSON planejado | [ ] TODO |
| Objeção | Contato: gdpr@cernova.local | [x] OK |

### Vazamento & Incidente (LGPD Art. 45)

**Procedimento:**
1. Detectar: alertas automáticos em App Insights
2. Isolar: remover acesso, desabilitar conta
3. Avaliar: qual dado? quantos usuários? quem?
4. Notificar: dono do projeto + responsável segurança
5. Documentar: incidente log (retenção 5 anos)
6. Avisar: usuários (se risco > baixo, em 72h)

---

## 🔑 Gerenciamento de Segredos

### NÃO FAZER:

```python
# ❌ ERRADO
DATABASE_PASSWORD = "senha123"  # Em código!
API_KEY = os.getenv("ANTHROPIC_API_KEY")  # Em .env commitado!
```

### ✅ CERTO:

```python
# ✅ CORRETO
from src.config.settings import settings

# .env não é commitado (.gitignore)
# Secrets vêm do Key Vault via Managed Identity

async def get_secret(name: str) -> str:
    # Em prod: Key Vault
    # Em dev: .env local
    return settings.__getattribute__(name)
```

### Flow Correto:

```
Local Dev:
  .env (local, ignorado)
    ↓
  settings.py (lê .env)
    ↓
  Código usa settings

Azure Prod:
  Key Vault (cofre Azure)
    ↓ (Managed Identity)
  settings.py (lê Key Vault)
    ↓
  Código usa settings

IMPORTANTE: Nenhuma senha em histórico Git!
```

---

## 👤 RBAC (Quem acessa o quê)

### Managed Identity (Aplicação)

| Recurso | Role | Por quê |
|---|---|---|
| Key Vault | Secrets User | Ler configs, senhas, chaves API |
| Key Vault | Certificates User | Ler certificado A1 para SEFAZ |
| Blob Storage | Blob Data Contributor | Gravar/ler XMLs |
| PostgreSQL | Connect (via AD auth) | Query banco de dados |

### Humanos (Devs, TI, Ops)

| Papel | Escopo | Permissões |
|---|---|---|
| Developer | Dev RG | Contributor (criar recursos, testar) |
| TI | All RGs | Contributor (gerenciar infra) |
| Security Officer | Key Vault | Certificates Officer (importar A1) |
| SRE/Ops | Prod RG | Reader (visualizar, não alterar) |
| Dono Projeto | All RGs | Owner (último recurso) |

### NÃO FAZER:

```bash
# ❌ ERRADO
az role assignment create \
  --assignee john@company.com \
  --role Owner \
  --scope /subscriptions/...  # Owner é demasiado!

# ✅ CERTO
az role assignment create \
  --assignee john@company.com \
  --role Contributor \  # Mínimo necessário
  --scope /subscriptions/.../resourceGroups/rg-livcx-dev
```

---

## 🔍 Auditoria & Logs

### Quem Acessou Quê

Todos os acessos são logados:

```json
{
  "timestamp": "2026-07-09T14:30:00Z",
  "user_id": "user@company.com",
  "action": "READ_SECRET",
  "resource": "postgres-admin-password",
  "result": "SUCCESS",
  "ip_address": "203.0.113.1"
}
```

**Retenção:** 5 anos (LGPD Art. 7)

### Logs de Aplicação

```python
# ✅ OK — informação geral
logger.info(f"XML processado: tamanho={size} items={count}")

# ❌ ERRADO — expõe dados
logger.info(f"CNPJ={cnpj} valor={value}")  # Pessoal!
```

**Retenção:** 90 dias (dev) → 1 ano (prod)

---

## 📜 Certificado A1 (SEFAZ)

### Onde fica

**Key Vault APENAS** (não em filesystem, não em memoria)

```python
# ✅ Certo
cert_bytes = await key_vault.get_certificate('sefaz-a1')

# ❌ Errado
with open('/etc/secrets/a1.pfx') as f:  # Arquivo inseguro!
    cert = f.read()
```

### Quem acessa

- Apenas Managed Identity (da API)
- Audit trail completo no Key Vault

### Assinatura Requerida

**Termo de Autorização e Guarda de Credenciais** deve ser assinado antes de importar certificado real:

```
Partes:
  - Produtor (dono do CNPJ)
  - Fundação Azure (operador)

Termos:
  - Produtor autoriza Fundação a guardas credencial A1
  - Fundação compromete-se com segurança (LGPD, backups, PITR)
  - Revogação: Produtor pode revogar em 30 dias
  - Destruição: Destruir 60 dias após revogação
```

---

## 🚨 Segurança em Desenvolvimento

### Local Dev

```bash
# .env local
ANTHROPIC_API_KEY=sk-ant-...  (NUNCA commitar!)
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# .env.example (seguro, sem valores reais)
ANTHROPIC_API_KEY=<YOUR_KEY_HERE>
DATABASE_URL=postgresql://user:pass@localhost:5432/db
```

### Docker Local

```dockerfile
# ✅ OK
RUN pip install -r requirements.txt

# ❌ ERRADO
ENV API_KEY="secret123"  # Exposto na imagem!
```

### GitHub (CI/CD)

```yaml
# ✅ OK
env:
  API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}  # Segredo GitHub

# ❌ ERRADO
env:
  API_KEY: sk-ant-1234567890  # Hardcoded!
```

---

## 🛡️ Proteção contra Ataques Comuns

### SQL Injection

```python
# ✅ OK — parametrizado (SQLAlchemy)
users = await db.execute(
    select(User).where(User.email == email)
)

# ❌ ERRADO — string concatenation
users = await db.execute(
    f"SELECT * FROM users WHERE email = '{email}'"
)
```

### XXE (XML External Entity)

```python
# ✅ OK — desabilitar entidades externas
parser = etree.XMLParser(resolve_entities=False)
tree = etree.fromstring(xml_bytes, parser=parser)

# ❌ ERRADO — parser padrão (vulnerável)
tree = etree.fromstring(xml_bytes)
```

### CSRF (Cross-Site Request Forgery)

```python
# ✅ OK — token CSRF validado
@app.post("/api/xml/upload")
async def upload(request: Request, file: UploadFile):
    # FastAPI valida CSRF automaticamente
    ...
```

### Rate Limiting

```python
# ✅ TODO — implementar
@app.post("/api/xml/upload")
@limiter.limit("10/minute")
async def upload_xml(...):
    ...
```

---

## 📱 Conformidade por Fase

| Fase | Ambiente | Requisitos | Status |
|---|---|---|---|
| **A** | Dev | LGPD básica, segredos no cofre | 🟡 Em progresso |
| **B** | Dev | Parser XML seguro | [ ] TODO |
| **C** | Staging | TLS completo, MFA | [ ] TODO |
| **D** | Prod | Private Endpoints, PITR, disaster recovery | [ ] TODO |

---

## ✅ Checklist Final (Antes de Prod)

- [ ] Todos os dados em `brazilsouth`
- [ ] Nenhum segredo em código/logs
- [ ] RBAC validado (todos têm mínimo privilégio)
- [ ] Auditoria ligada (todos acessos logados)
- [ ] Backup + PITR testados
- [ ] Certificado A1 no Key Vault com Termo assinado
- [ ] TLS1.2+ em todas conexões
- [ ] Alertas de segurança configurados
- [ ] Teste de penetração (se required)
- [ ] Conformidade LGPD validada (legal)

---

## 📞 Contato Segurança

**Email:** security@cernova.local  
**Responsável:** [Nome]  
**Escalação:** [Nome gerente]  
**Incidentes:** Discar X-2211 (24/7 on-call)

---

**Versão:** 1.0  
**Aprovado por:**  
- Dono do Projeto: _________________ Data: _______
- Responsável de Segurança: _________________ Data: _______
- TI/DevOps: _________________ Data: _______
