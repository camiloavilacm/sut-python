# Harness implementation specification

Phase 0.5 source implementation is present. MASTER-CONTRACT.md owns architectural requirements; planning/phase-05-report.md records actual checks and incomplete native acceptance.

## Shared controller
Use harness/config/{steps,providers,scope-policy}.yaml and separate state/evidence JSON schemas. Steps define prerequisite state, allowed repositories/categories, outputs, checks, forbidden future artifacts, approvals and exit conditions. State records phase, authorization provenance, owner, approvals, completions, revisions, baseline status, evidence, blockers and next eligible action. Evidence records check identity, exact command, exit code, actual output reference, timestamps, PASS/FAIL/NOT RUN, owner and revisions. Evidence completeness and acceptance outcomes are separate from process exit status.

Planned scripts: preflight.py, scope_guard.py, verify_step.py, validate_adapters.py, sync_skills.py. Lifecycle: authorize → preflight → context → execute → verify → audit → evidence → stop. Reject missing approval provenance, unmet prerequisites, conflicting owner, missing references and inconsistent workspace. Compare filesystem inventory and Git status/diffs against baseline, including untracked files and unauthorized repository creation. Never let an agent's state edit grant authority.

## Native adapters
Antigravity: AGENTS.md, .agents/skills, .agents/rules/qa-boundaries.md with supported activation frontmatter, .agents/hooks.json. Codex: AGENTS.md, shared .agents/skills, .codex/config.toml and optional tested .codex/rules/qa-commands.rules. Claude: CLAUDE.md references/imports shared instructions without duplicate loading, .claude/settings.json, generated .claude/skills.

Validate all paths, events, protocols, blocking outputs and configuration against official installed-version documentation before generating active files. Provider-specific adapters translate session initialization, pre-tool validation, post-tool audit and stop evidence checks where supported. Record unsupported interception and external compensating controls explicitly. No hook alone guarantees containment.

## Skills and distribution
Executor checks authorization/prerequisites/scope and stops; contract author covers shared specifications without runner definitions; verification demands actual evidence and flags unexpected changes; architecture reviewer inspects boundaries, dependencies, credentials, tags, AI behavior and release/reporting integrity. Use the skill-creator workflow when implementation is authorized.
Claude skill synchronization preserves name, intent and shared rules, translates provider references only, and fails on normalized-content/hash drift. Commit generated repository artifacts only when that repository is authorized. Record canonical governance and adapter revisions; test discovery and sync from clean independent checkouts without parent files.
