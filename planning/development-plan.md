# Development roadmap — post-Step 4 checkpoint

Steps 1–4 are implemented with retained signed acceptance evidence. The approved SEED-1 feature/tag is immutable. Current authorization is the bounded maintenance checkpoint requested by “Implement the plan” and “Continue”; it does not authorize Step 5.

| Gate | Deliverable | Exit evidence |
|---|---|---|
| Maintenance | Shared controller consolidation, refreshed provenance and assumption register | Registered checks, regressions, independent distribution, scope audit; retain original baselines |
| 5 | GitHub Issues CLI in qa-features/tools | Default dry-run; authorized labelled sandbox comment in camiloavilacm/ai-qa-agent; repeat/update idempotency; no issue transition |
| 6 | Private five-repository central workflow and campaign aggregation | Six slots, same campaign ID, verified actual SUT images, explicit missing slots, one serialized report, deterministic execution |
| 7 | Immutable smoke release | Source/image/frontend/dependency/governance manifest, clean-machine 18 passes, rollback |

Each numbered step requires separate explicit authorization. Host the five planned repository names privately under camiloavilacm when publishing is authorized. Keep checkout and reporting credentials separate. A campaign rerun retains campaign_id, archives attempts and updates one comment; a partial rerun cannot silently reuse old results. Step 5 consumes campaign inputs; aggregation remains Step 6.

Feature and tooling references are independent. No approved tag movement, new business criteria, SUT changes, browser assertion changes, tracker scaffolding or CI/release implementation belongs to maintenance. Live Claude remains NOT RUN under the approved exception.
