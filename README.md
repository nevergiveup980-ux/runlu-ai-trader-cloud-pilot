# RUNLU AI TRADER Cloud Pilot

Independent public offline demonstration. No paid services, market/AI APIs, broker or real trading. Does not modify RUNLU INVEST or the RUNLU production website.

Based exclusively on the supplied RUNLU_AI_TRADER_CLOUD_PILOT.zip. V5.7 snapshot preserved unchanged; this is not the V5.9 local application.

Workflow tests the cloud pilot and the V5.7 snapshot on Python 3.11, then generates and publishes only cloud_site/ to GitHub Pages. It runs on main pushes, manual dispatch, and weekdays at 15:15 UTC. Scheduled runs can be delayed or skipped; this is not a continuously operating trading service.

Official actions are pinned. Standard ubuntu-latest runners only; no packages, caches, paid runners, API secrets, custom domain or external integration. Pages artifact retention is one day.

Public evidence: status.json contains an auditable report digest; deployment.json contains commit, workflow run URL and actual generation timestamp. See README_CLOUD_PILOT.md for inherited limitations. The uploaded prebuilt files are regenerated during deployment; they are not evidence of a cloud run.

Cost check: GitHub Free confirmed in account billing UI before setup; included compute $0.69/$12 used, Actions storage displayed 0/0.5 GB, billable Actions amount $0 at inspection. These are point-in-time observations, not a permanent cost guarantee. Public standard runner compute and Pages are free under GitHub rules. No billing settings were changed.
