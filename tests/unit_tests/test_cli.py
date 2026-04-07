"""Tests for mcpdoc.cli module — focused on create_doc_sources_from_urls parsing.

These are fail-to-pass (F2P) tests: they fail on main (bug present) and pass
on the aneesh-fix branch (bug fixed).

Bug: --urls tokens are split on the first ':' even when that colon is part of
a 'file:' URL scheme or a Windows drive letter, not a label separator.
"""

import pytest

from mcpdoc.cli import create_doc_sources_from_urls


# ---------------------------------------------------------------------------
# file: URL handling
# ---------------------------------------------------------------------------


def test_file_url_not_split_into_label():
    """file:///path/to/llms.txt must NOT be treated as label='file', url='///path/to/llms.txt'.

    On main this fails because 'file:' is not excluded from the colon-split logic.
    """
    sources = create_doc_sources_from_urls(["file:///path/to/llms.txt"])
    assert len(sources) == 1
    assert sources[0]["llms_txt"] == "file:///path/to/llms.txt"
    assert "name" not in sources[0]


def test_file_url_preserves_full_value():
    """The full file: URL must reach llms_txt unchanged."""
    url = "file:///home/user/docs/llms.txt"
    sources = create_doc_sources_from_urls([url])
    assert sources[0]["llms_txt"] == url


# ---------------------------------------------------------------------------
# Windows drive path handling
# ---------------------------------------------------------------------------


def test_windows_drive_path_not_split_into_label():
    """C:/Users/docs/llms.txt must NOT be treated as label='C', url='/Users/docs/llms.txt'.

    On main this fails because a single-letter prefix before ':' is not excluded.
    """
    sources = create_doc_sources_from_urls(["C:/Users/docs/llms.txt"])
    assert len(sources) == 1
    assert sources[0]["llms_txt"] == "C:/Users/docs/llms.txt"
    assert "name" not in sources[0]


def test_windows_drive_path_lowercase():
    """Lowercase drive letter (c:/...) should also be treated as a path, not a label."""
    sources = create_doc_sources_from_urls(["c:/path/to/llms.txt"])
    assert len(sources) == 1
    assert sources[0]["llms_txt"] == "c:/path/to/llms.txt"
    assert "name" not in sources[0]


# ---------------------------------------------------------------------------
# Correct label:url format must still work
# ---------------------------------------------------------------------------


def test_label_with_http_url():
    """LangGraph:https://example.com/llms.txt must still parse label + URL correctly."""
    sources = create_doc_sources_from_urls(
        ["LangGraph:https://langchain-ai.github.io/langgraph/llms.txt"]
    )
    assert len(sources) == 1
    assert sources[0]["name"] == "LangGraph"
    assert sources[0]["llms_txt"] == "https://langchain-ai.github.io/langgraph/llms.txt"


def test_label_with_local_path():
    """MyDocs:/path/to/llms.txt — multi-char label with unix path must split correctly."""
    sources = create_doc_sources_from_urls(["MyDocs:/path/to/llms.txt"])
    assert len(sources) == 1
    assert sources[0]["name"] == "MyDocs"
    assert sources[0]["llms_txt"] == "/path/to/llms.txt"


# ---------------------------------------------------------------------------
# Plain URLs / paths with no label
# ---------------------------------------------------------------------------


def test_plain_http_url_no_label():
    """A bare https URL with no label prefix must be stored as-is."""
    sources = create_doc_sources_from_urls(
        ["https://langchain-ai.github.io/langgraph/llms.txt"]
    )
    assert len(sources) == 1
    assert sources[0]["llms_txt"] == "https://langchain-ai.github.io/langgraph/llms.txt"
    assert "name" not in sources[0]


def test_plain_unix_path_no_label():
    """A bare unix path with no colon must be stored as-is."""
    sources = create_doc_sources_from_urls(["/home/user/llms.txt"])
    assert len(sources) == 1
    assert sources[0]["llms_txt"] == "/home/user/llms.txt"
    assert "name" not in sources[0]


# ---------------------------------------------------------------------------
# Mixed input — multiple entries together
# ---------------------------------------------------------------------------


def test_mixed_entries_parsed_correctly():
    """When file: URL, Windows path, and a labelled URL are combined, all parse correctly.

    On main this fails because the first two entries are mis-parsed.
    """
    inputs = [
        "file:///opt/docs/llms.txt",
        "C:/docs/llms.txt",
        "LangGraph:https://langchain-ai.github.io/langgraph/llms.txt",
        "https://plain-url.com/llms.txt",
    ]
    sources = create_doc_sources_from_urls(inputs)

    assert sources[0] == {"llms_txt": "file:///opt/docs/llms.txt"}
    assert sources[1] == {"llms_txt": "C:/docs/llms.txt"}
    assert sources[2] == {
        "name": "LangGraph",
        "llms_txt": "https://langchain-ai.github.io/langgraph/llms.txt",
    }
    assert sources[3] == {"llms_txt": "https://plain-url.com/llms.txt"}
