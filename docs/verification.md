# Phase 1 verification record

Verified 2026-09-12 on macOS with Python 3.12.

| Check | Result |
|---|---|
| Editable project installation | Passed in local .venv using available system packages |
| Unit and API acceptance checks | 19 passed (`python -m unittest discover -s tests -v`) |
| JavaScript syntax | Passed (`node --check prism/static/dashboard.js`) |
| Synthetic data regeneration | 336 hourly rows, seed 42; all accepted, no gaps or imputations |
| Synthetic topology | 12 nodes, 12 edges; 700 MW aggregate supply and demand |
| Live Neo4j seed | Passed against Neo4j 5.26 Community in an isolated Docker container |
| Repeated Neo4j seed | Second seed still returned 12 nodes and 12 edges; no duplicates |
| Desktop dashboard | API data displayed; node inspection and refresh worked |
| Mobile dashboard | 375px viewport checked; asset selector updates inspector; graph scroll stays inside panel |
| Mobile page overflow | Document scroll width equals client width (360px with browser scrollbar) |
| Planned modules | Forecast, learned dispatch, explanation and scenario routes return explicit HTTP 501 |

Neo4j image digest:
`sha256:22ec5cd05a8cbb372fc4bed5e384c30bc75fd92504c72be4462039761b105f61`.
The disposable integration database was removed after verification. The Docker
image remains cached. Use the documented Compose workflow for a persistent local
database; the dashboard currently reads validated JSON rather than Neo4j.

The first design evaluation passed with a mobile readability refinement. Final
mobile checking found and fixed intrinsic-width overflow. A stale development
server template was also resolved by restarting after the HTML change. Final
browser checks used the updated served template and styles.

Limitations: a fully isolated dependency download/install on another machine has
not been tested. The local .venv reuses installed packages; requirements-tested.txt
records those core versions. Browser failure/recovery was not exhaustively tested.
There is no real data ingestion, trained model, dynamic simulation, power-flow
solver, operational control, or measured research-performance claim in Phase 1.

## Dashboard interaction update

Added collapsible desktop navigation and a mobile drawer, stored theme/sidebar
preferences, asset-type highlighting, and demand/solar/wind charts for 24 or 168
hourly records. Verified JavaScript syntax, both API ranges, preference persistence
across reload, eight dimmed nodes for the Plants filter, 168 observations for the
7-day Solar chart, mobile drawer Escape dismissal, and no browser console errors.
The previous contribution section, PBL-II label, and foundation banner remain
removed. Theme/sidebar preferences are local to the browser. No real-time data was
introduced by this interface update.

## Phase 2 implementation checkpoint

Verified 2026-09-26 on the same local Python 3.12 environment.

| Check | Result |
|---|---|
| Full automated suite | 37 passed (`python -m unittest discover -s tests -v`) |
| Python compilation | Passed for `prism`, `scripts`, and `tests` |
| Scenario profile | Hourly-to-quarter-hour interpolation and input isolation passed |
| Simulator dynamics | Generator, battery, shedding, faults, disconnection, reset, and termination checks passed |
| Q-learning | Reproducible seeded training, action masking, update, and JSON round trip passed |
| Q-learning training command | Default 500 episodes completed and wrote a temporary Q-table |
| Forecasting | Persistence, autoregression, validation, MAE, and RMSE checks passed |
| Forecast evaluation command | Chronological 288-row train / 48-row test run completed |
| Phase 2 APIs | Forecast, scenario execution, validation, and retained 501 model guards passed |
| OpenAPI JSON | Parsed successfully after Phase 2 route update |

Temporary smoke artifacts were written outside the repository and are not treated
as approved models. The reported forecasting values are derived from the synthetic
fixture and are not journal results. The template phase label and inspector wording
were updated, while JavaScript behavior was unchanged. Interactive simulation
controls and a new browser verification pass remain pending.

## Phase 2 completion verification

Verified 2026-09-26 on macOS with Python 3.12.

