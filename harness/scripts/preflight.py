import argparse
from pathlib import Path
from common import ROOT, preflight, cli_error

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--step', required=True)
    p.add_argument('--provider', required=True)
    p.add_argument('--owner', required=True)
    a = p.parse_args()
    try:
        preflight(a.root.resolve(), a.step, a.provider, a.owner)
        print('PASS: explicit authorization, prerequisites, owner and workspace')
        return 0
    except Exception as e:
        return cli_error(e)

if __name__ == '__main__':
    raise SystemExit(main())
