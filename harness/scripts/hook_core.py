"""Shared policy; provider wrappers alone encode native hook protocols."""
from pathlib import Path
import shlex
from common import preflight, state, permitted, read, audit, safe_relative

READ_TOOLS = {'Read', 'Glob', 'Grep', 'view_file', 'read_file', 'list_dir', 'grep_search', 'find_by_name', 'view_file_outline', 'view_code_item'}
WRITE_TOOLS = {'Write', 'Edit', 'MultiEdit', 'write_file', 'edit_file', 'write_to_file', 'replace_file_content', 'multi_replace_file_content'}
SHELL_TOOLS = {'Bash', 'run_command'}

def evaluate(root, provider, event, tool='', args=None):
    s = state(root)
    if event == 'SessionStart':
        return 'context', f"Authorized step {s['authorized_step']}; owner {s['owner']}; no next-step execution. Run preflight and inspect evidence."
    if event in ('PostToolUse', 'Stop'):
        baseline = root / s['baseline']
        if not baseline.exists():
            return 'report', 'NOT RUN: missing scope baseline; completion is blocked'
        result = audit(root, read(baseline))
        if result['status'] != 'PASS':
            return 'report', 'FAIL scope audit: ' + '; '.join(result['errors'])
        return 'report', 'Scope audit PASS. Completion still requires verify_step.py validate and gate; never infer approval.'
    if event != 'PreToolUse':
        return 'deny', 'Unsupported hook event'
    if tool in READ_TOOLS:
        return 'allow', 'Read-only inspection; no writable ownership granted'
    try:
        if s['owner'] is None:
            raise ValueError('No writable owner')
        preflight(root, s['authorized_step'], provider, s['owner']['id'])
    except Exception as e:
        return 'deny', str(e)
    args = args or {}
    if tool in WRITE_TOOLS:
        value = args.get('file_path') or args.get('path') or args.get('Path') or args.get('TargetFile') or args.get('AbsolutePath')
        if not isinstance(value, str):
            return 'deny', 'Missing target path'
        target = Path(value)
        if target.is_absolute():
            try:
                value = str(target.resolve().relative_to(root.resolve()))
            except ValueError:
                return 'deny', 'Target outside workspace'
        try:
            if not permitted(root, s['authorized_step'], value):
                return 'deny', 'Target outside authorized step'
            value = safe_relative(root, value).relative_to(root.resolve()).as_posix()
        except ValueError as e:
            return 'deny', str(e)
        if value in ('harness/state.json', 'harness/authorization.json'):
            return 'deny', 'Use controller ownership operations; no direct authorization/state edits'
        return 'allow', 'In-scope file action; mandatory post-execution audit remains required'
    if tool in SHELL_TOOLS:
        command = args.get('command') or args.get('CommandLine') or ''
        try:
            tokens = shlex.split(command)
        except ValueError:
            return 'deny', 'Unparseable shell command'
        if tokens[:2] in (['git', 'tag'], ['git', 'push']):
            return 'deny', 'Human-controlled Git approval boundary'
        if provider == 'antigravity':
            return 'deny', 'Antigravity shell interception requires external scoped execution; headless ask semantics are not trusted'
        return 'ask', 'Shell effects cannot be proven by token inspection; require scoped permission and final audit'
    return 'deny', 'Unsupported interception path denied; use an externally scoped operator action and final audit'
