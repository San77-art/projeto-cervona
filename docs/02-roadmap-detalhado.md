# Roadmap Detalhado — E-Cernova Livro Caixa Rural

**Versão:** 1.0  
**Última atualização:** 2026-07-09  
**Timeline total estimado:** 8-12 semanas

---

## 📅 Visão Geral (Gantt)

```
Fase 0 (Setup Local)        [████████] Semana 1 (AGORA)
  ├─ Fase 1 (Fundação Azure) [████████████] Semana 2-3 (quando tiver acesso)
  │
  ├─ Fase 2 (Captura SEFAZ)  [████████████████] Semana 4-6
  ├─ Fase 3 (Agent IA)       [████████████████] Semana 4-6 (paralelo)
  │
  ├─ Fase 4 (API Completa)   [████████████] Semana 7-8
  ├─ Fase 5 (Frontend)       [████████████████] Semana 8-10 (paralelo)
  │
  └─ Fase 6 (Prod + Harden)  [████████████] Semana 11-12
```

---

## 🔴 Fase 0: Setup Local (Semana 1 — AGORA)

### Objetivo
Estrutura completa pronta para rodar offline. Quando Azure chegar, é só colar e executar.

### Tasks

- [x] Criar estrutura de pastas + README
- [x] Criar IaC Bicep modular
- [ ] **CLI de deploy** (`deploy.sh`, `validate.sh`)
- [ ] **FastAPI boilerplate** rodando local
- [ ] **Parser XML** funcional (mock + exemplo real)
- [ ] **Testes unitários** cobrindo 50%+ do código
- [ ] **Docker Compose** (PostgreSQL + Redis) funcional
- [ ] **GitHub CI/CD** setup (Actions)
- [ ] **Documentação** pronta
- [ ] **Variáveis de ambiente** configuradas

### Dependências
Nenhuma — tudo offline.

### Entregáveis
- Repo GitHub privado com estrutura completa
- Código local rodando com `python src/api/main.py`
- Testes passando com `pytest tests/`
- IaC Bicep validado com `az bicep build`

### Owner
**Você** + Claude (código)

### Esforço
**3-5 dias** se dedicado 4-6h/dia  
**1-2 semanas** se ~2h/dia

---

## 🟠 Fase 1: Fundação Segura no Azure (Semana 2-3)

### Pré-requisitos
- ✅ Fase 0 completa
- ✅ Acesso Azure (Contributor no RG)
- ✅ Azure CLI instalado local

### Objetivo
Infraestrutura segura no Azure, pronta para dados reais.

### Tasks (na ordem)

1. **Budget + Alerta** (~30min)
   - [ ] Criar budget na subscription
   - [ ] Alerta em R$ 500 / semana (dev)
   - [ ] Notificação → email

2. **Resource Group** (~10min)
   - [ ] `az group create -n rg-livcx-dev -l brazilsouth`
   - [ ] Aplicar tags (projeto, produto, plataforma, ambiente, gestao)

3. **Key Vault** (~30min)
   - [ ] `./deploy.sh --resource key-vault --env dev`
   - [ ] Modo RBAC ativado
   - [ ] Soft-delete ativado
   - [ ] Firewall restringido

4. **PostgreSQL Flexible** (~1h)
   - [ ] `./deploy.sh --resource postgresql --env dev`
   - [ ] Tier: Burstable B1ms
   - [ ] Sem firewall público
   - [ ] Banco `junior` criado
   - [ ] Senha admin → Key Vault

5. **Storage Account** (~30min)
   - [ ] `./deploy.sh --resource storage --env dev`
   - [ ] `allowBlobPublicAccess=false`
   - [ ] `allowSharedKeyAccess=false`
   - [ ] TLS1.2 enforced
   - [ ] Versionamento ligado
   - [ ] Container `xml-acervo` criado

6. **Managed Identity** (~20min)
   - [ ] `./deploy.sh --resource identity --env dev`
   - [ ] 3 role assignments:
     - Key Vault Secrets User
     - Key Vault Certificates User
     - Storage Blob Data Contributor

