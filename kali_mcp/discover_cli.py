"""CLI to auto-discover installed Kali tools and generate JSON config."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from kali_mcp.config import load_config
from kali_mcp.config_writer import config_to_json_string, write_config
from kali_mcp.discovery import build_config_from_discovery, discover_installed_tools

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = "config/kali-mcp.generated.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover installed Kali tools and generate kali-mcp.config.json",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print generated JSON to stdout instead of writing a file",
    )
    parser.add_argument(
        "--merge",
        type=str,
        default=None,
        metavar="CONFIG",
        help="Merge discovered tools into an existing config (skip duplicates by binary)",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Comma-separated categories (reconnaissance,web,exploitation,...)",
    )
    parser.add_argument(
        "--no-dpkg",
        action="store_true",
        help="Skip dpkg-based discovery",
    )
    parser.add_argument(
        "--man-scan",
        action="store_true",
        help="Also discover tools via man -k keyword search (slower, broader)",
    )
    parser.add_argument(
        "--man-scan-limit",
        type=int,
        default=30,
        help="Max extra tools from man -k scan (default: 30)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print discovery summary before writing JSON",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    categories = [c.strip() for c in args.category.split(",")] if args.category else None
    logger.info("Scanning installed tools on this host...")

    discovered = discover_installed_tools(
        categories=categories,
        include_dpkg=not args.no_dpkg,
        include_man_scan=args.man_scan,
        man_scan_limit=args.man_scan_limit,
    )

    if not discovered:
        logger.error("No installed tools discovered. Run this command on Kali Linux.")
        sys.exit(1)

    merge_config = None
    if args.merge:
        try:
            merge_config, _ = load_config(args.merge)
            logger.info("Merging with existing config: %s", args.merge)
        except FileNotFoundError as exc:
            logger.error("%s", exc)
            sys.exit(1)

    config = build_config_from_discovery(discovered, merge_with=merge_config)

    if args.pretty:
        summary = [
            {
                "binary": item.binary,
                "category": item.category,
                "version": item.version,
                "man": item.man_available,
                "source": item.source,
                "path": item.path,
            }
            for item in discovered
        ]
        print(json.dumps({"discovered_count": len(summary), "tools": summary}, indent=2))

    if args.stdout:
        print(config_to_json_string(config))
    else:
        output_path = Path(args.output)
        write_config(config, output_path)
        logger.info("Wrote %d tool(s) to %s", len(config.tools), output_path.resolve())


if __name__ == "__main__":
    main()
