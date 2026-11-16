"""Static checks only; never labels these as native discovery or enforcement."""
import json
import re
import tomllib
from pathlib import Path
import yaml
from common import ROOT, state, validate, config, cli_error
from sync_skills import sync

def check(root):
    state(root)
    from native_acceptance import validation_profile
    validation_profile(root)
    for name in ('state', 'evidence'):
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(json.loads((root / f'harness/schemas/{name}.schema.json').read_text()))
    for name in ('steps', 'providers', 'scope-policy'):
        assert config(root, name)['version'] == 1
    skills = sorted((root / '.agents/skills').glob('*/SKILL.md'))
    assert len(skills) == 4
    for skill in skills:
        text = skill.read_text()
        front = yaml.safe_load(text.split('---', 2)[1])
        assert front['name'] == skill.parent.name and front['description']
        assert re.fullmatch('[a-z0-9-]{1,64}', front['name'])
    sync(root, check=True)
    assert (root / 'CLAUDE.md').read_text().strip() == '@AGENTS.md'
    rule = (root / '.agents/rules/qa-boundaries.md').read_text().split('---', 2)[1]
    assert yaml.safe_load(rule)['trigger'] == 'always_on'
    conf = tomllib.loads((root / '.codex/config.toml').read_text())
    assert conf['sandbox_mode'] == 'workspace-write'
    assert conf['approval_policy'] == 'on-request'
    assert conf['sandbox_workspace_write']['network_access'] is False
    claude = json.loads((root / '.claude/settings.json').read_text())
    google = json.loads((root / '.agents/hooks.json').read_text())['qa-development']
    for event in ('SessionStart', 'PreToolUse', 'PostToolUse', 'Stop'):
        assert event in claude['hooks'] and event in google
        c = claude['hooks'][event][0]['hooks'][0]
        g = google[event][0]['hooks'][0] if event in ('PreToolUse', 'PostToolUse') else google[event][0]
        assert 'claude_hook.py ' + event in c['command']
        assert 'antigravity_hook.py' in g['command'] and g['command'].endswith(' ' + event)
    return {'status': 'PASS', 'scope': 'static validation only', 'skills': [p.parent.name for p in skills]}

if __name__ == '__main__':
    try:
        print(json.dumps(check(ROOT), indent=2))
    except Exception as e:
        raise SystemExit(cli_error(e))
