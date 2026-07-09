using './main.bicep'

// ========================================
// Parâmetros para Deploy
// ========================================
// Use este arquivo para configurar valores por ambiente
// Alternativa: passar via CLI com --parameters

param environment = 'dev'
param location = 'brazilsouth'  // OBRIGATÓRIO: LGPD compliance
param projectName = 'livcx'

// ⚠️ SEGURANÇA: NUNCA coloque password aqui
// Passe via CLI: az deployment group create ... --parameters postgresAdminPassword="$PG_PWD"
// param postgresAdminPassword = 'XXXXXXXXXXXXXXXXXXX'  // NUNCA!

// Budget threshold (R$ brasileiros)
param budgetAlertThreshold = 500  // dev: R$500/semana

// ========================================
// Notas por Ambiente
// ========================================
/*
DEV (este arquivo):
  - Region: brazilsouth
  - Tier DB: B1ms (burstable, barato)
  - Budget: R$ 500/semana
  - Backup: diário, 7 dias retenção
  - Geo-redundancy: LRS (local only)
  - Private Endpoints: Não (simplificado para dev)

STAGING (usar staging.bicepparam):
  - Region: brazilsouth
  - Tier DB: B2s (mid-tier)
  - Budget: R$ 2000/semana
  - Backup: diário, 14 dias retenção
  - Geo-redundancy: GRS (geo-redundant)
  - Private Endpoints: Sim

PRODUCTION (usar prod.bicepparam):
  - Region: brazilsouth
  - Tier DB: D2s (production, escalável)
  - Budget: R$ 5000+/semana
  - Backup: horário, PITR 35 dias
  - Geo-redundancy: GRS + ZRS
  - Private Endpoints: Sim, obrigatório
  - HA: Sim (múltiplas AZs)
*/
