#!/bin/bash

# ========================================
# deploy.sh - Deploy Infrastructure
# ========================================
# Uso: ./deploy.sh [--validate] [--environment dev]

set -e  # Exit on error

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'  # No Color

# Variáveis padrão
ENVIRONMENT="dev"
ACTION="deploy"
LOCATION="brazilsouth"
PROJECT="livcx"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --validate)
      ACTION="validate"
      shift
      ;;
    --environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --cleanup)
      ACTION="cleanup"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

RG_NAME="rg-${PROJECT}-${ENVIRONMENT}"

echo -e "${YELLOW}========================================${NC}"
echo "Deploy Script - E-Cernova Infrastructure"
echo "Environment: $ENVIRONMENT"
echo "Resource Group: $RG_NAME"
echo "Action: $ACTION"
echo -e "${YELLOW}========================================${NC}"

# ========================================
# VALIDATE: Validar Bicep syntax
# ========================================

if [ "$ACTION" = "validate" ] || [ "$ACTION" = "deploy" ]; then
  echo -e "\n${YELLOW}[1/3] Validating Bicep syntax...${NC}"
  if az bicep build -f main.bicep &>/dev/null; then
    echo -e "${GREEN}✓ Bicep validation OK${NC}"
  else
    echo -e "${RED}✗ Bicep validation FAILED${NC}"
    exit 1
  fi
fi

# ========================================
# CREATE: Resource Group
# ========================================

if [ "$ACTION" = "deploy" ]; then
  echo -e "\n${YELLOW}[2/3] Creating Resource Group...${NC}"
  az group create \
    --name "$RG_NAME" \
    --location "$LOCATION" \
    --tags projeto="automacao-livro-caixa-rural" ambiente="$ENVIRONMENT" \
    || true
  echo -e "${GREEN}✓ Resource Group ready${NC}"

  # ========================================
  # WHAT-IF: Dry run
  # ========================================

  echo -e "\n${YELLOW}[3/3] Running what-if validation...${NC}"
  
  # Prompt para senha
  read -sp "PostgreSQL Admin Password: " PG_PASSWORD
  echo ""
  
  if az deployment group what-if \
    --resource-group "$RG_NAME" \
    --template-file main.bicep \
    --parameters main.bicepparam \
    --parameters postgresAdminPassword="$PG_PASSWORD" \
    2>/dev/null | grep -q "No changes"; then
    echo -e "${GREEN}✓ No changes needed (already deployed)${NC}"
  else
    echo -e "${GREEN}✓ Changes would be made:${NC}"
    az deployment group what-if \
      --resource-group "$RG_NAME" \
      --template-file main.bicep \
      --parameters main.bicepparam \
      --parameters postgresAdminPassword="$PG_PASSWORD"
    
    # Prompt para confirmar deploy
    read -p "Continue with deployment? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "Deployment cancelled."
      exit 0
    fi
  fi

  # ========================================
  # DEPLOY: Criar/atualizar recursos
  # ========================================

  echo -e "\n${YELLOW}Starting deployment...${NC}"
  az deployment group create \
    --resource-group "$RG_NAME" \
    --template-file main.bicep \
    --parameters main.bicepparam \
    --parameters postgresAdminPassword="$PG_PASSWORD" \
    --verbose

  echo -e "\n${GREEN}✓ Deployment completed!${NC}"
  echo -e "\n${YELLOW}Next steps:${NC}"
  echo "  1. Verify resources: az resource list -g $RG_NAME"
  echo "  2. Test Key Vault: az keyvault secret show --vault-name ${PROJECT}-kv-${ENVIRONMENT} --name postgres-admin-password"
  echo "  3. Connect to PostgreSQL: psql -h ${PROJECT}-pg-${ENVIRONMENT}.postgres.database.azure.com -U azureuser@${PROJECT}-pg-${ENVIRONMENT} -d junior"
fi

# ========================================
# CLEANUP: Remover recursos
# ========================================

if [ "$ACTION" = "cleanup" ]; then
  echo -e "${RED}WARNING: This will DELETE all resources!${NC}"
  read -p "Type '$RG_NAME' to confirm deletion: " confirmation
  
  if [ "$confirmation" = "$RG_NAME" ]; then
    echo -e "${YELLOW}Deleting Resource Group...${NC}"
    az group delete --name "$RG_NAME" --yes --no-wait
    echo -e "${GREEN}✓ Deletion started (may take a few minutes)${NC}"
  else
    echo "Deletion cancelled."
  fi
fi

echo -e "\n${GREEN}Done!${NC}\n"
