"""Tests for the JSONL extractor service."""

import json
import sys
import os

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.extractor import extract_from_jsonl


def make_jsonl(*entries) -> str:
    """Join multiple dicts into a JSONL string."""
    return "\n".join(json.dumps(e) for e in entries)


def _make_messages_entry(
    *,
    model="claude-opus-4-20250514",
    system=None,
    tools=None,
    messages=None,
    usage=None,
):
    """Build a single JSONL entry for POST /v1/messages."""
    body = {"model": model}
    if system is not None:
        body["system"] = system
    if tools is not None:
        body["tools"] = tools
    if messages is not None:
        body["messages"] = messages
    else:
        body["messages"] = []

    resp_body = {}
    if usage is not None:
        resp_body["usage"] = usage

    return {
        "request": {
            "method": "POST",
            "url": "https://api.anthropic.com/v1/messages",
            "body": body,
        },
        "response": {"body": resp_body},
    }


# --- Sample data ---

SYSTEM_BLOCKS = [
    {
        "type": "text",
        "text": "You are a helpful assistant.",
        "cache_control": {"type": "ephemeral"},
    },
    {
        "type": "text",
        "text": "Always be concise.",
    },
]

TOOLS = [
    {
        "name": "Read",
        "description": "Reads a file.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "Bash",
        "description": "Runs a command.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

USER_MSG_WITH_DEFERRED = {
    "role": "user",
    "content": [
        {
            "type": "text",
            "text": (
                "<available-deferred-tools>\n"
                "WebSearch\n"
                "WebFetch\n"
                "NotebookEdit\n"
                "</available-deferred-tools>\n\n"
                "<system-reminder>\n"
                "Today is 2026-03-12.\n"
                "</system-reminder>\n\n"
                "Please help me."
            ),
        }
    ],
}

ASSISTANT_MSG = {
    "role": "assistant",
    "content": [{"type": "text", "text": "Sure, I can help."}],
}

USAGE = {
    "input_tokens": 1000,
    "output_tokens": 200,
    "cache_creation_input_tokens": 500,
    "cache_read_input_tokens": 300,
}


def _sample_jsonl():
    """Build a realistic sample JSONL with two API calls."""
    entry1 = _make_messages_entry(
        model="claude-opus-4-20250514",
        system=SYSTEM_BLOCKS,
        tools=TOOLS,
        messages=[USER_MSG_WITH_DEFERRED],
        usage=USAGE,
    )
    entry2 = _make_messages_entry(
        model="claude-sonnet-4-20250514",
        system=SYSTEM_BLOCKS,
        tools=TOOLS,
        messages=[USER_MSG_WITH_DEFERRED, ASSISTANT_MSG, {"role": "user", "content": "Thanks"}],
        usage={"input_tokens": 500, "output_tokens": 100},
    )
    # A non-messages GET call
    get_entry = {
        "request": {"method": "GET", "url": "https://api.anthropic.com/v1/models"},
        "response": {"body": {}},
    }
    return make_jsonl(entry1, get_entry, entry2)


# --- Tests ---


def test_extract_system_prompt():
    result = extract_from_jsonl(_sample_jsonl())
    assert "You are a helpful assistant." in result["system_prompt"]
    assert "Always be concise." in result["system_prompt"]
    # Check blocks structure
    assert len(result["system_blocks"]) >= 2
    block0 = result["system_blocks"][0]
    assert block0["index"] == 0
    assert block0["text"] == "You are a helpful assistant."
    assert block0["length"] == len("You are a helpful assistant.")
    assert block0["cache_control"] == {"type": "ephemeral"}


def test_extract_tools():
    result = extract_from_jsonl(_sample_jsonl())
    assert result["tool_names"] == ["Read", "Bash"]
    assert len(result["tools"]) == 2
    assert result["tools"][0]["name"] == "Read"


def test_extract_deferred_tools():
    result = extract_from_jsonl(_sample_jsonl())
    assert "WebSearch" in result["deferred_tools"]
    assert "WebFetch" in result["deferred_tools"]
    assert "NotebookEdit" in result["deferred_tools"]
    assert len(result["deferred_tools"]) == 3


def test_extract_system_reminders():
    result = extract_from_jsonl(_sample_jsonl())
    assert len(result["system_reminders"]) == 1
    assert "Today is 2026-03-12." in result["system_reminders"][0]


def test_extract_model():
    result = extract_from_jsonl(_sample_jsonl())
    # model_used should be from the FIRST /v1/messages call
    assert result["model_used"] == "claude-opus-4-20250514"


def test_extract_api_calls():
    result = extract_from_jsonl(_sample_jsonl())
    assert len(result["api_calls"]) == 3
    assert result["api_calls"][0] == {
        "method": "POST",
        "url": "https://api.anthropic.com/v1/messages",
    }
    assert result["api_calls"][1] == {
        "method": "GET",
        "url": "https://api.anthropic.com/v1/models",
    }
    assert result["api_calls"][2] == {
        "method": "POST",
        "url": "https://api.anthropic.com/v1/messages",
    }


def test_extract_cache_strategy():
    result = extract_from_jsonl(_sample_jsonl())
    # First system block has cache_control
    cached = [c for c in result["cache_strategy"] if c["cache_control"]]
    assert len(cached) >= 1
    assert cached[0]["block_index"] == 0
    assert cached[0]["cache_control"] == {"type": "ephemeral"}


def test_extract_messages_chain():
    result = extract_from_jsonl(_sample_jsonl())
    assert len(result["messages_chain"]) == 2
    assert result["messages_chain"][0]["num_messages"] == 1
    assert result["messages_chain"][1]["num_messages"] == 3


def test_extract_token_usage():
    result = extract_from_jsonl(_sample_jsonl())
    # Should be from the last response with usage
    assert result["token_usage"]["input_tokens"] == 500
    assert result["token_usage"]["output_tokens"] == 100


def test_empty_jsonl():
    result = extract_from_jsonl("")
    assert result["system_prompt"] == ""
    assert result["tools"] == []
    assert result["model_used"] is None


def test_body_as_string():
    """Test that body provided as JSON string is handled."""
    body = json.dumps({
        "model": "claude-opus-4-20250514",
        "system": [{"type": "text", "text": "Hello"}],
        "messages": [],
    })
    entry = {
        "request": {
            "method": "POST",
            "url": "https://api.anthropic.com/v1/messages",
            "body": body,
        },
        "response": {"body": "{}"},
    }
    result = extract_from_jsonl(make_jsonl(entry))
    assert result["system_prompt"] == "Hello"


def test_dedup_system_reminders():
    """System reminders appearing in multiple calls should be deduplicated."""
    msg = {
        "role": "user",
        "content": "<system-reminder>\nDuplicate reminder.\n</system-reminder>\nHello",
    }
    entry1 = _make_messages_entry(messages=[msg])
    entry2 = _make_messages_entry(messages=[msg])
    result = extract_from_jsonl(make_jsonl(entry1, entry2))
    assert result["system_reminders"].count("Duplicate reminder.") == 1
