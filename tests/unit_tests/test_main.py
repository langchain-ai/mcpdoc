"""Tests for mcpdoc.main module."""

import httpx
import pytest

from mcpdoc.main import (
    _get_fetch_description,
    _is_http_or_https,
    create_server,
    extract_domain,
)


def test_extract_domain() -> None:
    """Test extract_domain function."""
    # Test with https URL
    assert extract_domain("https://example.com/page") == "https://example.com/"

    # Test with http URL
    assert extract_domain("http://test.org/docs/index.html") == "http://test.org/"

    # Test with URL that has port
    assert extract_domain("https://localhost:8080/api") == "https://localhost:8080/"

    # Check trailing slash
    assert extract_domain("https://localhost:8080") == "https://localhost:8080/"

    # Test with URL that has subdomain
    assert extract_domain("https://docs.python.org/3/") == "https://docs.python.org/"


@pytest.mark.parametrize(
    "url,expected",
    [
        ("http://example.com", True),
        ("https://example.com", True),
        ("/path/to/file.txt", False),
        ("file:///path/to/file.txt", False),
        (
            "ftp://example.com",
            False,
        ),  # Not HTTP or HTTPS, even though it's not a local file
    ],
)
def test_is_http_or_https(url, expected):
    """Test _is_http_or_https function."""
    assert _is_http_or_https(url) is expected


@pytest.mark.parametrize(
    "has_local_sources,expected_substrings",
    [
        (True, ["local file path", "file://"]),
        (False, ["URL to fetch"]),
    ],
)
def test_get_fetch_description(has_local_sources, expected_substrings):
    """Test _get_fetch_description function."""
    description = _get_fetch_description(has_local_sources)

    # Common assertions for both cases
    assert "Fetch and parse documentation" in description
    assert "Returns:" in description

    # Specific assertions based on has_local_sources
    for substring in expected_substrings:
        if has_local_sources:
            assert substring in description
        else:
            # For the False case, we only check that "local file path"
            # and "file://" are NOT present
            if substring in ["local file path", "file://"]:
                assert substring not in description


@pytest.mark.asyncio
async def test_fetch_docs_blocks_cross_domain_http_redirect(monkeypatch) -> None:
    """HTTP redirects must be checked against the allowed domains."""
    async_client = httpx.AsyncClient
    requested_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if str(request.url) == "http://allowed.test/redirect":
            return httpx.Response(
                302,
                headers={"location": "http://blocked.test/payload"},
                request=request,
            )
        if str(request.url) == "http://blocked.test/payload":
            return httpx.Response(
                200, text="secret from blocked origin", request=request
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *args, **kwargs: async_client(
            transport=httpx.MockTransport(handler),
            follow_redirects=kwargs.get("follow_redirects", False),
            timeout=kwargs.get("timeout"),
        ),
    )

    server = create_server(
        [{"llms_txt": "http://allowed.test/llms.txt"}],
        follow_redirects=True,
    )

    result = await server.call_tool(
        "fetch_docs",
        {"url": "http://allowed.test/redirect"},
    )

    text = result[0][0].text
    assert "Error: Redirect URL not allowed." in text
    assert "secret from blocked origin" not in text
    assert requested_urls == ["http://allowed.test/redirect"]


