#!/usr/bin/env python3
"""Analyze claude-trace JSONL files to study Claude Code's context engineering."""
import json
import sys
import os

def analyze_trace(jsonl_path):
    with open(jsonl_path) as f:
        entries = [json.loads(line) for line in f]

    output_dir = os.path.dirname(jsonl_path)
    base_name = os.path.splitext(os.path.basename(jsonl_path))[0]

    print(f"\n{'='*60}")
    print(f"Trace Analysis: {jsonl_path}")
    print(f"Total entries: {len(entries)}")
    print(f"{'='*60}\n")

    # Categorize requests
    api_calls = []
    message_turns = []

    for i, entry in enumerate(entries):
        req = entry.get('request', {})
        url = req.get('url', '')
        method = req.get('method', '')

        print(f"[{i+1}] {method} {url}")

        if '/v1/messages' in url:
            body = req.get('body', {})
            if isinstance(body, str):
                body = json.loads(body)

            msgs = body.get('messages', [])
            system = body.get('system', [])
            tools = body.get('tools', [])

            sys_chars = sum(len(str(s)) for s in system) if isinstance(system, list) else len(str(system))

            turn_info = {
                'entry_index': i,
                'model': body.get('model', ''),
                'num_messages': len(msgs),
                'system_blocks': len(system) if isinstance(system, list) else 1,
                'system_chars': sys_chars,
                'num_tools': len(tools),
                'max_tokens': body.get('max_tokens', 0),
                'temperature': body.get('temperature', None),
            }
            message_turns.append(turn_info)

            print(f"    Model: {turn_info['model']}")
            print(f"    System: {turn_info['system_blocks']} blocks, {sys_chars} chars")
            print(f"    Messages: {len(msgs)}, Tools: {len(tools)}")
            print(f"    Max tokens: {turn_info['max_tokens']}")

            # Message breakdown
            for j, msg in enumerate(msgs):
                role = msg['role']
                content = msg['content']
                if isinstance(content, str):
                    print(f"    Msg {j+1} [{role}]: text ({len(content)} chars)")
                elif isinstance(content, list):
                    types = []
                    for block in content:
                        btype = block.get('type', '?')
                        if btype == 'tool_use':
                            types.append(f"tool_use({block.get('name','')})")
                        elif btype == 'tool_result':
                            types.append(f"tool_result")
                        else:
                            types.append(btype)
                    print(f"    Msg {j+1} [{role}]: {types}")

    # Extract detailed content from the first /v1/messages call
    for i, entry in enumerate(entries):
        req = entry.get('request', {})
        url = req.get('url', '')
        if '/v1/messages' not in url:
            continue

        body = req.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)

        system = body.get('system', [])

        # Save system prompt
        prompt_file = os.path.join(output_dir, f'{base_name}_system_prompt.md')
        with open(prompt_file, 'w') as out:
            out.write(f"# System Prompt from {base_name}\n\n")
            if isinstance(system, list):
                for j, block in enumerate(system):
                    if isinstance(block, dict):
                        text = block.get('text', '')
                        cache = block.get('cache_control', {})
                        out.write(f"## Block {j+1}")
                        if cache:
                            out.write(f" (cache: {cache})")
                        out.write(f"\n\n```\n{text}\n```\n\n")
        print(f"\nSaved system prompt to: {prompt_file}")

        # Save tools
        tools = body.get('tools', [])
        tools_file = os.path.join(output_dir, f'{base_name}_tools.json')
        with open(tools_file, 'w') as out:
            json.dump(tools, out, indent=2, ensure_ascii=False)
        print(f"Saved {len(tools)} tools to: {tools_file}")

        # Save full request body
        full_file = os.path.join(output_dir, f'{base_name}_full.json')
        with open(full_file, 'w') as out:
            json.dump(body, out, indent=2, ensure_ascii=False)
        print(f"Saved full request to: {full_file}")

        break  # Only process first messages call for system prompt

    # Context engineering observations
    print(f"\n{'='*60}")
    print("Context Engineering Observations:")
    print(f"{'='*60}")

    if message_turns:
        print(f"\n1. API Turns: {len(message_turns)}")
        for t in message_turns:
            print(f"   Turn {t['entry_index']+1}: {t['num_messages']} messages, {t['system_chars']} sys chars, {t['num_tools']} tools")

        # Check if system prompt stays constant across turns
        sys_sizes = [t['system_chars'] for t in message_turns]
        if len(set(sys_sizes)) == 1:
            print(f"\n2. System prompt: CONSTANT across turns ({sys_sizes[0]} chars)")
        else:
            print(f"\n2. System prompt: VARIES across turns ({sys_sizes})")

        # Check tool count changes
        tool_counts = [t['num_tools'] for t in message_turns]
        if len(set(tool_counts)) == 1:
            print(f"3. Tools: CONSTANT across turns ({tool_counts[0]} tools)")
        else:
            print(f"3. Tools: VARIES across turns ({tool_counts})")

        # Message growth pattern
        msg_counts = [t['num_messages'] for t in message_turns]
        print(f"4. Message count growth: {msg_counts}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        # Default: analyze all jsonl files in .claude-trace/trace-logs/
        trace_dir = '.claude-trace/trace-logs'
        files = [os.path.join(trace_dir, f) for f in os.listdir(trace_dir) if f.endswith('.jsonl')]
        for f in sorted(files):
            analyze_trace(f)
    else:
        analyze_trace(sys.argv[1])
