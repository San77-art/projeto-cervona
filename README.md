# 📚 E-Cernova Livro Caixa Rural — Estrutura Completa

**Projeto:** Automação de captura e processamento de XMLs fiscais (SEFAZ) com IA para extração de dados estruturados (NCM, CFOP, CST).

**Status:** 🟡 Desenvolvimento — Fase A (Fundação) pronta para Azure  
**Tech Stack:** Python 3.11 + FastAPI + PostgreSQL + Azure + Claude (Anthropic)  
**Região:** `brazilsouth` (LGPD compliance)

---

## 🗂️ Estrutura do Projeto

```
projeto-cernova-completo/
│
├── README.md (você está aqui)
├── .gitignore
├── .env.example (variáveis de ambiente)
│
├── docs/
│   ├── 01-decisoes-arquitetura.md ← Decisões confirmadas
│   ├── 02-roadmap-detalhado.md ← Fases e timeline
│   ├── 03-seguranca-lgpd.md ← Compliance
│   ├── 04-operacao-azure.md ← Runbook para TI
│   ├── 05-api-endpoints.md ← Documentação API
│   ├── 06-agent-ia-prompts.md ← Engenharia de prompts
│   └── 07-troubleshooting.md ← Problemas comuns
│
├── infra/ (IaC — Bicep para Azure)
│   ├── main.bicep ← Orquestrador principal
│   ├── main.bicepparam ← Parâmetros (dev/staging/prod)
│   ├── deploy.sh ← Script automático de deploy
│   ├── validate.sh ← Validação pré-deploy
│   ├── modules/
│   │   ├── resource-group.bicep
│   │   ├── key-vault.bicep
│   │   ├── postgresql.bicep
│   │   ├── storage.bicep
│   │   ├── managed-identity.bicep
│   │   ├── app-insights.bicep
│   │   ├── budget.bicep
│   │   └── rbac.bicep
│   └── README.md ← Como usar IaC
│
├── src/ (Código da aplicação)
│   ├── api/
│   │   ├── main.py ← FastAPI app
│   │   ├── routes/
│   │   │   ├── health.py ← Health check
│   │   │   ├── xml_capture.py ← Captura SEFAZ
│   │   │   ├── extraction.py ← Extração com IA
│   │   │   └── admin.py ← Operações
│   │   └── middleware/
│   │       ├── auth.py ← Autenticação Entra ID
│   │       └── logging.py ← Audit trail
│   │
│   ├── agent/
│   │   ├── extractor.py ← Agent de extração
│   │   ├── prompts.py ← Prompts otimizados
│   │   ├── validators.py ← Validação de dados
│   │   └── models.py ← NCM, CFOP, CST
│   │
│   ├── sefaz/
│   │   ├── client.py ← Cliente SEFAZ real
│   │   ├── mock.py ← Mock para testes locais
│   │   ├── parser.py ← XML parsing
│   │   └── models.py ← Estruturas SEFAZ
│   │
│   ├── models/
│   │   ├── database.py ← SQLAlchemy ORM
│   │   ├── schemas.py ← Pydantic schemas
│   │   └── enums.py ← Enumerações
│   │
│   ├── config/
│   │   ├── settings.py ← Configuração centralizada
│   │   ├── logging.py ← Setup de logging
│   │   └── database.py ← Conexão PostgreSQL
│   │
│   └── utils/
│       ├── keyvault.py ← Integração Key Vault
│       ├── storage.py ← Integração Blob Storage
│       └── retry.py ← Retry logic
│
├── tests/
│   ├── conftest.py ← Pytest fixtures
│   ├── unit/
│   │   ├── test_sefaz_parser.py
│   │   ├── test_agent_extractor.py
│   │   └── test_api_routes.py
│   ├── integration/
│   │   ├── test_xml_flow.py
│   │   └── test_database.py
│   └── data/
│       ├── sample-nfe.xml ← XML de exemplo
│       └── sample-nfce.xml
│
├── .github/workflows/
│   ├── ci.yml ← Testes + linting
│   └── deploy.yml ← Deploy automático
│
├── docker-compose.yml ← Local PostgreSQL + Redis (opcional)
├── Dockerfile ← Para Azure Container Apps
├── requirements.txt ← Dependências Python
└── pyproject.toml ← Metadados do projeto
```

---

## 🚀 Quickstart (5 minutos)

### 1️⃣ Clone e setup

```bash
git clone https://github.com/seu-usuario/projeto-cernova-completo.git
cd projeto-cernova-completo

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

### 2️⃣ Variáveis de ambiente

```bash
cp .env.example .env
# Editar .env com seus valores (deixar Azure em branco por enquanto)
```

### 3️⃣ Subir PostgreSQL local (Docker)

```bash
docker-compose up -d
# PostgreSQL estará em localhost:5432
```

### 4️⃣ Rodar a API

```bash
cd src
python -m api.main
# API em http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 5️⃣ Rodar testes

```bash
pytest tests/ -v
```

---

## 📋 Roadmap Detalhado

### **Fase 0 — AGORA (Estrutura Local)** ✅
- [x] Estrutura de projeto criada
- [x] IaC Bicep modular pronta
- [ ] API boilerplate rodando local
- [ ] Parser XML funcional
- [ ] Testes cobrindo casos principais

**Tempo estimado:** 3-5 dias  
**Você faz:** Revisar estrutura, feedback, começar a completar código

---

