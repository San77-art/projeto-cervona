// ========================================
// modules/key-vault.bicep
// ========================================
// Cria Key Vault seguro com RBAC e soft-delete ativado

param location string
param projectName string
param environment string
param tags object

var keyVaultName = '${projectName}-kv-${environment}'

// ========================================
// Key Vault Resource
// ========================================

resource keyVault 'Microsoft.KeyVault/vaults@2021-06-01-preview' = {
  name: keyVaultName
  location: location
  tags: tags
  
  properties: {
    // LGPD: Tenant ID da empresa
    tenantId: subscription().tenantId
    
    // Tiers: standard, premium (HSM)
    sku: {
      family: 'A'
      name: environment == 'prod' ? 'premium' : 'standard'
    }
    
    // ========================================
    // Segurança
    // ========================================
    
    // RBAC Mode (recomendado vs access policies deprecated)
    enableRbacAuthorization: true
    
    // Soft-delete: permite recuperação de 90 dias após delete
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    
    // Purge protection: impede hard-delete
    enablePurgeProtection: environment == 'prod' ? true : false
    
    // Network: firewall ativo por padrão
    networkAcls: {
      defaultAction: 'Deny'  // IMPORTANTE: nega por padrão
      bypass: 'AzureServices'  // Permite Azure services (App Insights, etc.)
    }
    
    // Access policies: NÃO usar (usar RBAC em seu lugar)
    accessPolicies: []
  }
}

// ========================================
// Outputs
// ========================================

output keyVaultId string = keyVault.id
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
