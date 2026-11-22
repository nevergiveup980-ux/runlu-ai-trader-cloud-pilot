# RUNLU AI TRADER V0.9 — Corporate-action and FX safety foundation

Independent, **offline, paper-only** research prototype. RUNLU INVEST untouched.

## Added in V0.9
- `corporate_actions.py`: strictly validated split, gross cash dividend, and exact-date CAD/USD FX primitives using `Decimal`.
- Corporate-action event ledger ordering, symbol matching and duplicate protection.
- 12 additional synthetic-data unit tests in `test_v09.py`.

## Important limitations
These primitives are **not connected to the backtest execution or valuation**. They do not establish dividend entitlement, ex-date vs payment-date accounting, withholding tax, split-adjusted order prices, fractional-share cash-in-lieu, FX timing, or total-return benchmarks. No real CSU/VFV data or market-data license has been obtained. Do not interpret old backtests as split/dividend-aware. No broker connectivity or real trades.

Run `python -m unittest discover -p 'test*.py' -q` in this folder.

## V1.0 — Independent corporate-action accounting validation
- `portfolio_ledger.py` replays static buy-and-hold positions against **raw** daily closes.
- Applies split share changes on ex-date, records dividend entitlement on ex-date, credits gross cash on pay-date, and marks positions to account currency using exact-date FX.
- Explicitly rejects fractional shares without a settlement policy, missing event calendar dates, duplicate FX, and adjusted close inputs.
- Nine additional synthetic tests in `test_v10.py`.
- **NOT integrated into `open_backtest.py` or `trader.py`.** Not a multi-asset trading system, tax engine, or real market-data validation. No actual historical CSU/VFV data imported.

## V1.1 — Experimental corporate-action paper backtest adapter
- `action_backtest.py` adds CAD-only gross dividend entitlement/payment and whole-share split accounting to an offline next-open simulation.
- Split days trigger a conservative 30-session entry blackout because the scanner is not split-adjusted. No FX integration, tax, dividend reinvestment, or fractional-share settlement.
- `test_v11.py` adds seven synthetic tests; full suite: 94 tests passing.
- This adapter is experimental and NOT used by the existing `open_backtest.py` / `holdout_open.py` flows. It does not establish realistic historical returns. A split occurring during an existing position can still affect stop/risk valuation mechanics; independently validate before research use.
- No real market data, broker connections, GitHub changes or live trading.

## V1.2 — Offline market-data intake audit
- `data_quality.py` adds a CLI and JSON audit report with provider metadata and SHA-256 fingerprint.
- Flags zero volume, weekend dates, long calendar gaps and large overnight price changes. Findings require manual review; **no auto split adjustments**.
- CSV files must be supplied by the user from a source they are licensed to use. This version does not fetch or validate real market data or exchange holidays.
- Run `python -m unittest discover -p "test*.py" -q`.
- Example: `python data_quality.py prices.csv --symbol CSU --exchange TSX --currency CAD --provider YOUR_PROVIDER --retrieved-on 2026-11-04 --license-note "Your authorized data usage" --output audit.json --strict`
- `--strict` exits with code 2 if any warnings need review. No broker access, deployment or GitHub changes.

## V1.3 — Static offline research dashboard
- `research_dashboard.py` converts existing V0.8-schema research JSON and V1.2 audit JSON into a self-contained read-only HTML report.
- Checks that symbol, exchange, currency and input SHA-256 agree; refuses unverified audit fingerprints. Displays structural warnings prominently.
- Training/holdout metrics, equity curve and known limitations. Escapes untrusted source labels. No external JavaScript, network access or trade execution.
- Generate with: `python research_dashboard.py research.json audit.json dashboard.html`
- Does **not** fetch historical CSU/VFV prices or establish valid strategy performance. No broker connection.

## V1.4 — Offline benchmark comparison
- `benchmark.py` compares **two supplied, same-calendar, same-currency equity curves** after normalizing both to 1.0 at inception.
- Outputs strategy return, benchmark return, excess return in percentage points, each maximum drawdown, and aligned normalized curve JSON.
- Refuses mismatched dates, nonfinite/zero equity, and missing provenance/adjustment policy. No automatic filling or fetching.
- Nine new synthetic-data tests in `test_v14.py`.
- This is **not** yet a real CSU/VFV benchmark, and does not establish correct dividend, split, FX or tax accounting. No real data was downloaded.
- CLI: `python benchmark.py input.json comparison.json` where input JSON has `strategy` and `benchmark` arrays of `{ "date": "YYYY-MM-DD", "equity": 123.45 }`, plus `provenance` keys `strategy_source`, `benchmark_source`, `currency`, `adjustment_policy`.

