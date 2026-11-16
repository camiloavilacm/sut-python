# Phase 0 readiness report

Authorization: user instruction `phase 0`. Owner: Codex, this session. Scope: readiness verification and documentation only. Phase 0 checks performed; exit gate NOT satisfied. No Phase 0.5 or Step 1 authorization.

## Results

| Check | Status | Observed result |
|---|---|---|
| Git / GitHub CLI | PASS | Git 2.39.5 (Apple Git-154); gh 2.87.3 |
| GitHub authentication / public HTTPS Git | PASS | Authenticated API request and public ls-remote succeed outside sandbox |
| Python / pip / isolated environment | PASS | Python 3.14.4; pip 26.1; temporary venv created and interpreter isolation verified |
| Node / npm / registry | PASS | Node v26.13.0; npm 11.20.0; registry ping succeeds outside sandbox |
| Hurl / Hurl formatter | FAIL | hurl and hurlfmt not found on PATH; required Step 1 prerequisite missing |
| Docker / Compose / daemon | PASS | Docker 29.9.2; Compose v5.6.1; daemon 29.9.2 accessible outside sandbox |
| Codex / Claude Code availability | PASS | codex-cli 0.169.0; Claude Code 2.1.305 |
| Antigravity availability | PASS | agy CLI 1.5.9; Antigravity app 2.28.2; distinct installed artifacts, not assumed equivalent |
| Browser availability | PASS | Chrome app metadata: 157.0.8103.51; launch/automation not tested |
| Installation connectivity | PASS | npm ping and Python index HTTP 200; Homebrew 7.0.13 installed |
| Browser installation | NOT RUN | Download host responds HTTP 400 at root; real browser download/install not verified |
| Validator dependency compatibility | NOT RUN | No pinned dependencies or approved runtime matrix; installed versions alone do not prove compatibility |
| Target repositories and CI permissions | NOT RUN | No target GitHub organization/repository supplied; original repository has no remote |
| Native provider discovery/hooks and login | NOT RUN | CLI version checks only; Phase 0.5 live integration tests remain unperformed |
| Contract completeness | FAIL | Referenced prior approvals absent; see decisions.md |
| Repository boundary | PASS | Workspace has no .git or product directories; original Git status clean |

Initial network/Docker probes failed under sandbox restrictions. Escalated read-only retries succeeded; preserve both attempts in phase-0-evidence.json. No credentials printed, no package installation, no browser launch, no model invocation, no repository creation.

## Commands and evidence

Machine-readable commands, outputs, exit codes and connectivity probes: phase-0-evidence.json. Python environment fixture used tempfile.TemporaryDirectory; it was removed automatically. Its commands use a temporary-path placeholder in the evidence.

- `git --version` — exit 0; checks
- `gh --version` — exit 0; checks
- `python3 --version` — exit 0; checks
- `python3 -m pip --version` — exit 0; checks
- `python3 -c 'import venv,ensurepip; print("venv available; bundled pip="+ensurepip.version())'` — exit 0; checks
- `node --version` — exit 0; checks
- `npm --version` — exit 0; checks
- `hurl --version` — exit None; checks
- `hurlfmt --version` — exit None; checks
- `docker --version` — exit 0; checks
- `docker compose version` — exit 0; checks
- `docker info --format '{{.ServerVersion}}'` — exit 1; checks
- `codex --version` — exit 0; checks
- `claude --version` — exit 0; checks
- `agy --version` — exit 0; checks
- `/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' /Applications/Antigravity.app/Contents/Info.plist` — exit 0; checks
- `/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' '/Applications/Google Chrome.app/Contents/Info.plist'` — exit 0; checks
- `gh api user --jq '{authenticated: (.login != null)}'` — exit 1; checks
- `git ls-remote https://github.com/github/gitignore.git HEAD` — exit 128; checks
- `npm ping --fetch-retries=0 --fetch-timeout=15000` — exit 1; checks
- `brew --version` — exit 0; checks
- `docker info --format '{{.ServerVersion}}'` — exit 0; retries
- `codex --version` — exit 0; retries
- `gh api user --jq '{authenticated: (.login != null)}'` — exit 0; retries
- `git ls-remote https://github.com/github/gitignore.git HEAD` — exit 0; retries
- `npm ping --fetch-retries=0 --fetch-timeout=15000` — exit 0; retries

Additional checks: `git remote -v`, `git status --porcelain=v1`, `ls -la /Users/camiloavila/Documents/qa-workspace`, `command -v gh git python3 node npm hurl hurlfmt docker codex claude antigravity agy`; filesystem inspection of installed applications and agy executable. HTTP probes used Python urllib HEAD requests to https://pypi.org/simple/ and https://cdn.playwright.dev/ without downloading artifacts.

## Blockers and next actions

Install/verify Hurl and hurlfmt before Step 1; choose compatible pinned validator dependencies during authorized preparation. Supply target GitHub organization/repository and intended cross-repository CI access model before permissions can be assessed. Supply complete original story/AC tags and prior approved contract details listed in decisions.md. Browser installation/automation remains a later-step check; host connectivity is not installation proof.

Executable controller, four skills, native settings/hooks, schemas, evaluations and all product repositories remain unbuilt. Phase 0.5 requires explicit authorization. Work stopped at Phase 0.
