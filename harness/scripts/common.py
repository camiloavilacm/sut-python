"""Shared deterministic development controller. Never used by QA execution CI."""
from __future__ import annotations
import datetime as dt
import hashlib
import hmac
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
PROVIDERS = ('codex', 'claude', 'antigravity')
PRODUCTS = ('qa-features', 'sut-python', 'sut-node', 'qa-python', 'qa-typescript')

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as f:
        json.dump(data, f, indent=2)
        f.write('\n')
        tmp = f.name
    os.replace(tmp, path)

def config(root, name):
    return yaml.safe_load((root / 'harness/config' / (name + '.yaml')).read_text())

def location(root):
    path = root / 'harness/location.json'
    value = read(path) if path.exists() else {'kind': 'workspace', 'repository': None}
    if value['kind'] not in ('workspace', 'repository') or (value['kind'] == 'repository' and value['repository'] not in PRODUCTS):
        raise ValueError('Invalid harness installation location')
    return value

def validate(root, name, data):
    schema = read(root / 'harness/schemas' / (name + '.schema.json'))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(data)

def state(root):
    s = read(root / 'harness/state.json')
    validate(root, 'state', s)
    return s

def under(path, parent):
    return path == parent or parent in path.parents

def inventory(root):
    """Include empty directories and links; never follow links or git internals."""
    result = {}
    for base, dirs, files in os.walk(root, followlinks=False):
        base = Path(base)
        dirs[:] = sorted(d for d in dirs if d not in ('.git', '__pycache__') and not (d == '.venv' and (base == root or (base.parent == root and base.name in PRODUCTS))))
        for name in dirs + sorted(files):
            p = base / name
            rel = p.relative_to(root).as_posix()
            if rel.startswith('harness/evidence/'):
                continue  # validated separately; scope cannot be expanded through evidence
            if p.is_symlink():
                result[rel] = 'link:' + os.readlink(p)
            elif p.is_dir():
                result[rel] = 'directory'
            else:
                result[rel] = digest(p.read_bytes())
    return result

def git_context(root):
    context = {}
    candidates = [root] + [root / p for p in PRODUCTS if (root / p).exists()]
    for p in candidates:
        if not (p / '.git').exists():
            continue
        entry = {}
        for key, args in [('head', ['rev-parse', 'HEAD']), ('status', ['status', '--porcelain=v1', '--untracked-files=all']), ('refs', ['show-ref'])]:
            r = subprocess.run(['git', '-C', str(p), *args], capture_output=True, text=True)
            entry[key] = {'exit_code': r.returncode, 'output': r.stdout.strip()}
        context[p.relative_to(root).as_posix()] = entry
    return context

def source_digest(root):
    files = inventory(root)
    files.pop('harness/state.json', None)
    # Runtime artifacts are validated separately and remain in scope inventory.
    if location(root).get('repository') in ('qa-python', 'qa-typescript'):
        files = {k:v for k,v in files.items() if k not in ('reports','.pytest_cache') and not k.startswith(('reports/','.pytest_cache/'))}
    return digest(json.dumps(files, sort_keys=True).encode())

def safe_relative(root, value):
    p = Path(value)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('Expected workspace-relative path')
    target = (root / p).resolve()
    if not under(target, root.resolve()):
        raise ValueError('Path escapes workspace')
    return target