## V1.5 — Offline benchmark visualization
- `comparison_dashboard.py` generates a self-contained, read-only HTML visualization of two supplied same-date, same-currency equity series.
- Reuses V1.4 `benchmark.compare` validation and recomputes metrics from supplied observations. HTML-escapes labels; uses inline SVG without network or JavaScript.
- CLI: `python comparison_dashboard.py input.json comparison.html` (same input schema as `benchmark.py`).
- No new market data, no verified return results, no trading, no deployment, and no RUNLU INVEST changes.

## V1.6 — CSU/VFV two-file intake gate
- `intake_bundle.py` accepts a user-created JSON manifest with **exactly CSU and VFV**, each TSX/CAD, relative CSV path, pinned lowercase SHA-256, provider, retrieval date and license note.
- Rejects tampering, unsafe file paths, invalid OHLCV, missing overlap, unsupported currencies and incomplete manifests. Flags large price moves and calendar discrepancies; blocks review-needed bundles by default.
- `--allow-review` permits writing a review-status report, **not** research approval. `research_approved` is always false: neither data authenticity nor corporate actions are externally verified.
- Run `python -m unittest discover -p 'test*.py' -q`; CLI: `python intake_bundle.py manifest.json --output intake_report.json`.
- No market data was obtained. No real performance results, broker integration, deployment or RUNLU INVEST changes.

## V1.7 — Offline reproducibility lock
- `research_gate.py` creates and verifies a lock tying a V1.6 manifest to exact CSV bytes and a recomputed data-quality audit.
- Refuses audit warnings, missing/placeholder source metadata and input overwrite. Changes to CSV, manifest, audit results or lock metadata fail verification.
- Usage: `python research_gate.py create manifest.json lock.json`; later `python research_gate.py verify manifest.json lock.json`.
- **Lock is not a trusted signature**: anyone able to rewrite both files can create a new lock. Source authenticity, rights, corporate actions, FX, benchmark methodology and strategy returns remain unverified.
- Eight new synthetic tests. No real market data, orders, broker connection, deployment or RUNLU INVEST changes.

## V1.8 — Corporate action evidence review (offline)
- `action_evidence.py` reviews a user-supplied CSU/VFV split/dividend evidence JSON linked to the exact V1.6 manifest and verified V1.7 lock.
- Requires `raw_unadjusted` price policy; checks ex/pay dates, CAD denomination, positive amounts, split ratios, duplicates and coverage declarations.
- Empty event lists and out-of-range events are flagged. **Status is always REVIEW_REQUIRED and research_approved is always false**: user-provided evidence is not independently authenticated, and event completeness cannot be inferred.
- Example: `python action_evidence.py manifest.json lock.json events.json --output event_review.json`.
- Nine additional synthetic tests. No real market data, strategy returns, trading, deployment or RUNLU INVEST changes.

## V1.9 — Offline two-source corporate-action reconciliation
- `evidence_reconcile.py` compares two separately supplied V1.8 evidence files against the same locked manifest.
- Detects missing events, split-ratio and dividend conflicts, declared source duplication, and unverified empty histories.
- Equivalent split ratios are compared mathematically.
- Agreement **never approves** research or proves independent origin; source labels are user-declared.
- CLI: `python evidence_reconcile.py manifest.json lock.json source_a.json source_b.json --output reconciliation.json`
- All input data must be obtained lawfully; no automatic fetching, live trading or RUNLU INVEST changes.

## V2.0: end-to-end offline research readiness (new)

`research_readiness.py` composes the existing intake, reproducibility-lock and
independent corporate-action evidence reconciliation checks into one **fail-closed**
readiness JSON. Run only after preparing the four real input files:

```bash
python research_readiness.py manifest.json lock.json issuer_evidence.json second_evidence.json --output readiness.json
python -m unittest discover -p 'test*.py' -q
```

`READY_FOR_MANUAL_SOURCE_REVIEW` is **not** approval to trade, nor proof of
provider authenticity, license rights or historical returns. Discrepancies cause
`BLOCKED` (exit code 2); invalid input or lock causes an exception and no report.
No sample or synthetic results are presented as real historical performance.
The package is completely offline and has no broker connection. RUNLU INVEST
is a separate project and is not modified.

## V2.1 — Fixed chronological experiment calendar

- `experiment_plan.py` adds an offline CSU/VFV common-session training/holdout partition.
- Revalidates the V1.6 manifest and V1.7 reproducibility lock; requires zero unresolved intake warnings.
- Requires a user-chosen training end, holdout start, minimum observation counts, and a minimum excluded-session embargo. Never forward-fills missing sessions.
- The resulting JSON includes locked input SHA-256 fingerprints and the exact observation counts and date boundaries.
- This is **only a calendar plan**; it does not perform a backtest, prevent all look-ahead bias, authenticate data providers, or calculate investment returns.
- Example after preparing a valid manifest and lock:
  `python experiment_plan.py manifest.json lock.json --train-end 2024-12-31 --test-start 2025-01-09 --output experiment.json`
