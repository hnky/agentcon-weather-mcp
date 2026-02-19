# Weather MCP Server

A containerized **Model Context Protocol (MCP)** server that delivers current weather conditions and multi-day forecasts via the free [Open-Meteo API](https://open-meteo.com/). Supports **stdio**, **SSE**, and **streamable-http** transports.

---

## Features

| Tool | Description |
|---|---|
| `get_current_weather` | Current temperature, wind speed, conditions for any lat/lon |
| `get_forecast` | 1–16 day forecast with min/max temps & precipitation |

- Three transports: **stdio** (CLI), **SSE** (streaming), **streamable-http** (REST)
- Docker-ready with multi-stage build
- No API key needed (Open-Meteo is free & open)
- Full input validation, retry logic, and structured error handling

---

## Quick Start

### Prerequisites

- Python 3.11+ **or** Docker
- No API keys required

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run with stdio transport (default)
python -m src.weather_server

# Run with SSE transport
python -m src.weather_server --transport sse --port 8000

# Run with streamable-http transport
python -m src.weather_server --transport streamable-http --port 8000
```

### Run with Docker

```bash
# Build the image
docker build -t weather-mcp-server .

# Run with stdio
docker run -i weather-mcp-server

# Run with SSE (exposed on port 8001)
docker run -p 8001:8000 weather-mcp-server --transport sse

# Run with streamable-http (exposed on port 8002)
docker run -p 8002:8000 weather-mcp-server --transport streamable-http
```

### Run with Docker Compose

```bash
# Start SSE and HTTP services
docker compose up -d

# SSE available on http://localhost:8001
# HTTP available on http://localhost:8002
```

---

## Usage Examples

### Using with Claude Desktop (stdio)

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["-m", "src.weather_server"],
      "cwd": "/path/to/weather-mcp-server"
    }
  }
}
```

Or with Docker:

```json
{
  "mcpServers": {
    "weather": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "weather-mcp-server"]
    }
  }
}
```

### Using with a Web Client (SSE)

Start the server:

```bash
python -m src.weather_server --transport sse --port 8000
```

Connect from an MCP client pointing to `http://localhost:8000/sse`.

### Using with a REST Client (streamable-http)

Start the server:

```bash
python -m src.weather_server --transport streamable-http --port 8000
```

Connect from an MCP client pointing to `http://localhost:8000/mcp`.

### Using with MCP Inspector

```bash
# Install MCP CLI tools if needed
pip install "mcp[cli]"

# Inspect the server
mcp dev src/weather_server.py
```

---

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | Transport type: `stdio`, `sse`, `streamable-http` |
| `MCP_HOST` | `0.0.0.0` | Bind address (SSE/HTTP) |
| `MCP_PORT` | `8000` | Bind port (SSE/HTTP) |

CLI arguments take precedence over environment variables.

---

## API Reference

### `get_current_weather`

Get current weather conditions for any location.

**Parameters:**

| Name | Type | Required | Description |
|---|---|---|---|
| `latitude` | float | Yes | Latitude (-90 to 90) |
| `longitude` | float | Yes | Longitude (-180 to 180) |

**Example Response:**

```
Current weather at (52.52, 13.41):
  Temperature: 22.5°C
  Wind Speed: 15.3 km/h
  Conditions: Partly cloudy (WMO code 2)
  Observed at: 2025-06-15T12:00:00+00:00
```

### `get_forecast`

Get a multi-day weather forecast.

**Parameters:**

| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| `latitude` | float | Yes | — | Latitude (-90 to 90) |
| `longitude` | float | Yes | — | Longitude (-180 to 180) |
| `days` | int | No | 7 | Forecast days (1–16) |

**Example Response:**

```
Weather forecast for (52.52, 13.41) – 3 day(s):

  2025-06-15: Clear sky (WMO 0), 15.0°C – 25.0°C, Precipitation: 0.0 mm
  2025-06-16: Moderate rain (WMO 63), 17.0°C – 27.0°C, Precipitation: 2.5 mm
  2025-06-17: Mainly clear (WMO 1), 14.0°C – 23.0°C, Precipitation: 0.1 mm
```

---

## Testing

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src
```

---

## Project Structure

```
weather-mcp-server/
├── src/
│   ├── __init__.py
│   └── weather_server.py      # Main MCP server implementation
├── tests/
│   ├── __init__.py
│   ├── test_weather_tools.py  # Unit tests
│   └── test_transports.py     # Transport & integration tests
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Compose for SSE + HTTP services
├── requirements.txt            # Python dependencies
├── .dockerignore               # Docker build exclusions
├── .gitignore                  # Git exclusions
└── README.md                   # This file
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `Connection refused` on SSE/HTTP | Ensure `--transport sse` or `--transport streamable-http` is set and the port is correct |
| `Latitude must be between -90 and 90` | Check your coordinate values — latitude is ±90, longitude is ±180 |
| `Failed to fetch weather data – 429` | Open-Meteo rate limit hit — wait and retry |
| Container won't start | Check `docker logs <container>` for Python errors |
| Timeout errors | Open-Meteo may be slow — the client retries up to 3 times automatically |

---

## License

MIT