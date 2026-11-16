import argparse
from pathlib import Path
from common import ROOT, digest, cli_error

def sync(root, check=False):
    src, dst = root / '.agents/skills', root / '.claude/skills'
    sources = {p.relative_to(src): p.read_bytes() for p in src.rglob('*') if p.is_file()}
    copies = {p.relative_to(dst): p.read_bytes() for p in dst.rglob('*') if p.is_file()} if dst.exists() else {}
    if check:
        if sources != copies:
            raise ValueError('Claude skill copies drifted or extra files exist')
    else:
        if set(copies) - set(sources):
            raise ValueError('Unexpected mirrored files; review before synchronization')
        for name, content in sources.items():
            target = dst / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    return {str(k): digest(v) for k, v in sources.items()}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--check', action='store_true')
    a = p.parse_args()
    try:
        import json
        print(json.dumps(sync(a.root, a.check), indent=2))
        return 0
    except Exception as e:
        return cli_error(e)

if __name__ == '__main__':
    raise SystemExit(main())
