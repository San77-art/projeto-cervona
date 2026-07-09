// ========================================
// modules/storage.bicep
// ========================================
// Cria Storage Account com segurança

param location string
param projectName string
param environment string
param tags object

// Storage name sem hífens (requisito Azure)
var storageName = '${projectName}storage${environment}'

resource storageAccount 'Microsoft.Storage/storageAccounts@2021-06-01' = {
  name: storageName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: environment == 'prod' ? 'Standard_GRS' : 'Standard_LRS'
  }
  
  properties: {
    // Segurança
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    
    // Acesso: APENAS Managed Identity
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    
    // Network
    networkAcls: {
      defaultAction: environment == 'prod' ? 'Deny' : 'Allow'
      bypass: 'AzureServices'
    }
  }
}

// Container para armazenar XMLs brutos
resource xmlAcervoContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2021-06-01' = {
  name: '${storageAccount.name}/default/xml-acervo'
  properties: {
    publicAccess: 'None'  // Privado
  }
}

output storageAccountId string = storageAccount.id
output storageAccountName string = storageAccount.name
output containerName string = 'xml-acervo'