7. **Application Insights + Log Analytics** (~30min)
   - [ ] `./deploy.sh --resource monitoring --env dev`
   - [ ] Log Analytics workspace criado
   - [ ] App Insights conectado

8. **Validação & Testes** (~1h)
   - [ ] `az deployment group what-if` sem erros
   - [ ] Nenhum segredo em outputs
   - [ ] Health check: Managed Identity lê segredo de teste
   - [ ] Checklist do documento encaminhado ✅

### Checklist de Aceite
- [ ] Resource Group existe em `brazilsouth`
- [ ] Key Vault vazio, RBAC ativo, soft-delete ligado
- [ ] PostgreSQL rodando, banco `junior` criado, sem firewall público
- [ ] Storage privado, sem acesso público, container existe
- [ ] Managed Identity com 3 roles corretos
- [ ] App Insights + Log Analytics coletando dados
- [ ] Budget + alerta funcionando
- [ ] Nenhum segredo vazado

### Entregáveis
- Documentação: `docs/04-operacao-azure.md` atualizado
- Scripts: `infra/deploy.sh --cleanup` (teardown)
- Senha PostgreSQL no Key Vault (não no código)

### Owner
**TI** (com scripts que você prepara)

### Esforço
**2-3 horas** de execução manual  
**1 dia** de troubleshooting (se houver)

---

## 🟡 Fase 2: Captura SEFAZ (Semana 4-6)

### Pré-requisitos
- ✅ Fase 0 + 1 completas
- ✅ Documentação SEFAZ obtida
- ✅ NSU de teste disponível

### Objetivo
Buscar XMLs da SEFAZ automaticamente, armazenar em Blob Storage.

### Tasks

1. **Mock SEFAZ** (~1 dia)
   - [ ] `src/sefaz/mock.py` simula respostas SEFAZ
   - [ ] Mock retorna NFe/NFCe realistas
   - [ ] Tratamento de erro (timeout, não autorizado, etc.)
   - [ ] Testes: `tests/unit/test_sefaz_mock.py`

2. **Parser XML** (~2 dias)
   - [ ] `src/sefaz/parser.py` extrai dados relevantes
   - [ ] Suporte NFe (Nota Fiscal Eletrônica)
   - [ ] Suporte NFCe (Nota Fiscal ao Consumidor)
   - [ ] Extrai: CNPJ emitente, produtos, valores, impostos
   - [ ] Validação XSD (estrutura XML)
   - [ ] Testes: `tests/unit/test_xml_parser.py` com XMLs reais anônimizados

3. **Cliente SEFAZ Real** (~2 dias)
   - [ ] `src/sefaz/client.py` integra API real
   - [ ] Autenticação com certificado A1 (Key Vault)
   - [ ] Protocolo: Query (NSU) + Manifestação (Ciência)
   - [ ] Retry automático (exponential backoff): 3x em 5min
   - [ ] Timeout: 30s por requisição
   - [ ] Testes: `tests/integration/test_sefaz_client.py` (mock)

4. **Upload para Blob Storage** (~1 dia)
   - [ ] `src/utils/storage.py` grava XMLs brutos
   - [ ] Estrutura: `xml-acervo/{cnpj}/{data}/{nsu}.xml`
   - [ ] Managed Identity → sem chaves expostas
   - [ ] Versionamento automático
   - [ ] Testes: `tests/integration/test_blob_upload.py`

5. **Job Scheduler** (~1 dia)
   - [ ] Container Apps Job (ou Function Timer)
   - [ ] Executa 4x por dia (a cada 6h)
   - [ ] Lê lista de clientes ativos
   - [ ] Para cada cliente: query SEFAZ
   - [ ] Grava blocos de XMLs
   - [ ] Logs estruturados → Log Analytics

6. **Retry & Error Handling** (~1 dia)
   - [ ] Falha SEFAZ → retry automático
   - [ ] NSU duplicado → skip silencioso
   - [ ] Certificado expirado → alerta (não falha)
   - [ ] Storage indisponível → fila local + retry
   - [ ] Testes: `tests/integration/test_retry_logic.py`

