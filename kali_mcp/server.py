"""MCP server entry point."""

from __future__ import annotations

import argparse
import logging
import sys

from kali_mcp.backend import LocalBackend
from kali_mcp.config import load_config
from kali_mcp.tool_call_log import configure_tool_call_logger, set_execution_context
from kali_mcp.remote_client import KaliApiClient
from kali_mcp.remote_sync import load_config_from_remote, validate_remote_tools
from kali_mcp.tool_registry import ToolRegistry, create_mcp_server, create_remote_registry

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Kali MCP — config-driven MCP server for Kali Linux tools",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to kali-mcp.config.json (DAB-style declarative tool loading)",
    )
    parser.add_argument(
        "--remote",
        type=str,
        default=None,
        metavar="URL",
        help="Kali API server URL for Windows->Kali remote mode (e.g. http://127.0.0.1:5000)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="HTTP request timeout in seconds when using --remote (default: 300)",
    )
    parser.add_argument(
        "--use-remote-config",
        action="store_true",
        help="Load tool definitions from the Kali API config instead of local JSON",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--no-warm-cache",
        action="store_true",
        help="Skip pre-loading man/version metadata at startup",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="JSONL audit log for tool executions when running locally (default: logs/tool-calls.jsonl)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    if not args.remote:
        configure_tool_call_logger(args.log_file)

    try:
        config, config_path = load_config(args.config)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    if args.remote:
        client = KaliApiClient(args.remote, timeout=args.timeout)
        health = client.health()
        if health.get("error"):
            logger.warning("Cannot reach Kali API at %s: %s", args.remote, health["error"])
            logger.warning("MCP will start, but tool execution may fail until the API is available")
        else:
            logger.info("Connected to Kali API at %s (%s)", args.remote, health.get("status"))
            if health.get("config_path"):
                logger.info("Remote API config: %s", health["config_path"])

        if args.use_remote_config:
            remote_config = load_config_from_remote(client)
            if remote_config:
                config = remote_config
                logger.info("Using remote tool config from Kali API")
            else:
                logger.warning("Falling back to local config: %s", config_path)

        missing = validate_remote_tools(config, client)
        if missing:
            logger.warning(
                "Local tool names not found on Kali API: %s. "
                "Use the same config on both hosts or add --use-remote-config.",
                ", ".join(missing),
            )

        registry = create_remote_registry(config, args.remote, timeout=args.timeout)
    else:
        registry = ToolRegistry(config, backend=LocalBackend())
        registry.config_path = str(config_path)
        if not args.no_warm_cache:
            logger.info("Warming tool metadata cache (man pages and versions)...")
            registry.warm_cache()

    if args.remote and not args.no_warm_cache:
        logger.info("Fetching remote tool metadata from %s...", args.remote)
        registry.warm_cache()

    mcp = create_mcp_server(config, registry)
    mode = f"remote -> {args.remote}" if args.remote else "local"
    logger.info(
        "Starting %s v%s (%s) with %d configured tool(s)",
        config.name,
        config.version,
        mode,
        len(registry.enabled_tools()),
    )
    mcp.run()


if __name__ == "__main__":
    main()
