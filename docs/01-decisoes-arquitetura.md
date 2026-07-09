# Decisões de Arquitetura — E-Cernova Livro Caixa Rural

**Data:** 2026-07-09  
**Responsável:** Equipe técnica + Dono do projeto  
**Status:** ✅ CONFIRMADO

---

## 1. Stack Tecnológico

### Backend API

| Decisão | Valor | Justificativa |
|---|---|---|
| Linguagem | Python 3.11+ | Produtividade, ecossistema IA maduro, async nativo |
| Framework | FastAPI | Moderno, rápido, auto-documentação OpenAPI, type hints |
| ASGI Server | Uvicorn | Lightweight, excelente para Azure Container Apps |
| **Alternativas rejeitadas** | Node.js/Express, C#/ASP.NET | Python vence por clareza + IA |

### Database

| Decisão | Valor | Justificativa |
|---|---|---|
| Primary DB | PostgreSQL Flexible (Azure) | ACID, JSONB para XMLs brutos, escalável |
| ORM | SQLAlchemy 2.0 | Type hints, async support, migrations com Alembic |
| Migrations | Alembic | Padrão ouro para SQLAlchemy |
| **Local dev** | Docker PostgreSQL 16 | Mesma versão que prod, setup com `docker-compose` |

### Inteligência Artificial

| Decisão | Valor | Justificativa |
|---|---|---|
| Modelo | Anthropic Claude 3.5 Sonnet | Context window grande (200K), excelente reasoning, melhor custo-benefício |
| SDK | `anthropic` (Python) | Official, bem mantida, async support |
| **Alternativas rejeitadas** | OpenAI, Azure OpenAI | Claude vence em contexto + custo |

---

## 2. Infraestrutura (Azure)

### Compute

| Decisão | Valor | Justificativa |
|---|---|---|
| API Runtime | Azure Container Apps | Serverless, pay-per-use, suporta containers, Dapr integration |
| Captura SEFAZ | Container Apps Jobs | Schedulable, Event-driven, sem servidor ocioso |
| **Alternativas rejeitadas** | App Service (caro), Functions (limites), VMs (overhead) |

### Data & Storage

| Decisão | Valor | Justificativa |
|---|---|---|
| Database | PostgreSQL Flexible Server | Managed, auto-backup, PITR, suporta Private Endpoints |
| Object Storage | Azure Blob Storage | LGPD, versionamento, redundância configurável, acesso via Managed Identity |
| XML Raw | Blob Storage (`xml-acervo` container) | Imutável, auditável, compliance |
| **Alternativas rejeitadas** | Cosmos DB (overkill), Table Storage (sem ACID) |

### Segurança & Identidade

| Decisão | Valor | Justificativa |
|---|---|---|
| Secrets Management | Azure Key Vault | RBAC, auditoria, soft-delete, replicação geo |
| Identidade | Managed Identity (system-assigned) | Sem senhas, RBAC automático, Azure-native |
| Auth Clientes | Entra ID (Microsoft Entra) | SSO B2B, integração Azure, suporta B2C no futuro |
| **Alternativas rejeitadas** | Vault genérico (inseguro), JWT local (sem SSO) |

### Logging & Observabilidade

| Decisão | Valor | Justificativa |
|---|---|---|
| Logs Estruturados | Application Insights + Log Analytics | Nativo Azure, correlação automática, alertas avançados |
| Traces | OpenTelemetry | Padrão aberto, não lock-in, suporta múltiplos backends |
| Métricas | Application Insights | CPU, memória, requisições, latência automáticas |

### Networking

| Decisão | Valor | Justificativa |
|---|---|---|
| **Dev** | Internet aberto (simplificado) | Acelera prototipagem |
| **Prod** | Private Endpoints obrigatório (Fase D) | LGPD, segurança, sem exposição pública |
| VNet | Uma por ambiente (dev/staging/prod) | Isolamento, RBAC de rede |

---

## 3. Infraestrutura como Código (IaC)

| Decisão | Valor | Justificativa |
|---|---|---|
| Language | Bicep | Nativo Azure, mais legível que JSON ARM, suporta módulos |
| Versionamento | Git (GitHub) | Histórico, rollback, code review |
| CI/CD | GitHub Actions | Sem custo extra, YAML simples, integrado |
| **Alternativas rejeitadas** | Terraform (complexo), Manual (risco) |

**Princípios Bicep:**
- Cada recurso em módulo separado (`modules/`)
- Parâmetros centralizados (`main.bicepparam`)
- Script `deploy.sh` + validação `validate.sh`
- Nada hardcoded (tudo parametrizável)

---

## 4. Versionamento & CI/CD

### Git

