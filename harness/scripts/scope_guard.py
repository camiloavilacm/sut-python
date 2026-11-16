import argparse
from pathlib import Path
from common import ROOT, audit, inventory, git_context, state, read, write, cli_error, preflight

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--baseline', required=True, type=Path)
    p.add_argument('--capture', action='store_true')
    a = p.parse_args()
    try:
        root = a.root.resolve()
        if a.capture:
            if a.baseline.exists():
                raise ValueError('Refusing to overwrite baseline')
            s = state(root)
            preflight(root, s['authorized_step'], s['owner']['provider'], s['owner']['id'])
            write(a.baseline, {'step': s['authorized_step'], 'inventory': inventory(root), 'git': git_context(root)})
            print('PASS: baseline captured; retain a protected external copy for independent auditing')
        else:
            import json
            result = audit(root, read(a.baseline))
            print(json.dumps(result, indent=2))
            return int(result['status'] != 'PASS')
        return 0
    except Exception as e:
        return cli_error(e)

if __name__ == '__main__':
    raise SystemExit(main())
