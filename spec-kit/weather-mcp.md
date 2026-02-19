# Weather MCP Server - Spec-Kit Specification

## Constitution

### I. Code Quality Principles
- Write clean, well-documented Python code following PEP 8 standards
- All functions must include type hints and docstrings
- Error handling must be comprehensive and user-friendly
- Code must be production-ready and maintainable

### II. Architecture Principles
- Use the official MCP Python SDK for server implementation
- Keep dependencies minimal - only essential libraries
- All three MCP transports (stdio, SSE, HTTP) must be equally functional
- No authentication required - server should be open by default

### III. Container & Deployment
- Docker container must be lightweight and production-ready
- Container should start quickly and handle graceful shutdowns
- Include health checks and proper logging
- Documentation must cover all deployment scenarios

### IV. API Integration
- Use Open-Meteo API as the sole weather data source
- Handle API rate limits and failures gracefully
- Cache responses appropriately to minimize API calls
- Never expose API keys (Open-Meteo is open/free)

### V. Testing & Quality
- Include example usage for all three transports
- Provide clear error messages for troubleshooting
- Log all requests and errors for debugging
- Include validation for latitude/longitude inputs

---

## Feature Specification

### Feature Overview
**Feature Name:** Weather MCP Server  
**Feature ID:** 001-weather-mcp-server  
**Purpose:** Provide a containerized MCP server that delivers current weather and forecast data from Open-Meteo API

### User Stories

**US-001: Query Current Weather**  
*As a* MCP client  
*I want to* query current weather conditions by latitude and longitude  
*So that* I can get real-time weather data for any location

**Acceptance Criteria:**
- Accept latitude and longitude as decimal coordinates
- Return current temperature, wind speed, weather code, and conditions
- Handle invalid coordinates with clear error messages
- Response time under 2 seconds for valid requests

**US-002: Get Weather Forecast**  
*As a* MCP client  
*I want to* retrieve weather forecasts for a specified location  
*So that* I can plan based on future weather conditions

**Acceptance Criteria:**
- Accept latitude, longitude, and optional days parameter (default 7)
- Return daily forecasts with temperature min/max, precipitation, weather codes
- Support forecast periods from 1 to 16 days
- Format data in a structured, easy-to-parse format

**US-003: Connect via Multiple Transports**  
*As a* developer  
*I want to* connect to the MCP server using stdio, SSE, or HTTP  
*So that* I can integrate it into different application architectures

**Acceptance Criteria:**
- All three transports provide identical functionality
- Connection instructions documented for each transport
- Transport selection available via command-line arguments or environment variables
- Each transport handles errors consistently

### Functional Requirements

**FR-001:** System MUST implement get_current_weather tool accepting latitude and longitude  
**FR-002:** System MUST implement get_forecast tool accepting latitude, longitude, and optional days parameter  
**FR-003:** System MUST validate latitude (-90 to 90) and longitude (-180 to 180) ranges  
**FR-004:** System MUST handle Open-Meteo API errors gracefully with meaningful error messages  
**FR-005:** System MUST support stdio transport for command-line integration  
**FR-006:** System MUST support SSE transport for web-based streaming  
**FR-007:** System MUST support HTTP transport for REST API access  
**FR-008:** System MUST run in a Docker container  
**FR-009:** System MUST provide health check endpoint (for HTTP/SSE)  
**FR-010:** System MUST log all tool invocations and errors

### Non-Functional Requirements

**NFR-001: Performance**  
- Weather queries must complete within 2 seconds
- Container startup time under 5 seconds
- Support concurrent requests (HTTP/SSE only)

**NFR-002: Reliability**  
- Handle network failures with retry logic
- Graceful degradation when API is unavailable
- Proper error propagation to clients

**NFR-003: Maintainability**  
- Well-documented code with type hints
- Clear README with examples
- Minimal dependencies for easy updates

**NFR-004: Portability**  
- Run on any platform supporting Docker
- No platform-specific dependencies
- Configuration via environment variables

### Data Model

**WeatherLocation:**
- latitude: float (-90 to 90)
- longitude: float (-180 to 180)

**CurrentWeather:**
- temperature: float (Celsius)
- wind_speed: float (km/h)
- weather_code: int (WMO code)
- conditions: string (human-readable)
- timestamp: datetime (UTC)

**DailyForecast:**
- date: date
- temperature_min: float (Celsius)
- temperature_max: float (Celsius)
- precipitation: float (mm)
- weather_code: int (WMO code)
- conditions: string (human-readable)