- Tests in `test_v21.py` use synthetic data and mocked intake/lock verification. Run `python -m unittest discover -p 'test*.py' -q`.
- No real market data imported, no broker access, and RUNLU INVEST remains untouched.

## V2.2 — Offline transaction cost estimator

- `execution_costs.py` models fixed/per-share/minimum commissions, half-spread and per-side slippage for **whole-share CAD** paper fills. It reports estimated round-trip drag and net P&L, with decimal arithmetic and CAD-cent cash rounding.
- Default assumptions are **illustrative**, not a claim about a broker’s actual fee schedule or market liquidity.
- Not integrated into `action_backtest.py` or the live/paper execution engine; it does not constitute a cost-adjusted historical strategy result.
- No real CSU/VFV data, broker connection, deployment or RUNLU INVEST changes.
- Run `python -m unittest discover -p 'test*.py' -q`.

## V2.3 — Cost-aware offline strategy replay

- `cost_backtest.py` uses previous-session close-based scanner signals and next-session open fills, tracking gross and net cash on **identical simulated orders**.
- V2.2 `CostPolicy` is applied to each paper buy/sell, including final liquidation; capital sizing includes estimated transaction costs.
- `test_v23.py` adds ten synthetic unit tests. This is a separate experimental engine, **not** a replacement for `open_backtest.py` or `holdout_open.py`.
- **Limitations:** CAD-only; no splits/dividends, FX, tax, partial fills, broker quotes, intraday risk exits or verified CSU/VFV history. It does not claim valid holdout results. Gross-versus-net curves use the same positions but do not represent a separate no-cost optimized strategy.
- Run `python -m unittest discover -p 'test*.py' -q`. RUNLU INVEST untouched.

## V2.4: experimental pinned-data holdout cost replay

`holdout_cost_replay.py` accepts the V1.6 manifest, V1.7 lock and V2.1 calendar plan:

```bash
python holdout_cost_replay.py manifest.json research.lock plan.json --output holdout_replay.json
```

It revalidates hashes, the data quality gate and the calendar plan, and runs
**separate** CSU and VFV CAD-only cost-aware replays. Signals can read prior
training/embargo history as observable context, but trading begins at the
holdout start. No real historical dataset is bundled. This is an experimental
research adapter, **not** an approved strategy or combined portfolio. It does
not account for splits, dividends, FX, tax, point-in-time fundamentals or
broker execution. Do not interpret outputs as real or investable returns.

## V2.5 — Fixed-capital CSU/VFV combined holdout (experimental)

`portfolio_holdout.py` reuses the pinned V2.4 replay twice with **actual sleeve capital**
(e.g., CAD 500 CSU / CAD 1,500 VFV), then combines only strictly aligned
CAD gross/net daily equity. This preserves per-sleeve fixed commissions instead
of incorrectly scaling a previously computed cost curve. Rejects mismatched
input identities, dates, invalid capital/weights, and unsafe approval flags.

This is a **fixed independent-sleeve** portfolio, not a shared-cash execution
engine. No rebalancing, transfers, split/dividend integration, FX, tax, verified
real data or live orders. No investment performance has been established.

Run: `python -m unittest discover -p 'test*.py' -q`.

## V2.6 — Dual USD research budgets + multi-role council skeleton
- `risk_budget.py`: **USD 2,000** research allocation: **USD 1,500 core**, **USD 500 experimental**. Reservations, spent-loss tracking, no inter-bucket transfers, hard budget checks, halt after depleted budget. Long options, leveraged ETFs, and fully cash-covered defined-risk spreads are only considered in experimental sleeve. No borrowed margin, naked short options or uncapped-loss positions. These software checks do not guarantee actual broker loss limits.
- `agent_council.py`: deterministic advisory roles Atlas, Scout, Quill, Pitch, Risk, Ledger and Auditor. Requires evidence and data checks before *paper research reservation*. **These are role labels and a review protocol, not seven working LLM agents**. No autonomous news gathering or real order execution.
- `test_v26.py`: 12 synthetic unit tests. No actual market data, broker connection, API keys, orders, or deployment.
- **IMPORTANT CURRENCY BOUNDARY:** V2.5 backtest uses **CAD** and CSU/VFV. V2.6 budget is **USD** and is intentionally **NOT connected to V2.5's CAD accounting** until FX, contract specifications, and collateral handling are validated. `human_approved` in advisory review is a synthetic input, not a live authorization mechanism. `live_trading_enabled` always false.

