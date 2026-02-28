# Azure Container Deployment Script - Spec-Kit Specification

## Constitution

### I. DevOps Principles
- Deployment scripts must be idempotent and safe to re-run
- All operations must include error handling and rollback capabilities
- User must explicitly confirm destructive operations
- Scripts must validate prerequisites before execution

### II. User Experience Principles
- Interactive prompts must be clear and provide examples
- All operations must provide progress feedback
- Errors must include actionable remediation steps
- Success output must include all relevant connection information

### III. Azure Best Practices
- Use Azure CLI commands exclusively (already installed)
- Follow Azure naming conventions and resource tagging
- Enable monitoring and logging by default
- Use managed identities where possible

### IV. Security Principles
- Never hardcode credentials or secrets
- Validate Azure CLI authentication before operations
- Use Azure Container Registry with authentication
- Output sensitive information only when necessary

### V. Maintainability Principles
- Script must be self-documenting with clear comments
- Support both interactive and non-interactive modes
- Log all operations for troubleshooting
- Make configuration easily adjustable

---

## Feature Specification

### Feature Overview
**Feature Name:** Azure Container Deployment Automation  
**Feature ID:** 002-azure-deployment-script  
**Purpose:** Provide automated deployment of the Weather MCP Server to Azure Container Instances with minimal user input

### User Stories

**US-001: Deploy Container to Azure**  
*As a* developer  
*I want to* run a single script that deploys my container to Azure  
*So that* I can quickly get the MCP server running in the cloud

**Acceptance Criteria:**
- Script runs with zero arguments (fully interactive)
- Prompts for resource group name with validation
- Prompts for container registry name with validation
- Builds and tags the Docker image locally
- Pushes image to Azure Container Registry
- Deploys to Azure Container Instances
- Displays the public URL upon completion
- Completes in under 5 minutes (excluding image build)

**US-002: Handle Azure Authentication**  
*As a* developer  
*I want to* be notified if I'm not logged into Azure  
*So that* I can authenticate before deployment proceeds

**Acceptance Criteria:**
- Check Azure CLI authentication status
- Provide clear instructions if not authenticated
- Display current subscription information
- Allow user to confirm or switch subscriptions

**US-003: Validate Resources**  
*As a* developer  
*I want to* be notified if my resource group or registry doesn't exist  
*So that* I can create them or use existing ones

**Acceptance Criteria:**
- Check if resource group exists
- Offer to create resource group if missing
- Check if container registry exists
- Offer to create container registry if missing
- Validate registry has admin access enabled

**US-004: Build and Push Container**  
*As a* developer  
*I want to* have my container automatically built and pushed  
*So that* I don't need to remember Docker commands

**Acceptance Criteria:**
- Build Docker image with appropriate tags
- Authenticate to Azure Container Registry
- Push image with progress indication
- Verify successful push
- Handle build failures gracefully

**US-005: Deploy to Container Instances**  
*As a* developer  
*I want to* have the container deployed with appropriate settings  
*So that* the MCP server is accessible and properly configured

**Acceptance Criteria:**
- Deploy with appropriate CPU and memory limits
- Configure streamable-http transport (stdio N/A for ACI, SSE shares same port)
- Override Dockerfile CMD via `--command-line` to set correct transport (env vars alone are insufficient)
- Exposed port and `MCP_PORT` must match (ACI has no port mapping)
- Assign public IP address
- Set appropriate environment variables
- Delete existing container before re-creating (idempotent)
- Display connection information including URL

### Functional Requirements