7. **Logging & Auditoria** (~1 dia)
   - [ ] Cada requisição SEFAZ logada (quem, quando, resultado)
   - [ ] Cada upload logado (tamanho, hash)
   - [ ] Nenhum conteúdo sensível nos logs
   - [ ] Application Insights recebe estruturado

### Entregáveis
- `src/sefaz/` pronto para produção
- `src/utils/storage.py` testado
- Documentação: `docs/06-captura-sefaz-runbook.md`
- CI/CD estendido para testes de integração

### Owner
**Você** + Claude

### Esforço
**8-10 dias** dedicados  
**3-4 semanas** se part-time

---

## 🟡 Fase 3: Agent IA para Extração (Semana 4-6 — paralelo com Fase 2)

### Pré-requisitos
- ✅ Fase 0 + 1 completas
- ✅ Chave Anthropic API disponível
- ✅ Exemplos de XMLs com dados extraídos manualmente

### Objetivo
Claude extrai NCM, CFOP, CST de XMLs automaticamente e com qualidade.

### Tasks

1. **Setup Anthropic SDK** (~2h)
   - [ ] `pip install anthropic`
   - [ ] Chave API em Key Vault (ou .env local)
   - [ ] `src/agent/client.py` inicializa Claude
   - [ ] Testes de conexão

2. **Prompt Engineering** (~3 dias)
   - [ ] Versão 1: Extração básica (lista produtos)
   - [ ] Versão 2: Extração + validação (NCM válido? CFOP correto?)
   - [ ] Versão 3: Extração + contexto (é revenda? é importado?)
   - [ ] Few-shot examples (3-5 exemplos real-world)
   - [ ] Testes: `tests/unit/test_prompts.py`

3. **Extractor Agent** (~2 dias)
   - [ ] `src/agent/extractor.py` orquestra Claude
   - [ ] Input: XML bruto (ou parsed)
   - [ ] Output: Lista estruturada {ncm, cfop, cst, quantidade, valor}
   - [ ] Error handling: se Claude não conseguir extrair → fallback
   - [ ] Retry: 1-2x se confidence < 70%
   - [ ] Testes: `tests/unit/test_extractor.py`

4. **Validadores** (~2 dias)
   - [ ] `src/agent/validators.py` valida saída Claude
   - [ ] NCM: existe? tem 8 dígitos?
   - [ ] CFOP: válido para operação? (revenda, devolução, etc.)
   - [ ] CST (ICMS): válido para regime? (simples, normal, etc.)
   - [ ] Quantidade: > 0?
   - [ ] Valor: > 0?
   - [ ] Flagging baixa confiança para revisão humana

5. **Integração com XML** (~1 dia)
   - [ ] Pipeline: XML → Parse → Claude extrai → Valida → Salva DB
   - [ ] Testes end-to-end: `tests/integration/test_extraction_flow.py`

6. **Quality Metrics** (~1 dia)
   - [ ] Medir taxa de acerto (comparar com manual)
   - [ ] Medir confiança média (score Claude)
   - [ ] Logging: sucesso/erro → Application Insights
   - [ ] Dashboard opcional: % extraído corretamente

7. **Cost Optimization** (~1 dia)
   - [ ] Usar Claude 3.5 Haiku para casos simples?
   - [ ] Batch requests para reduzir latência?
   - [ ] Cache de prompts (reduce tokens)?
   - [ ] Custo estimado: R$ 0,01-0,05 por XML

### Entregáveis
- `src/agent/` pronto
- Prompt otimizado (versão final em `src/agent/prompts.py`)
- Testes de qualidade: 80%+ acurácia em dataset de teste
- Documentação: `docs/06-agent-ia-prompts.md`

### Owner
**Você** + Claude

### Esforço
**8-10 dias** dedicados  
**3-4 semanas** se part-time

---

## 🟢 Fase 4: API Completa (Semana 7-8)

### Pré-requisitos
- ✅ Fases 0-3 completas
- ✅ PostgreSQL com schema definido

### Objetivo
API expõe endpoints para clientes consumirem dados extraídos.

