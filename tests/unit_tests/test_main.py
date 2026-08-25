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


def _mock_client_factory(monkeypatch, routes, requested):
    """Patch ``httpx.AsyncClient`` so ``create_server`` gets a mock transport.

    ``routes`` maps a URL to the response it should produce. Every requested URL
    is appended to ``requested``, so a test can assert that a disallowed origin
    was never contacted at all.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return routes[str(request.url)]

    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


async def _fetch(server, url: str) -> str:
    """Call the server's ``fetch_docs`` tool and return its text output."""
    result = await server.call_tool("fetch_docs", {"url": url})
    contents = result[0] if isinstance(result, tuple) else result
    return "\n".join(getattr(item, "text", str(item)) for item in contents)


async def test_fetch_docs_rejects_redirect_outside_allowlist(monkeypatch) -> None:
    """A redirect to a domain outside the allowlist is refused, not followed."""
    allowed = "http://allowed.test/"
    disallowed = "http://evil.test/payload"
    requested: list[str] = []
    _mock_client_factory(
        monkeypatch,
        {
            allowed + "redirect": httpx.Response(302, headers={"location": disallowed}),
            disallowed: httpx.Response(200, text="secret"),
        },
        requested,
    )

    server = create_server(
        [{"name": "Allowed", "llms_txt": allowed + "llms.txt"}],
        follow_redirects=True,
    )
    output = await _fetch(server, allowed + "redirect")

    assert "Error: Redirect URL not allowed" in output
    assert "secret" not in output
    # The point of the allowlist is that the request is never made: checking the
    # response after the fact would still have forged the request.
    assert requested == [allowed + "redirect"]


async def test_fetch_docs_follows_redirect_inside_allowlist(monkeypatch) -> None:
    """A redirect that stays inside the allowlist is still followed."""
    allowed = "http://allowed.test/"
    requested: list[str] = []
    _mock_client_factory(
        monkeypatch,
        {
            allowed + "redirect": httpx.Response(
                302, headers={"location": allowed + "docs"}
            ),
            allowed + "docs": httpx.Response(200, text="real documentation"),
        },
        requested,
    )

    server = create_server(
        [{"name": "Allowed", "llms_txt": allowed + "llms.txt"}],
        follow_redirects=True,
    )
    output = await _fetch(server, allowed + "redirect")

    assert "real documentation" in output
    assert requested == [allowed + "redirect", allowed + "docs"]


async def test_fetch_docs_meta_refresh_target_redirect_is_checked(
    monkeypatch,
) -> None:
    """A redirect issued by a meta refresh target is checked like any other."""
    allowed = "http://allowed.test/"
    disallowed = "http://evil.test/payload"
    requested: list[str] = []
    _mock_client_factory(
        monkeypatch,
        {
            allowed + "page": httpx.Response(
                200,
                text=(f'<meta http-equiv="refresh" content="0; url={allowed}next" />'),
            ),
            allowed + "next": httpx.Response(302, headers={"location": disallowed}),
            disallowed: httpx.Response(200, text="secret"),
        },
        requested,
    )

    server = create_server(
        [{"name": "Allowed", "llms_txt": allowed + "llms.txt"}],
        follow_redirects=True,
    )
    output = await _fetch(server, allowed + "page")

    assert "Error: Redirect URL not allowed" in output
    assert "secret" not in output
    assert requested == [allowed + "page", allowed + "next"]


async def test_fetch_docs_does_not_follow_redirects_by_default(monkeypatch) -> None:
    """With follow_redirects off (the default) a redirect is not followed."""
    allowed = "http://allowed.test/"
    requested: list[str] = []
    _mock_client_factory(
        monkeypatch,
        {
            allowed + "redirect": httpx.Response(
                302, headers={"location": allowed + "docs"}
            ),
            allowed + "docs": httpx.Response(200, text="real documentation"),
        },
        requested,
    )

    server = create_server([{"name": "Allowed", "llms_txt": allowed + "llms.txt"}])
    await _fetch(server, allowed + "redirect")

    assert requested == [allowed + "redirect"]


@pytest.mark.parametrize(
    ("location", "should_fetch"),
    [
        ("/docs/deep", True),
        ("//evil.test/payload", False),
        ("http://evil.test/payload", False),
    ],
)
async def test_fetch_docs_resolves_relative_redirects_before_checking(
    monkeypatch, location, should_fetch
) -> None:
    """A relative target is resolved first, then checked against the allowlist."""
    allowed = "http://allowed.test/"
    requested: list[str] = []
    _mock_client_factory(
        monkeypatch,
        {
            allowed + "redirect": httpx.Response(302, headers={"location": location}),
            allowed + "docs/deep": httpx.Response(200, text="real documentation"),
            "http://evil.test/payload": httpx.Response(200, text="secret"),
        },
        requested,
    )

    server = create_server(
        [{"name": "Allowed", "llms_txt": allowed + "llms.txt"}],
        follow_redirects=True,
    )
    output = await _fetch(server, allowed + "redirect")

    if should_fetch:
        assert "real documentation" in output
        assert requested == [allowed + "redirect", allowed + "docs/deep"]
    else:
        assert "Error: Redirect URL not allowed" in output
        assert "secret" not in output
        assert requested == [allowed + "redirect"]


@pytest.mark.parametrize(("hops", "succeeds"), [(20, True), (21, False)])
async def test_fetch_docs_redirect_chain_bound_matches_httpx(
    monkeypatch, hops, succeeds
) -> None:
    """The chain is bounded exactly where httpx would bound it."""
    allowed = "http://allowed.test/"
    routes = {
        f"{allowed}r{i}": httpx.Response(
            302, headers={"location": f"{allowed}r{i + 1}"}
        )
        for i in range(hops)
    }
    routes[f"{allowed}r{hops}"] = httpx.Response(200, text="real documentation")
    requested: list[str] = []
    _mock_client_factory(monkeypatch, routes, requested)

    server = create_server(
        [{"name": "Allowed", "llms_txt": allowed + "llms.txt"}],
        follow_redirects=True,
    )
    output = await _fetch(server, allowed + "r0")

    if succeeds:
        assert "real documentation" in output
    else:
        assert "Exceeded maximum allowed redirects" in output
