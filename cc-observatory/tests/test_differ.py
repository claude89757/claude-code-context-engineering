"""Tests for the diff computation service."""

import sys
import os

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.differ import (
    classify_significance,
    compute_list_diff,
    compute_text_diff,
    compute_version_diffs,
)


# ---------- compute_text_diff ----------


def test_text_diff_identical():
    assert compute_text_diff("hello\nworld", "hello\nworld") == ""


def test_text_diff_empty_strings():
    assert compute_text_diff("", "") == ""


def test_text_diff_added_lines():
    diff = compute_text_diff("line1\n", "line1\nline2\n")
    assert "+line2\n" in diff
    assert "-" not in diff or "---" in diff  # only header minus


def test_text_diff_removed_lines():
    diff = compute_text_diff("line1\nline2\n", "line1\n")
    assert "-line2\n" in diff


def test_text_diff_modified_lines():
    diff = compute_text_diff("hello world\n", "hello claude\n")
    assert "-hello world\n" in diff
    assert "+hello claude\n" in diff


def test_text_diff_from_empty():
    diff = compute_text_diff("", "new content\n")
    assert "+new content\n" in diff


def test_text_diff_to_empty():
    diff = compute_text_diff("old content\n", "")
    assert "-old content\n" in diff


# ---------- compute_list_diff ----------


def test_list_diff_identical():
    added, removed = compute_list_diff(["a", "b"], ["a", "b"])
    assert added == []
    assert removed == []


def test_list_diff_added():
    added, removed = compute_list_diff(["a"], ["a", "b", "c"])
    assert added == ["b", "c"]
    assert removed == []


def test_list_diff_removed():
    added, removed = compute_list_diff(["a", "b", "c"], ["a"])
    assert added == []
    assert removed == ["b", "c"]


def test_list_diff_both():
    added, removed = compute_list_diff(["a", "b"], ["b", "c"])
    assert added == ["c"]
    assert removed == ["a"]


def test_list_diff_empty_to_items():
    added, removed = compute_list_diff([], ["x", "y"])
    assert added == ["x", "y"]
    assert removed == []


def test_list_diff_items_to_empty():
    added, removed = compute_list_diff(["x", "y"], [])
    assert added == []
    assert removed == ["x", "y"]


def test_list_diff_preserves_order():
    added, removed = compute_list_diff(["a"], ["c", "b", "a"])
    assert added == ["c", "b"]


# ---------- classify_significance ----------


def test_significance_none():
    assert classify_significance(0, 100) == "none"


def test_significance_none_zero_total():
    assert classify_significance(0, 0) == "none"


def test_significance_minor():
    # 5 / 100 = 0.05, under 0.1 threshold and under 20 lines
    assert classify_significance(5, 100) == "minor"


def test_significance_major_by_ratio():
    # 15 / 100 = 0.15, over 0.1 threshold
    assert classify_significance(15, 100) == "major"


def test_significance_major_by_count():
    # 25 > 20 threshold
    assert classify_significance(25, 1000) == "major"


def test_significance_major_exact_boundary_ratio():
    # 10 / 100 = 0.1, NOT > 0.1 so should be minor
    assert classify_significance(10, 100) == "minor"


def test_significance_major_just_over_ratio():
    # 11 / 100 = 0.11, > 0.1
    assert classify_significance(11, 100) == "major"


def test_significance_major_exactly_21():
    assert classify_significance(21, 1000) == "major"


def test_significance_minor_exactly_20():
    # 20 / 1000 = 0.02, not > 0.1 and not > 20
    assert classify_significance(20, 1000) == "minor"


# ---------- compute_version_diffs ----------


def _make_extracted(
    system_prompt="",
    tool_names=None,
    system_reminders=None,
):
    return {
        "system_prompt": system_prompt,
        "tool_names": tool_names or [],
        "system_reminders": system_reminders or [],
    }


def test_version_diffs_no_changes():
    old = _make_extracted("prompt", ["tool1"], ["reminder1"])
    new = _make_extracted("prompt", ["tool1"], ["reminder1"])
    diffs = compute_version_diffs(old, new)

    assert len(diffs) == 3
    for d in diffs:
        assert d["significance"] == "none"
        assert "no changes" in d["change_summary"]


def test_version_diffs_system_prompt_changed():
    old = _make_extracted(system_prompt="line1\nline2\n")
    new = _make_extracted(system_prompt="line1\nline2\nline3\n")
    diffs = compute_version_diffs(old, new)

    prompt_diff = next(d for d in diffs if d["diff_type"] == "system_prompt")
    assert prompt_diff["diff_content"] != ""
    assert prompt_diff["significance"] != "none"
    assert "changed" in prompt_diff["change_summary"]


def test_version_diffs_tools_changed():
    old = _make_extracted(tool_names=["Read", "Write"])
    new = _make_extracted(tool_names=["Read", "Edit"])
    diffs = compute_version_diffs(old, new)

    tools_diff = next(d for d in diffs if d["diff_type"] == "tools")
    assert tools_diff["diff_content"]["added"] == ["Edit"]
    assert tools_diff["diff_content"]["removed"] == ["Write"]
    assert "added: Edit" in tools_diff["change_summary"]
    assert "removed: Write" in tools_diff["change_summary"]


def test_version_diffs_reminders_changed():
    old = _make_extracted(system_reminders=["r1", "r2"])
    new = _make_extracted(system_reminders=["r2", "r3"])
    diffs = compute_version_diffs(old, new)

    rem_diff = next(d for d in diffs if d["diff_type"] == "system_reminders")
    assert "r3" in rem_diff["diff_content"]["added"]
    assert "r1" in rem_diff["diff_content"]["removed"]
    assert rem_diff["significance"] != "none"


def test_version_diffs_missing_keys():
    """Gracefully handles extracted dicts missing optional keys."""
    diffs = compute_version_diffs({}, {})
    assert len(diffs) == 3
    for d in diffs:
        assert d["significance"] == "none"


def test_version_diffs_major_prompt_change():
    old_prompt = "\n".join(f"line {i}" for i in range(50))
    # Change more than 20 lines
    new_prompt = "\n".join(
        f"modified {i}" if i < 25 else f"line {i}" for i in range(50)
    )
    old = _make_extracted(system_prompt=old_prompt)
    new = _make_extracted(system_prompt=new_prompt)
    diffs = compute_version_diffs(old, new)

    prompt_diff = next(d for d in diffs if d["diff_type"] == "system_prompt")
    assert prompt_diff["significance"] == "major"