def sign_evidence(root, evidence):
    value = os.environ.get('QA_EVIDENCE_KEY_FILE')
    if not value:
        raise ValueError('External recorder key required: QA_EVIDENCE_KEY_FILE')
    keyfile = Path(value)
    if keyfile.is_symlink() or under(keyfile.resolve(), root.resolve()):
        raise ValueError('Recorder key must be external and not a symlink')
    if keyfile.stat().st_mode & 0o077:
        raise ValueError('Recorder key permissions must be 0600')
    key = keyfile.read_bytes()
    if len(key) < 32:
        raise ValueError('Recorder key must have at least 32 random bytes')
    payload = {k: v for k, v in evidence.items() if k != 'signature'}
    return hmac.new(key, json.dumps(payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()

def verify_signature(root, evidence):
    if not hmac.compare_digest(evidence.get('signature', ''), sign_evidence(root, evidence)):
        raise ValueError('Evidence signature invalid; fabricated or modified execution claim')

def permitted(root, step, value):
    path = safe_relative(root, value)
    rel = path.relative_to(root.resolve()).as_posix()
    loc = location(root)
    policy = config(root, 'steps')['steps'][step]
    if loc['kind'] == 'repository' and loc['repository'] not in policy['allowed_repositories']:
        return False
    if rel in config(root, 'scope-policy')['controller_paths']:
        return True
    if loc['kind'] == 'repository':
        rel = loc['repository'] + '/' + rel
    allowed = policy['allowed_paths']
    if not any(rel == x.rstrip('/') or (x.endswith('/') and rel.startswith(x)) for x in allowed):
        return False
    if step not in ('0.5', '1'):
        for frozen in config(root, 'scope-policy')['immutable_contract_paths']:
            if rel == frozen.rstrip('/') or (frozen.endswith('/') and rel.startswith(frozen)):
                return False
    if step == '2' and any(part.lower() in ('cypress', 'step_definitions', 'pytest_bdd', 'campaign-report') for part in Path(rel).parts):
        return False
    if step == '1':
        lower = rel.lower()
        if any(x in lower for x in ('cypress', 'pytest', 'step_definitions', 'tracker', 'campaign-report', 'node_modules')):
            return False
        part = rel.removeprefix('qa-features/').rstrip('/')
        files = ['README.md', 'openapi.yml', 'selectors.json', 'api-expectations.yaml', 'api/auth.hurl', 'data/baseline.json', 'features/auth/login.feature', 'schemas/results.schema.json', 'schemas/campaign.schema.json']
        prefixes = ['tools/validate/', 'governance/', 'harness/', 'planning/', '.agents/', '.claude/', '.codex/']
        files += ['AGENTS.md', 'CLAUDE.md', 'MASTER-CONTRACT.md', '.gitignore']
        if rel != 'qa-features' and not any(part == f or f.startswith(part + '/') for f in files + prefixes) and not any(part.startswith(p) for p in prefixes):
            return False
    return True

def preflight(root, step, provider, owner, *, require_owner=True):
    s = state(root)
    if provider not in PROVIDERS:
        raise ValueError('Unknown provider')
    if require_owner and config(root, 'providers')['providers'][provider].get('validation_mode') == 'artifacts-only':
        raise ValueError('Provider is configured for artifacts only; validate live activation before writable ownership')
    if s['authorized_step'] != step:
        raise ValueError('Requested step is not explicitly authorized')
    policy = config(root, 'steps')['steps'].get(step)
    if not policy:
        raise ValueError('Unknown step')
    if any(x not in s['completed_steps'] for x in policy['requires_steps']):
        raise ValueError('Preceding steps incomplete')
    if any(s['prerequisites'].get(x) != 'PASS' for x in policy['requires_checks']):
        raise ValueError('Prerequisite checks incomplete')
    if require_owner and s['owner'] != {'provider': provider, 'id': owner}:
        raise ValueError('Ownership must be released and claimed before writes')
    loc = location(root)
    if loc['kind'] == 'workspace' and (root / '.git').exists():
        raise ValueError('Workspace must not be a Git repository')
    if loc['kind'] == 'repository':
        if loc['repository'] not in policy['allowed_repositories']:
            raise ValueError('Repository is outside the authorized step')
        proc = subprocess.run(['git', '-C', str(root), 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
        if proc.returncode or Path(proc.stdout.strip()).resolve() != root.resolve():
            raise ValueError('Repository adapter must be installed in its independent Git root')
    if step == '0.5':
        receipt = read(root / 'harness/authorization.json')
        if receipt != s['authorization'] or receipt['step'] != '0.5':
            raise ValueError('Preparation authorization receipt mismatch')
        if any((root / x).exists() for x in PRODUCTS):
            raise ValueError('Product directory exists before Step 1')
    else:
        # Operator-owned external file, never generated by this controller.
        value = os.environ.get('QA_AUTHORIZATION_FILE')
        if not value:
            raise ValueError('External human authorization file required')
        ledger = Path(value)
        if under(ledger.resolve(), root.resolve()) or ledger.is_symlink():
            raise ValueError('Authorization ledger must be external')
        receipt = read(ledger.resolve())
        if receipt != s['authorization'] or receipt.get('source') != 'human' or receipt.get('step') != step:
            raise ValueError('External authorization does not match active state')
        if step != '1' and not s['feature_ref']:
            raise ValueError('Approved immutable feature_ref required')
        if step != '1' and receipt.get('approved_feature_ref') != s['feature_ref']:
            raise ValueError('Feature approval must be externally confirmed')
        for label in ('feature_ref', 'tooling_ref'):
            if not s[label]:
                continue
            if loc['kind'] == 'repository' and loc['repository'] in ('sut-python', 'sut-node'):
                # Step 2 portable proof: independent checkout, no parent repo needed.
                with tempfile.TemporaryDirectory(prefix='qa-feature-proof-') as temp:
                    proc = subprocess.run(['git','clone','--bare','--quiet',str(root/'contracts/approved.bundle'),temp],capture_output=True)
                    if proc.returncode: raise ValueError('Approved feature Git bundle is unavailable')
                    proc = subprocess.run(['git','-C',temp,'rev-parse','--verify','--end-of-options',s[label]+'^{commit}'],capture_output=True,text=True)
                    if proc.returncode or proc.stdout.strip() != s['git_revisions'].get(label): raise ValueError('Pinned reference missing from proof')
                    tag = subprocess.run(['git','-C',temp,'rev-parse','seed-1-approved-v1^{commit}'],capture_output=True,text=True)
                    if tag.returncode or tag.stdout.strip() != s['feature_ref']: raise ValueError('Approved tag proof differs')
            else:
                repo = root if loc['repository'] == 'qa-features' else root / 'qa-features'
                proc = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', '--end-of-options', s[label] + '^{commit}'], capture_output=True, text=True)
                if proc.returncode != 0 or not s['git_revisions'].get(label) or proc.stdout.strip() != s['git_revisions'][label]:
                    raise ValueError(label + ' is missing or moved from its recorded immutable commit')
    return s

def audit(root, baseline):
    s = state(root)
    errors = []
    try:
        owner = s['owner'] or {'provider': 'codex', 'id': 'read-only-audit'}
        preflight(root, s['authorized_step'], owner['provider'], owner['id'], require_owner=False)
    except Exception as e:
        errors.append('Preflight/state integrity: ' + str(e))
    if baseline['step'] != s['authorized_step']:
        errors.append('Baseline belongs to another step')
    before, after = baseline['inventory'], inventory(root)
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    for name in changed:
        try:
            allowed = permitted(root, s['authorized_step'], name)
        except ValueError:
            allowed = False
        if not allowed:
            errors.append('Out-of-scope change: ' + name)
    for name, value in after.items():
        if value.startswith('link:'):
            errors.append('Symlink requires human review: ' + name)
    evidence = root / 'harness/evidence'
    if evidence.exists():
        for p in evidence.rglob('*'):
            if p.is_symlink() or (p.is_file() and p.suffix not in ('.json', '.log', '.md', '.lock')):
                errors.append('Unexpected evidence artifact: ' + str(p.relative_to(root)))
            if p.is_file() and p.suffix == '.json':
                try:
                    value = read(p)
                    if isinstance(value, dict) and value.get('instrumentation') == 'subprocess-capture':
                        validate(root, 'evidence', value)
                        verify_signature(root, value)
                except Exception as e:
                    errors.append('Invalid evidence artifact: ' + str(p.relative_to(root)) + ': ' + str(e))
    if s['authorized_step'] == '0.5':
        errors += ['Premature product: ' + x for x in PRODUCTS if (root / x).exists()]
    current = git_context(root)
    for repo in current.keys() | baseline['git'].keys():
        ctx = current.get(repo, {})
        oldrefs = baseline['git'].get(repo, {}).get('refs')
        new_unborn = repo not in baseline['git'] and ctx.get('head', {}).get('exit_code') != 0 and not ctx.get('refs', {}).get('output')
        # Step 3 imports an already human-approved detached submodule without
        # creating refs. Check the immutable pin and index, never waive ref edits.
        new_approved_submodule = False
        if location(root).get('repository') == 'qa-python' and repo == 'qa-features' and repo not in baseline['git']:
            index = subprocess.run(['git','-C',str(root),'ls-files','--stage','qa-features'], capture_output=True, text=True)
            new_approved_submodule = (ctx.get('refs') == {'exit_code':1,'output':''}
                and ctx.get('head') == {'exit_code':0,'output':s['feature_ref']}
                and ctx.get('status') == {'exit_code':0,'output':''}
                and index.returncode == 0 and index.stdout.split()[:2] == ['160000',s['feature_ref']])
        if oldrefs != ctx.get('refs') and not new_unborn and not new_approved_submodule:
            errors.append('Git reference changes require human review: ' + repo)
    return {'status': 'FAIL' if errors else 'PASS', 'changed': changed, 'errors': errors, 'git': current}

def cli_error(exc):
    print(json.dumps({'status': 'FAIL', 'reason': str(exc)}), file=sys.stderr)
    return 1
