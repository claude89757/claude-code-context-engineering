"""JSONL extractor service for CC Observatory.

Parses claude-trace JSONL output and extracts structured context engineering data.
"""

from __future__ import annotations

import json
import re
from typing import Any


def extract_from_jsonl(raw_jsonl: str) -> dict:
    """Parse claude-trace JSONL output and extract structured data.

    Args:
        raw_jsonl: Raw JSONL string with one JSON object per line.
            Each object has "request" and "response" keys.

    Returns:
        Dict with extracted context engineering data.
    """
    entries = _parse_entries(raw_jsonl)

    system_blocks: list[dict] = []
    tools: list[dict] = []
    tool_names: list[str] = []
    deferred_tools: list[str] = []
    messages_chain: list[dict] = []
    api_calls: list[dict] = []
    system_reminders: list[str] = []
    cache_strategy: list[dict] = []
    token_usage: dict = {}
    model_used: str | None = None

    for entry in entries:
        request = entry.get("request", {})
        response = entry.get("response", {})

        method = request.get("method", "")
        url = request.get("url", "")
        api_calls.append({"method": method, "url": url})

        if method == "POST" and "/v1/messages" in url:
            body = _parse_body(request.get("body", {}))

            # model_used: only from the FIRST /v1/messages call
            if model_used is None:
                model_used = body.get("model")

            # system blocks
            raw_system = body.get("system", [])
            if isinstance(raw_system, list) and raw_system:
                # Only capture system blocks from the first call that has them,
                # or accumulate — task says "full text of all system blocks joined"
                # so we accumulate across calls
                for idx, block in enumerate(raw_system):
                    block_entry: dict[str, Any] = {
                        "index": idx,
                        "text": block.get("text", ""),
                        "length": len(block.get("text", "")),
                    }
                    cc = block.get("cache_control")
                    block_entry["cache_control"] = cc
                    system_blocks.append(block_entry)

                    if cc:
                        cache_strategy.append({
                            "block_index": idx,
                            "cache_control": cc,
                        })

            # tools
            raw_tools = body.get("tools", [])
            if raw_tools:
                tools = raw_tools
                tool_names = [t.get("name", "") for t in raw_tools if "name" in t]

            # messages
            messages = body.get("messages", [])
            truncated_messages = _truncate_messages(messages)
            messages_chain.append({
                "num_messages": len(messages),
                "summary": _summarize_messages(messages),
                "messages": truncated_messages,
            })

            # deferred tools from first user message
            if not deferred_tools:
                deferred_tools = _extract_deferred_tools(messages)

            # system reminders from all messages
            reminders = _extract_system_reminders(messages)
            for r in reminders:
                if r not in system_reminders:
                    system_reminders.append(r)

            # token usage from response
            resp_body = _parse_body(response.get("body", {}))
            usage = resp_body.get("usage")
            if usage:
                token_usage = usage
            elif not token_usage:
                # Fallback: try to extract from response headers
                resp_headers = response.get("headers", {})
                if isinstance(resp_headers, dict):
                    input_t = resp_headers.get("anthropic-ratelimit-input-tokens")
                    output_t = resp_headers.get("anthropic-ratelimit-output-tokens")
                    if input_t or output_t:
                        token_usage = {
                            "input_tokens": int(input_t) if input_t else 0,
                            "output_tokens": int(output_t) if output_t else 0,
                            "source": "headers",
                        }

    system_prompt = "\n\n".join(b["text"] for b in system_blocks if b["text"])

    return {
        "system_prompt": system_prompt,
        "system_blocks": system_blocks,
        "tools": tools,
        "tool_names": tool_names,
        "deferred_tools": deferred_tools,
        "messages_chain": messages_chain,
        "api_calls": api_calls,
        "system_reminders": system_reminders,
        "cache_strategy": cache_strategy,
        "token_usage": token_usage,
        "model_used": model_used,
    }


def _parse_entries(raw_jsonl: str) -> list[dict]:
    """Parse JSONL string into list of dicts."""
    entries = []
    for line in raw_jsonl.strip().splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _parse_body(body: Any) -> dict:
    """Parse body which may be a dict or a JSON string."""
    if isinstance(body, dict):
        return body
    if isinstance(body, str):
        try:
            return json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _summarize_messages(messages: list[dict]) -> str:
    """Create a brief summary of a messages list."""
    if not messages:
        return "empty"
    roles = [m.get("role", "?") for m in messages]
    counts: dict[str, int] = {}
    for r in roles:
        counts[r] = counts.get(r, 0) + 1
    parts = [f"{count} {role}" for role, count in counts.items()]
    return ", ".join(parts)


def _extract_text_from_content(content: Any) -> str:
    """Extract all text from a message content field."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


def _extract_deferred_tools(messages: list[dict]) -> list[str]:
    """Extract deferred tool names from <available-deferred-tools> in user messages."""
    for msg in messages:
        if msg.get("role") != "user":
            continue
        text = _extract_text_from_content(msg.get("content", ""))
        match = re.search(
            r"<available-deferred-tools>\s*(.*?)\s*</available-deferred-tools>",
            text,
            re.DOTALL,
        )
        if match:
            inner = match.group(1).strip()
            # Tool names are typically one per line
            names = [n.strip() for n in inner.splitlines() if n.strip()]
            return names
    return []


def _truncate_messages(messages: list[dict], max_text_len: int = 1000) -> list[dict]:
    """Truncate message content to keep storage reasonable."""
    result = []
    for msg in messages:
        truncated = {"role": msg.get("role", "unknown")}
        content = msg.get("content", "")
        if isinstance(content, str):
            truncated["content"] = content[:max_text_len] + ("..." if len(content) > max_text_len else "")
        elif isinstance(content, list):
            truncated_blocks = []
            for block in content:
                if isinstance(block, dict):
                    b = dict(block)
                    if "text" in b and isinstance(b["text"], str) and len(b["text"]) > max_text_len:
                        b["text"] = b["text"][:max_text_len] + "..."
                    if "thinking" in b and isinstance(b["thinking"], str) and len(b["thinking"]) > max_text_len:
                        b["thinking"] = b["thinking"][:max_text_len] + "..."
                    truncated_blocks.append(b)
                else:
                    truncated_blocks.append(block)
            truncated["content"] = truncated_blocks
        else:
            truncated["content"] = str(content)[:max_text_len]
        result.append(truncated)
    return result


def _extract_system_reminders(messages: list[dict]) -> list[str]:
    """Extract all <system-reminder> content from messages."""
    reminders = []
    for msg in messages:
        text = _extract_text_from_content(msg.get("content", ""))
        for match in re.finditer(
            r"<system-reminder>\s*(.*?)\s*</system-reminder>",
            text,
            re.DOTALL,
        ):
            reminder = match.group(1).strip()
            if reminder and reminder not in reminders:
                reminders.append(reminder)
    return reminders