**FR-001:** Script MUST check Azure CLI is installed and user is authenticated  
**FR-002:** Script MUST prompt for resource group name interactively  
**FR-003:** Script MUST prompt for container registry name interactively  
**FR-004:** Script MUST validate resource group exists or offer to create it  
**FR-005:** Script MUST validate container registry exists or offer to create it  
**FR-006:** Script MUST build Docker image with versioned tag  
**FR-007:** Script MUST authenticate to Azure Container Registry  
**FR-008:** Script MUST push Docker image to registry  
**FR-009:** Script MUST deploy container to Azure Container Instances  
**FR-010:** Script MUST configure HTTP port exposure (port 8080) with matching `MCP_PORT` env var (ACI has no port mapping)  
**FR-011:** Script MUST assign public IP to container instance  
**FR-012:** Script MUST display public URL upon successful deployment  
**FR-013:** Script MUST handle errors gracefully with clear messages  
**FR-014:** Script MUST use `--command-line` to override the Dockerfile CMD, explicitly passing `--transport streamable-http --host 0.0.0.0 --port 8080` (env vars alone are insufficient because the Dockerfile CMD passes `--transport stdio` as a CLI arg which takes argparse precedence)  
**FR-015:** Script MUST delete any existing container instance before creating a new one (idempotent re-deploy)  
**FR-016:** Script MUST NOT use `--tags` with `az container create` (unsupported)  
**FR-017:** Script MUST validate ACR name availability globally before attempting to create (ACR names are globally unique across all Azure subscriptions). If the name exists in a different resource group or subscription, the script MUST inform the user and suggest alternatives rather than failing with a cryptic Azure error

### Non-Functional Requirements

**NFR-001: Performance**  
- Resource validation under 5 seconds
- Image push time depends on size but show progress
- Container deployment under 2 minutes
- Total script execution under 5 minutes (excluding build)

**NFR-002: Reliability**  
- All Azure operations must check for success
- Failed operations must not leave partial resources
- Script must be safely re-runnable
- Provide rollback instructions on failure

**NFR-003: Usability**  
- Clear prompts with examples
- Colored output for different message types
- Progress indicators for long operations
- Final output includes all connection details

**NFR-004: Portability**  
- Work on Linux, macOS, and Windows (via WSL/PowerShell)
- Support both Bash and PowerShell versions
- No dependencies beyond Azure CLI and Docker

### Data Model

**DeploymentConfiguration:**
- resource_group: string (Azure resource group name)
- registry_name: string (ACR name, must be globally unique)
- container_name: string (ACI name)
- image_name: string (Docker image name)
- image_tag: string (version tag)
- location: string (Azure region, default: eastus)
- cpu: float (CPU cores, default: 1.0)
- memory: float (GB, default: 1.5)
- port: int (HTTP port, default: 8080)

**DeploymentOutput:**
- registry_login_server: string
- container_id: string
- public_ip: string
- fqdn: string (fully qualified domain name)
- http_url: string (complete HTTP endpoint)
- sse_url: string (complete SSE endpoint)

### Success Criteria

**SC-001:** Developer can deploy from scratch in under 5 minutes  
**SC-002:** All error messages provide clear next steps  
**SC-003:** Script output includes copy-pasteable connection URLs  
**SC-004:** Re-running script updates existing deployment without errors (delete-before-create pattern)

---

## Implementation Plan

### Technical Stack

**Language/Version:** Bash 4.0+ (primary), PowerShell 7.0+ (alternative)  
**Primary Dependencies:**
- Azure CLI 2.50+ (pre-installed)
- Docker 20.0+ (for building images)
- jq (for JSON parsing, optional but recommended)

**Storage:** N/A  
**Testing:** Manual testing with multiple Azure subscriptions  
**Target Platform:** Linux/macOS (Bash), Windows (PowerShell)  
**Performance Goals:** <5 min total deployment  
**Constraints:** Requires active Azure subscription with appropriate permissions  
**Scale/Scope:** Single-container deployment script

### Project Structure

```
weather-mcp-server/
├── deploy/
│   ├── deploy-azure.sh           # Bash deployment script
│   ├── deploy-azure.ps1          # PowerShell deployment script
│   └── README.md                 # Deployment documentation
├── src/
│   └── weather_server.py
├── Dockerfile
└── requirements.txt
```

### Architecture Overview

**Script Flow:**
1. Prerequisites validation (Azure CLI, Docker, authentication)
2. Interactive prompts for configuration
3. Resource validation/creation
4. Docker image build
5. Azure Container Registry authentication
6. Image push to ACR
7. Container instance deployment
8. Output connection information

**Key Azure Resources:**
- Resource Group (container for all resources)
- Azure Container Registry (ACR) - stores Docker images
- Azure Container Instance (ACI) - runs the container
- Public IP - assigned automatically to ACI

**Port Configuration:**
- Port 8080: HTTP transport endpoint (both streamable-http and SSE share this port)
- stdio transport: Not applicable for ACI