## V2.7 — Offline multi-role agent runtime
- `agent_runtime.py` runs seven named roles through an injected `provider(role, context, notes)` adapter, producing a deterministic SHA-256 audit record.
- The provider is **not an LLM connection**; it is an interface for future integration. All outputs are untrusted. Strict Pitch schema and source matching, role notes, and fail-closed invalid output handling are included.
- **All council runs remain BLOCKED for live trading**, even with verified flags: no broker, no live authorization, no orders. Human approval cannot be inferred from AI-generated text.
- `test_v27.py` adds nine synthetic tests. No real market feeds, options pricing, currency conversion, or real brokerage integration.

## V2.8 — Model-ready JSON research adapter (offline)
- `llm_adapter.py`: dependency-injected `JsonResearchAdapter(transport)` with fixed role instructions, bounded prior-note context, strict JSON responses, and transport failure handling. A caller may later supply an authorized model API transport; **none is bundled or invoked**.
- `test_v28.py`: ten synthetic tests, including invalid JSON, prompt-injection containment, unauthorized fields and transport errors.
- This is **not** seven connected AI agents: no API keys, model requests, market/news feeds, broker, or live execution. Prior agent notes are still untrusted data, and no prompt can guarantee model compliance; deterministic checks remain authoritative.
- The USD 1,500 core / USD 500 experimental allocation remains unchanged. CAD portfolio accounting is separate. RUNLU INVEST is untouched.

## V2.9 — Optional live LLM API transport, research-only

`model_transport.py` adds an optional HTTPS OpenAI chat-completions transport
for `JsonResearchAdapter` and `run_council`. It uses `RUNLU_LLM_API_KEY`
from the process environment; never put keys in source code, prompts, or logs.
The endpoint is restricted to `https://api.openai.com/v1/chat/completions`.
Model name defaults to `gpt-4.1-mini` and is configurable in Python.
No API request is made by importing this module or running the tests.

Example (will incur API charges and transmit research context if you run it):

```python
from model_transport import ChatCompletionsTransport
from llm_adapter import JsonResearchAdapter
from agent_runtime import ResearchContext, run_council
adapter = JsonResearchAdapter(ChatCompletionsTransport())
result = run_council(ResearchContext('CSU', 'a'*64, 'EXAMPLE-UNVERIFIED'), adapter)
print(result['outcome'])  # BLOCKED unless data/evidence checks pass; NEVER submits orders
```

All tests use fake local responses, not a live model. No API key was provided,
no real AI model request has been performed, and no real market/news data or
brokerage connection is included. The LLM is not a reliable source of market
facts. Deterministic risk controls retain the final veto. USD 1500/500 budgets
remain separate from CAD backtests. RUNLU INVEST remains untouched.

## V3.0 — Local Research Control Center

`research_control.py` creates a **standalone offline HTML dashboard** and JSON audit showing seven role reviews, USD 1,500/500 research budgets and a blocked research-only outcome.

Run from the project directory:

```bash
python research_control.py --symbol CSU --output research_output
python -m unittest discover -p 'test*.py' -q
```

Open `research_output/dashboard.html` in a browser. The default provider is a **deterministic synthetic demonstration**, not AI analysis. The HTML is static and escapes role text. To invoke a paid OpenAI-compatible model, explicitly pass `--live-model` and set `RUNLU_LLM_API_KEY` in your environment; no API key is bundled and no live call was tested. Never treat model output as verified facts.

No market data, news, FX, options pricing, broker, live orders or execution authorization. RUNLU INVEST remains independent and unchanged.

## V3.1 — Browser-based offline research UI

Run `python web_control.py --port 8765` from the project directory and visit `http://127.0.0.1:8765/`. Select CSU or VFV and click the button to see the **synthetic, BLOCKED** seven-role report. The web UI **never** calls a paid model or a broker; it has no live trading endpoint. It only binds to localhost, restricts input and rejects cross-origin POST requests with mismatched Origin. No real market data, prices or trading results. Use Ctrl+C to stop the server.

Tests: `python -m unittest discover -p 'test*.py' -q`. This is a local prototype, not a hardened internet-facing application. RUNLU INVEST is untouched.


## V3.2 — Local research history + explicitly charged one-shot model research

`python web_control.py --port 8765` remains OFFLINE ONLY. `/history` displays up to 20 in-memory audit digests, statuses and symbols; no model transcript is stored there. History clears on restart.

For optional paid AI research (never broker trading), explicitly set `RUNLU_LLM_API_KEY` and run:

`python model_research_once.py --symbol CSU --confirm-charges I_ACCEPT_MODEL_API_CHARGES`

