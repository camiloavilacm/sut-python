# Unified QA Automation Platform — Master Contract

Authority: supplied Development Plan v2, Multi-Harness Edition. Status: architecture approved; development readiness unverified. Active authorization is recorded in harness/state.json and must match explicit user/operator approval. This architectural contract grants no phase or step authorization.

## Architecture and boundaries
Exactly five independent product repositories: qa-features, sut-python, sut-node, qa-python, qa-typescript. Use sibling directories; the workspace is not a Git repository. Create repositories only in their authorized step. No sixth governance repository. Preserve the tested canonical harness in qa-features as separate governance artifacts once Step 1 permits its creation; propagate generated native adapters to later repositories. Clean checkouts must work without untracked parent files.

## Frozen contracts
Use Conduit authentication and `Authorization: Token <jwt>`. Maintain one synthetic immutable baseline user and unique generated registration identities. UI selectors use only role, label, or data-testid. Preserve original story and AC tags. AC-3 requires UI error, no browser session, and protected-route denial. Independently check unauthenticated GET /user returns 401 with Hurl.
Observer states: complete, partial, unavailable, error. Six matrix slots, three scenarios each. One report per issue/campaign. No runtime model calls, auto-healing, or silent test changes to accommodate defects in QA CI.
Runners pin qa-features with feature_ref; reporting may separately pin tooling_ref. Relative GitHub submodule URL: ../qa-features.git. Local file transport requires explicit trusted-workstation authorization.

## Authorization gates
Phase 0: readiness. Phase 0.5A: shared harness; 0.5B: native adapters; 0.5C: skills/evaluation. Each requires its own authorized scope. Stop after Phase 0.5 pending explicit Step 1 authorization. No step implicitly authorizes another.
Step 1 produces a validated, untagged specification. Human approval separately permits an immutable feature tag. Agents cannot self-approve or autonomously tag. Steps 2–7 require explicit individual authorization and prerequisites. See planning/development-plan.md.

## Harness obligations
One authoritative shared controller, three adapters: Antigravity, Codex, Claude Code. Native artifacts must be verified against each provider's actual supported protocol. Never assume equivalent hooks or blocking semantics. Codex command rules are not a universal filesystem sandbox.
Use provider permissions, supported interception, preflight, filesystem/Git auditing, and human approval together. Final deterministic scope auditing is mandatory. Maintain schema-validated state and evidence separately from QA results/campaign schemas. Explicit human authorization must have external provenance; agent-edited state is not approval.
Only one writable owner per step. Release ownership before transfer. Receiving agents inspect state, handoff, and Git status and run preflight. Read-only independent reviews are allowed; concurrent writable agents are prohibited.
Four canonical skills: qa-step-executor, qa-contract-author, qa-verification, qa-architecture-reviewer. Canonical source is .agents/skills; Claude copies are deterministically generated and checked for drift. Native discovery must be tested from each repository's working directory.

## Security and integrity
No production secrets, blanket unrestricted shell permissions, unauthorized dependencies, unreviewed changes to approved features, automatic weakening of acceptance criteria, or future-step scaffolding. QA CI remains deterministic and separate from the development harness. Successful command execution alone is not acceptance evidence. Missing instrumentation cannot produce PASS.
Every implementation response includes summary, file tree, exact commands, PASS/FAIL/NOT RUN checklist, blockers/approvals, remaining unbuilt work, and an explicit boundary stop.
Release preserves image digests and provenance for application configuration and development harness. Preserve reporting integrity and rollback/reproduction evidence.

## Approved provider-readiness exception: CLAUDE-ARTIFACTS-ONLY

The user explicitly stated: “I dont have claude access, lets just create the file for them”. Retain and statically validate all Claude native instructions, settings, hooks and mirrored skills. Defer live Claude discovery, enforcement and handoff testing; those checks remain NOT RUN. The current Phase 0.5 exit gate requires live Antigravity → Codex → Antigravity validation and Claude artifact validation. This exception supersedes only the earlier all-three-live readiness requirement. It does not waive Step 1 inputs, step prerequisites, feature approval or product boundaries. Claude cannot claim writable ownership under the artifacts-only profile; validate and reactivate the stricter all-live profile before using it as a writer. The approval receipt is harness/approved-exceptions.json; executable policy is harness/config/providers.yaml.

Formal skill-task outcomes must follow the versioned schema and collector workflow in `harness/outcomes.md`. Valid JSON outcomes and controller receipts are mandatory at task acceptance, step completion and ownership handoff. Ordinary conversation remains free-form.
