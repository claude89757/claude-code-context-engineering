---
name: cc-trace
description: Capture and analyze Claude Code's real API requests using claude-trace. Use when you need to see what Claude Code actually sends to the LLM — system prompts, tools, thinking config, context management, etc. All data comes from live traces, nothing is hardcoded.
---

# CC Trace

Use `claude-trace` (`@mariozechner/claude-trace`) to capture the exact API requests Claude Code sends to the Anthropic API. This skill captures **real data only** — it does not contain any pre-baked knowledge about Claude Code internals.

> **Native Binary vs npm Version.** Since Claude Code v2.x, the system-installed `claude` binary is a compiled native executable. `claude-trace` works by monkey-patching Node.js `fetch`, so it cannot intercept native binaries. The npm package `@anthropic-ai/claude-code` still ships a Node.js `cli.js` entry point. All scripts use `npm install @anthropic-ai/claude-code@<version>` and pass `--claude-path` to `claude-trace`.

All `scripts/` paths below are relative to this skill's directory.

<HARD-GATE>
You MUST complete the Prerequisites Check before doing any analysis. Run the check script and verify the output. Do NOT skip this step.
</HARD-GATE>

## Prerequisites Check

```bash
bash scripts/prerequisites-check.sh
```

```
✓ All checks passed → Proceed to capture or analysis
⚠ BLOCKED → Check script output for specific fix instructions
```

For troubleshooting, see [references/troubleshooting.md](references/troubleshooting.md).

## Capture Trace Data

### Capture latest version

```bash
bash scripts/capture-trace.sh
```

Installs the latest Claude Code via npm, runs it with `claude-trace`, and outputs the JSONL trace file path.

### Capture a specific version

```bash
bash scripts/analyze-version.sh <version>
# Example: bash scripts/analyze-version.sh <version>
```

### Compare two versions

```bash
bash scripts/analyze-version.sh <v1>
bash scripts/analyze-version.sh <v2>
bash scripts/compare-versions.sh <v1> <v2>
```

See [references/version-analysis.md](references/version-analysis.md) for details.

## Analyze Trace Data

All analysis MUST be done on real JSONL trace files. If no trace data is available, capture it first using the scripts above. **Do not guess or assume any patterns — extract everything from the data.**

### Step 1: Filter LLM requests

Trace files contain all HTTP traffic (OAuth, MCP, telemetry, etc.). Always filter first:

```bash
LLM='select(.request.url | test("v1/messages"))'
```

### Step 2: Extract overview

```bash
# Request overview
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
}" FILE.jsonl
```

### Step 3: Deep inspection commands

Use these jq commands to extract specific aspects. Replace `FILE.jsonl` with the actual trace file path.

```bash
# System prompt blocks (text, length, cache control)
jq -c "$LLM | [.request.body.system[]? | {preview: (.text | .[0:80]), len: (.text | length), cache: .cache_control}]" FILE.jsonl

# Full system prompt text
jq -r "$LLM | .request.body.system[]? | .text" FILE.jsonl

# Tool names
jq -r "$LLM | .request.body.tools[]?.name" FILE.jsonl | sort -u

# Tool count per request
jq -c "$LLM | {tools: (.request.body.tools // [] | length), model: .request.body.model}" FILE.jsonl

# Thinking and effort config
jq -c "$LLM | {thinking: .request.body.thinking, effort: .request.body.output_config}" FILE.jsonl

# Context management
jq -c "$LLM | .request.body.context_management" FILE.jsonl

# Message count per request (shows growth across turns)
jq -c "$LLM | (.request.body.messages | length)" FILE.jsonl

# system-reminder tags in user messages
jq -r "$LLM | [.request.body.messages[] | if .content | type == \"array\" then [.content[] | select(.type == \"text\") | .text] | join(\"\") else .content // \"\" end] | join(\"\\n\")" FILE.jsonl | grep -A5 'system-reminder'

# Deferred tools declaration
jq -r "$LLM | .request.body.messages[] | if .content | type == \"string\" then . else .content[]? end | select(.text? // . | tostring | test(\"available-deferred-tools\"))" FILE.jsonl | head -10

# All request URLs (shows non-LLM traffic)
jq -c '{method: .request.method, url: .request.url}' FILE.jsonl
```

### Step 4: Generate HTML report (optional)

```bash
claude-trace --generate-html FILE.jsonl
```

## Important Notes

- **No hardcoded knowledge.** This skill does not contain any pre-baked descriptions of Claude Code's context engineering patterns. All findings must come from real trace data.
- **Data may vary.** Claude Code's behavior changes across versions. Do not assume patterns observed in one version apply to another — always verify with fresh traces.
- **If capture fails**, tell the user honestly what went wrong. Do not fill in gaps with assumptions.
- **Anthropic API format.** Claude Code uses the Anthropic Messages API, not OpenAI format. System prompt is in `.request.body.system[]` array, tools use `.tools[].name` (not `.tools[].function.name`).
