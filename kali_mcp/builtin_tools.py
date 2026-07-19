"""Built-in MCP tools that are always available regardless of discovery output."""

from __future__ import annotations

from kali_mcp.schema import ParameterDef, ServerConfig, ToolDef

RUN_COMMAND_TOOL = ToolDef(
    name="run_command",
    binary="bash",
    category="utility",
    description=(
        "Execute a shell command on the Kali host via bash -lc. "
        "Use only when no dedicated MCP tool exists. "
        "Supports shell operators: &&, ;, |, 2>/dev/null, $(...) within the command string."
    ),
    enabled=True,
    parameters=[
        ParameterDef(
            name="command",
            description="Shell command to execute (may include &&, ;, |, redirects)",
            type="string",
            required=True,
            arg_style="positional",
            position=0,
        )
    ],
    fixed_args=["-lc"],
    allow_additional_args=False,
)

BUILTIN_TOOLS: tuple[ToolDef, ...] = (RUN_COMMAND_TOOL,)


def ensure_builtin_tools(config: ServerConfig) -> ServerConfig:
    """Append built-in tools missing from a loaded or generated config."""
    existing_names = {tool.name for tool in config.tools}
    for tool in BUILTIN_TOOLS:
        if tool.name not in existing_names:
            config.tools.append(tool)
    return config