**ForecastResponse:**
- location: WeatherLocation
- forecasts: list[DailyForecast]

### Success Criteria

**SC-001:** Developer can start the container and query weather within 2 minutes  
**SC-002:** All three transports return identical data for same inputs  
**SC-003:** Server handles 100 requests per minute without degradation  
**SC-004:** Error messages are clear enough to troubleshoot without documentation

---

## Implementation Plan

### Technical Stack

**Language/Version:** Python 3.11+  
**Primary Dependencies:**
- `mcp` - Official MCP Python SDK
- `httpx` - HTTP client for API calls
- `uvicorn` - ASGI server (for SSE/HTTP transports)
- `pydantic` - Data validation

**Storage:** N/A (stateless service)  
**Testing:** pytest with httpx mock  
**Target Platform:** Docker container (Linux-based)  
**Performance Goals:** <2s response time, 100 req/min  
**Constraints:** No authentication, open API only  
**Scale/Scope:** Single-instance container for development/small deployments

### Project Structure

```
weather-mcp-server/
├── src/
│   └── weather_server.py          # Main MCP server implementation
├── tests/
│   ├── test_weather_tools.py      # Unit tests for weather tools
│   └── test_transports.py         # Transport integration tests
├── Dockerfile                      # Container definition
├── docker-compose.yml              # Optional compose file
├── requirements.txt                # Python dependencies
├── README.md                       # Documentation
└── .dockerignore                   # Docker build exclusions
```

### Architecture Overview

**Transport Layer:**
- Single server implementation with three transport modes
- Mode selection via CLI argument: `--transport [stdio|sse|http]`
- Each transport wraps the same core tool implementations

**Service Layer:**
- OpenMeteoClient class for API interactions
- WeatherTools class implementing MCP tool handlers
- Shared validation and error handling logic

**API Integration:**
- Base URL: `https://api.open-meteo.com/v1/forecast`
- Current weather: `/current` endpoint
- Forecast: `/daily` endpoint parameters
- No API key required (free tier)

### Implementation Phases

**Phase 0: Research & Setup**
1. Review MCP Python SDK documentation for transport implementations
2. Review Open-Meteo API documentation for endpoint parameters
3. Research Docker best practices for Python services
4. Determine optimal httpx configuration for async requests

**Phase 1: Core Implementation**
1. Implement OpenMeteoClient with current weather method
2. Implement OpenMeteoClient forecast method
3. Create WeatherTools MCP tool handlers
4. Add validation for coordinates and parameters
5. Implement error handling and logging

**Phase 2: Transport Implementation**
1. Implement stdio transport (stdin/stdout)
2. Implement SSE transport (HTTP streaming)
3. Implement HTTP transport (REST endpoints)
4. Add transport selection logic
5. Create unified error handling across transports

**Phase 3: Containerization**
1. Create Dockerfile with multi-stage build
2. Add docker-compose.yml for easy testing
3. Configure health checks
4. Optimize image size
5. Add environment variable configuration

**Phase 4: Documentation & Testing**
1. Write comprehensive README
2. Add transport-specific usage examples
3. Create pytest test suite
4. Add integration test examples
5. Document troubleshooting guide

### API Contracts

**Tool: get_current_weather**
```json
{
  "name": "get_current_weather",
  "description": "Get current weather conditions for a location",
  "inputSchema": {
    "type": "object",
    "properties": {
      "latitude": {
        "type": "number",
        "minimum": -90,
        "maximum": 90,
        "description": "Latitude coordinate"
      },
      "longitude": {
        "type": "number",
        "minimum": -180,
        "maximum": 180,
        "description": "Longitude coordinate"
      }
    },
    "required": ["latitude", "longitude"]
  }
}
```

**Tool: get_forecast**
```json
{
  "name": "get_forecast",
  "description": "Get weather forecast for a location",
  "inputSchema": {
    "type": "object",
    "properties": {
      "latitude": {
        "type": "number",
        "minimum": -90,
        "maximum": 90,
        "description": "Latitude coordinate"
      },
      "longitude": {
        "type": "number",
        "minimum": -180,
        "maximum": 180,
        "description": "Longitude coordinate"
      },
      "days": {
        "type": "integer",
        "minimum": 1,
        "maximum": 16,
        "default": 7,
        "description": "Number of forecast days"
      }
    },
    "required": ["latitude", "longitude"]
  }
}
```

