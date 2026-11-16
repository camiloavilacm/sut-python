# Phase 0.5 implementation report

Historical initial report. See native-acceptance-followup.md for the later completion-path fix and current evaluation results.

Authorization: user instruction `Move to Phase 0.5`. Owner: Codex phase05-builder. Source implementation is present; the Phase 0.5 exit gate remains NOT satisfied. Step 1 is unauthorized. No product repositories were created.

## Delivered source

- Shared step/provider/scope configuration; strict development state/evidence schemas; persisted authorization, ownership, prerequisite, approval and reference state.
- Preflight, filesystem/Git scope audit, command recorder/evidence validation, adapter validation, deterministic skill synchronization, release/claim handoffs and reproducible governance export.
- Four canonical skills and byte-identical Claude copies; concise AGENTS.md, CLAUDE.md import, Antigravity rule/hooks, Codex sandbox/approval configuration and optional command rules, Claude settings/hooks.
- Adversarial isolated evaluation cases, clean-room packaging test, native parser/discovery probes and bounded disposable native sessions. Development evaluation model calls remain outside QA execution CI.

## Acceptance checklist

| Check | Status | Evidence and limits |
|---|---|---|
| Contract, four skills, native artifacts present | PASS | Static adapter validation; skill-creator quick_validate passed all four |
| Skill synchronization | PASS | Exact byte/hash equivalence; mutation fixture fails |
| State/evidence schemas | PASS | JSON Schema 2020-12 validation; malformed/unexecuted claims fail |
| Controller and native protocol fixtures | PASS | 21 unittest methods plus provider subcases; registered evals captures final result |
| Scope/approval simulations | PASS | Unauthorized repo/empty dir/path/symlink changes, premature step, self-approval, missing evidence and forged signatures rejected |
| Handoff fixtures | PASS | Antigravity → Codex → Claude → Antigravity; release required, state/Git inventory preserved, drift rejected |
| Clean-room distribution | PASS | Reproducible export, content hashes, self-contained scripts/adapters, independent Git-root fixture and local path mapping; authorization and ownership not inherited |
| Codex native parsing/discovery/policy | PASS, partial | Strict startup parse; prompt-input sees instructions/four skills; execpolicy returns forbidden for git tag and prompt for git push |
| Codex active project trust/config | NOT RUN | Bounded exec warned project-local config was untrusted/disabled; no persistent personal trust was changed |
| Codex native scope-denial probe | PASS, partial | Disposable read-only session denied one file-tool write; no forbidden file or workspace modifications |
| Antigravity native parser | PASS, partial | Strict disposable plugin validation finds four skills, one rule and hook group; not proof of project activation |
| Antigravity live lifecycle | PARTIAL | Initial live probe exposed relative-command cwd failure; payload-based launcher corrected it. Retest observed native lifecycle events; actual CLI read_file/write_file naming and headless ask behavior exposed a scope failure in a disposable fixture. Added actual names and fail-closed unknown-tool handling. Final retest observed a fail-closed denial, SessionStart/PreToolUse/PostToolUse/Stop and no forbidden file. Its uppercase Path argument was then supported and checked in protocol fixtures, including an allowed in-scope write. Full session/handoff acceptance remains incomplete |
| Claude settings and native SessionStart | PASS, partial | Doctor and a disposable native session loaded SessionStart; import/settings static checks pass |
| Claude live behavior | NOT RUN | API HTTP 400: Credit balance is too low; no model turn completed |
| Full native fresh-session handoff cycle | NOT RUN | Fixture handoffs pass; no claim of completed three-provider live cycle |
| Mandatory final scope audit | See evidence | Run against retained pre-preparation filesystem baseline; original repository must remain unchanged |
| Phase 0.5 overall exit | FAIL (blocked) | Complete native acceptance evidence unavailable; gate must stay closed |

Native probes intentionally return code 3 / NOT RUN for incomplete provider acceptance even when individual checks succeed. Model text alone is not a hook-denial assertion. Preserve actual hook events and filesystem outcomes. Never treat a hook crash or timeout as a successful policy denial.

## Commands and evidence

From the workspace root, using its isolated interpreter:

```sh
.venv/bin/python harness/scripts/preflight.py --step 0.5 --provider codex --owner phase05-builder
.venv/bin/python harness/scripts/sync_skills.py --check
.venv/bin/python harness/scripts/verify_step.py run --check adapters
.venv/bin/python harness/scripts/verify_step.py run --check evals
.venv/bin/python harness/scripts/verify_step.py run --check codex-native
.venv/bin/python harness/scripts/verify_step.py run --check claude-native
.venv/bin/python harness/scripts/verify_step.py run --check antigravity-native
.venv/bin/python harness/scripts/scope_guard.py --baseline harness/evidence/baseline.json
.venv/bin/python harness/scripts/verify_step.py validate
.venv/bin/python harness/scripts/verify_step.py gate
```

Set QA_EVIDENCE_KEY_FILE to the operator-owned external recorder key before recorded checks. Exact argv, exit codes, logs, source hashes, signatures and timestamps are captured in harness/evidence/*.json and *.log. The recorder records validation and evaluation checks, not a fabricated overall PASS. Native live attempts made during staging are explicitly named *live*/*mapping* logs, or an observed-attempt summary, and are not signed acceptance records. Initial sandbox failures were retried with scoped escalation. No global provider configuration, persistent trust, model default or production credentials were changed.

## Blockers, remaining work and boundary

Restore Claude evaluation credit, establish trusted native project activation interactively where needed, complete provider discovery/denial/stop/fresh-session acceptance and rerun the gate. Continue Phase 0 readiness work before requesting Step 1: Hurl/hurlfmt, prior story/contract inputs, dependency compatibility and target CI permissions remain unresolved. Browser/runner installation is deferred to dependent steps.

Native interception gaps, same-principal trust assumptions and runtime-directory exclusions are documented in harness/README.md. Independently protect approval ledger, recorder key and baseline; project-local scripts are not a universal security sandbox.

No qa-features, SUT, runner, tracker, campaign tooling, feature tag or smoke release exists. Source remains in a non-Git workspace; tested governance will be versioned in qa-features only after Step 1 authorization. Work stops within Phase 0.5; this report does not approve its exit or authorize Step 1.
