"""Configuration schema for the Kali MCP server (DAB-style declarative loading)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


ArgStyle = Literal["positional", "flag", "kv", "long", "append"]


@dataclass
class ParameterDef:
    name: str
    description: str = ""
    type: str = "string"
    required: bool = False
    default: Any = None
    arg_style: ArgStyle = "kv"
    flag: str | None = None
    position: int | None = None


@dataclass
class ToolDef:
    name: str
    binary: str
    enabled: bool = True
    description: str = ""
    category: str = "general"
    man_page: str | None = None
    version_flags: list[str] = field(default_factory=lambda: ["--version", "-V", "-v"])
    timeout: int | None = None
    parameters: list[ParameterDef] = field(default_factory=list)
    fixed_args: list[str] = field(default_factory=list)
    allow_additional_args: bool = True
    additional_args_param: str = "additional_args"


@dataclass
class ServerDefaults:
    timeout: int = 300
    man_page_source: bool = True
    version_check: bool = True
    working_directory: str | None = None
    environment: dict[str, str] = field(default_factory=dict)


@dataclass
class ServerConfig:
    name: str = "kali-mcp"
    version: str = "0.1.0"
    description: str = ""
    defaults: ServerDefaults = field(default_factory=ServerDefaults)
    tools: list[ToolDef] = field(default_factory=list)


def _parse_parameter(raw: dict[str, Any]) -> ParameterDef:
    return ParameterDef(
        name=raw["name"],
        description=raw.get("description", ""),
        type=raw.get("type", "string"),
        required=raw.get("required", False),
        default=raw.get("default"),
        arg_style=raw.get("argStyle", raw.get("arg_style", "kv")),
        flag=raw.get("flag"),
        position=raw.get("position"),
    )


def _parse_tool(raw: dict[str, Any]) -> ToolDef:
    return ToolDef(
        name=raw["name"],
        binary=raw.get("binary", raw["name"]),
        enabled=raw.get("enabled", True),
        description=raw.get("description", ""),
        category=raw.get("category", "general"),
        man_page=raw.get("manPage", raw.get("man_page")),
        version_flags=raw.get("versionFlags", raw.get("version_flags", ["--version", "-V", "-v"])),
        timeout=raw.get("timeout"),
        parameters=[_parse_parameter(p) for p in raw.get("parameters", [])],
        fixed_args=raw.get("fixedArgs", raw.get("fixed_args", [])),
        allow_additional_args=raw.get("allowAdditionalArgs", raw.get("allow_additional_args", True)),
        additional_args_param=raw.get(
            "additionalArgsParam",
            raw.get("additional_args_param", "additional_args"),
        ),
    )


def parse_config(data: dict[str, Any]) -> ServerConfig:
    """Parse a JSON config document into a ServerConfig."""
    server_block = data.get("server", {})
    defaults_raw = data.get("defaults", {})

    defaults = ServerDefaults(
        timeout=defaults_raw.get("timeout", 300),
        man_page_source=defaults_raw.get("manPageSource", defaults_raw.get("man_page_source", True)),
        version_check=defaults_raw.get("versionCheck", defaults_raw.get("version_check", True)),
        working_directory=defaults_raw.get("workingDirectory", defaults_raw.get("working_directory")),
        environment=defaults_raw.get("environment", {}),
    )

    tools = [_parse_tool(t) for t in data.get("tools", [])]

    return ServerConfig(
        name=server_block.get("name", "kali-mcp"),
        version=server_block.get("version", "0.1.0"),
        description=server_block.get("description", ""),
        defaults=defaults,
        tools=tools,
    )