### **Fase 1 — Fundação Azure** (Quando tiver acesso)
- [ ] Deploy `infra/` no Azure
- [ ] Key Vault + PostgreSQL + Storage criados
- [ ] Managed Identity configurada
- [ ] CLI `deploy.sh` funciona automaticamente
- [ ] Validação com `what-if` OK

**Tempo estimado:** 2-3 dias  
**Quem faz:** TI (usando scripts que você prepara)

---

### **Fase 2 — Captura SEFAZ** 
- [ ] Integração real com API SEFAZ (DFe)
- [ ] NSU e tratamento de retentativas
- [ ] Upload para Blob Storage
- [ ] Logging e auditoria

**Tempo estimado:** 5-7 dias

---

### **Fase 3 — Agent IA (Claude)**
- [ ] Extração de NCM, CFOP, CST
- [ ] Validação de dados extraídos
- [ ] Fine-tuning de prompts
- [ ] Tratamento de erros

**Tempo estimado:** 5-7 dias

---

### **Fase 4 — API Completa**
- [ ] CRUD para XMLs processados
- [ ] Endpoints de relatórios
- [ ] Autenticação Entra ID
- [ ] Rate limiting + quotas

**Tempo estimado:** 5-7 dias

---

### **Fase 5 — Portal Web (Frontend)**
- [ ] Dashboard com React
- [ ] Upload de XMLs
- [ ] Visualização de dados extraídos
- [ ] Alertas e notificações

**Tempo estimado:** 7-10 dias

---

### **Fase 6 — Endurecimento (Prod)**
- [ ] Private Endpoints no Azure
- [ ] Alertas e monitoring avançado
- [ ] Backup + disaster recovery
- [ ] Testes de carga
- [ ] Documentação operacional final

**Tempo estimado:** 5-7 dias

---

## 🔧 Comandos Úteis

### Desenvolvimento Local

```bash
# Formato code (black)
black src/ tests/

# Linting (flake8)
flake8 src/ tests/

# Type checking (mypy)
mypy src/

# Testes
pytest tests/ -v --cov=src

# Testes de integração (com DB real)
pytest tests/integration/ -v -s
```

### Infraestrutura (Azure)

```bash
# Validar Bicep sintaxe
cd infra
az bicep build -f main.bicep

# Validação pre-deploy
./validate.sh

# Deploy automatizado
./deploy.sh --environment dev

# Cleanup (remover recursos)
./deploy.sh --cleanup --environment dev
```

### Git / CI-CD

```bash
# Branches: main (prod) | staging | develop (feature branches)
git checkout -b feature/sua-feature develop
git push origin feature/sua-feature
# → Cria PR → Tests rodam automaticamente → Merge quando OK

# Trigger deploy no staging
git tag -a staging-v1.0.0 -m "Deploy para staging"
git push origin staging-v1.0.0
```

---

## 📊 Decisões Confirmadas

| Aspecto | Decisão | Justificativa |
|---|---|---|
| **Linguagem API** | Python + FastAPI | Rápido de prototipar, excelente com async, ótimo para IA |
| **Modelo IA** | Anthropic Claude | API robusta, context windows maiores, melhor para documentos |
| **IaC** | Bicep | Nativo Azure, mais legível que Terraform, suporta modularização |
| **Banco de dados** | PostgreSQL Flexible | Compatível com Azure, JSONB para XMLs, sem vendor lock-in |
| **Storage** | Azure Blob Storage | LGPD, controle de acesso, versionamento, redundância configurável |
| **Autenticação** | Entra ID (Microsoft) | Integração nativa Azure, SSO para clientes B2B |
| **Container** | Azure Container Apps | Mais barato que App Service, ideal para APIs serverless |
| **Observabilidade** | App Insights + Log Analytics | Nativo Azure, integrado com alertas, caro mas poderoso |
| **Versionamento** | GitHub | Integração com Actions, fácil de usar, private repos |
| **CI/CD** | GitHub Actions | Sem custo adicional, integrado no GitHub, simples YAML |

---

## 🔐 Segurança & LGPD

- ✅ **Dados em Brasil** (`brazilsouth`) — requisito LGPD
- ✅ **Secrets no Key Vault** — NUNCA em código/env/logs
- ✅ **Managed Identity** — sem senhas, acesso granular RBAC
- ✅ **Storage privado** — sem acesso público, TLS1.2
- ✅ **Audit trail** — todos os acessos logados no Log Analytics
- ✅ **Conformidade** — checklist em `docs/03-seguranca-lgpd.md`

---

## 📞 Support & Troubleshooting

- **Problema com PostgreSQL local?** → Ver `docs/07-troubleshooting.md`
- **Erro ao conectar Azure?** → Verificar `docs/04-operacao-azure.md`
- **Agent IA gerando lixo?** → Ajustar prompts em `src/agent/prompts.py`
- **Testes falhando?** → Rodar `pytest tests/ -v -s` para debug

---

## 📝 Próximos Passos

1. **Leia** `docs/01-decisoes-arquitetura.md` (confirmação de decisões)
2. **Explore** a estrutura localmente (rodar `docker-compose up && python src/api/main.py`)
3. **Feedback** — mande comentários sobre a estrutura
4. **Comece a preencher** `src/api/main.py` e `src/agent/extractor.py`
5. **Quando acesso Azure chegar** → use `infra/deploy.sh` e pronto! 🚀

---

**Autor:** Claude (Anthropic)  
**Data:** 2026-07-09  
**Versão:** 1.0.0-alpha  
**Licença:** Proprietária (Fundação Azure)
