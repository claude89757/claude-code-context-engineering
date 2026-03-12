import os
import subprocess
from pathlib import Path

from backend.config import TRACES_DIR


def run_single_prompt_scenario(
    claude_cli_path: str,
    prompt: str,
    scenario_key: str,
    version: str,
) -> dict:
    """Run a single-prompt scenario via claude-trace and return the result."""
    trace_dir = TRACES_DIR / version
    trace_dir.mkdir(parents=True, exist_ok=True)

    claude_trace_dir = trace_dir / ".claude-trace"
    claude_trace_dir.mkdir(parents=True, exist_ok=True)

    log_name = scenario_key

    env = {k: v for k, v in os.environ.items() if "CLAUDECODE" not in k}
    env["CLAUDE_TRACE_DIR"] = str(claude_trace_dir)

    cmd = [
        "claude-trace",
        "--include-all-requests",
        "--no-open",
        "--claude-path", claude_cli_path,
        "--log", log_name,
        "--run-with",
        "-p", prompt,
        "--output-format", "json",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
            cwd=str(trace_dir),
        )

        jsonl_path = _find_jsonl(claude_trace_dir, log_name)
        raw_jsonl = None
        if jsonl_path and jsonl_path.exists():
            raw_jsonl = jsonl_path.read_text(encoding="utf-8")

        return {
            "success": result.returncode == 0,
            "error": result.stderr.strip() if result.returncode != 0 else None,
            "raw_jsonl": raw_jsonl,
            "jsonl_path": str(jsonl_path) if jsonl_path else None,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Scenario timed out after 300 seconds",
            "raw_jsonl": None,
            "jsonl_path": None,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "raw_jsonl": None,
            "jsonl_path": None,
        }


def run_multi_turn_scenario(
    claude_cli_path: str,
    turns: list[str],
    scenario_key: str,
    version: str,
) -> dict:
    """Run a multi-turn scenario by piping turns via stdin."""
    trace_dir = TRACES_DIR / version
    trace_dir.mkdir(parents=True, exist_ok=True)

    claude_trace_dir = trace_dir / ".claude-trace"
    claude_trace_dir.mkdir(parents=True, exist_ok=True)

    log_name = scenario_key

    env = {k: v for k, v in os.environ.items() if "CLAUDECODE" not in k}
    env["CLAUDE_TRACE_DIR"] = str(claude_trace_dir)

    cmd = [
        "claude-trace",
        "--include-all-requests",
        "--no-open",
        "--claude-path", claude_cli_path,
        "--log", log_name,
    ]

    stdin_text = "\n".join(turns + ["/exit"])

    try:
        result = subprocess.run(
            cmd,
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
            cwd=str(trace_dir),
        )

        jsonl_path = _find_jsonl(claude_trace_dir, log_name)
        raw_jsonl = None
        if jsonl_path and jsonl_path.exists():
            raw_jsonl = jsonl_path.read_text(encoding="utf-8")

        return {
            "success": result.returncode == 0,
            "error": result.stderr.strip() if result.returncode != 0 else None,
            "raw_jsonl": raw_jsonl,
            "jsonl_path": str(jsonl_path) if jsonl_path else None,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Scenario timed out after 600 seconds",
            "raw_jsonl": None,
            "jsonl_path": None,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "raw_jsonl": None,
            "jsonl_path": None,
        }


def _find_jsonl(trace_dir: Path, log_name: str) -> Path | None:
    """Find the JSONL output file in the trace directory."""
    candidates = list(trace_dir.glob(f"{log_name}*.jsonl"))
    if candidates:
        return max(candidates, key=lambda p: p.stat().st_mtime)
    # Fallback: any jsonl file
    all_jsonl = list(trace_dir.glob("*.jsonl"))
    if all_jsonl:
        return max(all_jsonl, key=lambda p: p.stat().st_mtime)
    return None
