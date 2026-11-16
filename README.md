# sut-python — SEED-1 SUT

Independent Step 2 application. The approved feature_ref is `12a55fb4b9312303378af72f96a28734b6b9ec9a` (`seed-1-approved-v1`). Contracts are byte-for-byte snapshots with a portable Git bundle proving their source; no parent workspace, Git file transport or untracked shared files are required.

## Run

Requires Docker Compose and Python 3 for configuration and development checks. Run `python3 tools/configure.py`, then `docker compose up --build -d --wait`. Open http://localhost:8001/login. The application uses a dedicated Postgres volume. `docker compose down` preserves data; `docker compose down -v` explicitly resets this synthetic local database.

Only public synthetic fixtures live in contracts/data/baseline.json. Local generated secrets stay in ignored, mode-0600 .env. The database has no host port. No production deployment configuration is supplied.

## Contract and implementation

POST /api/users (201), POST /api/users/login (200/422), GET /api/user (200/401). Authentication is exactly `Authorization: Token <jwt>`. Passwords use salted scrypt; HS256 JWTs expire in one hour and are issuer-validated. All queries are parameterized. Registration cannot overwrite existing identities. Baseline provisioning inserts once, verifies existing identity/password, and fails on drift rather than repairing it. A DB trigger denies baseline UPDATE/DELETE.

One frontend bundle is distributed identically in both SUT repositories. frontend/manifest.json locks its bytes; backends serve those bytes without template substitutions. /settings verifies GET /api/user before showing identity. Tokens use only localStorage.jwt; rejected login creates no cookies or storage. No runtime AI, healing, runners, tracker tools or campaign jobs exist.

## Development verification

Create `.venv` and install harness/requirements.txt and tools/requirements.txt. `python tools/verify.py --check digests` proves contract Git blobs and frontend hashes. Install UI probes with `npm ci --ignore-scripts --prefix tools` and `tools/node_modules/.bin/playwright install chromium`. Optionally install them outside the checkout and set `QA_BROWSER_MODULE_DIR` to that package directory. The other checks (`hurl`, `seeds`, `ui-parity`) require the running Compose stack; UI checks additionally use the exact Playwright package/browser in tools/package-lock.json. These are SUT acceptance probes, not Step 3/4 runner implementations. Logs omit tokens/passwords.

Native instructions and four skills are committed here. Canonical governance derives from qa-features at the feature_ref above, with Step 2 controller maintenance recorded in governance/adapter-revision.json. Fresh clones require external human authorization and recorder key before writable harness activation. Claude is artifacts-only under the approved exception; live Claude remains NOT RUN.

The Step 2 controller extension is maintained in this authorized repository, with a patch against the frozen canonical source in governance/step2-controller.patch. The parent workspace controller remains unchanged. Use this repository’s verify_step.py for Step 2 evidence; tools/workspace_gate.py combines both repository gates and the original workspace scope baseline. New Git repositories remain uncommitted for review; no remote or release tag is created.
