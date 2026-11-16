"""Step 2 SUT acceptance only; no BDD runner or campaign implementation."""
from pathlib import Path
import argparse, json, subprocess, hashlib, tempfile, uuid, urllib.request, urllib.error, os, time, base64, hmac
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.name
BASE=os.environ.get('QA_SUT_URL','http://127.0.0.1:'+('8001' if REPO=='sut-python' else '8002'))
FIXTURE=json.loads((ROOT/'contracts/data/baseline.json').read_text())
BASELINE=FIXTURE['users'][0]
def run(args,**kwargs):
    p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=120,**kwargs)
    if p.returncode: raise AssertionError('Command failed: '+args[0]+' '+str(p.returncode))
    return p.stdout

def request(path,body=None,authorization=None):
    headers={'Content-Type':'application/json'}
    if authorization is not None: headers['Authorization']=authorization
    req=urllib.request.Request(BASE+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
    try: response=urllib.request.urlopen(req,timeout=10)
    except urllib.error.HTTPError as e: response=e
    assert response.headers.get('Set-Cookie') is None
    return response.status,json.loads(response.read())

def digests():
    provenance=json.loads((ROOT/'contracts/provenance.json').read_text())
    ref=provenance['feature_ref']
    with tempfile.TemporaryDirectory() as d:
        run(['git','clone','--quiet',str(ROOT/'contracts/approved.bundle'),d])
        assert run(['git','-C',d,'rev-parse','seed-1-approved-v1^{commit}']).strip()==ref
        for name,expected in provenance['files'].items():
            data=(ROOT/'contracts'/name).read_bytes()
            assert hashlib.sha256(data).hexdigest()==expected
            p=subprocess.run(['git','-C',d,'show',ref+':'+name],capture_output=True,check=True)
            assert p.stdout==data
    manifest=json.loads((ROOT/'frontend/manifest.json').read_text())
    assert manifest['feature_ref']==ref
    assert set(manifest['files'])=={'index.html','assets/app.js','assets/style.css'}
    for name,sha in manifest['files'].items():
        assert hashlib.sha256((ROOT/'frontend'/name).read_bytes()).hexdigest()==sha
    lock=json.loads((ROOT/'images.lock.json').read_text())
    assert lock['base'] in (ROOT/'Dockerfile').read_text() and lock['postgres'] in (ROOT/'compose.yaml').read_text()
    for image in (lock['base'],lock['postgres']): assert '@sha256:' in image
    adapter=json.loads((ROOT/'harness/provenance.json').read_text())
    for name,sha in adapter['files'].items():
        if name == 'harness/state.json': continue  # Operator-owned runtime, schema validated separately.
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha, 'Adapter drift: '+name
    revision=json.loads((ROOT/'governance/adapter-revision.json').read_text())
    assert revision['feature_ref']==ref
    for name,hashes in revision['files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==hashes['adapter_sha256']
    print('PASS: approved Git blobs, contract hashes, frontend, base-image digests and adapter hashes')

def hurl():
    identity=uuid.uuid4().hex
    variables={'base_url':BASE+'/api','baseline_email':BASELINE['email'],'baseline_username':BASELINE['username'],'baseline_password':BASELINE['password'],'registration_username':'qa_'+identity,'registration_email':'qa.'+identity+'@example.test','registration_password':FIXTURE['registration_identity']['password'],'invalid_password':FIXTURE['invalid_login_password']}
    with tempfile.NamedTemporaryFile(mode='w') as f:
        os.chmod(f.name,0o600)
        f.write(''.join(k+'='+v+'\n' for k,v in variables.items()));f.flush()
        run(['hurl','--test','--variables-file',f.name,str(ROOT/'contracts/api/auth.hurl')])
    # Negative authentication cases beyond the approved happy-path Hurl assertions.
    status,body=request('/api/users/login',{'user':{'email':BASELINE['email'],'password':BASELINE['password']}})
    assert status==200 and set(body['user'])=={'username','email','token','bio','image'}
    token=body['user']['token']
    for header in ('Bearer '+token,'Token garbage','Token '+token[:-5]+'xxxxx',''):
        assert request('/api/user',authorization=header)[0]==401
    assert request('/api/users',{'user':{'email':BASELINE['email'],'username':'collision_'+identity,'password':'password123'}})[0]==422
    assert request('/api/users/login',{'user':{'email':"x' OR 1=1 --",'password':'password123'}})[0]==422
    assert request('/api/users/login',{'user':{'email':BASELINE['email'],'password':[]}})[0]==422
    secret=dict(line.split('=',1) for line in (ROOT/'.env').read_text().splitlines() if '=' in line and not line.startswith('#'))['JWT_SECRET']
    def encode(x): return base64.urlsafe_b64encode(json.dumps(x,separators=(',',':')).encode()).rstrip(b'=').decode()
    for claims in ({'sub':'1','iat':1,'exp':2,'iss':REPO},{'sub':'1','iat':int(time.time()),'iss':REPO},{'sub':'1','iat':int(time.time()),'exp':int(time.time())+60,'iss':'other'}):
        head=encode({'alg':'HS256','typ':'JWT'})+'.'+encode(claims)
        signature=base64.urlsafe_b64encode(hmac.new(secret.encode(),head.encode(),hashlib.sha256).digest()).rstrip(b'=').decode()
        assert request('/api/user',authorization='Token '+head+'.'+signature)[0]==401
    print('PASS: unchanged Hurl (7 requests) and 10 negative auth/input/identity checks')

def query(sql):
    return run(['docker','compose','exec','-T','db','psql','-U','qa','-d','qa','-tA','-v','ON_ERROR_STOP=1','-c',sql]).strip()

def seeds():
    before=query("SELECT row_to_json(u)::text FROM users u WHERE baseline")
    row=json.loads(before)
    assert all(row[k]==BASELINE[k] for k in ('username','email','bio','image'))
    assert row['password_hash']!=BASELINE['password'] and ':' in row['password_hash']
    command=['python','app.py'] if REPO=='sut-python' else ['node','app.js','--seed']
    for _ in range(2): run(['docker','compose','exec','-T','app',*command])
    assert query("SELECT row_to_json(u)::text FROM users u WHERE baseline")==before
    assert query('SELECT count(*) FROM users WHERE baseline')=='1'
    for sql in ("UPDATE users SET username='corrupt' WHERE baseline",'DELETE FROM users WHERE baseline'):
        p=subprocess.run(['docker','compose','exec','-T','db','psql','-U','qa','-d','qa','-v','ON_ERROR_STOP=1','-c',sql],cwd=ROOT,capture_output=True,text=True,timeout=30)
        assert p.returncode!=0 and 'immutable baseline' in p.stderr
    run(['docker','compose','restart','app'])
    for _ in range(60):
        try:
            if request('/health')[0]==200:break
        except (OSError,urllib.error.URLError):pass
        time.sleep(.3)
    else:raise AssertionError('App did not recover')
    assert query("SELECT row_to_json(u)::text FROM users u WHERE baseline")==before
    print('PASS: repeat provisioning preserves full row/hash, single baseline, UPDATE/DELETE denied, restart persistence')

def ui_parity():
    print(run(['node',str(ROOT/'tools/ui-check.mjs')],env=dict(os.environ,QA_SUT_URL=BASE)).strip())
    # Compare HTTP-served bytes to the immutable bundle, not just files on disk.
    for path,name in [('/login','index.html'),('/register','index.html'),('/settings','index.html'),('/assets/app.js','assets/app.js'),('/assets/style.css','assets/style.css')]:
        with urllib.request.urlopen(BASE+path) as response:
            assert response.read()==(ROOT/'frontend'/name).read_bytes()
    print('PASS: 3 real-browser scenarios and all HTTP-served frontend hashes')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',choices=['hurl','seeds','ui-parity','digests'],required=True);args=parser.parse_args()
    {'hurl':hurl,'seeds':seeds,'ui-parity':ui_parity,'digests':digests}[args.check]()
