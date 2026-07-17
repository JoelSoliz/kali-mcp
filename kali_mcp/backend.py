"""Execution backends for local (Kali) and remote (HTTP) tool runs."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from kali_mcp.command_builder import CommandBuildError, build_command
from kali_mcp.executor import run_command
from kali_mcp.introspection import build_tool_metadata
from kali_mcp.remote_client import KaliApiClient
from kali_mcp.schema import ServerConfig, ToolDef

logger = logging.getLogger(__name__)


class ExecutionBackend(Protocol):
    def get_tool_metadata(self, tool: ToolDef, config: ServerConfig) -> dict[str, Any]: ...

    def execute_tool(self, tool: ToolDef, arguments: dict[str, Any], config: ServerConfig) -> dict[str, Any]: ...

    def warm_metadata(self, tools: list[ToolDef], config: ServerConfig) -> dict[str, dict[str, Any]]: ...

    def reload_metadata(self, tool_name: str = "") -> dict[str, Any] | None: ...


class LocalBackend:
    """Run commands directly on the host where this process is running (Kali)."""

    def get_tool_metadata(self, tool: ToolDef, config: ServerConfig) -> dict[str, Any]:
        return build_tool_metadata(
            binary=tool.binary,
            man_page=tool.man_page,
            version_flags=tool.version_flags,
            use_man=config.defaults.man_page_source,
            use_version=config.defaults.version_check,
        )

    def execute_tool(self, tool: ToolDef, arguments: dict[str, Any], config: ServerConfig) -> dict[str, Any]:
        try:
            command = build_command(tool, arguments)
        except CommandBuildError as exc:
            return {"success": False, "error": str(exc), "tool": tool.name}

        timeout = tool.timeout or config.defaults.timeout
        result = run_command(
            command,
            timeout=timeout,
            cwd=config.defaults.working_directory,
            env=config.defaults.environment or None,
        )
        result["tool"] = tool.name
        result["binary"] = tool.binary
        return result

    def warm_metadata(self, tools: list[ToolDef], config: ServerConfig) -> dict[str, dict[str, Any]]:
        return {tool.name: self.get_tool_metadata(tool, config) for tool in tools}

    def reload_metadata(self, tool_name: str = "") -> dict[str, Any] | None:
        return None


class RemoteBackend:
    """Delegate execution and metadata to a Kali API server over HTTP."""

    def __init__(self, api_client: KaliApiClient):
        self.api = api_client

    def get_tool_metadata(self, tool: ToolDef, config: ServerConfig) -> dict[str, Any]:
        del config
        response = self.api.get_tool_metadata(tool.name)
        if response.get("success") is False:
            return {
                "binary": tool.binary,
                "installed": False,
                "error": response.get("error", "Failed to fetch remote metadata"),
            }
        return response.get("metadata", response)

    def execute_tool(self, tool: ToolDef, arguments: dict[str, Any], config: ServerConfig) -> dict[str, Any]:
        del config
        return self.api.execute_tool(tool.name, arguments)

    def warm_metadata(self, tools: list[ToolDef], config: ServerConfig) -> dict[str, dict[str, Any]]:
        del config
        response = self.api.list_tools()
        if response.get("error"):
            logger.warning("Remote warm cache failed: %s", response["error"])
            return {}

        remote_tools = {item["name"]: item for item in response.get("tools", [])}
        cache: dict[str, dict[str, Any]] = {}
        for tool in tools:
            remote = remote_tools.get(tool.name, {})
            cache[tool.name] = {
                "binary": tool.binary,
                "installed": remote.get("installed", False),
                "path": remote.get("path"),
                "version_info": {"version": remote.get("version")},
                "man": {"available": remote.get("man_available", False)},
            }
        return cache

    def reload_metadata(self, tool_name: str = "") -> dict[str, Any] | None:
        return self.api.reload_metadata(tool_name)
