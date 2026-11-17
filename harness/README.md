# Repository-local development harness

This harness governs coding-agent development; it is separate from QA execution runners. Read MASTER-CONTRACT.md and harness/state.json for authority, active step, owner, prerequisites and evidence. The user authorized Step 1 and has now approved its specification and assumptions. See governance/approvals/seed-1-approved-v1.json; later steps still require explicit authorization.

## Standalone specification validation

From this independent repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r tools/validate/requirements.txt
.venv/bin/python tools/validate/validate.py --check all
.venv/bin/python -m unittest discover -s tools/validate -p 'test_*.py' -v
.venv/bin/python -m unittest discover -s harness/evals -p 'test_*.py' -v
```

These tests do not call models or a SUT. Step 1 registered checks are openapi, hurl, gherkin, selectors, baseline, json-schemas and governance. Framework-specific runner definitions, tracker tools, campaign aggregation and applications are not implemented here.

## Controlled execution and evidence

The operator supplies QA_AUTHORIZATION_FILE, an external record matching the persisted step authorization, and QA_EVIDENCE_KEY_FILE, an external random recorder key (at least 32 bytes; permissions 0600). Neither credentials nor recorder keys belong in Git. The current workstation records are outside this repository in qa-workspace-control; fresh checkouts require local operator provisioning. A state edit alone cannot grant authorization.

```sh
.venv/bin/python harness/scripts/preflight.py --step 1 --provider codex --owner codex-step1
.venv/bin/python harness/scripts/verify_step.py run --check openapi
.venv/bin/python harness/scripts/verify_step.py validate
.venv/bin/python harness/scripts/verify_step.py gate
```

Use the actual owner and active step from state. Run all required check IDs, not just openapi, before the gate. The recorder captures exact commands, exit codes, logs, source fingerprints and signatures. Missing, modified or stale evidence cannot PASS. Checks currently support Phase 0.5 and Step 1; future step verification is added only when authorized. A passing technical gate does not approve business requirements, create a tag or authorize another step.

## Boundaries and handoff

Keep one writable owner. ownership.py release/claim creates and validates a structured handoff, source inventory and Git context. Unknown tool paths fail closed. Native hook wrappers retain distinct provider protocols. Antigravity shell execution requires externally scoped execution; Codex relies on sandbox/command rules plus explicit preflight/audit. Claude is artifacts-only and cannot claim writable ownership until its live profile is activated and validated. See .claude/ACTIVATION.md.

The final scope audit compares a retained baseline with tracked/untracked paths, empty directories, symlinks and Git references. New unborn repository initialization is allowed during its authorized step; new commits/tags are flagged for human review. The workspace and approved repository-root .venv folders, Python caches and Git internals are excluded from content fingerprints; Git references/status and development evidence are checked separately. A final audit cannot detect transient reverted writes or arbitrary changes outside its inspected root. Native permissions and independent review remain necessary.

## Provenance

Canonical source is governance/source. Root native artifacts are generated copies checked by governance/manifest.json; operational state/evidence are excluded from copy equivalence. The original tested Phase 0.5 source archive and its evidence are preserved separately. package_governance.py exports self-contained source without inherited authorization or ownership, and excludes generated provenance from its own inputs. No parent untracked files or cross-repository symlinks are required.

The Phase 0.5 native-cycle check runs real coding-agent sessions and may consume provider credits; it is development evaluation only and is not a Step 1 check or QA CI job. Current approved profile: Antigravity → Codex → Antigravity, with Claude artifacts statically validated and Claude live checks NOT RUN. Never report that exception as all three providers live-validated.

Formal skill-task outcomes follow `harness/outcomes.md`: the authorized collector registers and validates the JSON artifact and retains its signed receipt. Missing or invalid outcomes block acceptance and handoff. Ordinary conversation remains free-form.