**ACI Constraints (learned from implementation):**
- `az container create` does NOT support `--tags` — do not include resource tags in the create command
- ACI does NOT support Docker-style port mapping (host:container). The exposed port and `MCP_PORT` environment variable MUST be the same value (e.g. both set to 8080)
- Re-deploying to an existing container instance can fail silently or conflict — always delete the existing container instance before creating a new one for a clean re-deploy
- ACR admin credentials are required for ACI to pull images; always ensure `--admin-enabled true`
- The Dockerfile uses `CMD ["--transport", "stdio"]` which overrides the `MCP_TRANSPORT` env var (argparse CLI args take precedence over env-var defaults). ACI deployment MUST use `--command-line` to explicitly pass `--transport streamable-http --host 0.0.0.0 --port 8080`, replacing the default CMD
- The MCP SDK enables DNS rebinding protection by default when the server is constructed with `host=127.0.0.1` (the default). This validates the `Host` header against an allowlist of `localhost`/`127.0.0.1`/`[::1]` only. Requests arriving with an external FQDN (e.g. `weather-mcp-aci.swedencentral.azurecontainer.io:8080`) are rejected with **421 Misdirected Request**. The server code MUST set `transport_security = None` when binding to a non-loopback address like `0.0.0.0`
- ACR names are **globally unique** across all Azure subscriptions. Before creating a registry, use `az acr check-name --name <name>` to verify availability. If `az acr show --name <name>` succeeds without `--resource-group`, the registry exists in another RG/subscription — inform the user which resource group owns it and suggest using that RG or picking a different name. Never attempt `az acr create` with a globally-taken name (results in `AlreadyInUse` error)
- `az container create` MUST include `--os-type Linux` — without it, ACI may fail with `InvalidOsType` error (`The 'osType' for container group '<null>' is invalid`)
- The ACR and the ACI do NOT need to be in the same resource group. If a registry already exists in a different resource group, the script should offer to reuse it rather than forcing the user to re-run. Track the registry's resource group separately (e.g. `REGISTRY_RG`) and use it for all `az acr` commands (show, login, credential show), while continuing to use the user's chosen resource group for the ACI deployment
- The container instance name is also used as the DNS name label, which must be unique within the Azure region. Append a random suffix (e.g. 6 hex chars + 3 random digits) to the base name to avoid collisions across deployments (e.g. `weather-mcp-aci-a3f1b2742`). Use the same suffix for the Docker image name in the registry (e.g. `weather-mcp-server-a3f1b2742`) so that each deployment pushes to a unique image repository, avoiding conflicts in shared registries. Do NOT use `xxd` (not available in all environments) — prefer `/proc/sys/kernel/random/uuid` and `$RANDOM`

### Implementation Phases

**Phase 0: Prerequisites & Validation**
1. Check Azure CLI installation
2. Verify Docker is running
3. Check Azure authentication status
4. Display current subscription
5. Confirm or allow subscription switch

**Phase 1: Interactive Configuration**
1. Prompt for resource group name
2. Prompt for container registry name
3. Prompt for Azure region (default: eastus)
4. Prompt for container instance name
5. Display configuration summary for confirmation

**Phase 2: Resource Provisioning**
1. Check if resource group exists
2. Create resource group if needed
3. Check if container registry exists
4. Create container registry if needed (with admin enabled)
5. Validate registry is ready

**Phase 3: Container Build & Push**
1. Build Docker image with timestamp tag
2. Tag image for ACR
3. Login to ACR using Azure CLI
4. Push image to ACR
5. Verify image in registry

**Phase 4: Container Deployment**
1. Check for existing container instance and delete it if present (ensures clean re-deploy)
2. Create container instance with:
   - Image from ACR
   - CPU: 1 core
   - Memory: 1.5 GB
   - Port 8080 exposed
   - `MCP_PORT=8080` (must match exposed port — ACI has no port mapping)
   - `MCP_TRANSPORT=streamable-http`
   - `--command-line "python3 -m src.weather_server --transport streamable-http --host 0.0.0.0 --port 8080"` to override the Dockerfile CMD (which defaults to `--transport stdio`)
   - Do NOT use `--tags` (unsupported by `az container create`)
3. Assign public IP
4. Wait for deployment completion

**Phase 5: Output & Verification**
1. Retrieve public IP address
2. Get FQDN
3. Construct and display HTTP URL
4. Construct and display SSE URL
5. Display connection examples
6. Show next steps

### Script Structure