This may make **multiple chargeable model calls** per run; there is no automatic retry and no promised fee ceiling. The research still uses UNVERIFIED market evidence and returns BLOCKED, not investment authorization. The model endpoint is restricted to the configured HTTPS provider. Never put secrets in command arguments, version control or shared files.

Run tests: `python -m unittest discover -p 'test*.py' -q`. No live broker or order routing is implemented.

## V3.3 — Offline market/FX provenance and freshness gate

`market_intake.py` accepts **user-supplied** CSV snapshots (no internet connection, no market-data vendor, no automatic fetching). It requires timezone-aware quote and USD/CAD timestamps no older than 24 hours, positive finite prices/rates, strict CSV schemas, and records source labels and SHA-256 byte fingerprints. It computes **indicative** CAD equivalents of the USD 1,500 core and USD 500 experimental allocations. This does not convert or merge any existing CAD backtest account balances.

Example CSV files (illustrative values only, **not live prices**):

`market.csv`:
```
symbol,currency,timestamp,price,source
CSU,CAD,2026-11-05T19:00:00Z,2500.25,USER SAMPLE
```

`fx.csv`:
```
pair,timestamp,cad_per_usd,source
USD/CAD,2026-11-05T19:05:00Z,1.36,USER SAMPLE
```

Run: `python market_intake.py market.csv fx.csv --output market_intake_report.json` (use actual timestamps within the last 24 hours). The resulting JSON **always** marks `source_authenticated=false`, `market_data_verified=false`, `independent_evidence=false`, and `trading_authorized=false`. A plausible timestamp and file hash **cannot** establish vendor authenticity, independent evidence, executable quotes, or accurate prices. There is deliberately **no integration that sets `ResearchContext.market_data_verified=True`** from these user-supplied files. The existing local research UI remains synthetic; no broker, live order routing, or paid market data access has been added. RUNLU INVEST remains untouched.


## V3.4 — Offline two-source quote comparison and TSX session hint

`market_crosscheck.py` compares two **user-provided** CSU/VFV CAD quote records with different claimed source labels and SHA-256 evidence digests. It checks timestamp proximity, staleness and price deviation; reports `AGREE_UNAUTHENTICATED` or `DISAGREE_BLOCKED`. A Toronto-local weekday/regular-hours hint is included, **not** an exchange holiday/halts calendar. Even agreeing feeds remain **unverified**: source names and digests are self-reported. No live provider, auto-refresh, verified provenance, broker or live trading. This module is not connected to automatic trade authorization.

## V3.5 — Fail-closed exchange session calendar gate

- `session_gate.py` requires an explicit, exact-date TSX calendar declaration before marking a timestamp as a **possible** regular session.
- Unknown dates, declared holidays/closures, weekends, stale/future quotes, and out-of-hours timestamps fail closed.
- Uses `America/Toronto` timezone and handles DST via Python's timezone database.
- Calendar entries and sources are **caller-provided and unauthenticated**. A `POSSIBLE_SESSION_UNVERIFIED` result is never an approval to trade; halts, special sessions, live status, and source identity are not checked.
- `test_v35.py` adds 12 offline tests. No real market-data provider or broker is connected.

## V3.6 — Opt-in HTTPS quote provider adapter
- `quote_provider.py`: injectable HTTPS GET transport with environment-based API key, strict response schema, timestamp/currency checks, response-size cap, and SHA-256 provenance of bytes.
- Set `RUNLU_QUOTE_API_KEY` only when you have a licensed provider and a matching JSON endpoint; provider must return `{symbol,currency,price,timestamp}`. This is a **generic integration contract**, not a confirmed plug-and-play vendor integration.
- No provider account configured, no live market data fetched, and no claims of real-time pricing or exchange authenticity. Source flags remain false and trading stays blocked.
- Run `python -m unittest discover -p 'test*.py' -q`.

## V3.7 — Two-provider acquisition and review gate
- `provider_pair.py` orchestrates two independently configured **generic V3.6 JSON-contract** HTTPS feeds, with distinct provider names, hosts and credential environment variables.
- Validates and cross-checks prices, timestamps, CAD currency and source-response SHA-256; agreement yields `REVIEW_REQUIRED`, disagreement or failure yields `BLOCKED`.
- Never upgrades `market_data_verified`, `independent_evidence_verified`, or `trading_authorized`. No broker, real quotes, provider subscriptions, or authenticated TSX feeds were tested. Different hosts alone do not prove independent underlying data.
- Tests use mocked transports and synthetic prices. The existing browser UI remains offline/synthetic.
- This is **not** a turnkey integration with a named vendor. Before real data use, select two licensed TSX-capable vendors, confirm their actual API schemas, exchange delays and terms, and implement vendor-specific adapters.

