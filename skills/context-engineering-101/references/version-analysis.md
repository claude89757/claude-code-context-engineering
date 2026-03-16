# Version Analysis

Analyze specific Claude Code versions or compare behavior across versions.

## List Available Versions

```bash
# Latest 20 stable versions
npm view @anthropic-ai/claude-code versions --json 2>/dev/null | \
  jq -r '.[]' | grep -v -E '(next|beta|alpha|rc|canary)' | tail -20

# All version types (stable + beta + canary)
npm view @anthropic-ai/claude-code versions --json 2>/dev/null | jq -r '.[]' | tail -30
```

## Analyze a Specific Version

```bash
# Run from the skill's scripts/ directory
bash scripts/analyze-version.sh 2.1.74
```

The script installs the specified version to a temp directory, runs claude-trace against it, and outputs a request overview including:
- Model name
- Max tokens
- Message count and tool count
- System prompt block count and total length
- Thinking configuration (type, budget_tokens)
- Reasoning effort level

## Compare Two Versions

```bash
# First analyze both versions, then compare
bash scripts/analyze-version.sh 2.1.70
bash scripts/analyze-version.sh 2.1.74
bash scripts/compare-versions.sh 2.1.70 2.1.74
```

The comparison script diffs:
- **System prompts** — extracted from `.request.body.system[]` array
- **Tool counts and names** — using Anthropic format `.tools[].name`
- **Thinking configuration** — type, budget_tokens, effort level
- **Context management** — clear_thinking policy and keep settings
- **Model routing** — model name and max_tokens distribution

**Tip:** Adjacent patch versions often have identical system prompts. Compare across minor version boundaries for visible changes in thinking/effort configuration.
