"""Isolated adversarial controller tests; no model calls or business acceptance claims."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import ROOT, read, write, state, inventory, git_context, sign_evidence, now, source_digest, digest
from agent_outcome import start, submit, validate_task, require_outcomes, render, directory, ROLES
from ownership import transfer


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='qa-outcome-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = (Path(self.tmp.name) / 'checkout').resolve()
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('evidence', '.venv', '__pycache__', 'qa-features', 'sut-python', 'sut-node', 'qa-python', 'qa-typescript', '.git'))
        (self.root / 'harness/evidence').mkdir(exist_ok=True)
        self.key = Path(self.tmp.name) / 'key'
        self.key.write_bytes(os.urandom(32)); self.key.chmod(0o600)
        self.env = patch.dict(os.environ, {'QA_EVIDENCE_KEY_FILE': str(self.key)})
        self.env.start(); self.addCleanup(self.env.stop)
        write(self.root / 'harness/location.json', {'kind': 'workspace', 'repository': None})
        s = state(self.root)
        auth = {'step': '0.5', 'source': 'conversation', 'reference': 'ISOLATED FIXTURE', 'approved_feature_ref': None}
        s.update(authorized_step='0.5', phase='0.5', authorization=auth, owner={'provider': 'codex', 'id': 'fixture'}, completed_steps=[], evidence=[], agent_tasks=[], prerequisites={}, feature_ref=None, tooling_ref=None)
        write(self.root / 'harness/state.json', s)
        write(self.root / 'harness/authorization.json', auth)
        write(self.root / s['baseline'], {'step': '0.5', 'inventory': inventory(self.root), 'git': git_context(self.root)})

    def task(self, role='qa-step-executor', provider='codex', actor='fixture'):
        return start(self.root, role, provider, actor)

    def value(self, task, status='completed'):
        v = {k: task[k] for k in ('task_id', 'role', 'provider', 'actor', 'step')}
        v.update(schema_version='1.0', status=status, summary='Isolated fixture outcome', deliverables=[], commands=[], checks=[], blockers=[], pending_approvals=[], remaining_work=[], boundary_confirmation='Fixture boundary only.')
        if status != 'completed':v['blockers'] = ['Synthetic unavailable dependency']
        if task['role'] == 'qa-architecture-reviewer':v['findings'] = []
        return v

    def test_all_roles_and_readable_report(self):
        for role in ROLES:
            with self.subTest(role=role):
                task=self.task(role);value=self.value(task)
                submit(self.root,task['task_id'],value)
                self.assertEqual(validate_task(self.root,task['task_id']),value)
                self.assertIn(value['summary'],render(self.root,task['task_id']))
        self.assertEqual(len(require_outcomes(self.root,completed=True)),4)

    def test_missing_outcomes_block_gate_and_handoff(self):
        with self.assertRaises(ValueError):require_outcomes(self.root)
        with self.assertRaises(ValueError):transfer(self.root,'release','codex','fixture',self.root/'harness/evidence/handoff.json')
        from verify_step import gate
        self.assertTrue(any('Agent outcomes' in f for f in gate(self.root)))
        self.task()
        with self.assertRaises(FileNotFoundError):require_outcomes(self.root)

    def test_schema_rejects_missing_extra_version_role_status_and_types(self):
        t=self.task();valid=self.value(t)
        variants=[]
        for key in valid:
            v=copy.deepcopy(valid);v.pop(key);variants.append(v)
        for key,value in [('schema_version','9'),('role','unknown'),('status','PASS'),('summary',None),('commands',{}),('unexpected','x')]:
            v=copy.deepcopy(valid);v[key]=value;variants.append(v)
        for v in variants:
            with self.subTest(value=v):
                with self.assertRaises(Exception):submit(self.root,t['task_id'],v)
        self.assertFalse((directory(self.root,t['task_id'])/'receipt.json').exists())
        submit(self.root,t['task_id'],valid)

    def test_wrong_identity_and_replay(self):
        t=self.task();value=self.value(t)
        for key in ('task_id','actor','provider','step'):
            v=copy.deepcopy(value);v[key]='other'
            with self.assertRaises(Exception):submit(self.root,t['task_id'],v)
        other=self.task()
        with self.assertRaises(ValueError):submit(self.root,other['task_id'],value)

    def test_accepted_outcome_is_immutable_and_tampering_rejected(self):
        t=self.task();v=self.value(t);submit(self.root,t['task_id'],v)
        with self.assertRaises(ValueError):submit(self.root,t['task_id'],v)
        p=directory(self.root,t['task_id'])/'outcome.json';v['summary']='Changed';write(p,v)
        with self.assertRaises(ValueError):validate_task(self.root,t['task_id'])

    def test_modified_receipt_and_request_rejected(self):
        for filename in ('receipt.json','request.json'):
            t=self.task();submit(self.root,t['task_id'],self.value(t));p=directory(self.root,t['task_id'])/filename;v=read(p);v['version']=2;write(p,v)
            with self.assertRaises(ValueError):validate_task(self.root,t['task_id'])

    def test_stale_source_and_authorization_rejected(self):
        t=self.task();submit(self.root,t['task_id'],self.value(t))
        (self.root/'planning/new.md').write_text('Changed source')
        with self.assertRaises(ValueError):validate_task(self.root,t['task_id'])
        s=state(self.root);s['authorization']['reference']='different';write(self.root/'harness/state.json',s)
        with self.assertRaises(ValueError):validate_task(self.root,t['task_id'])

    def test_artifact_paths_missing_escape_and_symlink_rejected(self):
        (self.root/'link.md').symlink_to(self.root/'MASTER-CONTRACT.md')
        for path in ('../key','/etc/passwd','missing.json','link.md'):
            t=self.task();v=self.value(t);v['deliverables']=[path]
            with self.assertRaises(ValueError):submit(self.root,t['task_id'],v)

    def test_artifacts_bound_to_receipt(self):
        p=self.root/'harness/evidence/data.md';p.write_text('Fixture')
        t=self.task();v=self.value(t);v['deliverables']=['harness/evidence/data.md'];submit(self.root,t['task_id'],v);p.write_text('Tampered')
        with self.assertRaises(ValueError):validate_task(self.root,t['task_id'])

    def test_read_only_review_does_not_grant_ownership_and_detects_edits(self):
        t=self.task('qa-architecture-reviewer','antigravity','reviewer')
        self.assertEqual(state(self.root)['owner'],{'provider':'codex','id':'fixture'})
        (self.root/'planning/changed.md').write_text('Unexpected edit')
        with self.assertRaises(ValueError):submit(self.root,t['task_id'],self.value(t))
        with self.assertRaises(ValueError):self.task('qa-step-executor','antigravity','reviewer')

    def test_review_requires_findings_and_support(self):
        t=self.task('qa-architecture-reviewer');v=self.value(t);v.pop('findings')
        with self.assertRaises(Exception):submit(self.root,t['task_id'],v)
        v['findings']=[{'severity':'high','location':'README.md','evidence':[],'recommendation':'Review'}]
        with self.assertRaises(ValueError):submit(self.root,t['task_id'],v)

    def test_failed_blocked_and_not_run_can_be_retained_but_cannot_complete(self):
        for status in ('failed','blocked','not_run'):
            t=self.task();v=self.value(t,status);submit(self.root,t['task_id'],v)
            self.assertEqual(validate_task(self.root,t['task_id'])['status'],status)
        require_outcomes(self.root)
        with self.assertRaises(ValueError):require_outcomes(self.root,completed=True)

    def test_blocked_handoff_and_claim_preserve_outcome_without_completion(self):
        t=self.task();submit(self.root,t['task_id'],self.value(t,'blocked'))
        path=self.root/'harness/evidence/handoff.json'
        transfer(self.root,'release','codex','fixture',path)
        self.assertIsNone(state(self.root)['owner'])
        transfer(self.root,'claim','codex','receiver',path)
        self.assertEqual(state(self.root)['agent_tasks'],[])
        self.assertEqual(state(self.root)['completed_steps'],[])

    def test_handoff_rejects_changed_outcome(self):
        t=self.task();submit(self.root,t['task_id'],self.value(t));path=self.root/'harness/evidence/handoff.json'
        transfer(self.root,'release','codex','fixture',path)
        p=directory(self.root,t['task_id'])/'outcome.json';v=read(p);v['summary']='Tampered';write(p,v)
        with self.assertRaises(ValueError):transfer(self.root,'claim','codex','receiver',path)

    def test_old_handoff_cannot_be_replayed_after_a_new_release(self):
        first=self.task();submit(self.root,first['task_id'],self.value(first))
        old=self.root/'harness/evidence/old-handoff.json'
        transfer(self.root,'release','codex','fixture',old)
        transfer(self.root,'claim','codex','receiver',old)
        current=start(self.root,'qa-step-executor','codex','receiver')
        submit(self.root,current['task_id'],self.value(current))
        transfer(self.root,'release','codex','receiver',self.root/'harness/evidence/new-handoff.json')
        with self.assertRaisesRegex(ValueError,'replay'):
            transfer(self.root,'claim','codex','another',old)

    def test_fabricated_check_and_command_rejected(self):
        t=self.task()
        for key,entry in [('checks',{'check_id':'adapters','status':'PASS','evidence':[]}),('commands',{'argv':['true'],'cwd':str(self.root),'exit_code':0,'status':'PASS','evidence':['harness/evidence/fake.json']})]:
            v=self.value(t);v[key]=[entry]
            with self.assertRaises(ValueError):submit(self.root,t['task_id'],v)

    def test_evidence_status_cannot_be_relabelled(self):
        from verify_step import command
        path='harness/evidence/fixture-evidence.json';log='harness/evidence/fixture.log';(self.root/log).write_text('Isolated fixture, not an actual execution')
        e={'version':1,'step':'0.5','provider':'codex','owner':'fixture','check_id':'adapters','command':command(self.root,'adapters'),'cwd':str(self.root),'started_at':now(),'finished_at':now(),'exit_code':1,'status':'FAIL','log':log,'log_sha256':digest((self.root/log).read_bytes()),'source_sha256':source_digest(self.root),'git':git_context(self.root),'instrumentation':'subprocess-capture'}
        e['signature']=sign_evidence(self.root,e);write(self.root/path,e);s=state(self.root);s['evidence']=[path];write(self.root/'harness/state.json',s)
        t=self.task();v=self.value(t);v['checks']=[{'check_id':'adapters','status':'PASS','evidence':[path]}]
        with self.assertRaises(ValueError):submit(self.root,t['task_id'],v)
        v['checks'][0]['status']='FAIL';submit(self.root,t['task_id'],v)

    def test_governance_check_does_not_require_foreign_QA_archives(self):
        from verify_step import command, validate_evidence
        path='harness/evidence/governance.log';(self.root/path).write_text('Isolated controller fixture')
        s=state(self.root);s['authorized_step']='7';write(self.root/'harness/state.json',s)
        e={'version':1,'step':'7','provider':'codex','owner':'fixture','check_id':'agent-outcomes','command':command(self.root,'agent-outcomes'),'cwd':str(self.root),'started_at':now(),'finished_at':now(),'exit_code':0,'status':'PASS','log':path,'log_sha256':digest((self.root/path).read_bytes()),'source_sha256':source_digest(self.root),'git':git_context(self.root),'instrumentation':'subprocess-capture'}
        e['signature']=sign_evidence(self.root,e)
        self.assertEqual(validate_evidence(self.root,e),'PASS')

    def test_cli_rejects_malformed_json_and_requires_identity(self):
        t=self.task()
        p=subprocess.run([sys.executable,str(self.root/'harness/scripts/agent_outcome.py'),'submit','--task',t['task_id'],'--input','-'],cwd=self.root,input='{bad',text=True,capture_output=True)
        self.assertNotEqual(p.returncode,0);self.assertIn('Invalid JSON',p.stderr)

    def test_repository_binding_cannot_be_replayed(self):
        t=self.task();submit(self.root,t['task_id'],self.value(t));write(self.root/'harness/location.json',{'kind':'repository','repository':'qa-python'})
        with self.assertRaises(ValueError):validate_task(self.root,t['task_id'])

if __name__=='__main__':unittest.main()