@pytest.mark.asyncio
async def test_fetch_docs_blocks_meta_refresh_redirect_chain(monkeypatch) -> None:
    """Meta-refresh follow-up redirects must be checked before fetching."""
    async_client = httpx.AsyncClient
    requested_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if str(request.url) == "http://allowed.test/page":
            return httpx.Response(
                200,
                text='<meta http-equiv="refresh" content="0; url=/next">',
                request=request,
            )
        if str(request.url) == "http://allowed.test/next":
            return httpx.Response(
                302,
                headers={"location": "http://blocked.test/payload"},
                request=request,
            )
        if str(request.url) == "http://blocked.test/payload":
            return httpx.Response(
                200, text="secret from blocked origin", request=request
            )
        raise AssertionError(f"Unexpected request: {request.url}")

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *args, **kwargs: async_client(
            transport=httpx.MockTransport(handler),
            follow_redirects=kwargs.get("follow_redirects", False),
            timeout=kwargs.get("timeout"),
        ),
    )

    server = create_server(
        [{"llms_txt": "http://allowed.test/llms.txt"}],
        follow_redirects=True,
    )

    result = await server.call_tool(
        "fetch_docs",
        {"url": "http://allowed.test/page"},
    )

    text = result[0][0].text
    assert "Error: Redirect URL not allowed." in text
    assert "secret from blocked origin" not in text
    assert requested_urls == [
        "http://allowed.test/page",
        "http://allowed.test/next",
    ]


@pytest.mark.asyncio
async def test_fetch_docs_allows_same_domain_http_redirect(monkeypatch) -> None:
    """Allowed redirect targets should still return their fetched content."""
    async_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "http://allowed.test/redirect":
            return httpx.Response(
                302,
                headers={"location": "http://allowed.test/final"},
                request=request,
            )
        if str(request.url) == "http://allowed.test/final":
            return httpx.Response(200, text="<h1>Allowed docs</h1>", request=request)
        raise AssertionError(f"Unexpected request: {request.url}")

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *args, **kwargs: async_client(
            transport=httpx.MockTransport(handler),
            follow_redirects=kwargs.get("follow_redirects", False),
            timeout=kwargs.get("timeout"),
        ),
    )

    server = create_server(
        [{"llms_txt": "http://allowed.test/llms.txt"}],
        follow_redirects=True,
    )

    result = await server.call_tool(
        "fetch_docs",
        {"url": "http://allowed.test/redirect"},
    )

    assert "Allowed docs" in result[0][0].text


@pytest.mark.asyncio
@pytest.mark.parametrize(("redirects", "succeeds"), [(20, True), (21, False)])
async def test_fetch_docs_redirect_limit_matches_httpx(
    monkeypatch, redirects, succeeds
) -> None:
    """Allow 20 redirects and reject the 21st, matching httpx."""
    async_client = httpx.AsyncClient
    requested_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if len(requested_urls) > redirects:
            return httpx.Response(200, text="<h1>Final docs</h1>", request=request)
        return httpx.Response(
            302,
            headers={"location": f"/redirect/{len(requested_urls)}"},
            request=request,
        )

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *args, **kwargs: async_client(
            transport=httpx.MockTransport(handler),
            follow_redirects=kwargs.get("follow_redirects", False),
            timeout=kwargs.get("timeout"),
        ),
    )

    server = create_server(
        [{"llms_txt": "http://allowed.test/llms.txt"}],
        follow_redirects=True,
    )
    result = await server.call_tool(
        "fetch_docs",
        {"url": "http://allowed.test/redirect"},
    )

    if succeeds:
        assert "Final docs" in result[0][0].text
    else:
        assert "Error: Too many redirects." in result[0][0].text
    assert len(requested_urls) == 21


@pytest.mark.asyncio
async def test_fetch_docs_does_not_follow_304_location(monkeypatch) -> None:
    """A 304 response with Location is not an HTTP redirect."""
    async_client = httpx.AsyncClient
    requested_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(
            304,
            headers={"location": "http://blocked.test/payload"},
            text="<h1>Not redirected</h1>",
            request=request,
        )

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *args, **kwargs: async_client(
            transport=httpx.MockTransport(handler),
            follow_redirects=kwargs.get("follow_redirects", False),
            timeout=kwargs.get("timeout"),
        ),
    )

    server = create_server(
        [{"llms_txt": "http://allowed.test/llms.txt"}],
        follow_redirects=True,
    )
    result = await server.call_tool(
        "fetch_docs",
        {"url": "http://allowed.test/not-modified"},
    )

    assert "304 Not Modified" in result[0][0].text
    assert requested_urls == ["http://allowed.test/not-modified"]
