"""Claude snake_case input and permissionDecision output; never reused for Google."""
import json
import sys
from pathlib import Path
from common import ROOT, write, now
from hook_core import evaluate

def respond(event, decision, reason):
    if event == 'PreToolUse':
        native = {'allow': 'allow', 'deny': 'deny', 'ask': 'ask'}[decision]
        # allow delegates to normal permissions; it does not auto-grant shell access.
        return {'hookSpecificOutput': {'hookEventName': event, 'permissionDecision': native, 'permissionDecisionReason': reason}}
    if event == 'SessionStart':
        return {'hookSpecificOutput': {'hookEventName': event, 'additionalContext': reason}}
    if event == 'PostToolUse':
        return {'hookSpecificOutput': {'hookEventName': event, 'additionalContext': reason}}
    # Do not force an endless continuation loop for missing evidence; report blocked completion.
    return {'systemMessage': reason}

def main():
    event = sys.argv[1]
    try:
        payload = json.load(sys.stdin)
        root = Path(payload.get('cwd', str(ROOT))).resolve()
        if root != ROOT:
            raise ValueError('Hook cwd does not match installed harness root')
        decision, reason = evaluate(root, 'claude', event, payload.get('tool_name', ''), payload.get('tool_input', {}))
        # Do not store tool payloads: they can contain secrets.
        write(root / 'harness/evidence/hook-claude-last.json', {'event': event, 'decision': decision, 'reason': reason, 'time': now()})
        with (root / 'harness/evidence/hook-claude.log').open('a') as log:
            log.write(json.dumps({'event': event, 'decision': decision, 'reason': reason, 'tool_name': payload.get('tool_name', '')}) + '\n')
        print(json.dumps(respond(event, decision, reason)))
        return 0
    except Exception as e:
        if event == 'PreToolUse':
            print(json.dumps(respond(event, 'deny', 'Harness error: ' + str(e))))
            return 0
        print('Harness failure: ' + str(e), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
