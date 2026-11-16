---
name: qa-step-executor
description: Execute an explicitly authorized QA platform development step and stop at its boundary.
---

# qa-step-executor

Read MASTER-CONTRACT.md, harness/state.json and the requested step in harness/config/steps.yaml. Confirm explicit human authorization; state edits do not grant it. Run .venv/bin/python harness/scripts/preflight.py --step <active-step> --provider <provider> --owner <owner-id>. If authorization or prerequisites fail, report and stop dependent work.
Identify allowed repositories/categories, inspect the baseline and actual Git status, and use qa-contract-author for specification work and qa-verification for checks. Never begin the next step or create future-step scaffolding.
Only the recorded writable owner may edit; release and claim through harness/scripts/ownership.py with a structured handoff before switching providers. The receiving owner checks handoff/Git and reruns preflight.
Run required checks, mandatory scope audit and evidence validation. Report the seven fields required by MASTER-CONTRACT.md and stop. Never self-approve tags or modify state to grant authorization.
