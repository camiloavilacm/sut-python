"""Run allowlisted checks and verify captured evidence, without authorizing/completing steps."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import uuid
from common import ROOT, state, validate, preflight, now, digest, source_digest, git_context, write, read, safe_relative, cli_error, audit, sign_evidence, verify_signature, config, location

def command(root, check_id):
    if check_id == 'agent-outcomes':
        return [sys.executable, '-m', 'unittest', 'discover', '-s', 'harness/evals', '-p', 'test_agent_outcome.py', '-v']
    # One fixed registration table; arbitrary commands are never accepted.
    if state(root)['authorized_step']=='7' and check_id in ('image-digests','reproduction','18-passes','rollback','failure-reporting'):
        if location(root).get('repository')!='qa-features':raise ValueError('Smoke release checks require qa-features')
        return [sys.executable,str(root/'tools/release/verify.py'),'--check',check_id]
    if state(root)['authorized_step']=='6' and check_id in ('six-jobs','single-report','failure-paths','no-model-calls'):
        if location(root).get('repository')!='qa-features':raise ValueError('Campaign checks require qa-features')
        return [sys.executable,str(root/'tools/campaign/verify.py'),'--check',check_id]
    if state(root)['authorized_step']=='5' and check_id in ('dry-run','sandbox-comment','idempotency','no-transition'):
        if location(root).get('repository')!='qa-features':raise ValueError('Tracker checks require qa-features')
        return [sys.executable,str(root/'tools/tracker/verify.py'),'--check',check_id]
    registrations = {
        '2': (('sut-python','sut-node'), ('hurl','seeds','ui-parity','digests')),
        '3': (('qa-python',), ('12-passes','observer-complete')),
        '4': (('qa-typescript',), ('6-passes','result-schema')),
    }
    step = state(root)['authorized_step']
    if step in registrations and check_id in registrations[step][1]:
        if location(root).get('repository') not in registrations[step][0]:
            raise ValueError('Check requires its registered repository')
        return [sys.executable, str(root/'tools/verify.py'), '--check', check_id]
    spec = root if location(root).get('repository') == 'qa-features' else root / 'qa-features'
    if check_id in config(root, 'steps')['steps']['1']['verification_checks']:
        return [sys.executable, str(spec / 'tools/validate/validate.py'), '--check', check_id]
    commands = {
        'adapters': [sys.executable, 'harness/scripts/validate_adapters.py'],
        'evals': [sys.executable, '-m', 'unittest', 'discover', '-s', 'harness/evals', '-p', 'test_*.py', '-v'],
        'codex-native': [sys.executable, 'harness/scripts/native_probe.py', 'codex'],
        'claude-native': [sys.executable, 'harness/scripts/native_probe.py', 'claude'],
        'claude-artifacts': [sys.executable, 'harness/scripts/validate_adapters.py'],
        'antigravity-native': [sys.executable, 'harness/scripts/native_probe.py', 'antigravity'],
        'native-cycle': [sys.executable, 'harness/scripts/native_acceptance.py'],
    }
    if check_id not in commands:
        raise ValueError('Check is not registered; no arbitrary command evidence')
    return commands[check_id]

def run(root, check_id):
    s = state(root)
    preflight(root, s['authorized_step'], s['owner']['provider'], s['owner']['id'])
    if s['authorized_step'] not in ('0.5', '1', '2', '3', '4', '5', '6', '7'):
        raise ValueError('Only registered Phase 0.5 and Steps 1–7 checks are implemented')
    if check_id not in config(root, 'steps')['steps'][s['authorized_step']]['verification_checks']:
        raise ValueError('Check is outside the active step')
    args = command(root, check_id)
    started = now()
    before = source_digest(root)
    sign_evidence(root, {})  # Fail before executing if external recorder is unavailable.
    try:
        proc = subprocess.run(args, cwd=root, capture_output=True, timeout=600 if check_id in ('12-passes','observer-complete','6-passes','result-schema') else 300 if check_id in ('native-cycle','seeds','ui-parity') else 120)
        code, log = proc.returncode, proc.stdout + b'\nSTDERR:\n' + proc.stderr
    except subprocess.TimeoutExpired as e:
        code, log = None, (e.stdout or b'') + (e.stderr or b'') + b'\nTIMEOUT'
    # Native probes use exit 3 to indicate missing instrumentation or live evidence.
    status = 'NOT RUN' if code in (None, 3) else 'PASS' if code == 0 else 'FAIL'
    if before != source_digest(root):
        status = 'FAIL'
        log += b'\nSource changed during check'
    stem = 'harness/evidence/' + check_id + '-' + uuid.uuid4().hex
    (root / (stem + '.log')).write_bytes(log)
    evidence = {'version': 1, 'step': s['authorized_step'], 'provider': s['owner']['provider'], 'owner': s['owner']['id'], 'check_id': check_id, 'command': args, 'cwd': str(root), 'started_at': started, 'finished_at': now(), 'exit_code': code, 'status': status, 'log': stem + '.log', 'log_sha256': digest(log), 'source_sha256': before, 'git': git_context(root), 'instrumentation': 'subprocess-capture'}
    evidence['signature'] = sign_evidence(root, evidence)
    validate(root, 'evidence', evidence)
    write(root / (stem + '.json'), evidence)
    s['evidence'].append(stem + '.json')
    write(root / 'harness/state.json', s)
    return evidence

def validate_evidence(root, evidence):
    validate(root, 'evidence', evidence)
    verify_signature(root, evidence)
    if evidence['command'] != command(root, evidence['check_id']):
        raise ValueError('Evidence command differs from registered check')
    if evidence['instrumentation'] != 'subprocess-capture' or evidence['exit_code'] is None:
        raise ValueError('Check was not executed to completion')
    log = safe_relative(root, evidence['log'])
    if not evidence['log'].startswith('harness/evidence/') or digest(log.read_bytes()) != evidence['log_sha256']:
        raise ValueError('Log missing or modified')
    if evidence['source_sha256'] != source_digest(root):
        raise ValueError('Evidence is stale for current source')
    if evidence['cwd'] != str(root) or evidence['step'] != state(root)['authorized_step']:
        raise ValueError('Evidence belongs to a different workspace or step')
    if evidence['step'] in ('3','4'):
        import importlib.util
        module_spec=importlib.util.spec_from_file_location('step3_verifier', root/'tools/verify.py')
        verifier=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(verifier)
        verifier.verify_saved()
        receipt_digest=digest((root/'reports/latest.json').read_bytes())
        if ('RESULT_RECEIPT_SHA256 '+receipt_digest) not in log.read_text():
            raise ValueError('Execution results differ from the signed receipt')
    if evidence['step']=='6':
        import importlib.util
        sys.path.insert(0,str(root/'tools/campaign'))
        spec=importlib.util.spec_from_file_location('campaign_verifier',root/'tools/campaign/verify.py')
        verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
        receipt=verifier.verify_saved()
        if ('CAMPAIGN_RECEIPT_SHA256 '+receipt) not in log.read_text():raise ValueError('Campaign evidence differs from its signed receipt')
    if evidence['step']=='7':
        import importlib.util
        sys.path.insert(0,str(root/'tools/release'))
        spec=importlib.util.spec_from_file_location('smoke_verifier',root/'tools/release/verify.py')
        verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
        receipt=verifier.verify_saved()
        if ('SMOKE_RECEIPT_SHA256 '+receipt)not in log.read_text():raise ValueError('Smoke evidence differs from its signed receipt')
    return evidence['status']

def gate(root):
    s = state(root)
    preflight(root, s['authorized_step'], s['owner']['provider'], s['owner']['id'])
    if s['authorized_step'] not in ('0.5', '1', '2', '3', '4', '5', '6', '7'):
        raise ValueError('No product-step completion implementation')
    latest = {}
    for path in s['evidence']:
        e = read(safe_relative(root, path))
        if e['step'] == s['authorized_step']:
            latest[e['check_id']] = e
    required = config(root, 'steps')['steps'][s['authorized_step']]['verification_checks']
    failures = []
    if s['authorized_step'] == '1':
        spec = root if location(root).get('repository') == 'qa-features' else root / 'qa-features'
        for name in config(root, 'steps')['steps']['1']['required_outputs']:
            if not (spec / name).exists():
                failures.append('Missing required specification output: ' + name)
    if s['authorized_step'] == '7':
        for name in ('.github/workflows/smoke.yml','tools/release/candidate.json','tools/release/README.md'):
            if not(root/name).is_file():failures.append('Missing Step 7 output: '+name)
    if s['authorized_step'] == '6':
        for name in ('.github/workflows/campaign.yml','tools/campaign/aggregate.py','tools/campaign/README.md'):
            if not (root/name).is_file():failures.append('Missing Step 6 output: '+name)
    if s['authorized_step'] == '5':
        for name in ('tools/tracker/tracker.py','tools/tracker/verify.py','tools/tracker/README.md'):
            if not (root/name).is_file(): failures.append('Missing Step 5 output: '+name)
    if s['authorized_step'] == '2':
        for name in ('app.py' if location(root)['repository']=='sut-python' else 'app.js','compose.yaml','Dockerfile','db/schema.sql','frontend/manifest.json','contracts/provenance.json','tools/verify.py'):
            if not (root/name).is_file(): failures.append('Missing Step 2 output: '+name)
    if s['authorized_step'] == '4':
        for name in ('README.md','package-lock.json','cypress.config.ts','cypress/e2e/auth.cy.ts','runner/report.cjs','tools/verify.py'):
            if not (root/name).is_file(): failures.append('Missing Step 4 output: '+name)
    if s['authorized_step'] == '3':
        for name in ('README.md','pyproject.toml','requirements.txt','runner/browser.py','runner/observer.py','runner/results.py','tests/test_auth.py','tools/verify.py'):
            if not (root/name).is_file(): failures.append('Missing Step 3 output: '+name)
    for name in required:
        try:
            if name not in latest or validate_evidence(root, latest[name]) != 'PASS':
                failures.append(name + ': missing/non-PASS evidence')
        except Exception as e:
            failures.append(name + ': ' + str(e))
    baseline = safe_relative(root, s['baseline'])
    if not baseline.exists() or audit(root, read(baseline))['status'] != 'PASS':
        failures.append('Mandatory scope audit missing/failed')
    try:
        from agent_outcome import require_outcomes
        require_outcomes(root, completed=True)
    except Exception as exc:
        failures.append('Agent outcomes: ' + str(exc))
    return failures

def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['run', 'validate', 'gate'])
    p.add_argument('--check')
    a = p.parse_args()
    try:
        if a.action == 'run':
            result = run(ROOT, a.check)
            print(json.dumps(result, indent=2))
            return 0 if result['status'] == 'PASS' else 1
        if a.action == 'validate':
            s = state(ROOT)
            if not s['evidence']:
                raise ValueError('No evidence')
            latest = {}
            for path in s['evidence']:
                e = read(safe_relative(ROOT, path))
                if e['step'] == s['authorized_step']:
                    latest[e['check_id']] = e
            for e in latest.values():
                print(e['check_id'], validate_evidence(ROOT, e))
            return int(any(e['status'] != 'PASS' for e in latest.values()))
        failures = gate(ROOT)
        print(json.dumps({'status': 'FAIL' if failures else 'PASS', 'blockers': failures}, indent=2))
        return int(bool(failures))
    except Exception as e:
        return cli_error(e)

if __name__ == '__main__':
    raise SystemExit(main())
