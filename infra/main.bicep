// ========================================
// main.bicep - E-Cernova Infrastructure
// ========================================
// Orquestrador que deploy todos os recursos em sequência correta
// Versão: 1.0
// Data: 2026-07-09

targetScope = 'subscription'

@description('Environment name (dev/staging/prod)')
param environment string = 'dev'

@description('Azure region (use brazilsouth for LGPD compliance)')
param location string = 'brazilsouth'

@description('Project name (will be used in resource naming)')
param projectName string = 'livcx'

@description('PostgreSQL Admin Password - PASS VIA CLI, NEVER HARDCODE')
@secure()
param postgresAdminPassword string

@description('Budget alert threshold in BRL')
param budgetAlertThreshold int = 500

// ========================================
// Variables
// ========================================

var resourceGroupName = 'rg-${projectName}-${environment}'
var tags = {
  projeto: 'automacao-livro-caixa-rural'
  produto: 'E-Cernova-Livro-Caixa-Rural'
  plataforma: 'cernova'
  ambiente: environment
  gestao: 'IaC-Bicep'
  dataCriacacao: utcNow('yyyy-MM-dd')
}

// ========================================
// Step 1: Create Resource Group
// ========================================

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// ========================================
// Step 2: Deploy all resources in RG
// ========================================

module keyVault 'modules/key-vault.bicep' = {
  scope: rg
  name: 'deploy-keyvault'
  params: {
    location: location
    projectName: projectName
    environment: environment
    tags: tags
  }
}

module postgresql 'modules/postgresql.bicep' = {
  scope: rg
  name: 'deploy-postgresql'
  params: {
    location: location
    projectName: projectName
    environment: environment
    adminPassword: postgresAdminPassword
    tags: tags
  }
}

module storageAccount 'modules/storage.bicep' = {
  scope: rg
  name: 'deploy-storage'
  params: {
    location: location
    projectName: projectName
    environment: environment
    tags: tags
  }
}

module managedIdentity 'modules/managed-identity.bicep' = {
  scope: rg
  name: 'deploy-identity'
  params: {
    location: location
    projectName: projectName
    environment: environment
    tags: tags
  }
}

module appInsights 'modules/app-insights.bicep' = {
  scope: rg
  name: 'deploy-monitoring'
  params: {
    location: location
    projectName: projectName
    environment: environment
    tags: tags
  }
}

module rbac 'modules/rbac.bicep' = {
  scope: rg
  name: 'deploy-rbac'
  params: {
    keyVaultId: keyVault.outputs.keyVaultId
    keyVaultName: keyVault.outputs.keyVaultName
    managedIdentityPrincipalId: managedIdentity.outputs.principalId
    storageAccountId: storageAccount.outputs.storageAccountId
  }
}

module budget 'modules/budget.bicep' = {
  scope: subscription()
  name: 'deploy-budget'
  params: {
    resourceGroupName: rg.name
    alertThreshold: budgetAlertThreshold
    environment: environment
  }
}

// ========================================
// Store secrets in Key Vault (after deployment)
// ========================================

resource postgresSecretInKeyVault 'Microsoft.KeyVault/vaults/secrets@2021-06-01-preview' = {
  name: '${keyVault.outputs.keyVaultName}/postgres-admin-password'
  properties: {
    value: postgresAdminPassword
  }
}

// ========================================
// Outputs
// ========================================

output resourceGroupName string = rg.name
output resourceGroupId string = rg.id
output keyVaultName string = keyVault.outputs.keyVaultName
output keyVaultId string = keyVault.outputs.keyVaultId
output postgresqlServerName string = postgresql.outputs.serverName
output postgresqlDatabase string = postgresql.outputs.databaseName
output storageAccountName string = storageAccount.outputs.storageAccountName
output managedIdentityId string = managedIdentity.outputs.id
output appInsightsName string = appInsights.outputs.appInsightsName
output appInsightsInstrumentationKey string = appInsights.outputs.instrumentationKey
