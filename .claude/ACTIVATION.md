# Claude Code artifacts prepared for later use

No Claude account access is needed to retain or statically validate these files:

- CLAUDE.md imports the shared AGENTS.md instructions.
- .claude/settings.json contains project permissions and provider-specific hooks.
- .claude/skills contains four generated copies of .agents/skills.
- harness/scripts/claude_hook.py implements the native protocol.

Current mode: artifacts-only. Live discovery, enforcement, stopping and fresh-session handoff tests are NOT RUN. Do not claim writable step ownership using Claude in this mode. Do not add credentials to the project files.

When access becomes available, during authorized harness maintenance: authenticate through Claude Code, check installed-version documentation, verify skill hashes/settings, and restore validation_policy profile all-live with required_live_providers [antigravity, codex, claude], no artifacts_only_providers, and validation_mode live for all providers. Require claude-native instead of claude-artifacts in the Phase 0.5 check list. Then run all registered checks and the complete live handoff cycle before claiming Claude readiness or transferring writable ownership. Keep the exception receipt as historical provenance. No other gate is implicitly waived.

Static checks from the workspace root:

```sh
.venv/bin/python harness/scripts/sync_skills.py --check
.venv/bin/python harness/scripts/validate_adapters.py
```

Official references: https://code.claude.com/docs/en/hooks and https://code.claude.com/docs/en/memory . Actual activation remains to be verified.
