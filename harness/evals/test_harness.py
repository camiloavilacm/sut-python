"""Adversarial fixtures only. No product implementation and no model calls."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import ROOT, PROVIDERS, read, write, state, preflight, inventory, git_context, audit, source_digest, validate, digest, sign_evidence
from hook_core import evaluate
from claude_hook import respond as claude_response
from antigravity_hook import respond as google_response
from ownership import transfer
from sync_skills import sync
from validate_adapters import check
from verify_step import gate, validate_evidence
from package_governance import bundle

class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='qa-harness-eval-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'workspace'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('.git', 'evidence', '.venv', '__pycache__', 'qa-features', 'sut-python', 'sut-node', 'qa-python', 'qa-typescript'))
        (self.root / 'harness/evidence').mkdir()
        write(self.root / 'harness/location.json', {'kind': 'workspace', 'repository': None})
        # These provider-neutral simulations cover the stricter all-live profile.
        providers = read(self.root / 'harness/config/providers.yaml')
        providers['validation_policy'] = {'profile': 'all-live', 'required_live_providers': ['antigravity', 'codex', 'claude'], 'artifacts_only_providers': [], 'exception_reference': None}
        for item in providers['providers'].values():
            item['validation_mode'] = 'live'
        write(self.root / 'harness/config/providers.yaml', providers)
        write(self.root / 'harness/authorization.json', {'step': '0.5', 'source': 'conversation', 'reference': 'UNIT TEST FIXTURE; not actual project authorization', 'approved_feature_ref': None})
        self.s = state(self.root)
        self.s.update(agent_tasks=[], authorized_step='0.5', phase='0.5', authorization=read(self.root / 'harness/authorization.json'), completed_steps=[], prerequisites={}, feature_ref=None, tooling_ref=None)
        self.s['evidence'] = []
        self.s['owner'] = {'provider': 'codex', 'id': 'fixture-owner'}
        write(self.root / 'harness/state.json', self.s)
        self.old_auth = os.environ.pop('QA_AUTHORIZATION_FILE', None)
        self.addCleanup(self.restore_auth)
        self.old_key = os.environ.get('QA_EVIDENCE_KEY_FILE')
        key = Path(self.tmp.name) / 'fixture-recorder.key'
        key.write_bytes(os.urandom(32))
        key.chmod(0o600)
        os.environ['QA_EVIDENCE_KEY_FILE'] = str(key)

    def restore_auth(self):
        os.environ.pop('QA_AUTHORIZATION_FILE', None)
        if self.old_auth:
            os.environ['QA_AUTHORIZATION_FILE'] = self.old_auth
        os.environ.pop('QA_EVIDENCE_KEY_FILE', None)
        if self.old_key:
            os.environ['QA_EVIDENCE_KEY_FILE'] = self.old_key

    def owner(self, provider):
        self.s['owner'] = {'provider': provider, 'id': 'fixture-owner'}
        write(self.root / 'harness/state.json', self.s)

    def authorize_fixture(self, step='1'):
        self.s['authorized_step'] = step
        self.s['authorization'] = {'step': step, 'source': 'human', 'reference': 'ISOLATED TEST FIXTURE; not real project approval', 'approved_feature_ref': None}
        self.s['completed_steps'] = ['0.5']
        self.s['prerequisites'] = {'phase0': 'PASS', 'phase05': 'PASS', 'contract-inputs': 'PASS'}
        external = Path(self.tmp.name) / 'human-ledger.json'
        write(external, self.s['authorization'])
        os.environ['QA_AUTHORIZATION_FILE'] = str(external)
        write(self.root / 'harness/state.json', self.s)

    def baseline(self):
        return {'step': self.s['authorized_step'], 'inventory': inventory(self.root), 'git': git_context(self.root)}

    def test_schema_and_skill_equivalence(self):
        self.assertEqual(check(self.root)['status'], 'PASS')

    def test_clean_room_distribution_is_reproducible_and_unauthorized(self):
        import io
        import tarfile
        first, manifest = bundle(self.root)
        self.assertEqual(first, bundle(self.root)[0])
        target = Path(self.tmp.name) / 'clean-room'
        target.mkdir()
        with tarfile.open(fileobj=io.BytesIO(first)) as tar:
            tar.extractall(target, filter='data')
        self.assertEqual(check(target)['status'], 'PASS')
        self.assertIsNone(state(target)['authorized_step'])
        self.assertIsNone(state(target)['owner'])
        self.assertFalse((target / 'harness/authorization.json').exists())
        for name, checksum in manifest['files'].items():
            self.assertEqual(digest((target / name).read_bytes()), checksum)
        with self.assertRaises(ValueError):
            preflight(target, '1', 'codex', 'fixture-owner')

    def test_independent_repository_adapter_needs_no_parent_workspace(self):
        import io
        import tarfile
        from common import permitted
        data, _ = bundle(self.root, 'qa-features')
        target = Path(self.tmp.name) / 'independent-checkout-fixture'
        target.mkdir()
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(target, filter='data')
        proc = subprocess.run(['git', 'init', str(target)], capture_output=True)
        self.assertEqual(proc.returncode, 0)
        self.authorize_fixture()
        s = state(target)
        s.update(authorized_step='1', authorization=self.s['authorization'], completed_steps=['0.5'], prerequisites=self.s['prerequisites'], owner=self.s['owner'])
        write(target / 'harness/state.json', s)
        preflight(target, '1', 'codex', 'fixture-owner')
        self.assertTrue(permitted(target, '1', 'openapi.yml'))
        self.assertTrue(permitted(target, '1', 'harness/state.json'))
        self.assertTrue(permitted(self.root, '1', 'harness/state.json'))
        self.assertFalse(permitted(target, '1', 'cypress/test.cy.ts'))
        self.assertEqual(check(target)['status'], 'PASS')

    def test_explicit_step1_fixture_allows_each_provider(self):
        self.authorize_fixture()
        for provider in PROVIDERS:
            with self.subTest(provider=provider):
                self.owner(provider)
                preflight(self.root, '1', provider, 'fixture-owner')

    def test_step3_before_step2_is_blocked_each_provider(self):
        self.authorize_fixture('3')
        for provider in PROVIDERS:
            with self.subTest(provider=provider):
                self.owner(provider)
                with self.assertRaisesRegex(ValueError, 'Preceding'):
                    preflight(self.root, '3', provider, 'fixture-owner')

    def test_cypress_during_step1_blocked_each_adapter(self):
        self.authorize_fixture()
        for provider in PROVIDERS:
            with self.subTest(provider=provider):
                self.owner(provider)
                decision, _ = evaluate(self.root, provider, 'PreToolUse', 'Write', {'file_path': str(self.root / 'qa-features/cypress/test.cy.ts')})
                self.assertEqual(decision, 'deny')
                if provider == 'claude':
                    self.assertEqual(claude_response('PreToolUse', decision, '')['hookSpecificOutput']['permissionDecision'], 'deny')
                if provider == 'antigravity':
                    self.assertEqual(google_response('PreToolUse', decision, '')['decision'], 'deny')

    def test_unauthorized_repo_and_empty_dir_audited(self):
        for provider in PROVIDERS:
            with self.subTest(provider=provider):
                self.owner(provider)
                baseline = self.baseline()
                bad = self.root / 'qa-typescript'
                bad.mkdir()
                self.assertEqual(audit(self.root, baseline)['status'], 'FAIL')
                bad.rmdir()

    def test_missing_evidence_cannot_complete(self):
        self.assertTrue(gate(self.root))

    def test_unexecuted_pass_rejected_by_schema(self):
        with self.assertRaises(Exception):
            validate(self.root, 'evidence', {'status': 'PASS', 'exit_code': None})

    def test_missing_logs_and_stale_or_forged_commands_fail(self):
        e = {'version': 1, 'step': '0.5', 'provider': 'codex', 'owner': 'fixture-owner', 'check_id': 'adapters', 'command': [sys.executable, 'harness/scripts/validate_adapters.py'], 'cwd': str(self.root), 'started_at': 'fixture', 'finished_at': 'fixture', 'exit_code': 0, 'status': 'PASS', 'log': 'harness/evidence/missing.log', 'log_sha256': digest(b'PASS'), 'source_sha256': source_digest(self.root), 'git': {}, 'instrumentation': 'subprocess-capture'}
        e['signature'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'signature'):
            validate_evidence(self.root, e)
        e['signature'] = sign_evidence(self.root, e)
        with self.assertRaises(FileNotFoundError):
            validate_evidence(self.root, e)
        (self.root / e['log']).write_bytes(b'PASS')
        self.assertEqual(validate_evidence(self.root, e), 'PASS')
        e['command'] = ['echo', 'PASS']
        e['signature'] = sign_evidence(self.root, e)
        with self.assertRaisesRegex(ValueError, 'registered'):
            validate_evidence(self.root, e)
        e['command'] = [sys.executable, 'harness/scripts/validate_adapters.py']
        e['signature'] = sign_evidence(self.root, e)
        (self.root / 'MASTER-CONTRACT.md').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'stale'):
            validate_evidence(self.root, e)

    def test_self_approval_and_state_edit_do_not_grant_product_step(self):
        self.authorize_fixture('2')
        self.s['completed_steps'] = ['1']
        self.s['prerequisites'] = {'feature-approved': 'PASS'}
        self.s['feature_ref'] = 'self-approved-tag'
        self.s['approval_status'] = 'approved'
        write(self.root / 'harness/state.json', self.s)
        with self.assertRaisesRegex(ValueError, 'externally'):
            preflight(self.root, '2', 'codex', 'fixture-owner')
        self.authorize_fixture()
        os.environ.pop('QA_AUTHORIZATION_FILE')
        with self.assertRaisesRegex(ValueError, 'External'):
            preflight(self.root, '1', 'codex', 'fixture-owner')

    def test_next_step_never_implicitly_authorized(self):
        for provider in PROVIDERS:
            self.owner(provider)
            with self.assertRaisesRegex(ValueError, 'not explicitly authorized'):
                preflight(self.root, '1', provider, 'fixture-owner')

    def test_mirror_drift_fails(self):
        target = next((self.root / '.claude/skills').glob('*/SKILL.md'))
        target.write_text(target.read_text() + '\nDRIFT\n')
        with self.assertRaisesRegex(ValueError, 'drifted'):
            sync(self.root, check=True)

    def record_fixture_outcome(self, provider):
        from agent_outcome import start, submit
        task = start(self.root, 'qa-step-executor', provider, 'fixture-owner')
        value = {k: task[k] for k in ('task_id', 'role', 'provider', 'actor', 'step')}
        value.update(schema_version='1.0', status='completed', summary='Isolated handoff fixture', deliverables=[], commands=[], checks=[], blockers=[], pending_approvals=[], remaining_work=[], boundary_confirmation='No real implementation evidence.')
        submit(self.root, task['task_id'], value)

    def test_handoff_cycle_preserves_state_and_scope(self):
        self.owner('antigravity')
        for before, after in [('antigravity', 'codex'), ('codex', 'claude'), ('claude', 'antigravity')]:
            with self.subTest(before=before, after=after):
                handoff = self.root / 'harness/evidence/handoff.json'
                with self.assertRaisesRegex(ValueError, 'not released'):
                    transfer(self.root, 'claim', after, 'fixture-owner', handoff)
                self.record_fixture_outcome(before)
                transfer(self.root, 'release', before, 'fixture-owner', handoff)
                transfer(self.root, 'claim', after, 'fixture-owner', handoff)
                actual = preflight(self.root, '0.5', after, 'fixture-owner')
                self.assertEqual(actual['authorization'], self.s['authorization'])
                self.assertIsNone(actual['feature_ref'])

    def test_handoff_rejects_unexpected_modification(self):
        handoff = self.root / 'harness/evidence/handoff.json'
        self.record_fixture_outcome('codex')
        transfer(self.root, 'release', 'codex', 'fixture-owner', handoff)
        (self.root / 'MASTER-CONTRACT.md').write_text('changed after release')
        with self.assertRaisesRegex(ValueError, 'differ|stale'):
            transfer(self.root, 'claim', 'claude', 'fixture-owner', handoff)

    def test_path_escape_and_symlink_detection(self):
        for value in ['../elsewhere', '/private/tmp/elsewhere']:
            self.assertEqual(evaluate(self.root, 'codex', 'PreToolUse', 'Write', {'file_path': value})[0], 'deny')
        baseline = self.baseline()
        (self.root / 'planning/escape').symlink_to(self.tmp.name)
        self.assertEqual(audit(self.root, baseline)['status'], 'FAIL')

    def test_native_hook_subprocess_protocols_and_malformed_input(self):
        for provider, script, payload in [('claude', 'claude_hook.py', {'cwd': str(self.root), 'tool_name': 'Write', 'tool_input': {'file_path': str(self.root / 'qa-python/test.py')}}), ('antigravity', 'antigravity_hook.py', {'workspacePaths': [str(self.root)], 'toolCall': {'name': 'write_to_file', 'args': {'TargetFile': str(self.root / 'qa-python/test.py')}}})]:
            with self.subTest(provider=provider):
                self.owner(provider)
                result = subprocess.run([sys.executable, str(self.root / 'harness/scripts' / script), 'PreToolUse'], input=json.dumps(payload), capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                response = json.loads(result.stdout)
                decision = response['decision'] if provider == 'antigravity' else response['hookSpecificOutput']['permissionDecision']
                self.assertEqual(decision, 'deny')
                malformed = subprocess.run([sys.executable, str(self.root / 'harness/scripts' / script), 'PreToolUse'], input='not json', capture_output=True, text=True)
                self.assertIn('deny', malformed.stdout)

    def test_antigravity_launcher_is_independent_of_working_directory(self):
        self.owner('antigravity')
        (self.root / '.venv').symlink_to(Path(sys.prefix))
        settings = read(self.root / '.agents/hooks.json')
        command = settings['qa-development']['PreToolUse'][0]['hooks'][0]['command']
        payload = {'workspacePaths': [str(self.root)], 'toolCall': {'name': 'write_to_file', 'args': {'TargetFile': str(self.root / 'qa-typescript/denied.txt')}}}
        result = subprocess.run(command, shell=True, cwd=self.tmp.name, input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['decision'], 'deny')

    def test_unsupported_shell_requires_permission(self):
        for provider in PROVIDERS:
            self.owner(provider)
            self.assertEqual(evaluate(self.root, provider, 'PreToolUse', 'Bash', {'command': 'python3 -c "print(123)"'})[0], 'deny' if provider == 'antigravity' else 'ask')
            self.assertEqual(evaluate(self.root, provider, 'PreToolUse', 'Bash', {'command': 'git tag unauthorized'})[0], 'deny')

    def test_actual_antigravity_cli_tools_and_unknown_tools_fail_closed(self):
        self.owner('antigravity')
        self.assertEqual(evaluate(self.root, 'antigravity', 'PreToolUse', 'read_file', {'path': 'harness/state.json'})[0], 'allow')
        for tool in ('write_file', 'edit_file', 'unknown_tool'):
            self.assertEqual(evaluate(self.root, 'antigravity', 'PreToolUse', tool, {'path': str(self.root / 'qa-typescript/denied.txt')})[0], 'deny')
        self.assertEqual(evaluate(self.root, 'antigravity', 'PreToolUse', 'write_file', {'path': './harness/state.json'})[0], 'deny')
        self.assertEqual(evaluate(self.root, 'antigravity', 'PreToolUse', 'write_file', {'Path': str(self.root / 'qa-typescript/denied.txt')})[0], 'deny')
        self.assertEqual(evaluate(self.root, 'antigravity', 'PreToolUse', 'write_file', {'Path': str(self.root / 'planning/in-scope.md')})[0], 'allow')

    def test_approved_contract_paths_are_not_reopened_in_later_steps(self):
        from common import permitted
        self.assertFalse(permitted(self.root, '6', 'qa-features/openapi.yml'))
        self.assertFalse(permitted(self.root, '7', 'qa-features/features/auth/login.feature'))
        self.assertTrue(permitted(self.root, '6', 'qa-features/tools/aggregate.py'))

    def test_step1_can_initialize_an_unborn_repo_without_allowing_tags(self):
        self.authorize_fixture()
        before = self.baseline()
        target = self.root / 'qa-features'
        proc = subprocess.run(['git', 'init', '-b', 'validated', str(target)], capture_output=True)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(audit(self.root, before)['status'], 'PASS')

    def test_step1_registers_specification_checks_without_starting_a_runner(self):
        from verify_step import command
        expected = str(self.root / 'qa-features/tools/validate/validate.py')
        self.assertEqual(command(self.root, 'openapi'), [sys.executable, expected, '--check', 'openapi'])
        self.assertEqual(command(self.root, 'governance'), [sys.executable, expected, '--check', 'governance'])

if __name__ == '__main__':
    unittest.main()
