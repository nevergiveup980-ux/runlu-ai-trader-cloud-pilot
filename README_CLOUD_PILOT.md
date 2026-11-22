# RUNLU AI TRADER · Cloud Pilot (zero paid services)

This is an **additive, offline-only demonstration** built alongside the complete V5.7 source snapshot. It is **not a merge of the later Codex V5.8/V5.9 changes** (those source files were unavailable). It makes **no investment decisions or orders**, and does **not** connect to a broker, an AI API, or a market data provider.

## Local preview

```sh
python3 cloud_pilot.py --output cloud_site
python3 -m http.server 8766 --directory cloud_site
```

Open `http://127.0.0.1:8766` on the Mac. The page has large type and works on narrow phone screens. This local URL does not work remotely.

## Optional GitHub Pages deployment

1. Create a **new public repository** for this demonstration only. Do not modify RUNLU INVEST or the main RUNLU website. Upload `cloud_pilot.py` and `.github/workflows/cloud-pilot.yml` keeping paths intact. The workflow does not require any secrets.
2. In repository Settings > Pages > Build and deployment, choose **GitHub Actions**.
3. Open Actions > RUNLU Cloud Pilot > Run workflow. Once deployment succeeds, use the Pages URL from the workflow or Settings > Pages on iPhone. Do not guess the URL.
4. The workflow also attempts to run on weekdays at 15:15 UTC; GitHub scheduled jobs can be delayed or skipped. **This is not reliable continuous operation**.
5. GitHub Pages is public. Do **not** upload account numbers, API keys, real positions, private logs, or trading controls. Real trading must never be enabled from this demo.

**Cost note:** This is designed to use free features within applicable GitHub plan limits. Check your account's current usage/terms before enabling; $0 is a goal, not a provider guarantee. No API subscriptions are provisioned.

## What is and isn't achieved

- Achieved: scheduled offline Python execution, static mobile dashboard, no fabricated price/transaction data, no real trading, auditable output hash.
- Not achieved: real market data, AI inference, strategy validation, brokerage, continuous 24/7 operation, authenticated private dashboard.
- Next gate: obtain V5.9 source and integrate without losing prior features; add legitimately sourced market data and a *separate* paper trading ledger with explicit simulated fills and costs. Do not present demonstration as autonomous AI trading.
