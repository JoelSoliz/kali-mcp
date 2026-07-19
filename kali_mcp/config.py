"""Load and validate Kali MCP configuration from JSON files."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from kali_mcp.builtin_tools import ensure_builtin_tools
from kali_mcp.schema import ServerConfig, parse_config

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_NAME = "kali-mcp.config.json"


def resolve_config_path(explicit: str | None = None) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        return path

    candidates = [
        Path.cwd() / "config" / DEFAULT_CONFIG_NAME,
        Path.cwd() / DEFAULT_CONFIG_NAME,
        Path(__file__).resolve().parent.parent / "config" / DEFAULT_CONFIG_NAME,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "No configuration file found. Pass --config or place "
        f"{DEFAULT_CONFIG_NAME} in ./config/ or the current directory."
    )


def load_config(explicit: str | None = None) -> tuple[ServerConfig, Path]:
    path = resolve_config_path(explicit)
    logger.info("Loading configuration from %s", path)

    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    config = ensure_builtin_tools(parse_config(data))
    enabled = [t for t in config.tools if t.enabled]
    logger.info("Loaded %d tool(s) (%d enabled)", len(config.tools), len(enabled))
    return config, path