### Tasks

1. **Database Schema** (~1 dia)
   - [ ] Tabelas: `clients`, `xml_uploads`, `extracted_items`, `audit_logs`
   - [ ] Migrations Alembic pronto
   - [ ] Índices para performance
   - [ ] Testes: `tests/integration/test_db_schema.py`

2. **CRUD Endpoints** (~2 dias)
   ```
   POST   /api/v1/xml/upload          (enviar XML)
   GET    /api/v1/xml/{id}            (info XML)
   GET    /api/v1/extracted/{xml_id}  (dados extraídos)
   GET    /api/v1/dashboard           (resumo cliente)
   ```

3. **Autenticação** (~2 dias)
   - [ ] Entra ID integrado
   - [ ] JWT tokens (para frontend)
   - [ ] Rate limiting: 100 req/min por cliente
   - [ ] Testes de autenticação

4. **Validação & Error Handling** (~1 dia)
   - [ ] Input validation (Pydantic)
   - [ ] Erros estruturados (400, 401, 403, 500)
   - [ ] Error logging (não expor internals)

5. **Testes End-to-End** (~2 dias)
   - [ ] `tests/integration/test_api_e2e.py`
   - [ ] Cenários: upload, extraction, retrieve, filter
   - [ ] Coverage > 70%

6. **Documentação OpenAPI** (~1 dia)
   - [ ] Auto-documentada by FastAPI
   - [ ] Schemas Pydantic claros
   - [ ] Exemplos de request/response
   - [ ] Publicar em `/docs` (Swagger)

### Entregáveis
- API rodando em http://localhost:8000
- `/docs` Swagger completo
- Testes passando
- Documentação: `docs/05-api-endpoints.md`

### Owner
**Você** + Claude

### Esforço
**5-7 dias**

---

## 🟢 Fase 5: Frontend (Semana 8-10 — paralelo com Fase 4)

### Pré-requisitos
- ✅ API endpoints estáveis (Fase 4 em progresso)
- ✅ Decisão: React / Vue / Next?

### Objetivo
Interface web para clientes visualizarem XMLs processados.

### Tarefas Principais
- [ ] Setup: React + TypeScript + Vite
- [ ] Dashboard: resumo de XMLs por cliente
- [ ] Upload: arrastar XML, validar, enviar
- [ ] Histórico: lista de XMLs com status
- [ ] Detalhes: visualizar extração (NCM, CFOP, etc.)
- [ ] Autenticação: login com Entra ID
- [ ] Responsivo: mobile-friendly

### Não entra nesta fase
- Edição de dados extraídos
- Relatórios avançados
- Integração com contabilidade

### Entregáveis
- SPA funcionando em http://localhost:3000
- Conecta à API local
- Testes: 40%+ coverage

### Owner
Você (se frontend skill) ou contratar

### Esforço
**7-10 dias** se experiência com React

---

## 🔴 Fase 6: Endurecimento & Produção (Semana 11-12)

### Pré-requisitos
- ✅ Todas fases anteriores completas e testadas
- ✅ Dados de cliente real aprovados

### Objetivo
Pronto para produção com segurança, monitoring, backups.

### Tasks

1. **Private Endpoints** (~1 dia)
   - [ ] PostgreSQL: remover firewall público
   - [ ] Storage: remover acesso público
   - [ ] App: acessar via VNet
   - [ ] Testes de connectivity

2. **Alertas Avançados** (~1 dia)
   - [ ] CPU > 80% → Alerta
   - [ ] Erro rate > 5% → Page on-call
   - [ ] Certificado expira em 30 dias → Email
   - [ ] Quota de storage > 80% → Email

3. **Backups & PITR** (~1 dia)
   - [ ] PostgreSQL: backup horário, PITR 14 dias
   - [ ] Storage: versionamento com retenção
   - [ ] Plano de recuperação documentado
   - [ ] Teste de restore (1x/mês)

4. **Load Testing** (~2 dias)
   - [ ] Simular 100 clientes simultâneos
   - [ ] Simular 1000 XMLs/dia
   - [ ] Encontrar gargalos (CPU? DB? API?)
   - [ ] Escalar recursos conforme necessário

