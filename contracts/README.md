# qa-features — SEED-1

Status: human-approved specification for the explicitly authorized annotated tag seed-1-approved-v1. Technical validation is recorded separately from business approval.
Source: user-supplied Development Plan v2 and explicit instruction to draft missing details as new, unapproved assumptions. The user subsequently accepted this specification and all listed assumptions. This is a new approval; no unavailable prior specification has been reconstructed or presented as previously approved.

## Story and acceptance criteria

SEED-1: User can register and log in. Three scenarios: AC-1 unique registration, AC-2 baseline login, AC-3 rejected login without browser authentication plus protected-route denial. SEED-1 and AC-3 are supplied identifiers; AC-1/AC-2 mapping, exact @tag syntax and all newly authored wording were initially draft assumptions and are now accepted by the user. The feature has exactly three scenarios, with no runner implementations.

## Assumptions accepted by the user for this approval

- Conduit subset: POST /users, POST /users/login, GET /user, relative to /api. Success statuses are 201/200/200; invalid credentials yield 422 and errors["email or password"]=["is invalid"]. Unauthenticated GET /user must yield 401 (frozen rule). Other 401 bodies are not constrained.
- UI routes /register, /login and protected /settings; failed protected navigation redirects /login and exposes no account identity. English labels/messages in selectors/feature are new draft UI contracts.
- JWT stored only at localStorage key jwt. Each browser scenario begins with empty cookies and storage; after invalid login these remain empty. A successful session must identify the expected user through authenticated GET /user, not just a stored nonempty value.
- Baseline qa_baseline / qa.baseline@example.test is synthetic and immutable. Passwords in data/baseline.json are public synthetic fixtures, never production credentials. Test registration uses a fresh UUID v4 username/email on every attempt and retry, associated with execution/slot. Provisioning is idempotent; tests never modify the baseline.
- Selector names resolve only through role, label or data-testid. Accessible exact names in selectors.json are binding after approval. UI selectors alone do not establish API correctness.
- Result/campaign schemas version 1.0, exact fields, status spelling, required artifacts, timestamps and revision hashes are accepted assumptions. All six slots require all three scenario IDs. A passed scenario requires complete observation and evidence; missing instrumentation cannot PASS. Network events expose only method/path/status/authorization_present, never credentials/tokens.
- Fixed technologies from v2 are retained. Specific framework/DB/image versions remain unselected for later explicitly authorized steps. This specification adds no SUT/runtime dependencies.

## Validation and runtime boundary

Use Python 3.11+ (tested on 3.14.4); install tools/validate/requirements.txt into an isolated environment. Run `python tools/validate/validate.py --check all`. Hurl 8.1.0/hurlfmt is the tested syntax tool. Checks use the official Gherkin parser, OpenAPI validator and JSON Schema validator; no network against a SUT is performed. Result/campaign examples in the validator are specification fixtures, not actual QA results or a reporting implementation.

For future live Hurl execution, set base_url including /api, baseline_email/username/password, registration_username/email/password and invalid_password through Hurl variables (use invalid_login_password from baseline.json, at least eight characters and different from the baseline password). Generate fresh registration identities for every run; do not reuse captured tokens across scenarios. Treat Hurl logs as sensitive: token captures are redacted and passwords must never be published. Both SUTs must pass the same unchanged contract in Step 2. Live SUT/AC executions are NOT RUN in Step 1.

Consumers must validate result/campaign schema and semantic consistency: slot_id must match nested results; issue_id, campaign_id and feature_ref must agree; timestamps must be ordered; overall result status precedence is error > failed > not_run > passed; campaign precedence is error > failed > incomplete (missing/not_run) > passed; artifact paths must exist with matching digests and redacted contents. The validation tool demonstrates structural and cross-record invariants using fixtures; real artifact existence, digest matching and redaction require future runner checks. Future aggregators enforce them; none is implemented here. The six slots are sut-python/sut-node × playwright/selenium/cypress, giving 18 scenario executions. Campaigns contain one entry per slot; a missing slot is explicit and prevents PASS. Report publication and tracker tooling are deferred.

## Governance and approval

Canonical source, tested Phase 0.5 source bundle/provenance and development evidence live in governance/, separate from business contracts. Root native artifacts and harness scripts are generated from canonical source and their hashes are checked. Claude remains artifacts-only under the user's exception; its live checks are NOT RUN. The active single owner and authorization are in harness/state.json. New adapters must be checked from the actual repository directory; parser/discovery tests are distinct from live enforcement.

This is a local independent Git repository, branch validated, with no remote chosen, SUT, runner, tracker or campaign-report implementation. The user authorized the initial commit and annotated tag seed-1-approved-v1. GitHub organization/private CI permissions are deferred to the steps that need them. Runners will use ../qa-features.git as the GitHub submodule URL; no file transport override is enabled. Consumers resolve seed-1-approved-v1 to its commit SHA and pin that SHA as feature_ref; examples use fixture hashes only. tooling_ref remains unset because reporting tools are not implemented. The committed harness/state.json is an approval-time snapshot taken before Git can bind the new tag; the post-tag commit binding is recorded in the workspace state and external approval receipt. This avoids attempting to embed a commit's own SHA in its tree.

Human approval was received: “I accept and yes, crete and approval tag”. This explicitly accepts the listed assumptions and authorizes the initial commit and seed-1-approved-v1 tag. Step 2 still requires a separate explicit instruction. The approval receipt is governance/approvals/seed-1-approved-v1.json. No autonomous future tagging, tag movement, or feature changes are permitted.

## Sources

Conduit endpoint shapes/header: https://docs.realworld.show/specifications/backend/endpoints/ . Our statuses, error wording, UI/session conventions and schemas are explicit project decisions accepted in this approval, not claims of an earlier unavailable approval. Hurl syntax: https://hurl.dev/docs/manual.html . OpenAPI 3.0.3: https://spec.openapis.org/oas/v3.0.3.html .
