"""Diff computation service for CC Observatory.

Compares two extracted data snapshots and produces structured diffs
for system prompts, tools, and system reminders.
"""

from __future__ import annotations

import difflib


def compute_text_diff(old_text: str, new_text: str) -> str:
    """Compute a unified diff between two text strings.

    Args:
        old_text: The previous version of the text.
        new_text: The current version of the text.

    Returns:
        Unified diff string, or empty string if the texts are identical.
    """
    if old_text == new_text:
        return ""

    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="old",
        tofile="new",
    )
    return "".join(diff)


def compute_list_diff(old_list: list, new_list: list) -> tuple[list, list]:
    """Compare two lists and return added and removed items.

    Args:
        old_list: The previous version of the list.
        new_list: The current version of the list.

    Returns:
        Tuple of (added, removed) items.
    """
    old_set = set(old_list)
    new_set = set(new_list)

    added = [item for item in new_list if item not in old_set]
    removed = [item for item in old_list if item not in new_set]

    return added, removed


def classify_significance(diff_lines: int, total_lines: int) -> str:
    """Classify the significance of a change.

    Args:
        diff_lines: Number of changed lines.
        total_lines: Total number of lines in the content.

    Returns:
        "none" if diff_lines is 0,
        "major" if ratio > 0.1 or diff_lines > 20,
        "minor" otherwise.
    """
    if diff_lines == 0:
        return "none"

    if diff_lines > 20:
        return "major"

    if total_lines > 0 and diff_lines / total_lines > 0.1:
        return "major"

    return "minor"


def compute_version_diffs(
    old_extracted: dict, new_extracted: dict
) -> list[dict]:
    """Compare two extracted data sets and generate structured diffs.

    Compares system_prompt (text diff), tools (list diff by tool name),
    and system_reminders (list diff).

    Args:
        old_extracted: Previously extracted data dict.
        new_extracted: Newly extracted data dict.

    Returns:
        List of diff dicts, each with keys:
            - diff_type: "system_prompt", "tools", or "system_reminders"
            - diff_content: the raw diff output
            - change_summary: human-readable summary string
            - significance: "none", "minor", or "major"
    """
    diffs: list[dict] = []

    # --- system_prompt: text diff ---
    old_prompt = old_extracted.get("system_prompt", "")
    new_prompt = new_extracted.get("system_prompt", "")
    text_diff = compute_text_diff(old_prompt, new_prompt)

    diff_line_count = sum(
        1
        for line in text_diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
        or line.startswith("-") and not line.startswith("---")
    )
    total_line_count = max(
        len(old_prompt.splitlines()), len(new_prompt.splitlines()), 1
    )
    significance = classify_significance(diff_line_count, total_line_count)

    if text_diff:
        summary = f"{diff_line_count} line(s) changed"
    else:
        summary = "no changes"

    diffs.append({
        "diff_type": "system_prompt",
        "diff_content": text_diff,
        "change_summary": summary,
        "significance": significance,
    })

    # --- tools: list diff by tool name ---
    old_tools = old_extracted.get("tool_names", [])
    new_tools = new_extracted.get("tool_names", [])
    added_tools, removed_tools = compute_list_diff(old_tools, new_tools)

    tool_diff_count = len(added_tools) + len(removed_tools)
    tool_total = max(len(old_tools), len(new_tools), 1)
    tool_significance = classify_significance(tool_diff_count, tool_total)

    parts: list[str] = []
    if added_tools:
        parts.append(f"added: {', '.join(added_tools)}")
    if removed_tools:
        parts.append(f"removed: {', '.join(removed_tools)}")
    tool_summary = "; ".join(parts) if parts else "no changes"

    diffs.append({
        "diff_type": "tools",
        "diff_content": {"added": added_tools, "removed": removed_tools},
        "change_summary": tool_summary,
        "significance": tool_significance,
    })

    # --- system_reminders: list diff ---
    old_reminders = old_extracted.get("system_reminders", [])
    new_reminders = new_extracted.get("system_reminders", [])
    added_rem, removed_rem = compute_list_diff(old_reminders, new_reminders)

    rem_diff_count = len(added_rem) + len(removed_rem)
    rem_total = max(len(old_reminders), len(new_reminders), 1)
    rem_significance = classify_significance(rem_diff_count, rem_total)

    rem_parts: list[str] = []
    if added_rem:
        rem_parts.append(f"{len(added_rem)} added")
    if removed_rem:
        rem_parts.append(f"{len(removed_rem)} removed")
    rem_summary = "; ".join(rem_parts) if rem_parts else "no changes"

    diffs.append({
        "diff_type": "system_reminders",
        "diff_content": {"added": added_rem, "removed": removed_rem},
        "change_summary": rem_summary,
        "significance": rem_significance,
    })

    return diffs
