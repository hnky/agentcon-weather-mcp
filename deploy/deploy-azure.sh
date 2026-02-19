#!/usr/bin/env bash
# =============================================================================
# Azure Container Deployment Script for Weather MCP Server
# =============================================================================
#
# Deploys the Weather MCP Server to Azure Container Instances (ACI) via
# Azure Container Registry (ACR). Fully interactive – run with zero arguments.
#
# Prerequisites:
#   - Azure CLI (az) installed and on PATH
#   - Docker installed and daemon running
#   - Active Azure subscription
#
# Usage:
#   ./deploy/deploy-azure.sh
#
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants & Defaults
# ---------------------------------------------------------------------------

readonly DEFAULT_LOCATION="eastus"
readonly DEFAULT_CPU="1.0"
readonly DEFAULT_MEMORY="1.5"
readonly DEFAULT_PORT=8080
readonly IMAGE_NAME="weather-mcp-server"
readonly DEFAULT_CONTAINER_NAME="weather-mcp-aci"

# ---------------------------------------------------------------------------
# Color codes
# ---------------------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

info()    { echo -e "${BLUE}ℹ ${NC} $*"; }
success() { echo -e "${GREEN}✓ ${NC} $*"; }
warn()    { echo -e "${YELLOW}⚠ ${NC} $*"; }
error()   { echo -e "${RED}✗ ${NC} $*" >&2; }
header()  { echo -e "\n${BOLD}${CYAN}$*${NC}"; }
divider() { echo -e "${CYAN}$(printf '=%.0s' {1..60})${NC}"; }

# ---------------------------------------------------------------------------
# Error handler & cleanup guidance
# ---------------------------------------------------------------------------

on_error() {
    local exit_code=$?
    local line_no=$1
    error "Script failed at line ${line_no} with exit code ${exit_code}."
    echo ""
    warn "Current state of resources may be partial. To clean up:"
    echo "  # Delete container instance (if created):"
    echo "  az container delete -g \${RESOURCE_GROUP:-<rg>} -n \${CONTAINER_NAME:-<name>} -y 2>/dev/null"
    echo ""
    echo "  # Delete entire resource group (destroys everything inside):"
    echo "  az group delete -g \${RESOURCE_GROUP:-<rg>} -y 2>/dev/null"
    echo ""
    echo "  Re-run the script after resolving the issue – it is safe to re-run."
    exit "${exit_code}"
}
trap 'on_error ${LINENO}' ERR

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------

check_prerequisites() {
    header "🔍 Checking prerequisites"
    divider

    # Azure CLI
    if ! command -v az &>/dev/null; then
        error "Azure CLI (az) is not installed."
        echo "  Install: https://learn.microsoft.com/cli/azure/install-azure-cli"
        exit 1
    fi
    local az_version
    az_version=$(az version --query '"azure-cli"' -o tsv 2>/dev/null || echo "unknown")
    success "Azure CLI installed (version ${az_version})"

    # Docker
    if ! command -v docker &>/dev/null; then
        error "Docker is not installed."
        echo "  Install: https://docs.docker.com/get-docker/"
        exit 1
    fi
    local docker_version
    docker_version=$(docker --version | awk '{print $3}' | tr -d ',')
    success "Docker installed (version ${docker_version})"

    # Docker daemon
    if ! docker info &>/dev/null; then
        error "Docker daemon is not running."
        echo "  Start Docker Desktop or run: sudo systemctl start docker"
        exit 1
    fi
    success "Docker daemon is running"
}

# ---------------------------------------------------------------------------
# Azure authentication
# ---------------------------------------------------------------------------

check_azure_auth() {
    header "🔐 Checking Azure authentication"
    divider

    if ! az account show &>/dev/null; then
        warn "You are not logged in to Azure."
        echo ""
        info "Run the following command to log in:"
        echo "  az login"
        echo ""
        read -rp "Would you like to log in now? (y/n): " do_login
        if [[ "${do_login}" =~ ^[Yy]$ ]]; then
            az login
        else
            error "Azure authentication is required. Exiting."
            exit 1
        fi
    fi

    local sub_name sub_id
    sub_name=$(az account show --query "name" -o tsv)
    sub_id=$(az account show --query "id" -o tsv)
    success "Authenticated to Azure"
    info "Subscription: ${sub_name} (${sub_id})"

    echo ""
    read -rp "Use this subscription? (y/n) [y]: " confirm_sub
    confirm_sub=${confirm_sub:-y}
    if [[ ! "${confirm_sub}" =~ ^[Yy]$ ]]; then
        echo ""
        info "Available subscriptions:"
        az account list --query "[].{Name:name, Id:id, State:state}" -o table
        echo ""
        read -rp "Enter the subscription ID to use: " new_sub_id
        az account set --subscription "${new_sub_id}"
        success "Switched to subscription: $(az account show --query 'name' -o tsv)"
    fi
}

