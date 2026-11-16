---
name: qa-contract-author
description: Author framework-independent Gherkin, Conduit API contracts and shared QA specifications during an authorized specification step.
---

# qa-contract-author

Read MASTER-CONTRACT.md and the original approved story/AC inputs. Missing prior contract details are blockers; do not invent approvals or silently weaken criteria. Preserve original tags, baseline identity rules and allowed UI selectors.
During Step 1 author only its declared shared outputs: Gherkin, Conduit OpenAPI, Hurl checks, selector coverage, baseline data and QA result/campaign schemas. AC-3 covers UI error, no browser session and protected-route denial; include independent unauthenticated GET /user HTTP 401 Hurl coverage.
Do not write pytest-bdd/Cypress step definitions, tracker tools or campaign report stubs in Step 1. QA schemas are separate from development harness state/evidence. Validate technically without creating an approval tag. Use qa-verification for actual validation evidence.
