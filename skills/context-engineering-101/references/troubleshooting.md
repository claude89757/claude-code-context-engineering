# Troubleshooting: Context Engineering 101

> **Note:** `scripts/prerequisites-check.sh` auto-handles most setup issues below (tool installation, trace generation). Consult this guide only when the script reports BLOCKED or warnings.

## Prerequisite Issues

### Claude Code CLI installation fails

**Symptom:** `npm install -g @anthropic-ai/claude-code` fails with permission errors or network issues.

**Fix:**
```bash
# If permission denied, use sudo or fix npm permissions
sudo npm install -g @anthropic-ai/claude-code
# OR fix npm permissions:
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
npm install -g @anthropic-ai/claude-code
export PATH=~/.npm-global/bin:$PATH
```

### claude-trace installation fails

**Symptom:** `npm install -g @mariozechner/claude-trace` fails.

**Fix:**
```bash
# Try npx instead (no global install needed)
npx --yes @mariozechner/claude-trace --version

# Or install globally with sudo
sudo npm install -g @mariozechner/claude-trace

# Verify
claude-trace --version
```

### node version too old

**Symptom:** SyntaxError or feature not supported.

**Fix:**
```bash
node --version  # Need 16+
brew upgrade node          # macOS
nvm install 18 && nvm use 18  # if using nvm
```

### jq not available and cannot install

**Workaround:** Use Python instead of jq:
```bash
python3 -c "
import json, sys
for line in open(sys.argv[1]):
    d = json.loads(line)
    r = d['request']['body']
    sys_blocks = r.get('system', [])
    print(json.dumps({
        'model': r.get('model','?'),
        'max_tokens': r.get('max_tokens','?'),
        'msgs': len(r.get('messages',[])),
        'tools': len(r.get('tools',[])),
        'sys_blocks': len(sys_blocks),
        'sys_len': sum(len(b.get('text','')) for b in sys_blocks),
        'thinking': r.get('thinking'),
        'effort': r.get('output_config',{}).get('effort')
    }))
" FILE.jsonl
```

## Trace Data Issues

### No trace files at all

**Symptom:** `~/.claude-trace/` directory doesn't exist or is completely empty.

**Fix:**
```bash
# Manual trace generation
claude-trace --run claude -- -p "say hello"

# Or with npx
npx --yes @mariozechner/claude-trace --run claude -- -p "say hello"

# Check generated files
ls -lhS ~/.claude-trace/*.jsonl | head -5
```

### Trace files have data but jq fails

**Symptom:** `jq: error (at FILE.jsonl:1): ... is not valid`

**Fix:**
```bash
# Check which lines are valid
while IFS= read -r line; do
  echo "$line" | jq empty 2>/dev/null && echo "OK" || echo "INVALID"
done < FILE.jsonl

# Skip invalid lines
jq -c '...' FILE.jsonl 2>/dev/null
```

## HTML Report Issues

### HTML generation produces no output

**Fix:**
```bash
# Use claude-trace to generate HTML
claude-trace --generate-html ~/.claude-trace/FILE.jsonl

# Or with npx
npx --yes @mariozechner/claude-trace --generate-html ~/.claude-trace/FILE.jsonl
```

### HTML report missing response data

**Symptom:** Conversations view shows requests but no assistant responses.

**Cause:** Response data may be in `body_raw` (SSE stream), not `body`.

**Fix:**
```bash
# Verify body_raw exists and has data
jq -c '{body_raw_len: (.response.body_raw // "" | length)}' FILE.jsonl
```

## Pattern Analysis Issues

### Can't find system prompt

**Symptom:** jq command returns empty when looking for system prompt.

**Cause:** Claude Code uses `.request.body.system[]` array (Anthropic API format), NOT `messages[0]` (OpenAI format).

**Fix:**
```bash
# CORRECT: Extract from system[] array
jq -r '.request.body.system[] | .text' FILE.jsonl | head -50

# WRONG (OpenAI format, won't work for Claude Code):
# jq -r '.request.body.messages[0].content' FILE.jsonl
```

### Tool names extraction returns empty

**Cause:** Claude Code uses Anthropic format `.tools[].name`, not OpenAI format `.tools[].function.name`.

**Fix:**
```bash
# CORRECT: Anthropic format
jq -r '.request.body.tools[]?.name' FILE.jsonl | sort -u

# WRONG (OpenAI format):
# jq -r '.request.body.tools[]?.function.name' FILE.jsonl
```

### No thinking data in traces

**Cause:** Thinking configuration may not be present in older Claude Code versions, or the model decided not to think (adaptive mode).

**Fix:**
```bash
# Check if thinking field exists at all
jq -c 'select(.request.body.thinking != null) | {thinking: .request.body.thinking}' FILE.jsonl

# Check effort level
jq -c '.request.body.output_config' FILE.jsonl
```

## Version Analysis Issues

### Version installation fails

**Fix:**
```bash
# Verify the version exists
npm view @anthropic-ai/claude-code versions --json | jq '.[-10:]'

# If network error, check connectivity
npm ping
```

### Trace capture for specific version produces empty file

**Cause:** The version may be too old to support trace interception, or the binary path is incorrect.

**Fix:**
```bash
# Verify binary exists and is executable
ls -la $WORK_DIR/node_modules/.bin/claude

# Verify binary works
$WORK_DIR/node_modules/.bin/claude --version

# Try with explicit prompt
claude-trace --run "$WORK_DIR/node_modules/.bin/claude" -- -p "hello"
```

### Temp directory accumulation

**Fix:**
```bash
# List all version analysis temp dirs
ls -ld /tmp/claude-code-*/ 2>/dev/null

# Check total size
du -sh /tmp/claude-code-*/ 2>/dev/null

# Clean up all at once
rm -rf /tmp/claude-code-*/
```

## Ultrathink Issues

### Can't see thinking blocks in trace

**Cause:** `thinking.type: "adaptive"` means the model decides when to think. For simple prompts, it may skip thinking entirely.

**Fix:**
```bash
# Use a complex prompt to trigger thinking
claude-trace --run claude -- -p "Analyze the architectural trade-offs between microservices and monolith for a startup with 5 engineers"

# Then check thinking in the trace
jq -c '{thinking: .request.body.thinking, effort: .request.body.output_config.effort}' ~/.claude-trace/LATEST.jsonl
```

### Effort level doesn't change

**Cause:** Effort is injected via `<system-reminder>` at runtime, not from user config.

**Fix:**
```bash
# Check system-reminder content for effort injection
jq -r '.request.body.messages[] | if .content | type == "array" then [.content[] | select(.type == "text") | .text] | join("") else .content // "" end' FILE.jsonl | grep -i "effort\|reasoning"
```

### Context management not clearing thinking

**Cause:** `clear_thinking_20251015` only clears thinking from prior turns, not the current turn.

**Fix:**
```bash
# Verify context_management config
jq -c '.request.body.context_management' FILE.jsonl

# Expected output:
# {"edits":[{"type":"clear_thinking_20251015","keep":"all"}]}
```