# ---------------------------------------------------------------------------
# Interactive configuration
# ---------------------------------------------------------------------------

prompt_configuration() {
    header "📝 Configuration"
    divider

    # Resource group
    echo ""
    read -rp "Enter resource group name (e.g., weather-mcp-rg): " RESOURCE_GROUP
    if [[ -z "${RESOURCE_GROUP}" ]]; then
        error "Resource group name cannot be empty."
        exit 1
    fi

    # Container registry (must be alphanumeric, globally unique)
    echo ""
    read -rp "Enter container registry name (e.g., weathermcpreg): " REGISTRY_NAME
    if [[ -z "${REGISTRY_NAME}" ]]; then
        error "Container registry name cannot be empty."
        exit 1
    fi
    # ACR names must be alphanumeric only
    if [[ ! "${REGISTRY_NAME}" =~ ^[a-zA-Z0-9]+$ ]]; then
        error "Registry name must contain only alphanumeric characters (no hyphens or special chars)."
        exit 1
    fi

    # Azure region
    echo ""
    read -rp "Enter Azure region [${DEFAULT_LOCATION}]: " LOCATION
    LOCATION=${LOCATION:-${DEFAULT_LOCATION}}

    # Container instance name
    CONTAINER_NAME="${DEFAULT_CONTAINER_NAME}"

    # Image tag with timestamp
    IMAGE_TAG=$(date +%Y%m%d-%H%M%S)

    # Summary
    echo ""
    header "Configuration Summary"
    divider
    echo "  Resource Group:    ${RESOURCE_GROUP}"
    echo "  Container Registry: ${REGISTRY_NAME}"
    echo "  Location:          ${LOCATION}"
    echo "  Container Name:    ${CONTAINER_NAME}"
    echo "  Image:             ${IMAGE_NAME}:${IMAGE_TAG}"
    echo "  CPU / Memory:      ${DEFAULT_CPU} core(s) / ${DEFAULT_MEMORY} GB"
    echo "  External Port:     ${DEFAULT_PORT}"
    echo ""

    read -rp "Proceed with deployment? (y/n): " proceed
    if [[ ! "${proceed}" =~ ^[Yy]$ ]]; then
        info "Deployment cancelled."
        exit 0
    fi
}

# ---------------------------------------------------------------------------
# Resource group validation / creation
# ---------------------------------------------------------------------------

validate_resource_group() {
    header "🔍 Validating resources"
    divider

    local rg_exists
    rg_exists=$(az group exists --name "${RESOURCE_GROUP}" 2>/dev/null)
    if [[ "${rg_exists}" == "true" ]]; then
        success "Resource group '${RESOURCE_GROUP}' exists"
    else
        warn "Resource group '${RESOURCE_GROUP}' does not exist."
        read -rp "Create it now? (y/n): " create_rg
        if [[ "${create_rg}" =~ ^[Yy]$ ]]; then
            info "Creating resource group '${RESOURCE_GROUP}' in '${LOCATION}'..."
            az group create \
                --name "${RESOURCE_GROUP}" \
                --location "${LOCATION}" \
                --tags project=weather-mcp-server \
                --output none
            success "Resource group '${RESOURCE_GROUP}' created"
        else
            error "Resource group is required. Exiting."
            exit 1
        fi
    fi
}

# ---------------------------------------------------------------------------
# Container registry validation / creation
# ---------------------------------------------------------------------------