**Functions:**
- `check_prerequisites()` - Validate Azure CLI, Docker
- `check_azure_auth()` - Verify authentication
- `prompt_configuration()` - Interactive prompts
- `validate_resource_group()` - Check/create RG
- `validate_container_registry()` - Check/create ACR
- `build_image()` - Build Docker image
- `push_image()` - Push to ACR
- `deploy_container()` - Deploy to ACI
- `output_results()` - Display connection info
- `error_handler()` - Handle errors gracefully

### Configuration Defaults

```bash
# Default values
DEFAULT_LOCATION="eastus"
DEFAULT_CPU="1.0"
DEFAULT_MEMORY="1.5"
DEFAULT_PORT=8080
IMAGE_NAME="weather-mcp-server"
CONTAINER_INSTANCE_NAME="weather-mcp-aci"
```

---

## Task Breakdown

### Phase 0: Script Foundation [Foundation]

**T001: Create Bash script skeleton**
- File: `deploy/deploy-azure.sh`
- Add shebang and script header
- Define color codes for output
- Create logging functions (info, warn, error, success)
- Add error handling with set -e and trap
- Add help text and usage information

**T002: Implement prerequisites check function**
- File: `deploy/deploy-azure.sh`
- Check Azure CLI installation
- Check Docker installation
- Verify Docker daemon is running
- Display versions of required tools
- Exit gracefully if prerequisites missing

**T003: Implement Azure authentication check**
- File: `deploy/deploy-azure.sh`
- Run `az account show` to check auth
- Display current subscription info
- Prompt to login if not authenticated
- Allow user to switch subscriptions
- Validate user has appropriate permissions

### Phase 1: Configuration & Validation [US-001, US-002, US-003]

**T004: Implement interactive configuration prompts**
- File: `deploy/deploy-azure.sh`
- Prompt for resource group (with example)
- Prompt for registry name (with validation)
- Prompt for location (with default)
- Generate container instance name automatically
- Display configuration summary
- Ask for confirmation before proceeding

**T005: Implement resource group validation**
- File: `deploy/deploy-azure.sh`
- Check if resource group exists with `az group exists`
- If missing, ask user to create it
- Create resource group with `az group create`
- Verify creation successful
- Handle creation errors

**T006: Implement container registry validation**
- File: `deploy/deploy-azure.sh`
- Check if ACR exists with `az acr show`
- If missing, ask user to create it
- Create ACR with admin enabled: `az acr create --admin-enabled true`
- Wait for ACR to be ready
- Verify ACR is accessible
- Handle SKU and pricing considerations

### Phase 2: Image Build & Push [US-004]

**T007: Implement Docker image build function**
- File: `deploy/deploy-azure.sh`
- Generate image tag with timestamp
- Build image: `docker build -t $IMAGE_NAME:$TAG .`
- Display build progress
- Tag image for ACR: `$REGISTRY.azurecr.io/$IMAGE_NAME:$TAG`
- Also tag as :latest
- Verify build success

**T008: Implement ACR authentication and push**
- File: `deploy/deploy-azure.sh`
- Login to ACR: `az acr login --name $REGISTRY`
- Push image: `docker push $REGISTRY.azurecr.io/$IMAGE_NAME:$TAG`
- Push :latest tag
- Show push progress
- Verify image exists in registry
- Handle authentication failures

### Phase 3: Container Deployment [US-005]

**T009: Implement container instance deployment**
- File: `deploy/deploy-azure.sh`
- Get ACR credentials with `az acr credential show`
- Delete existing container instance if it exists (`az container delete --yes`) for safe re-deploy
- Create ACI with `az container create`:
  - Image from ACR
  - CPU and memory settings
  - Port 8080 exposed (must match MCP_PORT env var — ACI has no port mapping)
  - Environment variables: `MCP_TRANSPORT=streamable-http`, `MCP_HOST=0.0.0.0`, `MCP_PORT=8080`
  - Use `--command-line` to override Dockerfile CMD with explicit `--transport streamable-http --host 0.0.0.0 --port 8080` (env vars alone are not sufficient because the Dockerfile CMD passes `--transport stdio` as a CLI arg which takes precedence)
  - Public IP: --ip-address public
  - DNS name label
  - Do NOT use `--tags` (unsupported by `az container create`)
