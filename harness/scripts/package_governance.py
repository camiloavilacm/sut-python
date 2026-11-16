"""Export self-contained governance; never create or initialize product repositories."""
import argparse
import io
import json
from pathlib import Path
import tarfile
from common import ROOT, digest, state

def bundle(root, repository=None):
    names = ['MASTER-CONTRACT.md', 'AGENTS.md', 'CLAUDE.md']
    for prefix in ('.agents', '.claude', '.codex', 'harness', 'planning'):
        for f in sorted((root / prefix).rglob('*')):
            if f.is_file() and not f.is_symlink() and not any(x in f.parts for x in ('evidence', '__pycache__')):
                names.append(f.relative_to(root).as_posix())
    data = {name: (root / name).read_bytes() for name in names if name not in ('harness/state.json', 'harness/authorization.json', 'harness/provenance.json')}
    s = state(root)
    s.update(authorized_step=None, owner=None, completed_steps=[], evidence=[], prerequisites={}, git_revisions={}, feature_ref=None, tooling_ref=None, approval_status='not_requested', blockers=['Fresh distribution: human authorization and local verification required'], next_action='Obtain explicit human authorization; no product work')
    s['authorization'] = {'step': 'none', 'source': 'human', 'reference': 'Not authorized; operator must supply external approval', 'approved_feature_ref': None}
    data['harness/state.json'] = (json.dumps(s, indent=2) + '\n').encode()
    # Instructions describe the process, not a transferable owner grant.
    data['AGENTS.md'] = b'# Development instructions\n\nRead MASTER-CONTRACT.md and harness/state.json. Determine the active authorization and writable owner from persisted state and the external human authorization record. Verify prerequisites and scope, run real checks and retain evidence, and stop at the authorized boundary. A freshly exported distribution requires operator activation. See harness/README.md.\n'
    if repository is not None:
        from common import PRODUCTS
        if repository not in PRODUCTS:
            raise ValueError('Unknown product repository')
        data['harness/location.json'] = (json.dumps({'kind': 'repository', 'repository': repository}, indent=2) + '\n').encode()
    manifest = {'version': 1, 'files': {name: digest(content) for name, content in sorted(data.items())}, 'authorization_inherited': False}
    data['harness/provenance.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w', format=tarfile.PAX_FORMAT) as tar:
        for name, content in sorted(data.items()):
            item = tarfile.TarInfo(name)
            item.size = len(content)
            item.mode = 0o644
            item.mtime = 0
            tar.addfile(item, io.BytesIO(content))
    return buf.getvalue(), manifest

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--repository', choices=['qa-features', 'sut-python', 'sut-node', 'qa-python', 'qa-typescript'])
    a = p.parse_args()
    if a.output.exists():
        raise SystemExit('Refusing to overwrite existing bundle')
    data, manifest = bundle(ROOT, a.repository)
    a.output.write_bytes(data)
    print(json.dumps({'sha256': digest(data), 'files': len(manifest['files']), 'authorization_inherited': False}))
