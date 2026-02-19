"""
Weather MCP Server

A containerized MCP server that delivers current weather and forecast data
from the Open-Meteo API. Supports stdio, SSE, and streamable-http transports.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime, timezone
from typing import Any, Literal

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("weather-mcp")

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class WeatherLocation(BaseModel):
    """Geographic coordinates for a weather query."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(
        ..., ge=-180, le=180, description="Longitude coordinate"
    )


class CurrentWeather(BaseModel):
    """Current weather conditions at a location."""

    temperature: float = Field(..., description="Temperature in Celsius")
    wind_speed: float = Field(..., description="Wind speed in km/h")
    weather_code: int = Field(..., description="WMO weather code")
    conditions: str = Field(..., description="Human-readable conditions")
    timestamp: datetime = Field(..., description="Observation time (UTC)")


class DailyForecast(BaseModel):
    """Forecast for a single day."""

    forecast_date: date = Field(..., description="Forecast date")
    temperature_min: float = Field(..., description="Minimum temperature (°C)")
    temperature_max: float = Field(..., description="Maximum temperature (°C)")
    precipitation: float = Field(..., description="Precipitation (mm)")
    weather_code: int = Field(..., description="WMO weather code")
    conditions: str = Field(..., description="Human-readable conditions")


class ForecastResponse(BaseModel):
    """Multi-day forecast response."""

    location: WeatherLocation
    forecasts: list[DailyForecast]


# ---------------------------------------------------------------------------
# WMO weather code mapping
# ---------------------------------------------------------------------------

WMO_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def weather_code_to_conditions(code: int) -> str:
    """Convert a WMO weather code to a human-readable string."""
    return WMO_CODES.get(code, f"Unknown (code {code})")


# ---------------------------------------------------------------------------
# Open-Meteo client
# ---------------------------------------------------------------------------

OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
MAX_RETRIES = 3
RETRY_BACKOFF = 0.5  # seconds


class OpenMeteoClient:
    """Async HTTP client wrapper for the Open-Meteo API."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _validate_coordinates(latitude: float, longitude: float) -> None:
        """Raise ValueError for out-of-range coordinates."""
        if not (-90 <= latitude <= 90):
            raise ValueError(
                f"Latitude must be between -90 and 90, got {latitude}"
            )
        if not (-180 <= longitude <= 180):
            raise ValueError(
                f"Longitude must be between -180 and 180, got {longitude}"
            )

    async def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Perform a GET request and return parsed JSON."""
        logger.info("Open-Meteo request params: %s", params)
        response = await self._client.get(OPEN_METEO_BASE, params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        if "error" in data and data["error"]:
            raise RuntimeError(f"Open-Meteo API error: {data.get('reason', 'unknown')}")
        return data

    # -- public API ----------------------------------------------------------

    async def get_current_weather(
        self, latitude: float, longitude: float
    ) -> CurrentWeather:
        """Fetch current weather conditions for the given coordinates."""
        self._validate_coordinates(latitude, longitude)

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,wind_speed_10m,weather_code",
            "timezone": "UTC",
        }
        data = await self._get(params)
        current = data["current"]

        code = int(current["weather_code"])
        return CurrentWeather(
            temperature=float(current["temperature_2m"]),
            wind_speed=float(current["wind_speed_10m"]),
            weather_code=code,
            conditions=weather_code_to_conditions(code),
            timestamp=datetime.fromisoformat(current["time"]).replace(
                tzinfo=timezone.utc
            ),
        )

    async def get_forecast(
        self, latitude: float, longitude: float, days: int = 7
    ) -> ForecastResponse:
        """Fetch a multi-day forecast for the given coordinates."""
        self._validate_coordinates(latitude, longitude)
        if not (1 <= days <= 16):
            raise ValueError(f"Days must be between 1 and 16, got {days}")

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code",
            "timezone": "UTC",
            "forecast_days": days,
        }
        data = await self._get(params)
        daily = data["daily"]

        forecasts: list[DailyForecast] = []
        for i in range(len(daily["time"])):
            code = int(daily["weather_code"][i])
            forecasts.append(
                DailyForecast(
                    forecast_date=date.fromisoformat(daily["time"][i]),
                    temperature_min=float(daily["temperature_2m_min"][i]),
                    temperature_max=float(daily["temperature_2m_max"][i]),
                    precipitation=float(daily["precipitation_sum"][i]),
                    weather_code=code,
                    conditions=weather_code_to_conditions(code),
                )
            )

        return ForecastResponse(
            location=WeatherLocation(latitude=latitude, longitude=longitude),
            forecasts=forecasts,
        )


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Weather MCP Server",
    instructions=(
        "A weather data server powered by the Open-Meteo API. "
        "Use the get_current_weather tool to retrieve current conditions "
        "and the get_forecast tool to retrieve multi-day forecasts."
    ),
)

