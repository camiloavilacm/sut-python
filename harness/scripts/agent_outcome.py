"""Collect formal task outcomes; never grants authorization or executes QA/model calls."""
import argparse
from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import re
import sys
import uuid
from common import (ROOT, state, write, read, validate, preflight, now, digest,
                    source_digest, inventory, git_context, location, safe_relative,
                    sign_evidence, verify_signature, config, cli_error)

ROLES = ('qa-step-executor', 'qa-contract-author', 'qa-verification', 'qa-architecture-reviewer')
READ_ONLY = ('qa-architecture-reviewer', 'qa-verification')


def fingerprint(value):
    return digest(json.dumps(value, sort_keys=True).encode())


def refs(root):
    return {k: {n: v[n] for n in ('head', 'refs')} for k, v in git_context(root).items()}


@contextmanager
def locked(root):
    path = root / 'harness/evidence/ownership.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def directory(root, task_id):
    if not re.fullmatch('[a-f0-9]{32}', task_id):
        raise ValueError('Invalid task ID')
    return safe_relative(root, 'harness/evidence/agent-tasks/' + task_id)


def signed_write(root, path, value):
    value = dict(value, signature=sign_evidence(root, value))
    write(path, value)
    return value


def request(root, task_id):
    value = read(directory(root, task_id) / 'request.json')
    verify_signature(root, value)
    if value['kind'] != 'agent-task-request' or value['task_id'] != task_id:
        raise ValueError('Invalid task request')
    s = state(root)
    if (value['root'] != str(root.resolve()) or value['location'] != location(root)
            or value['authorization_sha256'] != fingerprint(s['authorization'])
            or value['step'] != s['authorized_step']):
        raise ValueError('Task belongs to another authorization, repository or step')
    return value


def start(root, role, provider, actor):
    with locked(root):
        s = state(root)
        if s['owner'] is None:
            raise ValueError('An authorized collector owner is required')
        preflight(root, s['authorized_step'], **{'provider': s['owner']['provider'], 'owner': s['owner']['id']})
        if role not in ROLES or provider not in config(root, 'providers')['providers'] or not actor.strip():
            raise ValueError('Unknown role/provider or empty actor')
        if role not in READ_ONLY and s['owner'] != {'provider': provider, 'id': actor}:
            raise ValueError('Writable tasks must belong to the current owner')
        if role not in READ_ONLY and config(root, 'providers')['providers'][provider]['validation_mode'] == 'artifacts-only':
            raise ValueError('Artifacts-only provider cannot execute writable tasks')
        task_id = uuid.uuid4().hex
        value = {'kind': 'agent-task-request', 'version': 1, 'task_id': task_id,
                 'role': role, 'provider': provider, 'actor': actor, 'step': s['authorized_step'],
                 'collector': s['owner'], 'root': str(root.resolve()), 'location': location(root),
                 'authorization_sha256': fingerprint(s['authorization']), 'started_at': now(),
                 'source_sha256': source_digest(root), 'git': refs(root), 'baseline': s['baseline']}
        value = signed_write(root, directory(root, task_id) / 'request.json', value)
        s.setdefault('agent_tasks', []).append(task_id)
        write(root / 'harness/state.json', s)
        return value


def artifact(root, path):
    target = safe_relative(root, path)
    if path.startswith(('.git/', '.venv/')) or not target.is_file():
        raise ValueError('Artifact must be an existing repository-relative file: ' + path)
    # Reject symlinks even when their target stays inside the repository.
    raw = root
    for part in Path(path).parts:
        raw = raw / part
        if raw.is_symlink():
            raise ValueError('Symlink artifact rejected')
    return digest(target.read_bytes())


def assess(root, req, value):
    validate(root, 'agent-outcome', value)
    for key in ('task_id', 'role', 'provider', 'actor', 'step'):
        if value[key] != req[key]:
            raise ValueError('Outcome identity differs from task: ' + key)
    if value['status'] == 'completed' and (value['blockers'] or value['pending_approvals'] or value['remaining_work']):
        raise ValueError('Completed outcome cannot hide unresolved work or approvals')
    if value['status'] == 'blocked' and not (value['blockers'] or value['pending_approvals']):
        raise ValueError('Blocked outcome must describe its blocker')
    if value['status'] in ('failed', 'not_run') and not (value['blockers'] or value['remaining_work']):
        raise ValueError('Unsuccessful outcome must describe remaining work or blockers')
    if req['role'] in READ_ONLY and (req['source_sha256'] != source_digest(root) or req['git'] != refs(root)):
        raise ValueError('Reviewed source changed during the read-only task')
    hashes = {p: artifact(root, p) for p in value['deliverables']}
    from verify_step import validate_evidence
    registered = set(state(root)['evidence'])
    for entry in value['checks'] + value['commands']:
        if not entry['evidence']:
            raise ValueError('Checks and commands require captured registered evidence')
        matched = False
        for path in entry['evidence']:
            if path not in registered:
                raise ValueError('Evidence is not registered in this repository')
            evidence = read(safe_relative(root, path))
            # NOT RUN can be retained and verified without pretending it executed.
            if evidence['status'] == 'NOT RUN':
                validate(root, 'evidence', evidence)
                verify_signature(root, evidence)
                if evidence['cwd'] != str(root) or evidence['step'] != state(root)['authorized_step']:
                    raise ValueError('NOT RUN evidence belongs to another execution context')
                if evidence['source_sha256'] != source_digest(root):
                    raise ValueError('NOT RUN evidence is stale')
                if evidence['command'] != __import__('verify_step').command(root, evidence['check_id']):
                    raise ValueError('Evidence command is not registered')
                if digest(safe_relative(root, evidence['log']).read_bytes()) != evidence['log_sha256']:
                    raise ValueError('Evidence log changed')
            else:
                validate_evidence(root, evidence)
            if evidence['status'] != entry['status']:
                raise ValueError('Claimed status contradicts recorded evidence')
            if 'check_id' in entry:
                matched |= evidence['check_id'] == entry['check_id']
            else:
                matched |= (entry['argv'] == evidence['command'] and entry['cwd'] == evidence['cwd']
                            and entry['exit_code'] == evidence['exit_code'])
            hashes[path] = artifact(root, path)
        if not matched:
            raise ValueError('Command or check differs from evidence')
    for finding in value.get('findings', []):
        if not finding['evidence']:
            raise ValueError('Review findings require supporting artifacts')
        for path in finding['evidence']:
            hashes[path] = artifact(root, path)
    return hashes


