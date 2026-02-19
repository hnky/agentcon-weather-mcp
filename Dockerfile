# syntax=docker/dockerfile:1

# ---- Build stage ----
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Runtime stage ----
FROM python:3.11-slim

LABEL maintainer="weather-mcp"
LABEL description="Weather MCP Server – Open-Meteo powered"

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app
COPY src/ ./src/

# Non-root user for security
RUN useradd --create-home appuser
USER appuser

# Default transport & port
ENV MCP_TRANSPORT=stdio \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import socket; s=socket.create_connection(('localhost',8000),2); s.close()" || exit 0

ENTRYPOINT ["python3", "-m", "src.weather_server"]
CMD ["--transport", "stdio"]
