#!/usr/bin/env bash
set -euo pipefail

echo "=== CC Trace Prerequisites Check ==="

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

# 3. claude-trace
if command -v claude-trace >/dev/null 2>&1; then
  echo "✓ claude-trace installed"
elif npx --yes @mariozechner/claude-trace --help >/dev/null 2>&1; then
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

# 4. npm registry accessibility
echo "--- npm Registry ---"
LATEST=$(npm view @anthropic-ai/claude-code version 2>/dev/null || echo "")
if [ -n "$LATEST" ]; then
  echo "✓ npm registry accessible, latest Claude Code: $LATEST"
else
  echo "⚠ npm registry not accessible. Version analysis will not work."
  echo "  Check network and npm config."
fi

# 5. Quick capture test (verify end-to-end)
echo "--- End-to-End Test ---"
if [ -n "$LATEST" ]; then
  echo "  To verify full pipeline, run:"
  echo "    bash scripts/capture-trace.sh"
else
  echo "  ⚠ Skipped (npm registry not accessible)"
fi

echo ""
echo "=== Check Complete ==="