5. **Escalabilidade Horizontal** (~1 dia)
   - [ ] Container Apps: múltiplas instâncias
   - [ ] Database: conexion pooling
   - [ ] Cache: Redis para queries frequentes
   - [ ] CDN: não relevante ainda

6. **IaC Versionado** (~1 dia)
   - [ ] Tag no Git: release-v1.0.0
   - [ ] Documentar manual de rollback
   - [ ] Validação `what-if` pré-deploy

7. **Documentação Final** (~2 dias)
   - [ ] Runbook de operação (24/7)
   - [ ] Playbook de incidentes
   - [ ] Guia de escalabilidade
   - [ ] Checklist de segurança

8. **Compliance & Auditoria** (~1 dia)
   - [ ] Verificar LGPD (dados em Brasil? auditoria? retenção?)
   - [ ] Certificação de segurança (se aplicável)
   - [ ] Assinatura de Termo de Autorização (Fase A final)

### Entregáveis
- Infraestrutura pronta para produção
- Documentação operacional completa
- Backups testados
- Alertas funcionando
- Aprovação de segurança

### Owner
**TI** (com suporte técnico)

### Esforço
**5-7 dias**

---

## 🎯 Marcos (Milestones)

| Data | Milestone | Critério de Sucesso |
|---|---|---|
| Fim Semana 1 | ✅ Fase 0 pronta | Código local rodando, testes passando |
| Fim Semana 3 | ✅ Azure Foundation | Checklist aceite assinado |
| Fim Semana 6 | ✅ Captura + IA | XMLs sendo processados, 80%+ qualidade |
| Fim Semana 8 | ✅ API Pronta | Dashboard web mostrando dados |
| Fim Semana 12 | 🚀 **Em Produção** | Clientes usando, alertas monitorando |

---

## 🚨 Riscos & Mitigações

| Risco | Impacto | Probabilidade | Mitigação |
|---|---|---|---|
| Acesso Azure atrasado | Bloqueia Fase 1 | Alta | Preparar tudo offline (já fazendo) |
| API SEFAZ instável | Captura falha | Média | Implementar retry robusto + mock |
| Claude impreciso em certas NFes | Dados ruins | Média | Fine-tuning de prompts + validação humana |
| PostgreSQL lento | Latência API | Baixa | Índices + caching + monitoring |
| Certificado A1 expirado | Captura SEFAZ falha | Média | Alerta 30 dias antes + auto-renewal |
| Mudança de escopo mid-project | Timeline estourada | Média | Freezing de escopo agora + change control |

---

## 📊 Estimativa de Custo (Azure)

### Desenvolvimento (Dev)
```
Budget/mês: R$ 500
- PostgreSQL B1ms: R$ 150
- Storage (100 GB): R$ 50
- Container Apps: R$ 200
- App Insights: R$ 100
```

### Produção (Estimado)
```
Budget/mês: R$ 5.000+
- PostgreSQL D2s (escalável): R$ 2.000
- Storage (redundância): R$ 500
- Container Apps (HA): R$ 1.500
- App Insights + Log Analytics: R$ 800
- Transferência de dados: R$ 200
```

---

## 📝 Próximas Ações

**Imediato (hoje):**
1. [ ] Revisar estrutura / feedback
2. [ ] Começar a preencher `src/api/main.py`
3. [ ] Começar parser XML (`src/sefaz/parser.py`)

**Próxima semana:**
1. [ ] API boilerplate rodando
2. [ ] Docker compose testado
3. [ ] Primeiros testes passando
4. [ ] GitHub Actions CI/CD setup

**Quando acesso Azure chegar:**
1. [ ] Executar `infra/deploy.sh`
2. [ ] Validar com `validate.sh`
3. [ ] Ajustar variáveis de ambiente
4. [ ] Testar conexão end-to-end

---

**Versão:** 1.0  
**Última revisão:** 2026-07-09  
**Próxima revisão:** Fim Fase 0 (Semana 1)
