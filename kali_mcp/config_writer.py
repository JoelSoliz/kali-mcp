"""Serialize ServerConfig and discovered tools to JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from kali_mcp.schema import ParameterDef, ServerConfig, ToolDef


def parameter_to_dict(param: ParameterDef) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": param.name,
        "description": param.description,
        "type": param.type,
        "required": param.required,
        "argStyle": param.arg_style,
    }
    if param.default is not None and param.default != "":
        data["default"] = param.default
    if param.flag:
        data["flag"] = param.flag
    if param.position is not None:
        data["position"] = param.position
    return data


def tool_to_dict(tool: ToolDef) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": tool.name,
        "binary": tool.binary,
        "enabled": tool.enabled,
        "category": tool.category,
        "description": tool.description,
        "parameters": [parameter_to_dict(p) for p in tool.parameters],
        "allowAdditionalArgs": tool.allow_additional_args,
    }
    if tool.man_page and tool.man_page != tool.binary:
        data["manPage"] = tool.man_page
    if tool.version_flags != ["--version", "-V", "-v"]:
        data["versionFlags"] = tool.version_flags
    if tool.timeout is not None:
        data["timeout"] = tool.timeout
    if tool.fixed_args:
        data["fixedArgs"] = tool.fixed_args
    return data


def config_to_dict(config: ServerConfig) -> dict[str, Any]:
    return {
        "$schema": "./kali-mcp.schema.json",
        "server": {
            "name": config.name,
            "version": config.version,
            "description": config.description
            or "Auto-generated Kali MCP configuration from installed tools.",
        },
        "defaults": {
            "timeout": config.defaults.timeout,
            "manPageSource": config.defaults.man_page_source,
            "versionCheck": config.defaults.version_check,
            **(
                {"workingDirectory": config.defaults.working_directory}
                if config.defaults.working_directory
                else {}
            ),
            **({"environment": config.defaults.environment} if config.defaults.environment else {}),
        },
        "tools": [tool_to_dict(tool) for tool in config.tools if tool.enabled],
    }


def write_config(config: ServerConfig, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = config_to_dict(config)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def config_to_json_string(config: ServerConfig, indent: int = 2) -> str:
    return json.dumps(config_to_dict(config), indent=indent, ensure_ascii=False)
