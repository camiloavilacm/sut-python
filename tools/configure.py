from pathlib import Path
import secrets
p=Path(__file__).resolve().parents[1]/'.env'
if p.exists(): raise SystemExit('Refusing to overwrite .env')
p.write_text('POSTGRES_PASSWORD='+secrets.token_hex(24)+'\nJWT_SECRET='+secrets.token_hex(32)+'\nPORT=8001\n')
p.chmod(0o600)
print('Created private local .env')
