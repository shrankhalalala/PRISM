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
