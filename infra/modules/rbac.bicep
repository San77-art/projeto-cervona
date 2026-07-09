// ========================================
// modules/rbac.bicep
// ========================================
// Atribui roles à Managed Identity

param keyVaultId string
param keyVaultName string
param managedIdentityPrincipalId string
param storageAccountId string

var keyVaultSecretsUserRole = '4633458b-17de-408a-b874-0445c86300d1'
var keyVaultCertificatesUserRole = 'db79e9a7-68ee-4b58-9aeb-b90e7c24fcba'
var storageBlobDataContributorRole = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

// 1. Key Vault Secrets User
resource secretsUserAssignment 'Microsoft.Authorization/roleAssignments@2020-10-01-preview' = {
  name: guid(keyVaultId, managedIdentityPrincipalId, keyVaultSecretsUserRole)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: '/subscriptions/${subscription().subscriptionId}/providers/Microsoft.Authorization/roleDefinitions/${keyVaultSecretsUserRole}'
    principalId: managedIdentityPrincipalId
  }
}

// 2. Key Vault Certificates User
resource certificatesUserAssignment 'Microsoft.Authorization/roleAssignments@2020-10-01-preview' = {
  name: guid(keyVaultId, managedIdentityPrincipalId, keyVaultCertificatesUserRole)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: '/subscriptions/${subscription().subscriptionId}/providers/Microsoft.Authorization/roleDefinitions/${keyVaultCertificatesUserRole}'
    principalId: managedIdentityPrincipalId
  }
}

// 3. Storage Blob Data Contributor
resource storageBlobAssignment 'Microsoft.Authorization/roleAssignments@2020-10-01-preview' = {
  name: guid(storageAccountId, managedIdentityPrincipalId, storageBlobDataContributorRole)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: '/subscriptions/${subscription().subscriptionId}/providers/Microsoft.Authorization/roleDefinitions/${storageBlobDataContributorRole}'
    principalId: managedIdentityPrincipalId
  }
}

output result string = 'RBAC assignments completed'
