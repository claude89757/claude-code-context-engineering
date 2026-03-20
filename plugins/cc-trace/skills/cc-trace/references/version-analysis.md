# Version Analysis

Analyze specific Claude Code versions or compare behavior across versions.

## List Available Versions

```bash
# Latest 20 stable versions
npm view @anthropic-ai/claude-code versions --json 2>/dev/null | \
  jq -r '.[]' | grep -v -E '(next|beta|alpha|rc|canary)' | tail -20

# All version types
npm view @anthropic-ai/claude-code versions --json 2>/dev/null | jq -r '.[]' | tail -30

# Get latest version
npm view @anthropic-ai/claude-code version
```

## Analyze a Specific Version

```bash
# Analyze latest
bash scripts/capture-trace.sh

# Analyze a specific version (get available versions from the commands above)
bash scripts/analyze-version.sh <version>
```

The script:
1. Installs the version via `npm install` to a temp dir
2. Runs `claude-trace` with `--claude-path` pointing to the npm `cli.js`
3. Outputs all captured request data (models, tools, system prompt size, thinking config, etc.)

## Compare Two Versions

```bash
# First list versions to pick two for comparison
npm view @anthropic-ai/claude-code versions --json | jq -r '.[]' | grep -v -E '(next|beta|alpha|rc|canary)' | tail -10

# Analyze both, then compare
bash scripts/analyze-version.sh <version_a>
bash scripts/analyze-version.sh <version_b>
bash scripts/compare-versions.sh <version_a> <version_b>
```

The comparison shows diffs in:
- System prompt text
- Tool counts and names
- Thinking and effort configuration
- Context management settings
- Model routing and token limits
