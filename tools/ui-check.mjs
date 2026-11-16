import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
const require=createRequire(process.env.QA_BROWSER_MODULE_DIR ? process.env.QA_BROWSER_MODULE_DIR+'/package.json' : new URL('./package.json',import.meta.url));
const {chromium}=require('playwright');
const fixture=JSON.parse(await readFile(new URL('../contracts/data/baseline.json',import.meta.url)));
const base=process.env.QA_SUT_URL;
assert(base);
const browser=await chromium.launch({headless:true});
try {
 for(const scenario of ['AC-1','AC-2','AC-3']) {
  const context=await browser.newContext();
  const page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const id=randomUUID().replaceAll('-','');
  const identity=scenario==='AC-1'?{username:'qa_'+id,email:'qa.'+id+'@example.test',password:fixture.registration_identity.password}:fixture.users[0];
  const register=scenario==='AC-1';
  await page.goto(base+(register?'/register':'/login'));
  assert.deepEqual(await context.cookies(),[]);
  assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
  if(register)await page.getByLabel('Username',{exact:true}).fill(identity.username);
  await page.getByLabel('Email',{exact:true}).fill(identity.email);
  await page.getByLabel('Password',{exact:true}).fill(scenario==='AC-3'?fixture.invalid_login_password:identity.password);
  const responsePromise=page.waitForResponse(r=>r.url()===base+(register?'/api/users':'/api/users/login')&&r.request().method()==='POST');
  await page.getByRole('button',{name:register?'Sign up':'Sign in',exact:true}).click();
  const response=await responsePromise;
  assert.equal(response.status(),register?201:scenario==='AC-3'?422:200);
  if(scenario==='AC-3') {
   await page.getByRole('alert').waitFor();
   assert.equal(await page.getByRole('alert').textContent(),'Email or password is invalid.');
   assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
   assert.deepEqual(await context.cookies(),[]);
   await page.goto(base+'/settings');
   await page.waitForURL(base+'/login');
   await page.getByRole('heading',{name:'Sign in',exact:true}).waitFor();
   assert.equal(await page.getByTestId('account-email').count(),0);
   assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
   assert.deepEqual(await context.cookies(),[]);
   assert.equal((await context.request.get(base+'/api/user')).status(),401);
  } else {
   await page.waitForURL(base+'/settings');
   await page.getByTestId('account-email').waitFor();
   assert.equal(await page.getByTestId('account-email').textContent(),identity.email);
   const authenticated=await page.evaluate(async()=>{
    const token=localStorage.getItem('jwt');
    const response=await fetch('/api/user',{headers:{Authorization:`Token ${token}`}});
    const {user}=await response.json();
    return {status:response.status,email:user.email,keys:Object.keys(localStorage),session:sessionStorage.length};
   });
   assert.deepEqual(authenticated,{status:200,email:identity.email,keys:['jwt'],session:0});
   assert.deepEqual(await context.cookies(),[]);
   await page.reload();await page.getByTestId('account-email').waitFor();
   assert.equal(await page.getByTestId('account-email').textContent(),identity.email);
  }
  assert.deepEqual(errors,[]);
  await context.close();
  console.log('PASS '+scenario+' browser acceptance');
 }
} finally {await browser.close();}
