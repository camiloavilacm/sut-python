"""Combine Step 2 repository evidence and the original workspace scope audit."""
from pathlib import Path
import json,subprocess,sys,os
HERE=Path(__file__).resolve().parents[1]
WORKSPACE=HERE.parent
sys.path.insert(0,str(WORKSPACE/'harness/scripts'))
from common import state,read,audit,write,now

def gate():
    s=state(WORKSPACE)
    assert s['authorized_step']=='2'
    checks=[]
    for name in ('sut-python','sut-node'):
        root=WORKSPACE/name
        interpreter=root/'.venv/bin/python'
        p=subprocess.run([str(interpreter),'harness/scripts/verify_step.py','gate'],cwd=root,capture_output=True,text=True,timeout=120)
        assert p.returncode==0, name+': '+p.stdout+p.stderr
        checks.append({'repository':name,'command':[str(interpreter),'harness/scripts/verify_step.py','gate'],'exit_code':p.returncode,'output':p.stdout})
    assert (WORKSPACE/'sut-python/frontend/manifest.json').read_bytes()==(WORKSPACE/'sut-node/frontend/manifest.json').read_bytes()
    frozen=WORKSPACE/'qa-features'
    assert not subprocess.check_output(['git','-C',str(frozen),'status','--porcelain'])
    assert subprocess.check_output(['git','-C',str(frozen),'rev-parse','seed-1-approved-v1^{commit}'],text=True).strip()==s['feature_ref']
    assert all(not (WORKSPACE/name).exists() for name in ('qa-python','qa-typescript'))
    result=audit(WORKSPACE,read(WORKSPACE/s['baseline']))
    assert result['status']=='PASS',json.dumps(result['errors'])
    receipt={'step':'2','status':'PASS','time':now(),'feature_ref':s['feature_ref'],'repository_gates':checks,'workspace_scope_audit':result,'cross_sut_frontend_parity':'PASS','step3_authorized':False}
    write(WORKSPACE/'harness/evidence/step2-combined-gate.json',receipt)
    print(json.dumps({'status':'PASS','checks':'both repository evidence gates, immutable feature, identical frontend, original workspace scope audit','step3_authorized':False},indent=2))
if __name__=='__main__':gate()
