"""MCP Llms-txt server for docs."""

import os
import re
from urllib.parse import urlparse, urljoin

import httpx
from markdownify import markdownify
from mcp.server.fastmcp import FastMCP
from typing_extensions import NotRequired, TypedDict


class DocSource(TypedDict):
    """A source of documentation for a library or a package."""

    name: NotRequired[str]
    """Name of the documentation source (optional)."""

    llms_txt: str
    """URL to the llms.txt file or documentation source."""

    description: NotRequired[str]
    """Description of the documentation source (optional)."""


def extract_domain(url: str) -> str:
    """Extract domain from URL.

    Args:
        url: Full URL

    Returns:
        Domain with scheme and trailing slash (e.g., https://example.com/)
    """
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/"


def _is_http_or_https(url: str) -> bool:
    """Check if the URL is an HTTP or HTTPS URL."""
    return url.startswith(("http:", "https:"))


def _get_fetch_description(has_local_sources: bool) -> str:
    """Get fetch docs tool description."""
    description = [
        "Fetch and parse documentation from a given URL or local file.",
        "",
        "Use this tool after list_doc_sources to:",
        "1. First fetch the llms.txt file from a documentation source",
        "2. Analyze the URLs listed in the llms.txt file",
        "3. Then fetch specific documentation pages relevant to the user's question",
        "",
    ]

    if has_local_sources:
        description.extend(
            [
                "Args:",
                "    url: The URL or file path to fetch documentation from. Can be:",
                "        - URL from an allowed domain",
                "        - A local file path (absolute or relative)",
                "        - A file:// URL (e.g., file:///path/to/llms.txt)",
            ]
        )
    else:
        description.extend(
            [
                "Args:",
                "    url: The URL to fetch documentation from.",
            ]
        )

    description.extend(
        [
            "",
            "Returns:",
            "    The fetched documentation content converted to markdown, or an error message",  # noqa: E501
            "    if the request fails or the URL is not from an allowed domain.",
        ]
    )

    return "\n".join(description)


def _normalize_path(path: str) -> str:
    """Accept paths in file:/// or relative format and map to absolute paths."""
    return (
        os.path.abspath(path[7:])
        if path.startswith("file://")
        else os.path.abspath(path)
    )


def _get_server_instructions(doc_sources: list[DocSource]) -> str:
    """Generate server instructions with available documentation source names."""
    # Extract source names from doc_sources
    source_names = []
    for entry in doc_sources:
        if "name" in entry:
            source_names.append(entry["name"])
        elif _is_http_or_https(entry["llms_txt"]):
            # Use domain name as fallback for HTTP sources
            domain = extract_domain(entry["llms_txt"])
            source_names.append(domain.rstrip("/").split("//")[-1])
        else:
            # Use filename as fallback for local sources
            source_names.append(os.path.basename(entry["llms_txt"]))

    instructions = [
        "Use the list_doc_sources tool to see available documentation sources.",
        "This tool will return a URL for each documentation source.",
    ]

    if source_names:
        if len(source_names) == 1:
            instructions.append(
                f"Documentation URLs are available from this tool "
                f"for {source_names[0]}."
            )
        else:
            names_str = ", ".join(source_names[:-1]) + f", and {source_names[-1]}"
            instructions.append(
                f"Documentation URLs are available from this tool for {names_str}."
            )

    instructions.extend(
        [
            "",
            "Once you have a source documentation URL, use the fetch_docs tool "
            "to get the documentation contents. ",
            "If the documentation contents contains a URL for additional documentation "
            "that is relevant to your task, you can use the fetch_docs tool to "
            "fetch documentation from that URL next.",
        ]
    )

    return "\n".join(instructions)