validate_container_registry() {
    local acr_exists
    acr_exists=$(az acr show --name "${REGISTRY_NAME}" --query "name" -o tsv 2>/dev/null || echo "")

    if [[ -n "${acr_exists}" ]]; then
        success "Container registry '${REGISTRY_NAME}' exists"
    else
        warn "Container registry '${REGISTRY_NAME}' does not exist."
        read -rp "Create it now? (Basic SKU ≈ \$0.17/day) (y/n): " create_acr
        if [[ "${create_acr}" =~ ^[Yy]$ ]]; then
            info "Creating container registry '${REGISTRY_NAME}' (Basic SKU)..."
            az acr create \
                --resource-group "${RESOURCE_GROUP}" \
                --name "${REGISTRY_NAME}" \
                --sku Basic \
                --admin-enabled true \
                --location "${LOCATION}" \
                --tags project=weather-mcp-server \
                --output none
            success "Container registry '${REGISTRY_NAME}' created"
        else
            error "Container registry is required. Exiting."
            exit 1
        fi
    fi

    # Ensure admin access is enabled (needed for ACI to pull images)
    local admin_enabled
    admin_enabled=$(az acr show --name "${REGISTRY_NAME}" --query "adminUserEnabled" -o tsv 2>/dev/null)
    if [[ "${admin_enabled}" != "true" ]]; then
        info "Enabling admin access on registry..."
        az acr update --name "${REGISTRY_NAME}" --admin-enabled true --output none
        success "Admin access enabled"
    fi
}

# ---------------------------------------------------------------------------
# Docker image build
# ---------------------------------------------------------------------------

build_image() {
    header "🏗️  Building Docker image"
    divider

    local login_server
    login_server=$(az acr show --name "${REGISTRY_NAME}" --query "loginServer" -o tsv)

    # Determine the project root (one level up from deploy/)
    local project_root
    project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

    info "Building ${IMAGE_NAME}:${IMAGE_TAG} ..."
    docker build \
        -t "${IMAGE_NAME}:${IMAGE_TAG}" \
        -t "${IMAGE_NAME}:latest" \
        -t "${login_server}/${IMAGE_NAME}:${IMAGE_TAG}" \
        -t "${login_server}/${IMAGE_NAME}:latest" \
        "${project_root}"

    success "Image built: ${IMAGE_NAME}:${IMAGE_TAG}"
    FULL_IMAGE="${login_server}/${IMAGE_NAME}:${IMAGE_TAG}"
}

# ---------------------------------------------------------------------------
# Push image to ACR
# ---------------------------------------------------------------------------

push_image() {
    header "📤 Pushing to Azure Container Registry"
    divider

    local login_server
    login_server=$(az acr show --name "${REGISTRY_NAME}" --query "loginServer" -o tsv)

    info "Logging in to ACR '${REGISTRY_NAME}'..."
    az acr login --name "${REGISTRY_NAME}" --output none
    success "Authenticated to ACR"

    info "Pushing ${login_server}/${IMAGE_NAME}:${IMAGE_TAG} ..."
    docker push "${login_server}/${IMAGE_NAME}:${IMAGE_TAG}"
    docker push "${login_server}/${IMAGE_NAME}:latest"
    success "Image pushed successfully"

    # Verify
    local digest
    digest=$(az acr repository show-tags --name "${REGISTRY_NAME}" --repository "${IMAGE_NAME}" --query "[?@=='${IMAGE_TAG}']" -o tsv 2>/dev/null || echo "")
    if [[ -n "${digest}" ]]; then
        success "Verified image tag '${IMAGE_TAG}' in registry"
    else
        warn "Could not verify image tag in registry – deployment will continue"
    fi
}

# ---------------------------------------------------------------------------
# Deploy to Azure Container Instances
# ---------------------------------------------------------------------------

