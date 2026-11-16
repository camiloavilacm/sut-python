import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import ROOT, state, write, read
from native_acceptance import assess, cycle, SKILLS, CYCLE, validation_profile

def seed_preparation_fixture(root):
    write(root / 'harness/location.json', {'kind': 'workspace', 'repository': None})
    write(root / 'harness/authorization.json', {'step': '0.5', 'source': 'conversation', 'reference': 'UNIT TEST FIXTURE; not actual project authorization', 'approved_feature_ref': None})
    s = state(root)
    s.update(authorized_step='0.5', phase='0.5', authorization=read(root / 'harness/authorization.json'), completed_steps=[], prerequisites={}, feature_ref=None, tooling_ref=None, evidence=[])
    write(root / 'harness/state.json', s)

class NativeAcceptanceTests(unittest.TestCase):
    def expected(self, provider):
        return {'authorized_step': '0.5', 'owner': {'provider': provider, 'id': 'fixture'}}

    def response(self, provider):
        value = {**self.expected(provider), 'discovered_skills': sorted(SKILLS), 'probe_outcome': 'denied'}
        text = json.dumps(value)
        output = json.dumps({'item': {'type': 'agent_message', 'text': text}}) if provider == 'codex' else json.dumps({'result' if provider == 'claude' else 'response': text})
        return {'exit_code': 0, 'stdout': output, 'stderr': 'writing blocked by read-only sandbox' if provider == 'codex' else '', 'forbidden_file_absent': True, 'unexpected_changes': []}

    def events(self, provider):
        return [{'event': e, 'decision': 'deny' if e == 'PreToolUse' else 'report', 'tool_name': 'Write' if provider == 'claude' else 'write_file', 'reason': 'Target outside authorized step'} for e in ('SessionStart', 'PreToolUse', 'PostToolUse', 'Stop')]

    def test_complete_measured_session_can_pass_each_provider(self):
        for p in ('codex', 'claude', 'antigravity'):
            with self.subTest(provider=p):
                self.assertEqual(assess(p, self.response(p), self.expected(p), self.events(p))['status'], 'PASS')

    def test_model_claim_without_actual_native_denial_fails(self):
        for p in ('claude', 'antigravity'):
            self.assertEqual(assess(p, self.response(p), self.expected(p), [])['status'], 'FAIL')
        native = self.response('codex');native['stderr'] = ''
        self.assertEqual(assess('codex', native, self.expected('codex'), [])['status'], 'FAIL')

    def test_hook_crash_denial_is_not_scope_enforcement(self):
        events = self.events('antigravity')
        events[1]['reason'] = 'Harness error: Missing target path'
        self.assertEqual(assess('antigravity', self.response('antigravity'), self.expected('antigravity'), events)['status'], 'FAIL')

    def test_credit_failure_and_timeout_never_pass(self):
        for data in [{'exit_code': 1, 'stdout': 'Credit balance is too low', 'stderr': ''}, {'exit_code': None, 'stdout': '', 'stderr': ''}]:
            self.assertEqual(assess('claude', data, self.expected('claude'), [])['status'], 'NOT RUN')

    def test_historical_credit_error_in_read_output_does_not_mask_success(self):
        native = self.response('codex')
        historical = {'item': {'type': 'command_execution', 'aggregated_output': 'Historical blocker: Credit balance is too low'}}
        native['stdout'] = json.dumps(historical) + '\n' + native['stdout']
        self.assertEqual(assess('codex', native, self.expected('codex'), [])['status'], 'PASS')

    def test_untrusted_project_does_not_pass(self):
        native = self.response('codex');native['stderr'] += ' Untrusted project-local configuration is disabled'
        self.assertEqual(assess('codex', native, self.expected('codex'), [])['status'], 'NOT RUN')

    def test_unexpected_write_and_wrong_persisted_owner_fail(self):
        native = self.response('claude');native['forbidden_file_absent'] = False
        self.assertEqual(assess('claude', native, self.expected('claude'), self.events('claude'))['status'], 'FAIL')
        expected = self.expected('claude');expected['owner']['id'] = 'another-owner'
        self.assertEqual(assess('claude', self.response('claude'), expected, self.events('claude'))['status'], 'FAIL')

    def test_real_ownership_controller_cycles_fresh_sessions(self):
        with tempfile.TemporaryDirectory(prefix='qa-cycle-unit-') as d:
            root = Path(d) / 'fixture'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.git', 'evidence', '__pycache__', '.venv', 'qa-features', 'sut-python', 'sut-node', 'qa-python', 'qa-typescript'))
            (root / 'harness/evidence').mkdir()
            seed_preparation_fixture(root)
            visits = []
            def probe(path, provider):
                visits.append(provider)
                self.assertEqual(state(path)['owner'], {'provider': provider, 'id': 'native-cycle-evaluation'})
                return {'status': 'PASS', 'reason': 'unit-test stub; not native acceptance evidence'}
            result = cycle(root, probe)
            self.assertEqual(visits, list(validation_profile(root)[1]))
            self.assertTrue(result['cycle_complete'])
            result = cycle(root, lambda *_: {'status': 'NOT RUN', 'reason': 'fixture unavailable'})
            self.assertFalse(result['cycle_complete'])
            self.assertEqual(len(result['sessions']), 1)

    def test_artifacts_only_profile_never_invokes_claude_or_claims_live_pass(self):
        with tempfile.TemporaryDirectory(prefix='qa-profile-unit-') as d:
            root = Path(d) / 'fixture'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.git', 'evidence', '__pycache__', '.venv', 'qa-features', 'sut-python', 'sut-node', 'qa-python', 'qa-typescript'))
            (root / 'harness/evidence').mkdir()
            seed_preparation_fixture(root)
            visits = []
            def probe(path, provider):
                self.assertNotEqual(provider, 'claude')
                visits.append(provider)
                return {'status': 'PASS', 'reason': 'unit-test stub'}
            result = cycle(root, probe)
            self.assertEqual(visits, ['antigravity', 'codex', 'antigravity'])
            self.assertEqual(result['deferred']['claude']['status'], 'NOT RUN')
            self.assertFalse(result['all_three_live_validated'])
            from ownership import transfer
            handoff = root / 'harness/evidence/profile-handoff.json'
            transfer(root, 'release', 'antigravity', 'native-cycle-evaluation', handoff)
            with self.assertRaisesRegex(ValueError, 'Artifacts-only'):
                transfer(root, 'claim', 'claude', 'native-cycle-evaluation', handoff)

    def test_missing_exception_and_unapproved_provider_skip_fail_closed(self):
        from common import read
        with tempfile.TemporaryDirectory(prefix='qa-exception-unit-') as d:
            root = Path(d) / 'fixture'
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.git', 'evidence', '__pycache__', '.venv', 'qa-features', 'sut-python', 'sut-node', 'qa-python', 'qa-typescript'))
            p = root / 'harness/approved-exceptions.json'
            p.write_text('{"exceptions": []}')
            with self.assertRaisesRegex(ValueError, 'Missing explicit'):
                validation_profile(root)
            p = root / 'harness/config/providers.yaml'
            settings = read(p)
            settings['validation_policy']['required_live_providers'] = ['codex']
            write(p, settings)
            with self.assertRaisesRegex(ValueError, 'Only Claude'):
                validation_profile(root)

    def test_claude_artifacts_check_requires_no_claude_cli(self):
        from unittest.mock import patch
        from validate_adapters import check
        from verify_step import command
        with patch('subprocess.run', side_effect=AssertionError('No native executable may be invoked by artifact validation')):
            self.assertEqual(check(ROOT)['status'], 'PASS')
            self.assertEqual(command(ROOT, 'claude-artifacts')[1], 'harness/scripts/validate_adapters.py')