---

## Task Breakdown

### Phase 0: Project Setup [Foundation]

**T001: Initialize Python project structure**
- Create directory structure
- Initialize requirements.txt with dependencies
- Create .dockerignore and .gitignore
- Set up basic logging configuration

**T002: Research MCP SDK patterns [P]**
- Review MCP Python SDK transport examples
- Document stdio transport implementation pattern
- Document SSE transport implementation pattern
- Document HTTP transport implementation pattern

**T003: Research Open-Meteo API [P]**
- Document current weather endpoint parameters
- Document forecast endpoint parameters
- Test API responses manually
- Document WMO weather codes mapping

### Phase 1: Core Weather Service [US-001, US-002]

**T004: Implement OpenMeteoClient class**
- File: `src/weather_server.py`
- Create async HTTP client wrapper
- Implement coordinate validation
- Add retry logic for transient failures
- Include comprehensive error handling

**T005: Implement get_current_weather method**
- File: `src/weather_server.py`
- Parse Open-Meteo current weather response
- Map weather codes to conditions
- Return structured CurrentWeather model
- Add unit tests

**T006: Implement get_forecast method**
- File: `src/weather_server.py`
- Parse Open-Meteo daily forecast response
- Handle days parameter (default 7)
- Return structured ForecastResponse model
- Add unit tests

### Phase 2: MCP Server Implementation [US-003]

**T007: Create WeatherTools MCP tool class**
- File: `src/weather_server.py`
- Define MCP tool schemas
- Implement tool handler for get_current_weather
- Implement tool handler for get_forecast
- Add input validation

**T008: Implement stdio transport [P]**
- File: `src/weather_server.py`
- Create stdio server instance
- Register weather tools
- Add error handling for stdin/stdout
- Test with MCP inspector

**T009: Implement SSE transport [P]**
- File: `src/weather_server.py`
- Create SSE server with uvicorn
- Register weather tools
- Add health check endpoint
- Configure CORS if needed

**T010: Implement HTTP transport [P]**
- File: `src/weather_server.py`
- Create HTTP server with uvicorn
- Register weather tools as REST endpoints
- Add OpenAPI documentation
- Add health check endpoint

**T011: Add transport selection logic**
- File: `src/weather_server.py`
- Parse CLI arguments for transport type
- Initialize appropriate transport
- Add environment variable fallback
- Create main entry point

### Phase 3: Containerization [US-003]

**T012: Create Dockerfile**
- File: `Dockerfile`
- Use Python 3.11-slim base image
- Multi-stage build for smaller image
- Install dependencies
- Copy source code
- Configure entry point with transport selection

**T013: Create docker-compose.yml**
- File: `docker-compose.yml`
- Define service for each transport
- Add environment variables
- Configure port mappings for HTTP/SSE
- Add health checks

**T014: Optimize container**
- Review and minimize image layers
- Add .dockerignore for faster builds
- Configure logging to stdout
- Test graceful shutdown

### Phase 4: Testing & Documentation

**T015: Write unit tests**
- File: `tests/test_weather_tools.py`
- Test coordinate validation
- Mock Open-Meteo API responses
- Test error handling scenarios
- Achieve 80%+ code coverage

**T016: Write integration tests [P]**
- File: `tests/test_transports.py`
- Test each transport end-to-end
- Verify identical responses across transports
- Test concurrent requests (HTTP/SSE)

**T017: Create comprehensive README**
- File: `README.md`
- Quick start guide
- Transport-specific examples
- Configuration reference
- Troubleshooting guide
- API documentation

**T018: Add usage examples**
- File: `README.md`
- Example: Using with Claude Desktop (stdio)
- Example: Using with web client (SSE)
- Example: Using with REST client (HTTP)
- Example: Docker compose setup

### Validation Checkpoints

**After Phase 1:** Core weather functionality works independently
- Can query current weather programmatically
- Can query forecasts programmatically
- Error handling works for invalid inputs

**After Phase 2:** All transports operational
- Can connect via stdio
- Can connect via SSE
- Can connect via HTTP
- Tools return consistent data

**After Phase 3:** Production-ready container
- Container builds successfully
- Container starts in under 5 seconds
- Health checks pass
- All transports accessible from container

**After Phase 4:** Complete and documented
- README provides clear setup instructions
- All examples work as documented
- Tests pass with good coverage
- Troubleshooting guide helps resolve common issues