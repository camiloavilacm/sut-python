"""Regression checks for Step 2 controller adaptations, using isolated fixtures."""
from pathlib import Path
import unittest, tempfile, shutil, os, sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import ROOT,read,write,preflight,inventory,git_context,audit
from verify_step import command,gate
class Step2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'repo'
        shutil.copytree(ROOT,self.root,ignore=shutil.ignore_patterns('.git','.venv','evidence','__pycache__','node_modules'))
        (self.root/'harness/evidence').mkdir()
        import subprocess
        subprocess.run(['git','init','--quiet',str(self.root)],check=True)
        self.s=read(self.root/'harness/state.json');self.s['evidence']=[]
        self.s['baseline']='harness/evidence/fixture-baseline.json'
        write(self.root/'harness/state.json',self.s)
        self.auth=Path(self.tmp.name)/'auth.json';write(self.auth,self.s['authorization'])
        self.env=patch.dict(os.environ,{'QA_AUTHORIZATION_FILE':str(self.auth)})
        self.env.start();self.addCleanup(self.env.stop)
        self.baseline={'step':'2','inventory':inventory(self.root),'git':git_context(self.root)}
        write(self.root/self.s['baseline'],self.baseline)
    def test_step2_hurl_executes_live_contract_probe(self):
        args=command(self.root,'hurl')
        self.assertEqual(args[-3:],[str(self.root/'tools/verify.py'),'--check','hurl'])
    def test_missing_evidence_cannot_complete_step2(self):
        failures=gate(self.root)
        self.assertTrue(any('missing/non-PASS' in item for item in failures))
    def test_tampered_external_authorization_blocks(self):
        receipt=read(self.auth);receipt['approved_feature_ref']='0'*40;write(self.auth,receipt)
        with self.assertRaises(ValueError):preflight(self.root,'2',self.s['owner']['provider'],self.s['owner']['id'])
    def test_missing_approved_git_proof_blocks_clean_checkout(self):
        (self.root/'contracts/approved.bundle').unlink()
        with self.assertRaises(ValueError):preflight(self.root,'2',self.s['owner']['provider'],self.s['owner']['id'])
    def test_future_repository_adapter_is_denied(self):
        write(self.root/'harness/location.json',{'kind':'repository','repository':'qa-python'})
        self.assertEqual(audit(self.root,self.baseline)['status'],'FAIL')
    def test_future_runner_scaffolding_is_rejected(self):
        (self.root/'cypress').mkdir()
        self.assertEqual(audit(self.root,self.baseline)['status'],'FAIL')
if __name__=='__main__':unittest.main()
