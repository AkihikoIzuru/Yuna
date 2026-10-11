import json
import re

def test_parse(content):
    # Copy the new logic
    start = content.find('{"tool"')
    if start == -1:
        start = content.find('{ "tool"')
    if start == -1:
        return None

    brace_count = 0
    in_string = False
    escape_next = False
    end = -1

    for i, char in enumerate(content[start:], start=start):
        if escape_next:
            escape_next = False
            continue
        if char == '\\' and in_string:
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break

    if end > start:
        json_str = content[start:end]
        try:
            return json.loads(json_str)
        except:
            pass
    return None

# Test cases
tests = [
    '{"tool": "set_volume", "args": {"level": 20}}',
    '{"tool": "open_app", "args": {"app_name": "chrome"}}',
    'Some text {"tool": "get_time", "args": {}} more text',
    '```json\n{"tool": "get_system_info", "args": {}}\n```',
    'No tool here',
]

for t in tests:
    result = test_parse(t)
    print(f'Input: {t[:60]}...')
    print(f'Result: {result}')
    print()