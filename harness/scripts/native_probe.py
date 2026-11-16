"""Offline native parser/discovery probes. Live lifecycle acceptance remains separate."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from common import ROOT

def main():
    provider = sys.argv[1]
    result = {'provider': provider, 'static_native_checks': [], 'live_discovery': 'NOT RUN', 'live_enforcement': 'NOT RUN', 'fresh_session_handoff': 'NOT RUN'}
    if provider == 'codex':
        trusted = f'projects."{ROOT}".trust_level="trusted"'
        checks = [
            ['codex', '-C', str(ROOT), '-c', trusted, '--strict-config', 'app-server', '--print-startup-config'],
            ['codex', '-C', str(ROOT), '-c', trusted, 'debug', 'prompt-input', 'Read-only harness discovery probe; do not execute any work'],
            ['codex', 'execpolicy', 'check', '--rules', str(ROOT / '.codex/rules/qa-commands.rules'), 'git', 'tag', 'fixture'],
            ['codex', 'execpolicy', 'check', '--rules', str(ROOT / '.codex/rules/qa-commands.rules'), 'git', 'push'],
        ]
        for i, args in enumerate(checks):
            p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=45)
            entry = {'command': args, 'exit_code': p.returncode}
            if i == 1 and p.returncode == 0:
                names = ['qa-step-executor', 'qa-contract-author', 'qa-verification', 'qa-architecture-reviewer']
                entry['four_skills_visible'] = all(n in p.stdout for n in names)
                entry['instructions_visible'] = 'Read MASTER-CONTRACT.md' in p.stdout
                result['prompt_discovery'] = 'PASS' if entry['four_skills_visible'] and entry['instructions_visible'] else 'FAIL'
            if i >= 2:
                try:
                    entry['policy'] = json.loads(p.stdout)
                except ValueError:
                    entry['error'] = 'Native policy did not return JSON'
            if p.returncode:
                entry['error'] = p.stderr[-1000:]
            result['static_native_checks'].append(entry)
    elif provider == 'claude':
        args = ['claude', 'doctor']
        p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=45)
        result['static_native_checks'].append({'command': args, 'exit_code': p.returncode, 'output': p.stdout[-5000:], 'stderr': p.stderr[-1000:]})
    elif provider == 'antigravity':
        # Native plugin validator is not a project loader. Use a disposable package
        # to validate the actual skills/rules/hooks without installing a plugin.
        with tempfile.TemporaryDirectory(prefix='qa-agy-parser-') as d:
            d = Path(d)
            (d / '.antigravity-plugin').mkdir()
            (d / '.antigravity-plugin/plugin.json').write_text(json.dumps({'name': 'qa-harness-evaluation', 'version': '0.1.0'}))
            for name in ('skills', 'rules'):
                shutil.copytree(ROOT / '.agents' / name, d / name)
            shutil.copytree(ROOT / 'harness', d / 'harness', ignore=shutil.ignore_patterns('evidence', '__pycache__'))
            shutil.copyfile(ROOT / '.agents/hooks.json', d / 'hooks.json')
            (d / '.venv/bin').mkdir(parents=True)
            (d / '.venv/bin/python').symlink_to(sys.executable)
            args = ['agy', 'plugin', 'validate', str(d), '--strict', '--json']
            p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=45)
            result['static_native_checks'].append({'command': args, 'exit_code': p.returncode, 'output': p.stdout, 'stderr': p.stderr[-1000:], 'scope': 'disposable plugin parser, not project discovery'})
    else:
        raise ValueError('Unknown provider')
    passed = all(c['exit_code'] == 0 for c in result['static_native_checks'])
    if provider == 'codex':
        passed = passed and result.get('prompt_discovery') == 'PASS'
        passed = passed and result['static_native_checks'][2].get('policy', {}).get('decision') == 'forbidden'
        passed = passed and result['static_native_checks'][3].get('policy', {}).get('decision') == 'prompt'
    elif provider == 'antigravity' and passed:
        report = json.loads(result['static_native_checks'][0]['output'])
        passed = report['components']['skills'] == 4 and report['components']['rules'] == 1 and report['components']['hooks'] == 1
    result['status'] = 'PASS' if passed else 'FAIL'
    result['scope'] = 'native parser/discovery checks only; native-cycle separately gates live acceptance'
    print(json.dumps(result, indent=2))
    return 0 if passed else 1

if __name__ == '__main__':
    raise SystemExit(main())