deploy_container() {
    header "🚀 Deploying to Azure Container Instances"
    divider

    local login_server acr_username acr_password
    login_server=$(az acr show --name "${REGISTRY_NAME}" --query "loginServer" -o tsv)
    acr_username=$(az acr credential show --name "${REGISTRY_NAME}" --query "username" -o tsv)
    acr_password=$(az acr credential show --name "${REGISTRY_NAME}" --query "passwords[0].value" -o tsv)

    local dns_label="${CONTAINER_NAME}"

    # Delete existing container instance if present (idempotent re-deploy)
    local existing
    existing=$(az container show \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${CONTAINER_NAME}" \
        --query "name" -o tsv 2>/dev/null || echo "")
    if [[ -n "${existing}" ]]; then
        warn "Container instance '${CONTAINER_NAME}' already exists – replacing it."
        az container delete \
            --resource-group "${RESOURCE_GROUP}" \
            --name "${CONTAINER_NAME}" \
            --yes \
            --output none
        success "Existing container deleted"
    fi

    info "Creating container instance '${CONTAINER_NAME}'..."
    az container create \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${CONTAINER_NAME}" \
        --image "${login_server}/${IMAGE_NAME}:${IMAGE_TAG}" \
        --registry-login-server "${login_server}" \
        --registry-username "${acr_username}" \
        --registry-password "${acr_password}" \
        --cpu "${DEFAULT_CPU}" \
        --memory "${DEFAULT_MEMORY}" \
        --ports "${DEFAULT_PORT}" \
        --environment-variables \
            MCP_TRANSPORT=streamable-http \
            MCP_HOST=0.0.0.0 \
            MCP_PORT="${DEFAULT_PORT}" \
        --command-line "python3 -m src.weather_server --transport streamable-http --host 0.0.0.0 --port ${DEFAULT_PORT}" \
        --ip-address public \
        --dns-name-label "${dns_label}" \
        --os-type Linux \
        --restart-policy Always \
        --output none

    # Wait for the container to be in Running state
    info "Waiting for container to start..."
    local state=""
    local retries=0
    while [[ "${state}" != "Running" && ${retries} -lt 30 ]]; do
        state=$(az container show \
            --resource-group "${RESOURCE_GROUP}" \
            --name "${CONTAINER_NAME}" \
            --query "instanceView.state" -o tsv 2>/dev/null || echo "Pending")
        if [[ "${state}" == "Running" ]]; then
            break
        fi
        sleep 5
        retries=$((retries + 1))
    done

    if [[ "${state}" == "Running" ]]; then
        success "Container deployed and running"
    else
        warn "Container state: ${state}. It may still be starting."
        info "Check logs with: az container logs -g ${RESOURCE_GROUP} -n ${CONTAINER_NAME}"
    fi
}

# ---------------------------------------------------------------------------
# Output connection information
# ---------------------------------------------------------------------------

output_results() {
    local ip fqdn
    ip=$(az container show \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${CONTAINER_NAME}" \
        --query "ipAddress.ip" -o tsv 2>/dev/null || echo "N/A")
    fqdn=$(az container show \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${CONTAINER_NAME}" \
        --query "ipAddress.fqdn" -o tsv 2>/dev/null || echo "N/A")

    local base_url
    if [[ "${fqdn}" != "N/A" && -n "${fqdn}" ]]; then
        base_url="http://${fqdn}:${DEFAULT_PORT}"
    else
        base_url="http://${ip}:${DEFAULT_PORT}"
    fi

    echo ""
    header "✅ Deployment Complete!"
    divider
    echo ""
    echo -e "${BOLD}  Deployment Summary${NC}"
    echo "  ──────────────────────────────────────"
    echo "  Resource Group:      ${RESOURCE_GROUP}"
    echo "  Container Registry:  ${REGISTRY_NAME}"
    echo "  Image Tag:           ${IMAGE_TAG}"
    echo "  Container Instance:  ${CONTAINER_NAME}"
    echo "  Public IP:           ${ip}"
    echo "  FQDN:                ${fqdn}"
    echo ""
    echo -e "${BOLD}  🌐 Connection Information${NC}"
    echo "  ╔══════════════════════════════════════════════════════════════════╗"
    echo "  ║  HTTP URL:  ${base_url}/mcp/                                    "
    echo "  ║  SSE  URL:  ${base_url}/sse                                     "
    echo "  ╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    echo -e "${BOLD}  📋 Test your deployment:${NC}"
    echo "  curl ${base_url}/mcp/ -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"initialize\",\"id\":1}'"
    echo ""
    echo -e "${BOLD}  📚 Next steps:${NC}"
    echo "  1. Configure your MCP client with the URLs above"
    echo "  2. Monitor logs:"
    echo "     az container logs -g ${RESOURCE_GROUP} -n ${CONTAINER_NAME}"
    echo "  3. Stream logs:"
    echo "     az container logs -g ${RESOURCE_GROUP} -n ${CONTAINER_NAME} --follow"
    echo "  4. View metrics in Azure Portal"
    echo ""
    echo -e "${BOLD}  🧹 Cleanup:${NC}"
    echo "  # Delete container instance:"
    echo "  az container delete -g ${RESOURCE_GROUP} -n ${CONTAINER_NAME} -y"
    echo ""
    echo "  # Delete entire resource group (destroys everything inside):"
    echo "  az group delete -g ${RESOURCE_GROUP} -y"
    echo ""
    echo -e "  ${YELLOW}💰 Estimated cost: ~\$0.50–1.00 per day (ACI) + ~\$0.17/day (ACR Basic)${NC}"
    echo ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    echo ""
    header "🚀 Azure Container Deployment Script"
    divider
    echo ""

    check_prerequisites
    check_azure_auth
    prompt_configuration
    validate_resource_group
    validate_container_registry
    build_image
    push_image
    deploy_container
    output_results
}

main "$@"
