---
name: qa-verification
description: Collect and assess real development acceptance evidence, including missing instrumentation and unauthorized modifications.
---

# qa-verification

Read the active step checks in harness/config/steps.yaml. Run registered checks through harness/scripts/verify_step.py run --check <id>; do not hand-edit evidence to claim execution. Evidence records commands, exit codes, logs, source digest and PASS/FAIL/NOT RUN.
Missing tools, unexecuted checks and unavailable observation cannot PASS. A subprocess exit code alone does not prove business acceptance. Inspect required artifacts and semantic check outcomes. Run scope_guard.py against the retained baseline; include untracked files, empty directories, Git refs and unexpected changes.
Run verify_step.py validate before reporting acceptance. Do not mark completion or approval when evidence is missing, stale, failed or merely simulated. Distinguish provider-protocol fixtures from live integration tests. Report failures, blockers and outstanding checks explicitly.

For formal task results, follow [the outcome workflow](../../../harness/outcomes.md). The authorized collector registers the task and validates its JSON outcome before acceptance or handoff; retain the artifact and link it from the readable report. Do not substitute an outcome claim for execution evidence. Read-only roles return their JSON to the collector and acquire no writable ownership.
