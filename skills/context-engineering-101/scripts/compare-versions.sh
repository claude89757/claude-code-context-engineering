#!/usr/bin/env bash
# Usage: ./compare-versions.sh <version_a> <version_b>
# Example: ./compare-versions.sh 2.1.70 2.1.74
# Prerequisites: Run analyze-version.sh for both versions first.
set -euo pipefail

VERSION_A="${1:?Usage: $0 <version_a> <version_b>}"
VERSION_B="${2:?Usage: $0 <version_a> <version_b>}"

# Temp dir with auto-cleanup
TMPDIR_CMP=$(mktemp -d "/tmp/claude-cmp-$$-XXXX")
trap 'rm -rf "$TMPDIR_CMP"' EXIT

# Locate trace files from analyze-version.sh output
find_trace() {
  local version="$1"
  # Check work dirs from analyze-version.sh, then ~/.claude-trace
  local found=""
  found=$(find /tmp/claude-code-${version}-* -name "*.jsonl" -size +0c 2>/dev/null | head -1)
  if [ -z "$found" ]; then
    found=$(find "$HOME/.claude-trace" -name "*${version}*" -name "*.jsonl" -size +0c 2>/dev/null | head -1)
  fi
  echo "$found"
}

TRACE_A=$(find_trace "$VERSION_A")
TRACE_B=$(find_trace "$VERSION_B")

if [ -z "$TRACE_A" ] || [ -z "$TRACE_B" ]; then
  echo "✗ Missing trace files. Run analyze-version.sh for both versions first."
  [ -z "$TRACE_A" ] && echo "  Missing: v${VERSION_A}"
  [ -z "$TRACE_B" ] && echo "  Missing: v${VERSION_B}"
  exit 1
fi

echo "Using traces:"
echo "  v${VERSION_A}: $TRACE_A"
echo "  v${VERSION_B}: $TRACE_B"

echo ""
echo "=== System Prompt Comparison ==="
# Claude Code: system prompt is in .system[] array, not messages[0]
jq -r '[.request.body.system[]? | .text] | join("\n---\n")' "$TRACE_A" | head -1000 > "$TMPDIR_CMP/prompt_a.txt"
jq -r '[.request.body.system[]? | .text] | join("\n---\n")' "$TRACE_B" | head -1000 > "$TMPDIR_CMP/prompt_b.txt"

echo "v${VERSION_A} system prompt: $(wc -c < "$TMPDIR_CMP/prompt_a.txt" | tr -d ' ') chars"
echo "v${VERSION_B} system prompt: $(wc -c < "$TMPDIR_CMP/prompt_b.txt" | tr -d ' ') chars"
diff --unified "$TMPDIR_CMP/prompt_a.txt" "$TMPDIR_CMP/prompt_b.txt" | head -80 || true

echo ""
echo "=== Tool Count Comparison ==="
echo "v${VERSION_A}:"
jq -c '{tools: (.request.body.tools // [] | length)}' "$TRACE_A" | sort -u
echo "v${VERSION_B}:"
jq -c '{tools: (.request.body.tools // [] | length)}' "$TRACE_B" | sort -u

echo ""
echo "=== Tool Names Diff ==="
# Claude Code uses .tools[].name (Anthropic format), not .tools[].function.name
jq -r '.request.body.tools[]?.name' "$TRACE_A" | sort -u > "$TMPDIR_CMP/tools_a.txt"
jq -r '.request.body.tools[]?.name' "$TRACE_B" | sort -u > "$TMPDIR_CMP/tools_b.txt"
diff --unified "$TMPDIR_CMP/tools_a.txt" "$TMPDIR_CMP/tools_b.txt" || echo "(no differences in tool names)"

echo ""
echo "=== Thinking Configuration Diff ==="
echo "v${VERSION_A}:"
jq -c '{thinking: .request.body.thinking, effort: .request.body.output_config.effort, ctx_mgmt: .request.body.context_management}' "$TRACE_A" | sort -u
echo "v${VERSION_B}:"
jq -c '{thinking: .request.body.thinking, effort: .request.body.output_config.effort, ctx_mgmt: .request.body.context_management}' "$TRACE_B" | sort -u

echo ""
echo "=== Model Routing Comparison ==="
echo "v${VERSION_A}:"
jq -c '{model: .request.body.model, max_tokens: .request.body.max_tokens}' "$TRACE_A" | sort | uniq -c | sort -rn
echo "v${VERSION_B}:"
jq -c '{model: .request.body.model, max_tokens: .request.body.max_tokens}' "$TRACE_B" | sort | uniq -c | sort -rn

echo ""
echo "=== Cleanup ==="
echo "Run to clean up: rm -rf /tmp/claude-code-${VERSION_A}-* /tmp/claude-code-${VERSION_B}-*"
