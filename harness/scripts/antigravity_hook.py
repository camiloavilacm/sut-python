"""Google camelCase toolCall protocol. Exit code is not Claude's blocking API."""
import json
import sys
from pathlib import Path
from common import ROOT, write, now
from hook_core import evaluate

def respond(event, decision, reason):
    if event == 'PreToolUse':
        return {'decision': {'allow': 'allow', 'deny': 'deny', 'ask': 'force_ask'}[decision], 'reason': reason}
    if event == 'SessionStart':
        return {'injectSteps': [{'systemMessage': {'systemMessage': reason}}]}
    if event == 'PostToolUse':
        return {}  # Native protocol cannot carry an audit verdict here; persisted external report is mandatory.
    return {'decision': 'stop', 'reason': reason}

def main():
    event = sys.argv[1]
    try:
        payload = json.load(sys.stdin)
        paths = [Path(x).resolve() for x in payload.get('workspacePaths', [])]
        if ROOT not in paths:
            raise ValueError('Installed harness root missing from workspacePaths')
        call = payload.get('toolCall', {})
        decision, reason = evaluate(ROOT, 'antigravity', event, call.get('name', ''), call.get('args', {}))
        write(ROOT / 'harness/evidence/hook-antigravity-last.json', {'event': event, 'decision': decision, 'reason': reason, 'time': now()})
        with (ROOT / 'harness/evidence/hook-antigravity.log').open('a') as log:
            log.write(json.dumps({'event': event, 'decision': decision, 'reason': reason, 'tool_name': call.get('name', ''), 'argument_keys': sorted(call.get('args', {})), 'tool_call_keys': sorted(call), 'payload_keys': sorted(payload)}) + '\n')
        print(json.dumps(respond(event, decision, reason)))
        return 0
    except Exception as e:
        if event == 'PreToolUse':
            print(json.dumps(respond(event, 'deny', 'Harness error: ' + str(e))))
            return 0
        print('Harness failure: ' + str(e), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
