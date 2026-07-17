"""Build argv command lists from declarative tool definitions."""

from __future__ import annotations

import shlex
from typing import Any

from kali_mcp.schema import ToolDef


class CommandBuildError(ValueError):
    pass


def build_command(tool: ToolDef, arguments: dict[str, Any]) -> list[str]:
    """Translate MCP tool arguments into a safe argv list."""
    command = [tool.binary, *tool.fixed_args]
    positional: list[tuple[int, str]] = []
    append_tokens: list[str] = []

    for param in tool.parameters:
        value = arguments.get(param.name, param.default)
        if value is None or value == "":
            if param.required:
                raise CommandBuildError(f"Missing required parameter: {param.name}")
            continue

        if param.type == "boolean":
            if value and param.flag:
                command.append(param.flag)
            continue

        if param.arg_style == "append":
            append_tokens.extend(shlex.split(str(value)))
            continue

        if param.arg_style == "positional":
            position = param.position if param.position is not None else len(positional)
            positional.append((position, str(value)))
            continue

        if param.arg_style == "flag":
            if param.flag:
                command.append(param.flag)
            continue

        if param.arg_style in ("kv", "long"):
            if not param.flag:
                raise CommandBuildError(f"Parameter {param.name} requires a flag")
            command.append(param.flag)
            command.append(str(value))
            continue

        raise CommandBuildError(f"Unsupported arg style for {param.name}: {param.arg_style}")

    command.extend(append_tokens)

    for _, value in sorted(positional, key=lambda item: item[0]):
        command.append(value)

    if tool.allow_additional_args:
        extra = arguments.get(tool.additional_args_param, "")
        if extra:
            command.extend(shlex.split(str(extra)))

    return command
