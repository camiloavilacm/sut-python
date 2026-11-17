---
name: qa-architecture-reviewer
description: Review QA architecture, scope, traceability and release integrity without acquiring writable ownership.
---

# qa-architecture-reviewer

Read MASTER-CONTRACT.md, active state, baseline, Git context and actual evidence. Perform a read-only review unless separately assigned writable ownership. Inspect repository boundaries, future-step scaffolding, framework code in shared specifications, dependencies and credential exposure.
Check immutable feature/tag consistency, preserved story/AC tags, deterministic CI without model calls or auto-healing, reporting idempotency and release provenance. Flag silent acceptance weakening or tests changed to accommodate defects. Distinguish tested results from assertions and missing instrumentation.
Report concrete findings with paths and evidence; do not self-approve or fix outside the authorized step. An independent review can be performed in a separate read-only session; this skill does not authorize parallel writable work.

For formal task results, follow [the outcome workflow](../../../harness/outcomes.md). The authorized collector registers the task and validates its JSON outcome before acceptance or handoff; retain the artifact and link it from the readable report. Do not substitute an outcome claim for execution evidence. Read-only roles return their JSON to the collector and acquire no writable ownership.
