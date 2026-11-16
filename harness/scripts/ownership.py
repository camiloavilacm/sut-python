"""Explicit release/claim; cannot grant step authorization."""
import argparse
import fcntl
from pathlib import Path
from common import ROOT, state, preflight, write, inventory, git_context, read, now, cli_error, audit, config

def transfer(root, action, provider, owner, handoff):
    lock = root / 'harness/evidence/ownership.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        s = state(root)
        if action == 'release':
            preflight(root, s['authorized_step'], provider, owner)
            checks = []
            for path in s['evidence']:
                item = read(root / path)
                checks.append({k: item.get(k) for k in ('check_id', 'command', 'exit_code', 'status', 'source_sha256')})
            baseline = root / s['baseline']
            write(handoff, {'step': s['authorized_step'], 'released_by': s['owner'], 'time': now(), 'inventory': inventory(root), 'git': git_context(root), 'completed_steps': s['completed_steps'], 'recorded_checks': checks, 'evidence': s['evidence'], 'scope_audit': audit(root, read(baseline)) if baseline.exists() else {'status': 'NOT RUN'}, 'blockers': s['blockers'], 'pending': s['next_action'], 'exclusions': 'No future-step execution; no product work during Phase 0.5'})
            s['owner'] = None
        else:
            if config(root, 'providers')['providers'][provider].get('validation_mode') == 'artifacts-only':
                raise ValueError('Artifacts-only provider cannot claim writable ownership')
            if s['owner'] is not None:
                raise ValueError('Previous owner has not released ownership')
            h = read(handoff)
            preflight(root, s['authorized_step'], provider, owner, require_owner=False)
            expected = dict(h['inventory'])
            expected.pop('harness/state.json', None)
            current = inventory(root)
            current.pop('harness/state.json', None)
            if h['step'] != s['authorized_step'] or expected != current or h['git'] != git_context(root):
                raise ValueError('Handoff and actual workspace differ')
            s['owner'] = {'provider': provider, 'id': owner}
        write(root / 'harness/state.json', s)
        return s

def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['release', 'claim'])
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--provider', required=True)
    p.add_argument('--owner', required=True)
    p.add_argument('--handoff', type=Path, required=True)
    a = p.parse_args()
    try:
        transfer(a.root, a.action, a.provider, a.owner, a.handoff)
        print('PASS: ownership ' + a.action)
        return 0
    except Exception as e:
        return cli_error(e)

if __name__ == '__main__':
    raise SystemExit(main())
