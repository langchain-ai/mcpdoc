#!/usr/bin/env python3
"""Command-line interface for mcp-llms-txt server."""

import argparse
import json
import sys
from typing import List, Dict

import yaml

from mcpdoc._version import __version__
from mcpdoc.main import create_server, DocSource
from mcpdoc.splash import SPLASH


class CustomFormatter(
    argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter
):
    # Custom formatter to preserve epilog formatting while showing default values
    pass


EPILOG = """
Examples:
  # Directly specifying llms.txt URLs with optional names
  mcpdoc --urls LangGraph:https://langchain-ai.github.io/langgraph/llms.txt
  
  # Using a local file (absolute or relative path)
  mcpdoc --urls LocalDocs:/path/to/llms.txt --allowed-domains '*'
  
  # Using a YAML config file
  mcpdoc --yaml sample_config.yaml

  # Using a JSON config file
  mcpdoc --json sample_config.json

  # Combining multiple documentation sources
  mcpdoc --yaml sample_config.yaml --json sample_config.json --urls LangGraph:https://langchain-ai.github.io/langgraph/llms.txt

  # Using SSE transport with default host (127.0.0.1) and port (8000)
  mcpdoc --yaml sample_config.yaml --transport sse
  
  # Using SSE transport with custom host and port
  mcpdoc --yaml sample_config.yaml --transport sse --host 0.0.0.0 --port 9000
  
  # Using SSE transport with additional HTTP options
  mcpdoc --yaml sample_config.yaml --follow-redirects --timeout 15 --transport sse --host localhost --port 8080
  
  # Allow fetching from additional domains. The domains hosting the llms.txt files are always allowed.
  mcpdoc --yaml sample_config.yaml --allowed-domains https://example.com/ https://another-example.com/
  
  # Allow fetching from any domain
  mcpdoc --yaml sample_config.yaml --allowed-domains '*'
"""


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    # Custom formatter to preserve epilog formatting
    parser = argparse.ArgumentParser(
        description="MCP LLMS-TXT Documentation Server",
        formatter_class=CustomFormatter,
        epilog=EPILOG,
    )

    # Allow combining multiple doc source methods
    parser.add_argument(
        "--yaml", "-y", type=str, help="Path to YAML config file with doc sources"
    )
    parser.add_argument(
        "--json", "-j", type=str, help="Path to JSON config file with doc sources"
    )
    parser.add_argument(
        "--urls",
        "-u",
        type=str,
        nargs="+",
        help="List of llms.txt URLs or file paths with optional names (format: 'url_or_path' or 'name:url_or_path')",
    )

    parser.add_argument(
        "--follow-redirects",
        action="store_true",
        help="Whether to follow HTTP redirects",
    )
    parser.add_argument(
        "--allowed-domains",
        type=str,
        nargs="*",
        help="Additional allowed domains to fetch documentation from. Use '*' to allow all domains.",
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="HTTP request timeout in seconds"
    )
    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        choices=["stdio", "sse"],
        help="Transport protocol for MCP server",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help=(
            "Log level for the server. Use one on the following: DEBUG, INFO, "
            "WARNING, ERROR."
            " (only used with --transport sse)"
        ),
    )

    # SSE-specific options
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to (only used with --transport sse)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (only used with --transport sse)",
    )

    # Version information
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"mcpdoc {__version__}",
        help="Show version information and exit",
    )

    return parser.parse_args()


def load_config_file(file_path: str, file_format: str) -> List[Dict[str, str]]:
    """Load configuration from a file.

    Args:
        file_path: Path to the config file
        file_format: Format of the config file ("yaml" or "json")

    Returns:
        List of doc source configurations
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            if file_format.lower() == "yaml":
                config = yaml.safe_load(file)
            elif file_format.lower() == "json":
                config = json.load(file)
            else:
                raise ValueError(f"Unsupported file format: {file_format}")

        if not isinstance(config, list):
            raise ValueError("Config file must contain a list of doc sources")

        return config
    except (FileNotFoundError, yaml.YAMLError, json.JSONDecodeError) as e:
        print(f"Error loading config file: {e}", file=sys.stderr)
        sys.exit(1)


def create_doc_sources_from_urls(urls: List[str]) -> List[DocSource]:
    """Create doc sources from a list of URLs or file paths with optional names.

    Args:
        urls: List of llms.txt URLs or file paths with optional names
             (format: 'url_or_path' or 'name:url_or_path')

    Returns:
        List of DocSource objects
    """
    doc_sources = []
    for entry in urls:
        if not entry.strip():
            continue
        parts = entry.split(":", 1)
        is_windows_drive = len(parts[0]) == 1 and parts[0].isalpha()
        if (
            ":" in entry
            and not entry.startswith(("http:", "https:", "file:"))
            and not is_windows_drive
        ):
            # Format is name:url
            name, url = parts
            doc_sources.append({"name": name, "llms_txt": url})
        else:
            # Format is just url or file: URL or Windows drive path
            doc_sources.append({"llms_txt": entry})
    return doc_sources


def main() -> None:
    """Main entry point for the CLI."""
    # Check if any arguments were provided
    if len(sys.argv) == 1:
        # No arguments, print help
        # Use the same custom formatter as parse_args()
        help_parser = argparse.ArgumentParser(
            description="MCP LLMS-TXT Documentation Server",
            formatter_class=CustomFormatter,
            epilog=EPILOG,
        )
        # Add version to help parser too
        help_parser.add_argument(
            "--version",
            "-V",
            action="version",
            version=f"mcpdoc {__version__}",
            help="Show version information and exit",
        )
        help_parser.print_help()
        sys.exit(0)

    args = parse_args()

    # Load doc sources based on command-line arguments
    doc_sources: List[DocSource] = []

    # Check if any source options were provided
    if not (args.yaml or args.json or args.urls):
        print(
            "Error: At least one source option (--yaml, --json, or --urls) is required",
            file=sys.stderr,
        )
        sys.exit(1)

    # Merge doc sources from all provided methods
    if args.yaml:
        doc_sources.extend(load_config_file(args.yaml, "yaml"))
    if args.json:
        doc_sources.extend(load_config_file(args.json, "json"))
    if args.urls:
        doc_sources.extend(create_doc_sources_from_urls(args.urls))

    # Only used with SSE transport
    settings = {
        "host": args.host,
        "port": args.port,
        "log_level": "INFO",
    }

    # Create and run the server
    server = create_server(
        doc_sources,
        follow_redirects=args.follow_redirects,
        timeout=args.timeout,
        settings=settings,
        allowed_domains=args.allowed_domains,
    )

    if args.transport == "sse":
        print()
        print(SPLASH)
        print()

        print(
            f"Launching MCPDOC server with {len(doc_sources)} doc sources",
        )

    # Pass transport-specific options
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
