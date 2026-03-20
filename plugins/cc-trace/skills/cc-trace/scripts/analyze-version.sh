#!/usr/bin/env bash
# Usage: ./analyze-version.sh <version>
# Example: ./analyze-version.sh $(npm view @anthropic-ai/claude-code version)
set -euo pipefail

VERSION="${1:?Usage: $0 <version>}"
WORK_DIR=$(mktemp -d "/tmp/claude-code-${VERSION}-XXXXX")

echo "=== Installing Claude Code v${VERSION} ==="
cd "$WORK_DIR"
npm install --no-save "@anthropic-ai/claude-code@${VERSION}" 2>&1 | tail -3

CLAUDE_CLI="$WORK_DIR/node_modules/@anthropic-ai/claude-code/cli.js"
if [ ! -f "$CLAUDE_CLI" ]; then
  echo "✗ Installation failed — cli.js not found."
  rm -rf "$WORK_DIR"
  exit 1
fi
echo "✓ Claude Code v${VERSION} installed"

echo "=== Running trace for v${VERSION} ==="
LOG_NAME="v${VERSION}"

# Unset CLAUDECODE env var to allow running inside a Claude Code session
unset CLAUDECODE 2>/dev/null || true

if command -v claude-trace >/dev/null 2>&1; then
  cd "$WORK_DIR" && claude-trace \
    --claude-path "$CLAUDE_CLI" \
    --log "$LOG_NAME" \
    --no-open \
    --include-all-requests \
    --run-with -p "hello" 2>&1 || true
else
  cd "$WORK_DIR" && npx --yes @mariozechner/claude-trace \
    --claude-path "$CLAUDE_CLI" \
    --log "$LOG_NAME" \
    --no-open \
    --include-all-requests \
    --run-with -p "hello" 2>&1 || true
fi

# Find the trace file (claude-trace writes to .claude-trace/ in cwd)
TRACE_FILE=$(find "$WORK_DIR/.claude-trace" "$WORK_DIR" -maxdepth 2 -name "*.jsonl" -size +0c 2>/dev/null | head -1)

if [ -n "$TRACE_FILE" ] && [ -s "$TRACE_FILE" ]; then
  LINES=$(wc -l < "$TRACE_FILE" | tr -d ' ')
  echo "✓ Trace captured: ${LINES} requests"
  echo "  File: $TRACE_FILE"
  echo ""
  echo "=== Request Overview ==="
  LLM='select(.request.url | test("v1/messages"))'
  jq -c "$LLM | {
    model: .request.body.model,
    max_tokens: .request.body.max_tokens,
    msgs: (.request.body.messages | length),
    tools: (.request.body.tools // [] | length),
    sys_blocks: (.request.body.system // [] | length),
    sys_len: ([.request.body.system[]? | .text | length] | add // 0),
    thinking: .request.body.thinking,
    effort: .request.body.output_config,
    ctx_mgmt: .request.body.context_management
  }" "$TRACE_FILE" 2>/dev/null || echo "(no LLM requests found — all traffic may be non-LLM)"

  echo ""
  echo "=== All Request URLs ==="
  jq -c '{method: .request.method, url: .request.url}' "$TRACE_FILE" 2>/dev/null
else
  echo "✗ No trace data captured."
  echo "  This could mean:"
  echo "    - No API key / OAuth token available"
  echo "    - Claude Code version too old for this method"
  echo "    - Network issue"
  echo "  Try manually: cd $WORK_DIR && claude-trace --claude-path $CLAUDE_CLI --run-with -p hello"
fi

echo ""
echo "=== Info ==="
echo "Work dir: $WORK_DIR"
echo "Trace file: ${TRACE_FILE:-none}"
echo "Run to clean up: rm -rf $WORK_DIR"
