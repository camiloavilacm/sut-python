import os, json, hashlib, secrets, hmac, time
from pathlib import Path
import jwt, psycopg
from psycopg.rows import dict_row
from flask import Flask, request, jsonify, send_from_directory

ROOT = Path(__file__).resolve().parent
SECRET = os.environ['JWT_SECRET']
if len(SECRET) < 32: raise RuntimeError('JWT_SECRET must be at least 32 characters')
ISSUER = 'sut-python'
app = Flask(__name__, static_folder=None)
app.config['MAX_CONTENT_LENGTH'] = 16384

def connect():
    return psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row)

def password_hash(password):
    salt = secrets.token_bytes(32)
    value = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=64)
    return salt.hex() + ':' + value.hex()

def password_matches(password, value):
    salt, expected = value.split(':')
    actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=64)
    return hmac.compare_digest(actual.hex(), expected)

def seed():
    baseline = json.loads((ROOT/'contracts/data/baseline.json').read_text())['users'][0]
    with connect() as db:
        db.execute('SELECT pg_advisory_xact_lock(2002)')
        db.execute((ROOT/'db/schema.sql').read_text())
        db.execute('INSERT INTO users (username,email,password_hash,bio,image,baseline) VALUES (%s,%s,%s,%s,%s,true) ON CONFLICT DO NOTHING', (baseline['username'],baseline['email'],password_hash(baseline['password']),baseline['bio'],baseline['image']))
        user = db.execute('SELECT * FROM users WHERE baseline').fetchone()
        if not user or any(user[k] != baseline[k] for k in ('username','email','bio','image')) or not password_matches(baseline['password'], user['password_hash']):
            raise RuntimeError('Baseline drift: refusing to overwrite')

def envelope(user, token=None):
    now = int(time.time())
    token = token or jwt.encode({'sub':str(user['id']),'iat':now,'exp':now+3600,'iss':ISSUER}, SECRET, algorithm='HS256')
    return {'user': {k:user[k] for k in ('email','username','bio','image')} | {'token':token}}

def invalid():
    return jsonify(errors={'email or password':['is invalid']}), 422

def payload(register=False):
    body = request.get_json(silent=True)
    keys = {'email','password','username'} if register else {'email','password'}
    if not isinstance(body,dict) or set(body) != {'user'} or not isinstance(body['user'],dict) or set(body['user']) != keys: return None
    user = body['user']
    if any(not isinstance(x,str) for x in user.values()): return None
    if len(user['password']) < 8 or len(user['password'].encode()) > 1024 or not user['email'] or '@' not in user['email'] or len(user['email']) > 320: return None
    if register and not 1 <= len(user['username']) <= 64: return None
    return user

@app.post('/api/users')
def register():
    user = payload(True)
    if user is None: return invalid()
    try:
        with connect() as db:
            row = db.execute('INSERT INTO users (username,email,password_hash) VALUES (%s,%s,%s) RETURNING *',(user['username'],user['email'],password_hash(user['password']))).fetchone()
        return jsonify(envelope(row)),201
    except psycopg.errors.UniqueViolation:
        return jsonify(errors={'identity':['is already taken']}),422

@app.post('/api/users/login')
def login():
    user = payload()
    if user is None: return invalid()
    with connect() as db:
        row = db.execute('SELECT * FROM users WHERE email=%s',(user['email'],)).fetchone()
    if row is None or not password_matches(user['password'],row['password_hash']): return invalid()
    return jsonify(envelope(row))

@app.get('/api/user')
def current():
    header = request.headers.get('Authorization','')
    if not header.startswith('Token ') or len(header.split()) != 2: return jsonify(errors={'auth':['unauthorized']}),401
    token = header[6:]
    try:
        claims = jwt.decode(token,SECRET,algorithms=['HS256'],issuer=ISSUER,options={'require':['sub','iat','exp','iss']})
        if not isinstance(claims['sub'],str) or not claims['sub'].isdigit(): raise ValueError('subject')
    except (jwt.InvalidTokenError,ValueError,KeyError): return jsonify(errors={'auth':['unauthorized']}),401
    with connect() as db:
        user = db.execute('SELECT * FROM users WHERE id=%s',(claims['sub'],)).fetchone()
    if not user: return jsonify(errors={'auth':['unauthorized']}),401
    return jsonify(envelope(user,token))

@app.get('/health')
def health():
    with connect() as db: db.execute('SELECT 1')
    return jsonify(status='ok')

@app.get('/')
@app.get('/login')
@app.get('/register')
@app.get('/settings')
def index(): return send_from_directory(ROOT/'frontend','index.html')

@app.get('/assets/<path:name>')
def asset(name): return send_from_directory(ROOT/'frontend/assets',name)

@app.after_request
def headers(response):
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    return response

if __name__ == '__main__': seed()