| Check | Result |
|---|---|
| Synthetic data regeneration | 2,160 hourly rows; all accepted; zero gaps, rejections, or imputations |
| Forecast evaluation | 70/15/15 chronological split; three targets × three models; report and model checksums recorded |
| Q-learning evaluation | Five 500-episode seeds; validation-only selection; two paired held-out fault scenarios |
| Reviewed model loading | Three LSTM artifacts and seed-23 Q-table loaded and exercised through tests/API |
| Full automated suite | 42 passed (`python -m unittest discover -s tests -v`) |
| Python compilation | Passed for `prism`, `scripts`, and `tests` |
| JavaScript syntax | Passed (`node --check prism/static/dashboard.js`) |
| OpenAPI document | Parsed as valid JSON and served through `/api/openapi.json` |
| Forecast dashboard | Persistence, autoregression, and LSTM controls return and render results |
| Scenario dashboard | Baseline/Q-learning, fault scheduling, metrics, trajectory, and event log exercised |
| Responsive dashboard | Desktop and mobile layout, sidebar, theme, focus, containment, and console checked |

The final evidence is committed under `reports/`, `models/`, and
`data/scenarios/`. Q-learning underperforms the baseline on most held-out metrics;
the report preserves this negative result. Every learned action is marked
non-executable. Real-time ingestion, electrical power flow, XGBoost/SHAP, and
operational control remain outside Phase 2.
# Phase 3 live Grid Watch increment — 2026-10-22

- All 51 automated tests pass; `node --check prism/static/dashboard.js` and
  `git diff --check` pass.
- New tests cover field mapping, source timestamps, malformed/partial responses,
  finite measurements, per-process cache concurrency, retry throttling, stale
  records, timestamp regression, outage recovery, HTTP 503, and TLS verification.
- A live Flask test-client request to `/api/live/gridwatch` returned HTTP 200 with
  Delhi SLDC source time, demand, frequency, drawal, schedule, and freshness.
- The browser displayed the Delhi panel with live values and IST source time;
  its refresh control returned the latest cached snapshot. The preview viewport
  used the responsive narrow layout. Existing synthetic measurements still load.
- Public endpoint access was observed; a reuse licence, historical completeness,
  operational accuracy, and a service availability guarantee remain unverified.

## Phase 3 Step 3 source evidence — 2026-10-22

- The full automated suite passes 58 tests. New archive tests exercise untouched
  byte capture, verified TLS, HTML-as-PDF rejection, size/time failures, modified
  and missing files, catalog completeness, path boundaries and snapshot protection.
- The dated archive has 17 attempts, 14 captured originals, three explicit failures
  and 17 source-bound extraction locators. All eight required DTL captures passed.
- Offline verification checks catalog/source sets, file sizes, SHA-256 values,
  PDF signatures and locator fingerprints without external requests.
- Table counts were checked against captured HTML. BBMB physical page 86 and
  PPS-I physical pages 1-2 were visually inspected; the latter is scanned and
  requires further visual/OCR extraction. PDF page counts were inspected locally.
- Raw originals stay local and are ignored by Git. No runtime grid, measurement
  fixture, forecast/policy model, API behavior or dashboard was changed by Step 3.

## Phase 3 Step 4 node inventory — 2026-10-22

- All 67 tests pass. New checks cover typography versus identity, alias conflicts,
  Roman-suffix endpoint parsing, physical table-row positions, declared character
  encodings, evidence hashes, complete selected-source coverage, separated site
  identities and unverified operating parameters.
- All 47 directory rows and 258 endpoint occurrences from 129 circuit source rows
  are represented. All 46 transformation observations are retained, including
  the unassigned SOW row. Eight node-level issues remain explicitly open.
- `python -m scripts.build_delhi_node_inventory --check` regenerates matching
  JSON/CSV without writing. Archive integrity checks precede extraction.
- The 64 record IDs are not certified as 64 unique operating sites. The 50-node
  goal remains unverified; edge and completeness validation remain later gates.
- Runtime grid bytes, models, API and dashboard are unchanged by Step 4.
