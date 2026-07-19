"""Validate and reconcile local vs remote MCP tool configuration."""

from __future__ import annotations

import logging
from typing import Any

from kali_mcp.builtin_tools import ensure_builtin_tools
from kali_mcp.remote_client import KaliApiClient
from kali_mcp.schema import ServerConfig, parse_config

logger = logging.getLogger(__name__)


def load_config_from_remote(client: KaliApiClient) -> ServerConfig | None:
    payload = client.get_config()
    if payload.get("error"):
        logger.error("Failed to load remote config: %s", payload["error"])
        return None
    return ensure_builtin_tools(parse_config(payload))


def build_remote_name_map(client: KaliApiClient) -> dict[str, str]:
    """Map local tool/binary identifiers to the remote server's tool names."""
    response = client.list_tools()
    if response.get("error"):
        return {}

    by_name = {item["name"]: item["name"] for item in response.get("tools", [])}
    by_binary: dict[str, str] = {}
    for item in response.get("tools", []):
        binary = item.get("binary")
        if binary and binary not in by_binary:
            by_binary[binary] = item["name"]

    mapping = dict(by_name)
    mapping.update(by_binary)
    return mapping


def validate_remote_tools(config: ServerConfig, client: KaliApiClient) -> list[str]:
    """Return local tool names that cannot be resolved on the remote API."""
    remote_names = {item["name"] for item in client.list_tools().get("tools", [])}
    remote_binaries = {
        item.get("binary"): item["name"]
        for item in client.list_tools().get("tools", [])
        if item.get("binary")
    }

    missing: list[str] = []
    for tool in config.tools:
        if not tool.enabled:
            continue
        if tool.name in remote_names:
            continue
        if tool.binary in remote_binaries:
            continue
        missing.append(tool.name)
    return missing


def resolve_remote_tool_name(
    tool_name: str,
    binary: str,
    name_map: dict[str, str],
    remote_tools: list[dict[str, Any]] | None = None,
) -> str | None:
    if tool_name in name_map:
        return name_map[tool_name]

    if binary in name_map:
        return name_map[binary]

    if remote_tools:
        for item in remote_tools:
            if item.get("binary") == binary:
                return item["name"]

    return None
