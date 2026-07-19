"""HTTP API server — runs on Kali and executes tools for remote MCP clients."""

from __future__ import annotations

import argparse
import logging
import sys

from flask import Flask, jsonify, request

from kali_mcp.backend import LocalBackend
from kali_mcp.config import load_config
from kali_mcp.config_writer import config_to_dict
from kali_mcp.discovery import build_config_from_discovery, discover_installed_tools
from kali_mcp.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

DEFAULT_PORT = 5000
DEFAULT_HOST = "127.0.0.1"


def create_app(registry: ToolRegistry) -> Flask:
    app = Flask(__name__)
    config = registry.config
    backend = registry.backend

    @app.get("/health")
    def health() -> tuple[dict, int]:
        tools = registry.enabled_tools()
        installed = 0
        for tool in tools:
            meta = registry.get_runtime_metadata(tool.name) or {}
            if meta.get("installed"):
                installed += 1

        return jsonify(
            {
                "status": "healthy",
                "server": config.name,
                "version": config.version,
                "tool_count": len(tools),
                "installed_tool_count": installed,
                "mode": "api",
                "config_path": registry.config_path,
            }
        ), 200

    @app.get("/api/config")
    def get_config() -> tuple[dict, int]:
        return jsonify(config_to_dict(config)), 200

    @app.get("/api/tools")
    def list_tools() -> tuple[dict, int]:
        tools_info = []
        for tool in registry.enabled_tools():
            meta = registry.get_runtime_metadata(tool.name) or {}
            version_info = meta.get("version_info", {})
            effective_timeout = tool.timeout or config.defaults.timeout
            tools_info.append(
                {
                    "name": tool.name,
                    "binary": tool.binary,
                    "category": tool.category,
                    "description": tool.description,
                    "installed": meta.get("installed", False),
                    "path": meta.get("path"),
                    "version": version_info.get("version"),
                    "man_available": meta.get("man", {}).get("available", False),
                    "parameters": [p.name for p in tool.parameters],
                    "timeout_seconds": effective_timeout,
                    "supports_shell_chaining": tool.name == "run_command",
                }
            )
        return jsonify(
            {
                "server": config.name,
                "version": config.version,
                "default_timeout_seconds": config.defaults.timeout,
                "tool_count": len(tools_info),
                "tools": tools_info,
            }
        ), 200

    @app.get("/api/tools/<tool_name>")
    def get_tool(tool_name: str) -> tuple[dict, int]:
        tool = registry.find_tool(tool_name) or registry.find_tool_by_binary(tool_name)
        if not tool:
            return jsonify({"success": False, "error": f"Unknown tool: {tool_name}"}), 404

        meta = registry.get_runtime_metadata(tool_name) or {}
        return jsonify(
            {
                "success": True,
                "tool": tool_name,
                "binary": tool.binary,
                "configured_description": tool.description,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "required": p.required,
                        "default": p.default,
                        "flag": p.flag,
                        "description": p.description,
                    }
                    for p in tool.parameters
                ],
                "metadata": meta,
            }
        ), 200

    @app.post("/api/tools/<tool_name>/execute")
    def execute_tool(tool_name: str) -> tuple[dict, int]:
        tool = registry.find_tool(tool_name) or registry.find_tool_by_binary(tool_name)
        if not tool or not tool.enabled:
            return jsonify({"success": False, "error": f"Tool not found or disabled: {tool_name}"}), 404

        payload = request.get_json(silent=True) or {}
        arguments = payload.get("arguments", {})
        result = backend.execute_tool(tool, arguments, config)
        return jsonify(result), 200

    @app.post("/api/tools/metadata/reload")
    def reload_metadata() -> tuple[dict, int]:
        payload = request.get_json(silent=True) or {}
        tool_name = payload.get("tool_name", "")
        if tool_name:
            registry.invalidate_metadata(tool_name)
            meta = registry.get_runtime_metadata(tool_name)
            return jsonify({"success": bool(meta), "tool": tool_name, "metadata": meta}), 200

        registry.invalidate_metadata()
        registry.warm_cache()
        return jsonify({"success": True, "reloaded": [t.name for t in registry.enabled_tools()]}), 200

    @app.post("/api/config/discover")
    def discover_config() -> tuple[dict, int]:
        payload = request.get_json(silent=True) or {}
        categories = payload.get("categories")
        include_dpkg = payload.get("includeDpkg", True)
        include_man_scan = payload.get("includeManScan", False)
        merge_tools = payload.get("mergeWithConfig", False)

        discovered = discover_installed_tools(
            categories=categories,
            include_dpkg=include_dpkg,
            include_man_scan=include_man_scan,
        )
        merge_config = config if merge_tools else None
        generated = build_config_from_discovery(discovered, merge_with=merge_config)
        return jsonify(config_to_dict(generated)), 200

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kali MCP HTTP API server (run on Kali Linux)")
    parser.add_argument("--config", type=str, default=None, help="Path to kali-mcp.config.json")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bind port (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    parser.add_argument("--no-warm-cache", action="store_true", help="Skip man/version pre-load")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    try:
        config, config_path = load_config(args.config)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    registry = ToolRegistry(config, backend=LocalBackend())
    registry.config_path = str(config_path)
    if not args.no_warm_cache:
        logger.info("Warming tool metadata cache...")
        registry.warm_cache()

    app = create_app(registry)
    logger.info("Starting Kali API server on %s:%s", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
