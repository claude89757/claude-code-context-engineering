#!/usr/bin/env bash
set -euo pipefail

echo "=== Prerequisites Check ==="

# 1. node
NODE_VER=$(node --version 2>/dev/null || echo "")
if [ -n "$NODE_VER" ]; then
  echo "✓ node $NODE_VER"
else
  echo "✗ node not found — installing..."
  if command -v brew >/dev/null 2>&1; then brew install node
  elif command -v apt-get >/dev/null 2>&1; then sudo apt-get install -y nodejs npm
  else echo "BLOCKED: Install Node.js 16+ manually from https://nodejs.org"; exit 1; fi
fi

# 2. jq
JQ_VER=$(jq --version 2>/dev/null || echo "")
if [ -n "$JQ_VER" ]; then
  echo "✓ jq $JQ_VER"
else
  echo "✗ jq not found — installing..."
  if command -v brew >/dev/null 2>&1; then brew install jq
  elif command -v apt-get >/dev/null 2>&1; then sudo apt-get install -y jq
  else echo "BLOCKED: Install jq manually from https://jqlang.github.io/jq/download/"; exit 1; fi
fi

# 3. Claude Code CLI
if command -v claude >/dev/null 2>&1; then
  echo "✓ claude $(claude --version 2>/dev/null || echo 'installed')"
else
  echo "✗ Claude Code CLI not found — installing..."
  if npm install -g @anthropic-ai/claude-code; then
    echo "✓ Claude Code CLI installed"
  else
    echo "BLOCKED: Failed to install Claude Code CLI via npm."
    echo "  Try: npm install -g @anthropic-ai/claude-code"
    exit 1
  fi
fi

# 4. claude-trace
if command -v claude-trace >/dev/null 2>&1; then
  TRACE_VER=$(claude-trace --version 2>/dev/null || echo "installed")
  echo "✓ claude-trace $TRACE_VER"
elif npx --yes claude-trace --version >/dev/null 2>&1; then
  echo "✓ claude-trace available via npx"
else
  echo "✗ claude-trace not found — installing..."
  if npm install -g @mariozechner/claude-trace; then
    echo "✓ claude-trace installed"
  else
    echo "BLOCKED: Failed to install claude-trace."
    echo "  Try: npm install -g @mariozechner/claude-trace"
    exit 1
  fi
fi

# 5. npm registry accessibility (for version analysis)
echo "--- Optional: Version Analysis Support ---"
LATEST=$(npm view @anthropic-ai/claude-code version 2>/dev/null || echo "")
if [ -n "$LATEST" ]; then
  echo "✓ npm registry accessible, latest stable: $LATEST"
else
  echo "⚠ npm registry not accessible. Version analysis will not work."
fi

# 6. Trace data — check and auto-generate if missing
generate_trace() {
  echo "Launching Claude Code with tracing enabled..."
  echo "  Running: claude-trace --run claude -- -p 'say hello'"
  if command -v claude-trace >/dev/null 2>&1; then
    claude-trace --run claude -- -p "say hello" 2>/dev/null || true
  else
    npx --yes @mariozechner/claude-trace --run claude -- -p "say hello" 2>/dev/null || true
  fi
  sleep 2
  if ls "$HOME/.claude-trace/"*.jsonl >/dev/null 2>&1; then
    echo "✓ Trace data auto-generated successfully"
  else
    echo "⚠ Trace generation may have failed. Try manually:"
    echo "  claude-trace --run claude -- -p 'say hello'"
  fi
}

if [ -d "$HOME/.claude-trace" ]; then
  TOTAL=0; NONEMPTY=0
  while IFS= read -r -d '' f; do
    TOTAL=$((TOTAL + 1))
    [ -s "$f" ] && NONEMPTY=$((NONEMPTY + 1))
  done < <(find "$HOME/.claude-trace" -name "*.jsonl" -print0 2>/dev/null)
  echo "✓ Found $TOTAL trace files ($NONEMPTY non-empty)"

  if [ "$NONEMPTY" -eq 0 ]; then
    echo "⚠ All trace files are empty. Auto-generating trace data..."
    generate_trace
  else
    echo "  Largest files:"
    ls -lhS "$HOME/.claude-trace/"*.jsonl 2>/dev/null | head -3
  fi
else
  echo "✗ No trace directory found at ~/.claude-trace/"
  echo "  Auto-generating trace data..."
  generate_trace
fi

echo ""
echo "=== Check Complete ==="
