// ========================================
// modules/budget.bicep
// ========================================

param resourceGroupName string
param alertThreshold int
param environment string

resource budget 'Microsoft.CostManagement/budgets@2021-10-01' = {
  name: 'budget-${environment}'
  properties: {
    category: 'Cost'
    amount: alertThreshold
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: utcNow('yyyy-MM-01')
      endDate: '2099-12-31'
    }
    notifications: {
      notificationByResourceGroupDefault: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        contactEmails: []
      }
    }
  }
}

output budgetName string = budget.name
