#!/usr/bin/env bash
# Usage: ./capture-trace.sh [prompt]
# Example: ./capture-trace.sh "hello"
# Captures a trace of the latest Claude Code version from npm.
set -euo pipefail

PROMPT="${1:-hello}"
LATEST_VER=$(npm view @anthropic-ai/claude-code version 2>/dev/null || echo "")

if [ -z "$LATEST_VER" ]; then
  echo "✗ Cannot determine latest Claude Code version from npm."
  echo "  Check: npm view @anthropic-ai/claude-code version"
  exit 1
fi

echo "=== Capturing trace for Claude Code v${LATEST_VER} ==="

# Delegate to analyze-version.sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec bash "$SCRIPT_DIR/analyze-version.sh" "$LATEST_VER"