def create_server(
    doc_sources: list[DocSource],
    *,
    follow_redirects: bool = False,
    timeout: float = 10,
    settings: dict | None = None,
    allowed_domains: list[str] | None = None,
) -> FastMCP:
    """Create the server and generate documentation retrieval tools.

    Args:
        doc_sources: List of documentation sources to make available
        follow_redirects: Whether to follow HTTP redirects when fetching docs
        timeout: HTTP request timeout in seconds
        settings: Additional settings to pass to FastMCP
        allowed_domains: Additional domains to allow fetching from.
            Use ['*'] to allow all domains
            The domain hosting the llms.txt file is always appended to the list
            of allowed domains.

    Returns:
        A FastMCP server instance configured with documentation tools
    """
    settings = settings or {}
    server = FastMCP(
        name="llms-txt",
        instructions=_get_server_instructions(doc_sources),
        **settings,
    )
    httpx_client = httpx.AsyncClient(follow_redirects=follow_redirects, timeout=timeout)

    local_sources = []
    remote_sources = []

    for entry in doc_sources:
        url = entry["llms_txt"]
        if _is_http_or_https(url):
            remote_sources.append(entry)
        else:
            local_sources.append(entry)

    # Let's verify that all local sources exist
    for entry in local_sources:
        path = entry["llms_txt"]
        abs_path = _normalize_path(path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Local file not found: {abs_path}")

    # Parse the domain names in the llms.txt URLs and identify local file paths
    domains = set(extract_domain(entry["llms_txt"]) for entry in remote_sources)

    # Add additional allowed domains if specified, or set to '*' if we have local files
    if allowed_domains:
        if "*" in allowed_domains:
            domains = {"*"}  # Special marker for allowing all domains
        else:
            domains.update(allowed_domains)

    allowed_local_files = set(
        _normalize_path(entry["llms_txt"]) for entry in local_sources
    )

    @server.tool()
    def list_doc_sources() -> str:
        """List all available documentation sources.

        This is the first tool you should call in the documentation workflow.
        It provides URLs to llms.txt files or local file paths that the user has made available.

        Returns:
            A string containing a formatted list of documentation sources with their URLs or file paths
        """
        content = ""
        for entry_ in doc_sources:
            url_or_path = entry_["llms_txt"]

            if _is_http_or_https(url_or_path):
                name = entry_.get("name", extract_domain(url_or_path))
                content += f"{name}\nURL: {url_or_path}\n\n"
            else:
                path = _normalize_path(url_or_path)
                name = entry_.get("name", path)
                content += f"{name}\nPath: {path}\n\n"
        return content

    fetch_docs_description = _get_fetch_description(
        has_local_sources=bool(local_sources)
    )

    @server.tool(description=fetch_docs_description)
    async def fetch_docs(url: str) -> str:
        nonlocal domains, follow_redirects
        url = url.strip()
        # Handle local file paths (either as file:// URLs or direct filesystem paths)
        if not _is_http_or_https(url):
            abs_path = _normalize_path(url)
            if abs_path not in allowed_local_files:
                raise ValueError(
                    f"Local file not allowed: {abs_path}. Allowed files: {allowed_local_files}"
                )
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return markdownify(content)
            except Exception as e:
                return f"Error reading local file: {str(e)}"
        else:
            # Otherwise treat as URL
            if "*" not in domains and not any(
                url.startswith(domain) for domain in domains
            ):
                return (
                    "Error: URL not allowed. Must start with one of the following domains: "
                    + ", ".join(domains)
                )

            try:
                response = await httpx_client.get(url, timeout=timeout)
                response.raise_for_status()
                content = response.text

                if follow_redirects:
                    # Check for meta refresh tag which indicates a client-side redirect
                    match = re.search(
                        r'<meta http-equiv="refresh" content="[^;]+;\s*url=([^"]+)"',
                        content,
                        re.IGNORECASE,
                    )

                    if match:
                        redirect_url = match.group(1)
                        new_url = urljoin(str(response.url), redirect_url)

                        if "*" not in domains and not any(
                            new_url.startswith(domain) for domain in domains
                        ):
                            return (
                                "Error: Redirect URL not allowed. Must start with one of the following domains: "
                                + ", ".join(domains)
                            )

                        response = await httpx_client.get(new_url, timeout=timeout)
                        response.raise_for_status()
                        content = response.text

                return markdownify(content)
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                return f"Encountered an HTTP error: {str(e)}"

    return server
