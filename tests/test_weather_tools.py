"""Unit tests for the Weather MCP Server tools and OpenMeteoClient."""

from __future__ import annotations

from datetime import date, datetime, timezone

import httpx
import pytest
import respx

from src.weather_server import (
    CurrentWeather,
    DailyForecast,
    ForecastResponse,
    OpenMeteoClient,
    WeatherLocation,
    get_current_weather,
    get_forecast,
    weather_code_to_conditions,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client() -> OpenMeteoClient:
    """Return a fresh OpenMeteoClient for each test."""
    return OpenMeteoClient()


# ---------------------------------------------------------------------------
# WMO code mapping
# ---------------------------------------------------------------------------


class TestWeatherCodeMapping:
    """Tests for weather_code_to_conditions."""

    def test_known_code(self) -> None:
        assert weather_code_to_conditions(0) == "Clear sky"
        assert weather_code_to_conditions(95) == "Thunderstorm"

    def test_unknown_code(self) -> None:
        result = weather_code_to_conditions(999)
        assert "Unknown" in result
        assert "999" in result


# ---------------------------------------------------------------------------
# Coordinate validation
# ---------------------------------------------------------------------------


class TestCoordinateValidation:
    """Tests for coordinate validation logic."""

    def test_valid_coordinates(self, client: OpenMeteoClient) -> None:
        # Should not raise
        client._validate_coordinates(0, 0)
        client._validate_coordinates(90, 180)
        client._validate_coordinates(-90, -180)

    def test_latitude_out_of_range(self, client: OpenMeteoClient) -> None:
        with pytest.raises(ValueError, match="Latitude"):
            client._validate_coordinates(91, 0)
        with pytest.raises(ValueError, match="Latitude"):
            client._validate_coordinates(-91, 0)

    def test_longitude_out_of_range(self, client: OpenMeteoClient) -> None:
        with pytest.raises(ValueError, match="Longitude"):
            client._validate_coordinates(0, 181)
        with pytest.raises(ValueError, match="Longitude"):
            client._validate_coordinates(0, -181)


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestDataModels:
    """Tests for Pydantic data models."""

    def test_weather_location_valid(self) -> None:
        loc = WeatherLocation(latitude=52.52, longitude=13.41)
        assert loc.latitude == 52.52
        assert loc.longitude == 13.41

    def test_weather_location_invalid_latitude(self) -> None:
        with pytest.raises(Exception):
            WeatherLocation(latitude=100, longitude=0)

    def test_current_weather_model(self) -> None:
        cw = CurrentWeather(
            temperature=20.5,
            wind_speed=12.3,
            weather_code=0,
            conditions="Clear sky",
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        assert cw.temperature == 20.5
        assert cw.conditions == "Clear sky"

    def test_daily_forecast_model(self) -> None:
        df = DailyForecast(
            forecast_date=date(2025, 1, 1),
            temperature_min=5.0,
            temperature_max=15.0,
            precipitation=1.2,
            weather_code=61,
            conditions="Slight rain",
        )
        assert df.temperature_max == 15.0

    def test_forecast_response_model(self) -> None:
        fr = ForecastResponse(
            location=WeatherLocation(latitude=1.0, longitude=2.0),
            forecasts=[],
        )
        assert fr.forecasts == []


# ---------------------------------------------------------------------------
# OpenMeteoClient – mocked HTTP
# ---------------------------------------------------------------------------

CURRENT_WEATHER_RESPONSE = {
    "current": {
        "time": "2025-06-15T12:00",
        "temperature_2m": 22.5,
        "wind_speed_10m": 15.3,
        "weather_code": 2,
    }
}

FORECAST_RESPONSE = {
    "daily": {
        "time": ["2025-06-15", "2025-06-16", "2025-06-17"],
        "temperature_2m_max": [25.0, 27.0, 23.0],
        "temperature_2m_min": [15.0, 17.0, 14.0],
        "precipitation_sum": [0.0, 2.5, 0.1],
        "weather_code": [0, 63, 1],
    }
}


class TestOpenMeteoClientCurrentWeather:
    """Tests for OpenMeteoClient.get_current_weather (mocked)."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, client: OpenMeteoClient) -> None:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=httpx.Response(200, json=CURRENT_WEATHER_RESPONSE)
        )
        result = await client.get_current_weather(52.52, 13.41)
        assert isinstance(result, CurrentWeather)
        assert result.temperature == 22.5
        assert result.wind_speed == 15.3
        assert result.weather_code == 2
        assert result.conditions == "Partly cloudy"

    @pytest.mark.asyncio
    async def test_invalid_coordinates(self, client: OpenMeteoClient) -> None:
        with pytest.raises(ValueError):
            await client.get_current_weather(100, 0)

    @pytest.mark.asyncio
    @respx.mock
    async def test_api_error(self, client: OpenMeteoClient) -> None:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=httpx.Response(500)
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_current_weather(52.52, 13.41)


class TestOpenMeteoClientForecast:
    """Tests for OpenMeteoClient.get_forecast (mocked)."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success(self, client: OpenMeteoClient) -> None:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=httpx.Response(200, json=FORECAST_RESPONSE)
        )
        result = await client.get_forecast(52.52, 13.41, days=3)
        assert isinstance(result, ForecastResponse)
        assert len(result.forecasts) == 3
        assert result.forecasts[0].temperature_max == 25.0
        assert result.forecasts[1].conditions == "Moderate rain"

    @pytest.mark.asyncio
    async def test_invalid_days(self, client: OpenMeteoClient) -> None:
        with pytest.raises(ValueError, match="Days"):
            await client.get_forecast(0, 0, days=0)
        with pytest.raises(ValueError, match="Days"):
            await client.get_forecast(0, 0, days=17)


# ---------------------------------------------------------------------------
# MCP tool handler tests (mocked)
# ---------------------------------------------------------------------------


class TestGetCurrentWeatherTool:
    """Tests for the get_current_weather MCP tool handler."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success_output(self) -> None:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=httpx.Response(200, json=CURRENT_WEATHER_RESPONSE)
        )
        result = await get_current_weather(52.52, 13.41)
        assert "22.5" in result
        assert "Partly cloudy" in result

    @pytest.mark.asyncio
    async def test_invalid_coordinates_output(self) -> None:
        result = await get_current_weather(200, 0)
        assert "Error" in result

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_error_output(self) -> None:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=httpx.Response(503)
        )
        result = await get_current_weather(52.52, 13.41)
        assert "Error" in result


class TestGetForecastTool:
    """Tests for the get_forecast MCP tool handler."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_success_output(self) -> None:
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=httpx.Response(200, json=FORECAST_RESPONSE)
        )
        result = await get_forecast(52.52, 13.41, 3)
        assert "forecast" in result.lower()
        assert "25.0" in result

    @pytest.mark.asyncio
    async def test_invalid_coordinates_output(self) -> None:
        result = await get_forecast(200, 0)
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_invalid_days_output(self) -> None:
        result = await get_forecast(0, 0, days=20)
        assert "Error" in result