| Decisão | Valor | Justificativa |
|---|---|---|
| Plataforma | GitHub | Private repos, ótima integração Actions, industry standard |
| Strategy | Git Flow | `main` (prod) ← `staging` ← `develop` ← feature branches |
| Merges | Squash + PR review | Histórico limpo, code review obrigatório |

### Branches

```
main (produção)
├── tags: v1.0.0, v1.0.1 (releases)
│
staging (pré-produção)
├── tags: staging-v1.0.0
│
develop (integração)
├── feature/xml-parser
├── feature/agent-ia
└── feature/api-endpoints
```

### CI/CD Pipeline (GitHub Actions)

**On Push (develop/staging/main):**
- ✅ Lint (black, flake8, isort)
- ✅ Type check (mypy)
- ✅ Unit tests (pytest)
- ✅ Coverage report (codecov)
- ✅ Build Docker image
- 🔄 Deploy (automático se tests passam)

**On Tag:**
- ✅ Build final Docker image
- 📦 Push para Azure Container Registry
- 🚀 Deploy automático ao ambiente correto

---

## 5. Segurança (LGPD & Compliance)

### Princípios Inegociáveis

1. **Dados apenas em Brasil** (`brazilsouth`)
2. **Nenhum segredo em código/logs/output**
3. **Mínimo privilégio (RBAC)** para todo acesso
4. **Auditoria completa** (quem, o quê, quando)
5. **Encryção em trânsito** (TLS1.2+) e repouso (AES-256)

### RBAC (Role-Based Access Control)

| Quem | Papel | Sobre |
|---|---|---|
| Managed Identity (API) | Key Vault Secrets User | Ler senhas/configs |
| Managed Identity (API) | Key Vault Certificates User | Ler certificado A1 |
| Managed Identity (API) | Storage Blob Data Contributor | Ler/gravar XMLs |
| Responsável Segurança | Key Vault Certificates Officer | Importar .pfx |
| TI | Contributor no RG | Gerenciar infra (não Owner) |
| Desenvolvedores | Reader no RG | Ver recursos (não alterar) |

### Secrets Flow

```
Local Dev:
  .env (ignorado no Git)
    ↓
  Config settings.py (lê .env)
    ↓
  Código (usa settings)

Azure Prod:
  Key Vault (cofre)
    ↓ (Managed Identity acessa)
  Código (via @app.get secret)
    ↓
  Nenhum log de secrets!
```

### Certificados A1 (SEFAZ)

- **Armazenamento:** Key Vault apenas
- **Acesso:** Managed Identity + audit trail
- **Importação:** Manual por Responsável de Segurança
- **Assinatura Requerida:** Termo de Autorização e Guarda de Credenciais (Fase 1)

---

## 6. Operação & Manutenção

### Ambientes

| Ambiente | Propósito | Tier DB | Backup | Private Endpoints | Budget |
|---|---|---|---|---|---|
| **dev** | Desenvolvimento local | - (Docker) | Manual | Não | N/A |
| **dev (Azure)** | Testes integrados | B1ms | Diário | Não | R$ 500/mês |
| **staging** | Pré-produção | B2s | Diário | Sim | R$ 2000/mês |
| **production** | Clientes reais | D2s (escalável) | Horário + PITR | Sim | R$ 5000+/mês |

### Monitoramento & Alertas

- CPU/Memória > 80% → Alerta
- Erro rate > 5% → Página on-call
- Latência P95 > 2s → Investigate
- Certificado expira em 30 dias → Lembrança

### Disaster Recovery

- **RTO:** 2 horas (objetivo)
- **RPO:** 1 hora (máx. perda de dados)
- **Backup:** PostgreSQL PITR (14 dias)
- **Failover:** Manual ou automático (definir depois)

---

## 7. Decisões Ainda em Aberto (Confirmar depois)

- [ ] Entra ID com B2C ou somente Entra External ID?
- [ ] PostgreSQL apenas com senha (Key Vault) ou Entra AD auth?
- [ ] Alertas automáticos → SMS/Email/PagerDuty/Slack?
- [ ] Budget alert → notificação ou corte automático?
- [ ] Retenção de XMLs brutos — 6 meses? 1 ano?
- [ ] Redundância de dados — LRS (local) ou GRS (geo)?

---

## 8. Próximas Revisões

- **Fase B (Captura SEFAZ):** Validar integração real com DFe
- **Fase C (API):** Revisar endpoints e autenticação
- **Fase D (Prod):** Confirmar Private Endpoints + alertas
- **Fase E:** Avaliar escalabilidade (load test)

---

**Aprovado por:**
- Dono do projeto: _________________ Data: _______
- TI: _________________ Data: _______
- Segurança: _________________ Data: _______
