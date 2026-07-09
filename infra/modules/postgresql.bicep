// ========================================
// modules/postgresql.bicep
// ========================================
// Cria PostgreSQL Flexible Server com segurança LGPD

param location string
param projectName string
param environment string
@secure()
param adminPassword string
param tags object

var postgresqlServerName = '${projectName}-pg-${environment}'
var databaseName = 'junior'  // Nome fixo conforme especificação

// Tier mapping por ambiente
var skuConfig = {
  dev: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  staging: {
    name: 'Standard_B2s'
    tier: 'Burstable'
  }
  prod: {
    name: 'Standard_D2s_v3'
    tier: 'GeneralPurpose'
  }
}

var sku = contains(skuConfig, environment) ? skuConfig[environment] : skuConfig['dev']

// ========================================
// PostgreSQL Flexible Server
// ========================================

resource postgresqlServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: postgresqlServerName
  location: location
  tags: tags
  
  sku: {
    name: sku.name
    tier: sku.tier
  }
  
  properties: {
    // ========================================
    // Administração
    // ========================================
    
    version: '16'
    administratorLogin: 'azureuser'
    administratorLoginPassword: adminPassword
    
    // ========================================
    // Armazenamento
    // ========================================
    
    storage: {
      storageSizeGB: 32  // Inicia com 32GB, auto-scale depois
    }
    
    // ========================================
    // Backup & PITR
    // ========================================
    
    backup: {
      backupRetentionDays: environment == 'prod' ? 35 : (environment == 'staging' ? 14 : 7)
      geoRedundantBackup: environment == 'prod' ? 'Enabled' : 'Disabled'
    }
    
    // ========================================
    // Network Security
    // ========================================
    
    network: {
      delegatedSubnetResourceId: null  // Dev: simples, sem VNet
      privateDnsZoneArmResourceId: null  // Dev: simplificado
    }
    
    // ========================================
    // Segurança
    // ========================================
    
    // SSL enforcement (TLS1.2+)
    sslEnforcement: 'REQUIRE'
    minimalTlsVersion: 'TLSEnforcementEnabled'
    
    // High availability (apenas prod)
    highAvailability: {
      mode: environment == 'prod' ? 'ZoneRedundant' : 'Disabled'
    }
    
    // Maintenance
    maintenanceWindow: {
      customWindow: 'Disabled'
      dayOfWeek: 0  // Domingo
      startHour: 2  // 2am (madrugada)
      startMinute: 0
    }
  }
}

// ========================================
// Database (junior)
// ========================================

resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  name: databaseName
  parent: postgresqlServer
  properties: {
    charset: 'UTF8'
    collation: 'pt_BR.utf-8'  // LGPD: locale Brasil
  }
}

// ========================================
// Firewall Rules
// ========================================

// Dev: permitir azure services (App Insights, etc)
resource allowAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  name: 'AllowAzureServices'
  parent: postgresqlServer
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'  // Azure services
  }
}

// Importante: NÃO adicionar firewall público em prod!
// Private Endpoint será adicionado em Fase D

// ========================================
// Outputs
// ========================================

output serverName string = postgresqlServer.name
output serverFqdn string = postgresqlServer.properties.fullyQualifiedDomainName
output databaseName string = database.name
output administratorLogin string = postgresqlServer.properties.administratorLogin
