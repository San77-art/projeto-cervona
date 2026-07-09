// ========================================
// modules/managed-identity.bicep
// ========================================

param location string
param projectName string
param environment string
param tags object

var identityName = '${projectName}-identity-${environment}'

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
  tags: tags
}

output id string = managedIdentity.id
output principalId string = managedIdentity.properties.principalId
output clientId string = managedIdentity.properties.clientId
