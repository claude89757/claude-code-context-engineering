#!/usr/bin/env bash
# Usage: ./analyze-version.sh <version>
# Example: ./analyze-version.sh 2.1.74
set -euo pipefail

VERSION="${1:?Usage: $0 <version>}"
WORK_DIR=$(mktemp -d "/tmp/claude-code-${VERSION}-XXXXX")

echo "=== Installing Claude Code v${VERSION} ==="
cd "$WORK_DIR"
npm install --no-save "@anthropic-ai/claude-code@${VERSION}" 2>&1 | tail -3

CLAUDE_BIN="$WORK_DIR/node_modules/.bin/claude"
if [ ! -x "$CLAUDE_BIN" ]; then
  echo "✗ Installation failed. Check npm output above."
  rm -rf "$WORK_DIR"
  exit 1
fi
echo "✓ Claude Code v${VERSION} installed at $CLAUDE_BIN"

echo "=== Running trace for v${VERSION} ==="
TRACE_OUT="$WORK_DIR/trace"
mkdir -p "$TRACE_OUT"

if command -v claude-trace >/dev/null 2>&1; then
  claude-trace --output "$TRACE_OUT" --run "$CLAUDE_BIN" -- -p "hello" 2>/dev/null || true
else
  npx --yes @mariozechner/claude-trace --output "$TRACE_OUT" --run "$CLAUDE_BIN" -- -p "hello" 2>/dev/null || true
fi

# Find the trace file
TRACE_FILE=$(find "$TRACE_OUT" "$HOME/.claude-trace" -name "*.jsonl" -newer "$WORK_DIR" 2>/dev/null | head -1)

if [ -n "$TRACE_FILE" ] && [ -s "$TRACE_FILE" ]; then
  echo "✓ Trace captured: $(wc -l < "$TRACE_FILE") requests"
  echo ""
  echo "=== Request Overview ==="
  # Note: Claude Code uses system[] array (not messages[0]) and .tools[].name (not .function.name)
  jq -c '{
    model: .request.body.model,
    max_tokens: .request.body.max_tokens,
    msgs: (.request.body.messages | length),
    tools: (.request.body.tools // [] | length),
    sys_blocks: (.request.body.system // [] | length),
    sys_len: ([.request.body.system[]? | .text | length] | add // 0),
    thinking: .request.body.thinking,
    effort: .request.body.output_config.effort
  }' "$TRACE_FILE"
else
  echo "✗ No trace data captured. Check claude-trace output."
  echo "  Try manually: claude-trace --run $CLAUDE_BIN -- -p 'hello'"
fi

echo ""
echo "=== Info ==="
echo "Work dir: $WORK_DIR"
echo "Run to clean up: rm -rf $WORK_DIR"