## V3.8 — Canadian listing chart adapter (experimental)

`yahoo_chart_adapter.py` maps CSU -> CSU.TO and VFV -> VFV.TO, and parses
Yahoo Finance's **unofficial** chart JSON format. This is NOT a contracted
market-data feed; availability, exchange metadata, price delays, and terms of
use must be checked independently. A valid response remains
`RESEARCH_ONLY_UNVERIFIED`; it never unlocks trading or asserts provenance.

Network access is **off by default**. For an explicitly authorized one-time
research request only:

```python
from yahoo_chart_adapter import fetch_chart
quote = fetch_chart('CSU', allow_network=True)
print(quote)
```

No API credentials or broker are configured. The adapter does not assert
real-time pricing and is not integrated into live trading. `test_v38.py` uses
synthetic JSON fixtures, not external network calls. Prices can be up to seven
days old for weekend/holiday research; this is NOT acceptable for live order
execution. Before operational use, obtain a licensed Canadian-market feed,
verify vendor terms, data latency, TSX holidays, corporate actions and FX.

## V3.9 — Quote-provider diagnostic report (research-only)

- New `provider_diagnostics.py` runs a structured check for CSU.TO and VFV.TO via the experimental V3.8 adapter. It emits timestamped JSON, per-symbol status and SHA-256 response/report fingerprints.
- **Offline by default**: `python provider_diagnostics.py` returns blocked observations and exit status 2. `--allow-network` explicitly opts in to an unofficial Yahoo Finance request, which may fail or be disallowed by terms; it is not a licensed or independently verified feed.
- Example: `python provider_diagnostics.py --symbol CSU --allow-network --output diagnostics.json` (only after reviewing the provider's terms and deciding to make a request).
- A successful request is always `RESEARCH_ONLY_UNVERIFIED`. All reports have `market_data_verified=false`, `licensed_source_confirmed=false`, `trading_authorized=false`.
- V3.9 tests use mocked network responses; **no live quote provider has been verified**. A production feed requires explicit vendor licensing, credentials, delay disclosure, TSX trading calendar, FX and corporate-action reconciliation.

## V4.0 — Vendor entitlement readiness (offline)

`vendor_readiness.py` defines a two-vendor evidence checklist for TSX coverage, HTTPS documentation, contract terms, automated use, redistribution, disclosed latency, CAD denomination and underlying feed independence. The outcome is BLOCKED or MANUAL_DUE_DILIGENCE_REQUIRED, **never VERIFIED or trade-authorized**. Claims in a VendorRecord are user-supplied and cannot establish license rights. No provider accounts, live requests, broker access or real-money trades are included.

Run `python -m unittest discover -p "test*.py" -q`.

## V4.1 — Offline vendor shortlist and evidence gap report

Use `vendor_shortlist_template.csv` to record *unverified* vendor candidates. Do not treat the sample placeholder names as real vendors. Enter documented URLs and verified terms manually; unknowns should be left blank. Run `python vendor_shortlist.py vendor_shortlist_template.csv --output vendor_report.json`. The report identifies missing TSX/CSU.TO/VFV.TO coverage evidence, license/automated use, price and latency, and shared underlying feeds. **Even complete self-reported checklists remain MANUAL_REVIEW_REQUIRED**; never trade-authorized. No live API, vendor contract, entitlement, or quote verification was performed.

## V4.2 — Human-reviewed vendor evidence register (offline)

`vendor_evidence.py` records timestamped vendor source links, reviewer names and short evidence excerpts for eight diligence categories. It flags evidence older than 90 days and missing categories, hashes excerpts and emits a reproducible audit JSON. Run `python vendor_evidence.py vendor_evidence_template.json --output vendor_evidence_report.json` after replacing all placeholders. No HTTP requests, live vendor subscriptions, contracts or independent verification are performed. Even a complete checklist **never** verifies licenses or unlocks trading. Candidate names, actual fees and exchange rights must be researched and confirmed separately.

## V4.3 — Real vendor candidate research (public-doc claims only)

`vendor_candidates.py` records EODHD and Twelve Data as *unverified* candidates with official source URLs, reference pricing where available, feed differences, and explicit due-diligence gaps. Run `python vendor_candidates.py` to create `vendor_candidates_report.json`. No external quote APIs or subscriptions have been tested. EODHD's listed USD 19.99/month is a publicly advertised EOD reference price, not a verified checkout quote. Twelve Data XTSE EOD is distinct from its Cboe Canada NEO-L real-time add-on; these are not automatically interchangeable or independent consolidated TSX feeds. Public docs do not prove individual-symbol access, API license, or trading eligibility. All decisions remain manual review and trading disabled.

## V4.4 — EODHD historical daily-bar research adapter (offline-first)

`eodhd_history.py` adds a strict, opt-in EODHD historical daily-bar adapter for CSU.TO and VFV.TO. It validates date ordering, OHLC consistency, adjusted-close and volume, records a SHA-256 bar digest, and always marks the result `RESEARCH_ONLY_UNVERIFIED`, with `market_data_verified=false` and `trading_authorized=false`. No brokerage or execution functions are added.

- Offline fixture: `python eodhd_history.py --symbol CSU --fixture path/to/eodhd_response.json --output research.json`
- Optional API test (requires an EODHD account token and review of vendor terms): set `EODHD_API_TOKEN` in the environment, then run `python eodhd_history.py --symbol CSU --allow-network --output research.json`. **Do not put tokens in code or command-line flags.** The free account is advertised as 20 calls/day and about one year of EOD history; the public `demo` token does not cover Canadian tickers. CSU.TO/VFV.TO access, exchange mapping, quote currency, entitlement and actual API success must be independently verified. Do not buy a plan until confirmed.
- No network access occurs in the tests. Mocked HTTP is not evidence of a successful vendor request. These are *historical bars*, not a real-time feed; do not apply the intraday 24-hour freshness gate to older history or use them to approve orders.
- Vendor docs: https://eodhd.com/financial-apis/api-for-historical-data-and-volumes ; https://eodhd.com/help/plans ; https://eodhd.com/financial-apis/our-data-sources-and-data-partners

## V4.5 — EODHD 历史价格的离线样本分区与完整性检查

新增 `historical_validation.py`，从 V4.4 的 `eodhd_history.py` 生成的 JSON 报告读取数据，核对股票身份、SHA-256、时间顺序、价格有效性；将调整后收盘价分为前70%研究区和后30%保留区，报告各自的**描述性**价格变化和最大回撤。使用方法：

```bash
python historical_validation.py --report eodhd_history_report.json --output historical_validation_report.json
```

**限制：** 这不是可执行价格的策略回测。调整后收盘价不可直接当作实际成交价；未验证复权规则、拆股、股息、汇率、税费、交易成本、基准和真实数据授权；也未验证样本外交易策略的盈利能力。没有券商连接或下单权限。需要至少40条有效历史记录。所有外部数据仍需独立核验。

## V4.6 — Illustrative next-open strategy vs buy-and-hold (offline)

`strategy_benchmark.py` compares a fixed 5-day close momentum long/flat signal (using only prior-day information) against a buy-and-hold baseline. Both use unadjusted next-session opens, fixed illustrative CAD fees and slippage, and independent chronological training/holdout segments. No parameters are tuned on holdout.

Run `python strategy_benchmark.py --report eodhd_history_report.json --output strategy_benchmark_report.json`. **This is not a validated tradable backtest:** splits, dividends, FX, taxes, dynamic spreads and real broker execution are not modeled; last-day liquidation uses an illustrative close. Only a single share is traded, and no actual EODHD account data was accessed or tested. Returns cannot establish alpha or predict profit. No broker connection, live orders, or RUNLU INVEST changes.


## V4.7 — Corporate-action anomaly gate (offline)

Added `corporate_action_gate.py` and `test_v47.py`. `strategy_benchmark.compare` now fails closed on suspicious adjusted/raw close ratio changes (>50 bps) or raw close jumps (>25%). It does **not** automatically adjust prices or certify dividend/split completeness. This is an intentionally conservative diagnostic: legitimate price moves may be blocked, and smaller dividend adjustments may escape detection. Independent corporate-action histories, transaction fees, CAD/USD and executable-price reconciliation are still required before interpreting returns. No broker, live trade or changes to RUNLU INVEST.

## V4.8 — Corporate-action evidence ledger (offline)
`action_event_ledger.py` accepts manually supplied split and cash-dividend event records with ex-date, symbol, amount, currency (for dividends), and HTTPS evidence URL. It validates structure, dates, positive amounts, duplicate events, and computes a deterministic SHA-256 audit digest. `reconcile_dates()` flags asserted ex-dates missing from the bar series. **No source URL is fetched, no evidence is independently verified, and no historical prices are repaired.** Output is always `MANUAL_EVIDENCE_REVIEW_REQUIRED`; trading authorization remains false. Use `python -m unittest discover -p 'test*.py' -q` to run tests.

## V4.9 — Corporate-action evidence reconciliation gate

`action_reconciliation.py` links the V4.8 event ledger to historical bar dates, detects
unmatched dates and malformed chronological input, and records deterministic SHA-256
provenance. `compare_with_events()` combines this diagnostic with the existing
illustrative strategy replay, but **never** labels it verified total return or
approves real orders. A user-provided `reviewed=True` is merely an assertion.
No independently verified corporate-action feed, dividend reinvestment, split
share accounting, or executable historical fills are implemented yet.
Run `python -m unittest discover -p 'test*.py' -q` for regression tests.


## V5.0 — Offline research readiness gate

`research_evidence_gate.py` combines integrity-checked history, asserted corporate-action event dates, and illustrative strategy replay into one **always-blocked** evidence checklist. It cannot verify provider identity, licenses, dividends, FX or real trading returns. Operator-supplied provenance is recorded but **never accepted as verification**. No broker, no orders, no network.

```bash
python research_evidence_gate.py --history eodhd_history_report.json --events corporate_actions.json --output readiness.json
```

Event file is a JSON array (may be empty; an empty array does **not** prove there were no corporate actions). If the history is invalid the CLI fails closed.


## V5.1 — Historical intake pipeline

`history_pipeline.py` ties offline EODHD-shaped daily-bar import to historical descriptive validation and optionally the existing corporate-action evidence gate. It **does not** authenticate the source, certify licensing, establish strategy alpha, or enable trades.

Offline: `python history_pipeline.py --symbol CSU --fixture daily_bars.json --output csu_intake.json`

Optional one-shot network request: set `EODHD_API_TOKEN` in your environment and run `python history_pipeline.py --symbol VFV --allow-network --output vfv_intake.json`. This may incur provider charges, and requires the user's own account and permission. No API call occurs by default.

Optional `--events corporate_actions.json` requires a JSON array. The program refuses to overwrite an existing output report. Historical adjusted-close statistics are descriptive only; no independently verified returns.


## V5.2 — Local read-only intake viewer

Start with `python web_control.py --report-dir ./reports` (create the directory first). Open `http://127.0.0.1:8765/intake`. The viewer accepts only same-directory regular `.json` files with safe names, a V5.1 pipeline SHA-256 match, and matching history digest references. It never uploads, edits, fetches, or trades. A hash match only checks local consistency, **not** provider authenticity, market-data rights, or profitability. The report directory must be trusted and local; never expose this service outside loopback.


## V5.3 — Read-only history quality diagnostics
`history_quality.inspect(history)` checks weekday gaps (including holidays), large raw-close moves (25% default), and adjusted/raw close ratio shifts (3% default). It does not identify splits or dividends, authenticate sources, or authorize trading. The local `/intake/view` page shows aggregate diagnostics. All calculations are offline.


## V5.4 — TSX holiday estimates and anomaly detail view
`tsx_calendar.py` estimates standard TSX holidays (not verified official calendar). The `/intake` report detail view now separates estimated holidays from unexplained weekdays and displays per-date raw-price/adjustment-ratio anomalies (first 50 per category). Neither calendar estimates nor diagnostic flags verify data or authorize trading. No network or broker connection.

## V5.5 — Offline exchange-schedule evidence comparison

`calendar_evidence.py` accepts a user-supplied CSV with exactly `date,status,source_url` columns. Status is `CLOSED` or `OPEN`; dates must be ISO weekdays and URLs must be HTTPS. `reconcile(gap_days, csv_text)` compares estimated TSX holiday classifications to the supplied schedule and flags open dates with missing bars. All entries remain **USER_SUPPLIED_SCHEDULE_UNVERIFIED**: the code does not fetch links, authenticate source documents, establish licensed data provenance, or authorize trading. No vendor API or broker is connected. `test_v55.py` exercises conservative behavior. Example CSV below is fictional, not official TSX data.


## V5.6 — Read-only calendar evidence in local UI
Place an optional `<report-stem>.calendar.csv` beside a `<report-stem>.json` inside `--report-dir` (example `csu_intake.json` + `csu_intake.calendar.csv`). Use the columns in `calendar_evidence_template.csv`: `date,status,source_url`. The `/intake/view?name=...` page now shows counts and up to 50 date-by-date source records, or a clear warning for invalid evidence. Source URLs are displayed as escaped text, never fetched or treated as verified. Symlinks and oversized CSVs are rejected. All trading stays BLOCKED.

## V5.7 — Source provenance receipts (offline)
`source_provenance.py` provides `file_receipt(path, symbol=..., source_label=..., captured_at=...)` and `verify(raw_bytes, receipt)`. Use a timezone-aware ISO 8601 capture time. Receipts record a SHA-256 hash of exact input bytes, byte count, a declared source label, and a deterministic receipt fingerprint. **This only detects local tampering; it does not authenticate the vendor, validate market-data licensing, confirm completeness or prove trading performance.** The receipt is a separate utility, not yet integrated into history_pipeline; EODHD network calls are not performed by this release. Do not put API tokens in source labels. Trading remains disabled.
