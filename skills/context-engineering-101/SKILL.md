---
name: context-engineering-101
description: Use when learning how Claude Code constructs prompts, manages context windows, uses ultrathink (extended thinking), or debugging why Claude Code did or didn't do something. Uses claude-trace to capture and visualize actual API requests, system prompts, tool definitions, thinking configuration, and reasoning effort levels.
---

# Context Engineering 101 (Claude Code Ultrathink Edition)

Use `claude-trace` (npm package `@mariozechner/claude-trace`) to intercept and visualize the exact API requests Claude Code sends to the Anthropic API. Focus on **extended thinking (ultrathink)** and context engineering patterns unique to Claude Code.

All `scripts/` paths below are relative to this skill's directory.

<HARD-GATE>
You MUST complete the Prerequisites Check before starting the Learning Loop. Do NOT skip this step, even if you "think" the tools are installed. Run the check script and verify the output.
</HARD-GATE>

## Prerequisites Check

Run the auto-install and verification script:

```bash
bash scripts/prerequisites-check.sh
```

The script auto-installs node, jq, Claude Code CLI, claude-trace, and generates trace data if missing.

```
✓ All checks passed → Proceed to Learning Loop
⚠ BLOCKED → Check script output for specific fix instructions
```

For detailed troubleshooting, see [references/troubleshooting.md](references/troubleshooting.md).

## Learning Loop

**1. Find trace data** at `~/.claude-trace/*.jsonl` (pick largest non-empty files).

> **Important:** Trace files contain all HTTP requests (OAuth, MCP, telemetry, etc.). Always filter for LLM requests with `select(.request.url | test("v1/messages"))`.

```bash
# Reusable filter: only LLM API calls
LLM='select(.request.url | test("v1/messages"))'

# Overview of all LLM requests in a trace
jq -c "$LLM | {model: .request.body.model, max_tokens: .request.body.max_tokens, msgs: (.request.body.messages | length), tools: (.request.body.tools // [] | length), sys_blocks: (.request.body.system // [] | length), thinking: .request.body.thinking, effort: .request.body.output_config.effort}" FILE.jsonl

# Extract system prompt (from system[] array, not messages)
jq -r "$LLM | .request.body.system[] | .text" FILE.jsonl | head -200
```

**2. Generate HTML report** (optional — skip if CLI-only):

```bash
claude-trace --generate-html ~/.claude-trace/FILE.jsonl
```

**3. Inspect** the HTML report's **Conversations** tab (system prompt, tool definitions, message flow, `<system-reminder>` tags, thinking blocks) or use the jq commands above and the Inspection Checklist below.

## Version Analysis (Optional)

See [references/version-analysis.md](references/version-analysis.md) for analyzing specific versions and cross-version comparison.

Scripts: `scripts/analyze-version.sh <version>` and `scripts/compare-versions.sh <v1> <v2>`.

## 7 Context Engineering Patterns

1. **Layered System Prompt** (~25KB total, 3 blocks) — Block 1: billing header (~80 chars, `cc_version=X.Y.Z`); Block 2: agent identity (~62 chars, cached 1h `ephemeral`); Block 3: core instructions (~25KB, cached 1h). Includes security, task execution, tool usage, tone, memory system, environment info. Constant across turns.

2. **Extended Thinking (Ultrathink)** — `thinking.type: "adaptive"` lets the model dynamically decide when to think. Triggered by keywords like "ultrathink" or "think harder". See **Ultrathink Deep Dive** below.

3. **Reasoning Effort Levels** — `output_config.effort`: `low` / `medium` / `high`. Injected via `<system-reminder>` in user messages. Controls how much reasoning the model applies. Default is `medium`; `/fast` toggle adjusts this.

4. **Context Management** — `context_management.edits: [{type: "clear_thinking_20251015", keep: "all"}]`. Clears thinking blocks from prior turns to free context space while keeping all content blocks.

5. **Tool Lazy Loading** — 9 base tools (Agent, Bash, Glob, Grep, Read, Edit, Write, Skill, ToolSearch) always loaded. Deferred tools (WebFetch, WebSearch, TaskCreate, etc.) + MCP tools loaded on-demand via `ToolSearch`. Declared in `<available-deferred-tools>` tag in user messages.

6. **Dynamic Context Injection** — Runtime context injected as `<system-reminder>` tags inside user messages (not system prompt), keeping the base prompt cacheable. Includes: SessionStart hooks, skill lists, current date, reasoning effort, available deferred tools.

7. **Full History Replay & Compression** — Complete message history sent each turn (2 → 4 → 7 → 9+). Near context limit, the system automatically compresses prior messages. Conversation is not limited by the context window.

## Ultrathink Deep Dive

### Trigger Methods

- **Keywords**: "ultrathink", "think harder", "think more carefully" in user messages
- **API config**: `thinking.type: "adaptive"` (dynamic) or explicit `budget_tokens` (fixed allocation)
- **/fast toggle**: Switches between effort levels without changing thinking type

### Three Configuration Dimensions