_client = OpenMeteoClient()


@mcp.tool()
async def get_current_weather(latitude: float, longitude: float) -> str:
    """Get current weather conditions for a location.

    Args:
        latitude: Latitude coordinate (-90 to 90).
        longitude: Longitude coordinate (-180 to 180).

    Returns:
        A formatted string describing current weather conditions.
    """
    logger.info(
        "Tool invoked: get_current_weather(lat=%s, lon=%s)", latitude, longitude
    )
    try:
        weather = await _client.get_current_weather(latitude, longitude)
        return (
            f"Current weather at ({latitude}, {longitude}):\n"
            f"  Temperature: {weather.temperature}°C\n"
            f"  Wind Speed: {weather.wind_speed} km/h\n"
            f"  Conditions: {weather.conditions} (WMO code {weather.weather_code})\n"
            f"  Observed at: {weather.timestamp.isoformat()}"
        )
    except ValueError as exc:
        logger.warning("Validation error: %s", exc)
        return f"Error: {exc}"
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error from Open-Meteo: %s", exc)
        return f"Error: Failed to fetch weather data – {exc.response.status_code}"
    except Exception as exc:
        logger.error("Unexpected error: %s", exc, exc_info=True)
        return f"Error: An unexpected error occurred – {exc}"


@mcp.tool()
async def get_forecast(
    latitude: float, longitude: float, days: int = 7
) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude coordinate (-90 to 90).
        longitude: Longitude coordinate (-180 to 180).
        days: Number of forecast days (1-16, default 7).

    Returns:
        A formatted string listing the daily forecast.
    """
    logger.info(
        "Tool invoked: get_forecast(lat=%s, lon=%s, days=%s)",
        latitude,
        longitude,
        days,
    )
    try:
        forecast = await _client.get_forecast(latitude, longitude, days)
        lines = [f"Weather forecast for ({latitude}, {longitude}) – {days} day(s):\n"]
        for day in forecast.forecasts:
            lines.append(
                f"  {day.forecast_date}: {day.conditions} "
                f"(WMO {day.weather_code}), "
                f"{day.temperature_min}°C – {day.temperature_max}°C, "
                f"Precipitation: {day.precipitation} mm"
            )
        return "\n".join(lines)
    except ValueError as exc:
        logger.warning("Validation error: %s", exc)
        return f"Error: {exc}"
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error from Open-Meteo: %s", exc)
        return f"Error: Failed to fetch forecast – {exc.response.status_code}"
    except Exception as exc:
        logger.error("Unexpected error: %s", exc, exc_info=True)
        return f"Error: An unexpected error occurred – {exc}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

TransportType = Literal["stdio", "sse", "streamable-http"]


def _parse_args() -> TransportType:
    """Parse CLI arguments and return chosen transport."""
    parser = argparse.ArgumentParser(description="Weather MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="MCP transport to use (default: stdio, or MCP_TRANSPORT env var)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "0.0.0.0"),
        help="Host to bind (SSE/HTTP, default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "8000")),
        help="Port to bind (SSE/HTTP, default: 8000)",
    )
    args = parser.parse_args()

    # FastMCP uses FASTMCP_ prefix for settings
    os.environ["FASTMCP_HOST"] = args.host
    os.environ["FASTMCP_PORT"] = str(args.port)

    return args.transport  # type: ignore[return-value]


def main() -> None:
    """Start the Weather MCP Server with the selected transport."""
    transport = _parse_args()

    # Apply host/port to the already-constructed FastMCP instance
    mcp.settings.host = os.environ.get("FASTMCP_HOST", "0.0.0.0")
    mcp.settings.port = int(os.environ.get("FASTMCP_PORT", "8000"))

    # When binding to a non-loopback address (e.g. 0.0.0.0 in a container),
    # disable the default DNS-rebinding protection so that external Host
    # headers (like an Azure FQDN) are accepted.
    if mcp.settings.host not in ("127.0.0.1", "localhost", "::1"):
        mcp.settings.transport_security = None

    logger.info("Starting Weather MCP Server with transport=%s", transport)
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