def submit(root, task_id, value):
    with locked(root):
        s = state(root)
        req = request(root, task_id)
        if task_id not in s.get('agent_tasks', []) or s['owner'] != req['collector']:
            raise ValueError('Task is not active for the authorized collector')
        preflight(root, s['authorized_step'], s['owner']['provider'], s['owner']['id'])
        base = directory(root, task_id)
        if (base / 'receipt.json').exists():
            raise ValueError('Accepted outcomes are immutable; register another task')
        try:
            hashes = assess(root, req, value)
        except Exception as exc:
            # Retain diagnostics only; malformed/untrusted input is not accepted evidence.
            write(base / ('rejected-' + uuid.uuid4().hex + '.json'), {'status': 'REJECTED', 'reason': str(exc), 'time': now()})
            raise
        write(base / 'outcome.json', value)
        receipt = {'kind': 'agent-outcome-receipt', 'version': 1, 'task_id': task_id,
                   'request_sha256': digest((base / 'request.json').read_bytes()),
                   'outcome_sha256': digest((base / 'outcome.json').read_bytes()),
                   'source_sha256': source_digest(root), 'git': refs(root),
                   'artifacts': hashes, 'validated_at': now(), 'collector': s['owner']}
        return signed_write(root, base / 'receipt.json', receipt)


def validate_task(root, task_id):
    req = request(root, task_id)
    base = directory(root, task_id)
    receipt = read(base / 'receipt.json')
    verify_signature(root, receipt)
    if (receipt['kind'] != 'agent-outcome-receipt' or receipt['task_id'] != task_id
            or receipt['collector'] != req['collector']
            or receipt['request_sha256'] != digest((base / 'request.json').read_bytes())
            or receipt['outcome_sha256'] != digest((base / 'outcome.json').read_bytes())
            or receipt['source_sha256'] != source_digest(root) or receipt['git'] != refs(root)):
        raise ValueError('Outcome receipt is stale or belongs to another task/source')
    value = read(base / 'outcome.json')
    if receipt['artifacts'] != assess(root, req, value):
        raise ValueError('Outcome artifacts changed')
    return value


def require_outcomes(root, completed=False, ids=None, collector=None):
    s = state(root)
    ids = s.get('agent_tasks', []) if ids is None else ids
    collector = s['owner'] if collector is None else collector
    if not ids:
        raise ValueError('No formal task outcome registered')
    values = []
    for task_id in ids:
        req = request(root, task_id)
        if req['collector'] != collector:
            raise ValueError('Task collector differs from current/handoff owner')
        values.append(validate_task(root, task_id))
    if completed:
        if not any(v['role'] in ('qa-step-executor', 'qa-contract-author') for v in values):
            raise ValueError('Step completion requires an implementation/authoring outcome')
        if any(v['status'] != 'completed' for v in values):
            raise ValueError('Unsuccessful formal task blocks step completion')
    return ids


def render(root, task_id):
    value = validate_task(root, task_id)
    lines = ['# Agent outcome: ' + value['status'], '', value['summary'], '']
    for title, key in [('Deliverables', 'deliverables'), ('Blockers', 'blockers'),
                       ('Pending approvals', 'pending_approvals'), ('Remaining work', 'remaining_work')]:
        lines.extend(['## ' + title, '', *(['- ' + p for p in value[key]] or ['None.']), ''])
    lines.extend(['## Commands and checks', '', '```json', json.dumps(value['commands'] + value['checks'], indent=2), '```', ''])
    if 'findings' in value:
        lines.extend(['## Findings', '', '```json', json.dumps(value['findings'], indent=2), '```', ''])
    lines.extend(['## Boundary', '', value['boundary_confirmation'], ''])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'submit', 'validate', 'render'])
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--role', choices=ROLES)
    parser.add_argument('--provider', choices=['codex', 'claude', 'antigravity'])
    parser.add_argument('--actor')
    parser.add_argument('--task')
    parser.add_argument('--input', help='JSON file, or - for stdin')
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.action == 'start':
            if not all((args.role, args.provider, args.actor)):
                raise ValueError('start requires --role, --provider and --actor')
            result = start(root, args.role, args.provider, args.actor)
        elif not args.task:
            raise ValueError('--task is required')
        elif args.action == 'submit':
            if not args.input:
                raise ValueError('submit requires --input FILE or -')
            try:
                value = json.load(sys.stdin) if args.input == '-' else read(args.input)
            except (ValueError, OSError) as exc:
                raise ValueError('Invalid JSON input: ' + str(exc)) from exc
            result = submit(root, args.task, value)
        elif args.action == 'validate':
            result = validate_task(root, args.task)
        else:
            print(render(root, args.task))
            return 0
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        return cli_error(exc)


if __name__ == '__main__':
    raise SystemExit(main())
