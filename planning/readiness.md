# Readiness register

Current authorization: Phase 0.5 development harness implementation/evaluation, by explicit user instruction `Move to Phase 0.5`. Owner: Codex phase05-builder. Phase 0 checks recorded; overall readiness gate remains NOT satisfied. The user has explicitly authorized Step 1; activation remains pending prerequisite gates. See phase-05-report.md.

See [Phase 0 report](phase-0-report.md) for version inventory, PASS/FAIL/NOT RUN results, commands and blockers; [machine-readable evidence](phase-0-evidence.json) preserves initial probes and escalated retries. Evidence collection timestamp is recorded in JSON.

Hurl/hurlfmt 8.1.0 now pass version and positive/negative parser checks; see harness/evidence/step1-readiness.json. Blocking before Step 1: prior contract inputs incomplete; target repository/CI permissions unverified; dependency compatibility not established. Phase 0.5 source is implemented; deterministic evaluations run. Full native acceptance remains incomplete, as recorded in phase-05-report.md. Only Step 1 dependencies are required before Step 1; Docker/browser runner requirements may be resolved before their dependent steps.

GitHub authentication/public Git, Python isolation, Node/npm registry, Docker daemon and provider binary availability passed. These do not establish project-specific CI permissions, native provider discovery/hooks, model-session authentication, or full browser-installation capability.

Definition of Ready additionally requires the full Phase 0.5 exit gate, authoritative contract access, explicit Step 1 authorization, and absence of premature product implementation.

## Current provider exception

The user explicitly approved Claude artifacts only because account access is unavailable. Its live tests stay NOT RUN; absence of access is no longer a blocker for the current profile. Required live acceptance is Antigravity → Codex → Antigravity, plus static validation of all Claude artifacts. See harness/approved-exceptions.json and the latest artifacts-only evidence. Other Step 1 readiness/input requirements remain in force; no product implementation is authorized by this exception alone.

## Step 1 local draft readiness

Step 1 and new unapproved assumptions are explicitly authorized. Git, isolated Python, Node/npm and Hurl/hurlfmt are available; pinned OpenAPI/Gherkin/JSON Schema validators have been installed and exercised against the draft. Phase 0.5 passed the approved Claude-artifacts-only profile. These satisfy local Step 1 prerequisites; they do not establish business approval, live SUT passes, or GitHub private CI permissions. Remote repository creation is not performed in Step 1; runtime/CI readiness remains recorded for dependent stages.
