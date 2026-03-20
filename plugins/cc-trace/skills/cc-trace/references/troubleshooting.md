# Troubleshooting: CC Trace

## "Claude Code cannot be launched inside another Claude Code session"

**Cause:** The `CLAUDECODE` env var is set when running inside Claude Code.

**Fix:** Scripts already handle this with `unset CLAUDECODE`. If running manually:
```bash
unset CLAUDECODE && claude-trace --claude-path <path>/cli.js --run-with -p "hello"
```

## claude-trace cannot intercept the system claude binary

**Cause:** Claude Code v2.x installs as a native binary (Mach-O/ELF), not Node.js.

**Fix:** Use the npm Node.js version instead:
```bash
WORK=$(mktemp -d /tmp/claude-trace-fix-XXXXX)
npm install --prefix "$WORK" @anthropic-ai/claude-code --no-save
claude-trace --claude-path "$WORK/node_modules/@anthropic-ai/claude-code/cli.js" --no-open --run-with -p "hello"
```

## Trace file is empty (0 bytes)

**Possible causes:**
- No API key / OAuth token available
- Network issue
- Claude Code exited before making API calls

**Fix:** Check that `claude` works standalone first:
```bash
WORK=$(mktemp -d /tmp/claude-test-XXXXX)
npm install --prefix "$WORK" @anthropic-ai/claude-code --no-save
unset CLAUDECODE
node "$WORK/node_modules/@anthropic-ai/claude-code/cli.js" -p "hello"
```

## jq fails on JSONL file

**Symptom:** `jq: error (at FILE.jsonl:1): ... is not valid`

**Fix:**
```bash
# Check which lines are valid JSON
while IFS= read -r line; do
  echo "$line" | jq empty 2>/dev/null && echo "OK" || echo "INVALID"
done < FILE.jsonl

# Skip invalid lines
jq -c '...' FILE.jsonl 2>/dev/null
```

## jq not available

**Workaround:** Use Python:
```bash
python3 -c "
import json, sys
for line in open(sys.argv[1]):
    d = json.loads(line)
    b = d['request'].get('body', {})
    if isinstance(b, str):
        try: b = json.loads(b)
        except: continue
    sys_blocks = b.get('system', [])
    print(json.dumps({
        'model': b.get('model'),
        'max_tokens': b.get('max_tokens'),
        'msgs': len(b.get('messages', [])),
        'tools': len(b.get('tools', [])),
        'sys_blocks': len(sys_blocks),
        'thinking': b.get('thinking'),
        'effort': b.get('output_config')
    }))
" FILE.jsonl
```

## Version installation fails

```bash
# Check version exists
npm view @anthropic-ai/claude-code versions --json | jq '.[-5:]'

# Check network
npm ping
```

## Temp directory accumulation

```bash
ls -ld /tmp/claude-code-*/ 2>/dev/null
du -sh /tmp/claude-code-*/ 2>/dev/null
# Clean up
rm -rf /tmp/claude-code-*/
```