| Dimension | Field | Values | Effect |
|-----------|-------|--------|--------|
| Thinking type | `thinking.type` | `"adaptive"` / `"enabled"` | Whether model decides autonomously or always thinks |
| Budget tokens | `thinking.budget_tokens` | integer | Max tokens for thinking (when type=enabled) |
| Reasoning effort | `output_config.effort` | `"low"` / `"medium"` / `"high"` | Overall reasoning depth |

### How Effort is Injected

Claude Code injects reasoning effort via `<system-reminder>` tags in user messages (observed format may vary by version):

```
<system-reminder>
<thinking_mode>auto</thinking_mode>
<reasoning_effort>medium</reasoning_effort>
</system-reminder>
```

> **Note:** This injection may only appear in specific scenarios (e.g., after `/fast` toggle or multi-turn conversations). In the base case, effort is set at the API level via `output_config.effort` and thinking is configured via `thinking.type`. Use the jq commands in the Inspection Checklist to verify what your trace actually contains.

This keeps the system prompt cacheable while allowing per-turn effort adjustment.

### Impact on Behavior

- **High effort / ultrathink**: Deeper analysis, more thorough code review, better architectural decisions. Higher token usage and potential rate limiting.
- **Medium effort**: Default balance of speed and quality. Suitable for most tasks.
- **Low effort**: Fast responses for simple queries. Skips deep reasoning.

### Inspecting Thinking in Traces

```bash
LLM='select(.request.url | test("v1/messages"))'

# Check thinking configuration per request
jq -c "$LLM | {thinking: .request.body.thinking, effort: .request.body.output_config.effort, ctx_mgmt: .request.body.context_management}" FILE.jsonl

# Find requests with explicit budget_tokens
jq -c "$LLM | select(.request.body.thinking.budget_tokens != null) | {budget: .request.body.thinking.budget_tokens, model: .request.body.model}" FILE.jsonl

# Check how context_management handles thinking blocks
jq -c "$LLM | .request.body.context_management" FILE.jsonl
```

## Common Misconceptions

| Wrong | Right |
|---|---|
| "System prompt is in messages[0]" | Claude Code uses `.request.body.system[]` array (Anthropic API format), not OpenAI-style messages[0] |
| "Tools use function.name format" | Anthropic format: `.tools[].name`, not `.tools[].function.name` |
| "thinking: adaptive means always thinking" | Adaptive means the model decides when to think; it may skip thinking for simple queries |
| "effort: high = ultrathink" | Effort controls reasoning depth; ultrathink triggers extended thinking blocks (different mechanism) |
| "Context compression loses data" | Compression is selective — `clear_thinking_20251015` with `keep: "all"` preserves content, only clears thinking blocks |

## Inspection Checklist

```bash
# Reusable filter: only LLM API calls (trace files also contain OAuth, MCP, telemetry requests)
LLM='select(.request.url | test("v1/messages"))'

# System prompt (3 blocks in system[] array)
jq -r "$LLM | .request.body.system[] | .text" FILE.jsonl | head -50

# System prompt total length
jq -c "$LLM | [.request.body.system[] | .text | length] | add" FILE.jsonl

# Cache control on system blocks
jq -c "$LLM | [.request.body.system[] | {text_preview: (.text | .[0:60]), cache: .cache_control}]" FILE.jsonl

# Tool count per request (lazy loading visible)
jq -c "$LLM | {tools: (.request.body.tools // [] | length), model: .request.body.model}" FILE.jsonl

# Tool names (Anthropic format: .name not .function.name)
jq -r "$LLM | .request.body.tools[]?.name" FILE.jsonl | sort -u

# Thinking and effort config
jq -c "$LLM | {thinking: .request.body.thinking, effort: .request.body.output_config.effort}" FILE.jsonl

# Context management
jq -c "$LLM | .request.body.context_management" FILE.jsonl

# system-reminder injection points
jq -r "$LLM | [.request.body.messages[] | if .content | type == \"array\" then [.content[] | select(.type == \"text\") | .text] | join(\"\") else .content // \"\" end] | join(\"\\n\")" FILE.jsonl | grep -c 'system-reminder'

# Message count growth per turn
jq -c "$LLM | (.request.body.messages | length)" FILE.jsonl

# Deferred tools declaration
jq -r "$LLM | .request.body.messages[] | if .content | type == \"string\" then . else .content[]? end | select(.text? // . | tostring | test(\"available-deferred-tools\"))" FILE.jsonl | head -5
```

- [ ] System prompt structure (3 blocks: billing, identity, instructions)
- [ ] Tool count per request (lazy loading visible)
- [ ] Message count growth per turn
- [ ] Thinking configuration (adaptive vs enabled, budget_tokens)
- [ ] Reasoning effort level (low/medium/high)
- [ ] Context management (clear_thinking, keep policy)
- [ ] system-reminder injection points
- [ ] Deferred tools declaration
- [ ] Cache control on system blocks (ephemeral, 1h TTL)

If stuck on any checklist item, see [references/troubleshooting.md](references/troubleshooting.md).
