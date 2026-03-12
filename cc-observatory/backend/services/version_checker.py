"""Version checker service for Claude Code npm package."""

import json
import os
import subprocess
from typing import Optional


PACKAGE_NAME = "@anthropic-ai/claude-code"


def get_all_npm_versions() -> list[str]:
    """Run npm view to get all published versions of Claude Code, sorted.

    Returns:
        Sorted list of version strings.

    Raises:
        subprocess.CalledProcessError: If the npm command fails.
        json.JSONDecodeError: If the output is not valid JSON.
    """
    result = subprocess.run(
        ["npm", "view", PACKAGE_NAME, "versions", "--json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    result.check_returncode()
    versions = json.loads(result.stdout)
    if isinstance(versions, str):
        # npm returns a plain string instead of a list when there is only one version
        versions = [versions]
    return sorted(versions, key=_version_sort_key)


def get_latest_npm_version() -> str:
    """Return the latest published version of Claude Code.

    Returns:
        The latest version string.
    """
    versions = get_all_npm_versions()
    return versions[-1]


def get_npm_metadata(version: str) -> dict:
    """Fetch npm metadata for a specific version of Claude Code.

    Args:
        version: The version string to query (e.g. "1.0.0").

    Returns:
        Parsed JSON metadata dict from npm.

    Raises:
        subprocess.CalledProcessError: If the npm command fails.
        json.JSONDecodeError: If the output is not valid JSON.
    """
    result = subprocess.run(
        ["npm", "view", f"{PACKAGE_NAME}@{version}", "--json"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    result.check_returncode()
    return json.loads(result.stdout)


def install_claude_code_version(version: str, target_dir: str) -> str:
    """Install a specific version of Claude Code into a target directory.

    Args:
        version: The version string to install (e.g. "1.0.0").
        target_dir: The directory prefix to install into.

    Returns:
        The path to the installed cli.js entry point.

    Raises:
        subprocess.CalledProcessError: If the npm install command fails.
    """
    result = subprocess.run(
        ["npm", "install", f"{PACKAGE_NAME}@{version}", "--prefix", target_dir],
        capture_output=True,
        text=True,
        timeout=30,
    )
    result.check_returncode()
    return os.path.join(
        target_dir, "node_modules", "@anthropic-ai", "claude-code", "cli.js"
    )


def _version_sort_key(version: str) -> tuple:
    """Convert a semver string into a tuple for sorting.

    Handles versions like "1.2.3" and "1.2.3-beta.1".
    Pre-release versions sort before their release counterpart.
    """
    parts = version.split("-", 1)
    main_parts = tuple(int(x) for x in parts[0].split("."))
    # Versions without pre-release tag sort after those with one
    if len(parts) == 1:
        return (main_parts, (1,))
    return (main_parts, (0, parts[1]))
