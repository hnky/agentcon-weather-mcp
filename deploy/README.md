# Azure Deployment Guide – Weather MCP Server

Deploy the Weather MCP Server to **Azure Container Instances (ACI)** with a single interactive script.

## Prerequisites

| Tool | Minimum Version | Install Guide |
|------|----------------|---------------|
| Azure CLI (`az`) | 2.50+ | [Install Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| Docker | 20.0+ | [Get Docker](https://docs.docker.com/get-docker/) |
| Active Azure subscription | — | [Create free account](https://azure.microsoft.com/free/) |

## Quick Start

```bash
# From the project root:
./deploy/deploy-azure.sh
```

The script is fully interactive—no arguments required. It will prompt you for:

1. **Resource group name** – logical container for Azure resources
2. **Container registry name** – globally unique, alphanumeric only (e.g. `weathermcpreg`)
3. **Azure region** – defaults to `eastus`

## What the Script Does

| Phase | Description |
|-------|-------------|
| Prerequisites | Validates Azure CLI, Docker, and authentication |
| Configuration | Interactively collects deployment parameters |
| Resource Provisioning | Creates resource group and container registry if missing |
| Build & Push | Builds the Docker image and pushes it to Azure Container Registry |
| Deploy | Creates/updates an Azure Container Instance with a public IP |
| Output | Displays connection URLs, test commands, and cleanup instructions |

## Configuration Defaults

| Setting | Default | Notes |
|---------|---------|-------|
| Location | `eastus` | Any Azure region supported |
| CPU | 1.0 core | Adjust in script if needed |
| Memory | 1.5 GB | Adjust in script if needed |
| External Port | 8080 | Maps to internal port 8000 |
| Container Name | `weather-mcp-aci` | Auto-generated |
| Transport | `streamable-http` | Used by ACI deployment |

## Connection URLs

After deployment the script prints two endpoints:

| Transport | URL |
|-----------|-----|
| Streamable HTTP | `http://<fqdn>:8080/mcp/` |
| SSE | `http://<fqdn>:8080/sse` |

### Test the deployment

```bash
curl http://<fqdn>:8080/mcp/ \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1}'
```

## Re-running the Script

The script is **idempotent**. Running it again will:

- Skip resource group and registry creation if they already exist
- Rebuild and push a new image tag (timestamped)
- Replace the existing container instance with the updated image

## Monitoring

```bash
# View container logs
az container logs -g <resource-group> -n weather-mcp-aci

# Stream logs in real time
az container logs -g <resource-group> -n weather-mcp-aci --follow

# Check container status
az container show -g <resource-group> -n weather-mcp-aci --query instanceView.state
```

## Cleanup

```bash
# Delete the container instance only
az container delete -g <resource-group> -n weather-mcp-aci -y

# Delete the entire resource group (removes all resources inside)
az group delete -g <resource-group> -y
```

## Cost Estimate

| Resource | Approximate Cost |
|----------|-----------------|
| Azure Container Instance (1 CPU / 1.5 GB) | ~$0.50–1.00/day |
| Azure Container Registry (Basic SKU) | ~$0.17/day |

> Stop the container when not in use to reduce costs:
> `az container stop -g <resource-group> -n weather-mcp-aci`

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `az: command not found` | Install [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| `docker: command not found` | Install [Docker](https://docs.docker.com/get-docker/) |
| Docker daemon not running | Start Docker Desktop or `sudo systemctl start docker` |
| Not logged in to Azure | Run `az login` |
| Registry name taken | ACR names are globally unique – pick a different name |
| Container stuck in "Creating" | Check logs: `az container logs -g <rg> -n weather-mcp-aci` |
| Port not reachable | Verify NSG rules and that the container is in `Running` state |
