# Formal agent outcomes

Formal tasks using any of the four QA skills require a versioned JSON outcome. Ordinary questions, plans, and progress messages remain conversational. The controller checks structure, task identity, source context, and referenced evidence. Schema-valid text alone is not proof of success.

## Register and collect

From the activated repository root, with the external authorization and evidence key configured, the authorized collector runs:

```sh
.venv/bin/python harness/scripts/agent_outcome.py start --role qa-step-executor --provider codex --actor <current-owner-id>
.venv/bin/python harness/scripts/agent_outcome.py submit --task <returned-task-id> --input /absolute/path/to/outcome.json
.venv/bin/python harness/scripts/agent_outcome.py validate --task <task-id>
.venv/bin/python harness/scripts/agent_outcome.py render --task <task-id>
```

`submit --input -` reads JSON from stdin. The outcome schema is [agent-outcome.schema.json](schemas/agent-outcome.schema.json). Use exactly the role/provider/actor/step returned by `start`. Valid statuses are `completed`, `blocked`, `failed`, and `not_run`. Review tasks require `findings`, including an empty array when no findings were found. File references are repository-relative; nonexistent, escaping, or symlink references are rejected. Outcome artifacts must contain sanitized descriptions, never credentials or raw sensitive payloads.

The collector records requests, immutable accepted outcomes, signed receipts, and rejected-submission diagnostics in `harness/evidence/agent-tasks/<task-id>/`. Requests and receipts are bound to the installation, human authorization, task, collector, source and Git refs. Evidence references must belong to the local registered checks; outcome text cannot manufacture a passing result. Commands require exact captured command/working-directory/exit-code evidence. Uninstrumented commands can be described in the summary but cannot be asserted as verified command entries.

Register implementation tasks before changing source; register verification/review tasks after the reviewed source is settled. Source changes invalidate accepted receipts. Read-only tasks reject source/ref changes between registration and collection. The active collector retains the reviewer’s returned JSON without transferring writable ownership to the reviewer. Provider identity is the collector’s recorded attribution, not a cryptographic attestation of which model produced the text. Claude remains artifacts-only and cannot become a writable owner.

## Acceptance and handoff

A completed outcome cannot contain blockers, pending approvals, or remaining work. Blocked, failed and not-run outcomes are retained for accountability. A review may complete with findings; the findings remain visible for human assessment and do not approve implementation or business requirements.

Step completion requires an implementation/authoring outcome and completed outcomes for all registered tasks, in addition to the existing evidence checks and scope audit. Missing, malformed, tampered, or stale outcomes fail acceptance. Validation does not run the completion gate recursively.

Ownership release and claim require valid outcomes. A blocked/failed outcome may support a handoff, but cannot complete the step. The handoff carries the task IDs and releasing collector; the receiver verifies them before claiming. A successful claim clears the active task list for the receiving owner; prior task artifacts remain archived. Register a new task when work resumes. Accepted task results cannot be overwritten.

The signed recorder is an existing external control, not protection against a user deliberately replacing both the controller and its key. Native provider chat output is not universally schema-constrained; enforcement occurs at harness acceptance and handoff boundaries. No runtime model calls are added to QA CI.

## Migration and validation

Historical reports are retained as history; no retrospective outcomes are fabricated. Fresh distributions contain an empty task list and inherit no authorization. Activated checkouts require a new formal task before their next completion or handoff. Repository adapters are self-contained and never depend on parent-workspace files.

The registered `agent-outcomes` check executes adversarial controller fixtures, not business QA or live provider validation. Existing live-provider requirements and the approved Claude exception remain separate.
