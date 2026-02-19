"""Integration tests for MCP transport layers.

These tests verify that the MCP server can be started with each transport
and that the tools are properly registered.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from mcp.server.fastmcp import FastMCP

from src.weather_server import mcp


class TestServerSetup:
    """Tests for MCP server configuration."""

    def test_server_is_fastmcp_instance(self) -> None:
        assert isinstance(mcp, FastMCP)

    def test_server_has_tools(self) -> None:
        """Verify both tools are registered."""
        tools = mcp._tool_manager._tools
        tool_names = list(tools.keys())
        assert "get_current_weather" in tool_names
        assert "get_forecast" in tool_names

    def test_tool_count(self) -> None:
        """Ensure exactly two tools are registered."""
        tools = mcp._tool_manager._tools
        assert len(tools) == 2


class TestTransportSelection:
    """Tests for transport CLI argument parsing."""

    def test_stdio_transport_default(self) -> None:
        """Verify stdio is the default transport."""
        from src.weather_server import _parse_args

        with patch("sys.argv", ["weather_server.py"]):
            transport = _parse_args()
        assert transport == "stdio"

    def test_sse_transport_arg(self) -> None:
        from src.weather_server import _parse_args

        with patch("sys.argv", ["weather_server.py", "--transport", "sse"]):
            transport = _parse_args()
        assert transport == "sse"

    def test_streamable_http_transport_arg(self) -> None:
        from src.weather_server import _parse_args

        with patch(
            "sys.argv",
            ["weather_server.py", "--transport", "streamable-http"],
        ):
            transport = _parse_args()
        assert transport == "streamable-http"

    def test_env_var_fallback(self) -> None:
        from src.weather_server import _parse_args

        with (
            patch("sys.argv", ["weather_server.py"]),
            patch.dict("os.environ", {"MCP_TRANSPORT": "sse"}),
        ):
            transport = _parse_args()
        assert transport == "sse"


class TestToolSchemas:
    """Tests for MCP tool input schemas."""

    def _get_tool(self, name: str):
        return mcp._tool_manager._tools[name]

    def test_get_current_weather_params(self) -> None:
        tool = self._get_tool("get_current_weather")
        schema = tool.parameters
        assert "latitude" in schema["properties"]
        assert "longitude" in schema["properties"]
        assert set(schema["required"]) == {"latitude", "longitude"}

    def test_get_forecast_params(self) -> None:
        tool = self._get_tool("get_forecast")
        schema = tool.parameters
        assert "latitude" in schema["properties"]
        assert "longitude" in schema["properties"]
        assert "days" in schema["properties"]
        # days should not be required (has default)
        assert "days" not in schema.get("required", [])