- Wait for deployment: `az container show --query instanceView.state`
- Handle deployment failures
- Re-running the script replaces the existing container cleanly

**T010: Implement connection information retrieval**
- File: `deploy/deploy-azure.sh`
- Get public IP: `az container show --query ipAddress.ip`
- Get FQDN: `az container show --query ipAddress.fqdn`
- Construct HTTP URL: `http://$FQDN:8080`
- Construct SSE URL: `http://$FQDN:8080/sse`
- Display all connection details

### Phase 4: Output & Documentation

**T011: Implement output formatting function**
- File: `deploy/deploy-azure.sh`
- Display success message with colors
- Show deployment summary:
  - Resource group
  - Registry name
  - Image tag
  - Container instance name
- Show connection URLs in a box
- Provide example curl commands
- Show next steps and documentation links

**T012: Create deployment documentation**
- File: `deploy/README.md`
- Quick start guide
- Prerequisites list
- Step-by-step usage instructions
- Configuration options
- Troubleshooting guide
- Cost considerations
- Cleanup instructions

**T013: Add error handling and rollback guidance**
- File: `deploy/deploy-azure.sh`
- Trap errors with trap command
- Log all operations
- On failure, display:
  - What failed
  - Current state of resources
  - Rollback/cleanup commands
  - Link to troubleshooting docs
- Provide cleanup script option

### Phase 5: PowerShell Alternative [Optional]

**T014: Create PowerShell version [P]**
- File: `deploy/deploy-azure.ps1`
- Port all Bash functionality to PowerShell
- Use Azure CLI commands (same as Bash)
- Implement equivalent error handling
- Match output formatting
- Test on Windows environment

### Validation Checkpoints

**After Phase 0:** Prerequisites validation works
- Script detects missing tools
- Authentication check works correctly
- Error messages are clear

**After Phase 1:** Configuration flow is smooth
- All prompts are clear and helpful
- Resource validation works correctly
- Confirmation summary is comprehensive

**After Phase 2:** Image pipeline works
- Image builds successfully
- Push to ACR completes
- Tags are correct

**After Phase 3:** Deployment succeeds
- Container instance runs successfully
- Public IP is assigned
- Container is accessible

**After Phase 4:** Documentation is complete
- README covers all scenarios
- Error messages include solutions
- Users can troubleshoot independently

---

## Example Usage

### Basic Deployment
```bash
./deploy/deploy-azure.sh
```

### Example Session
```
🚀 Azure Container Deployment Script
====================================

✓ Azure CLI installed (version 2.50.0)
✓ Docker installed (version 24.0.0)
✓ Azure authenticated

Current Subscription: My Subscription (12345678-1234-1234-1234-123456789012)

📝 Configuration
==============

Enter resource group name (e.g., weather-mcp-rg): my-resources
Enter container registry name (e.g., weathermcpreg): myweatherregistry
Enter Azure region [eastus]: 

Configuration Summary:
- Resource Group: my-resources
- Registry: myweatherregistry
- Location: eastus
- Container: weather-mcp-aci

Proceed with deployment? (y/n): y

🔍 Validating resources...
✓ Resource group exists
✓ Container registry exists

🏗️  Building Docker image...
✓ Image built: weather-mcp-server:20250217-143022

📤 Pushing to Azure Container Registry...
✓ Image pushed successfully

🚀 Deploying to Azure Container Instances...
✓ Container deployed successfully

✅ Deployment Complete!
======================

🌐 Connection Information:
╔════════════════════════════════════════════════════════════╗
║ HTTP URL:  http://weather-mcp-aci.eastus.azurecontainer.io:8080 ║
║ SSE URL:   http://weather-mcp-aci.eastus.azurecontainer.io:8080/sse ║
╚════════════════════════════════════════════════════════════╝

📋 Test your deployment:
curl http://weather-mcp-aci.eastus.azurecontainer.io:8080/mcp/ -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","method":"initialize","id":1}'

📚 Next steps:
1. Configure your MCP client with the URLs above
2. Monitor logs: az container logs -g my-resources -n weather-mcp-aci
3. View metrics in Azure Portal

💰 Estimated cost: ~$0.50-1.00 per day
```

### Cleanup
```bash
# Delete container instance
az container delete -g my-resources -n weather-mcp-aci -y

# Delete entire resource group (careful!)
az group delete -g my-resources -y
```