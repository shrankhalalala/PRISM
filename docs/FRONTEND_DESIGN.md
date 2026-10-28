# Frontend structure and design

This describes the current frontend. Earlier restyle iterations are available in
Git history; they are not additional active layouts or verification claims.

## Application structure

Flask serves `prism/templates/index.html`, local CSS/fonts and native JavaScript.
There is no React/Tailwind migration or npm build. The complete application runs
through Docker at [localhost:5050](http://127.0.0.1:5050).

The existing continuous workspace is retained: Home, Network evidence, Demand
outlook, then Research. Research has Simulation, Policy review, Alarm investigation,
and Models/history tabs. Original forms, backend contracts, source metadata,
authorization and polling behavior remain.

Public Sans Regular/Medium/SemiBold are self-hosted with their bundled licence.
Dark/light themes share component geometry. Headings use stronger weight and clear
size differences; measurements use tabular numerals. Teal emphasizes data/selection;
warning and error colours describe source/service states. Service availability
never certifies electrical-grid health. Motion is confined to control/selection
feedback and the existing Home brand animation, with reduced-motion fallbacks.

## Geographic Network evidence

`reference-grid.js` uses vendored Leaflet 1.9.4 with OpenStreetMap street tiles.
The location overlay `delhi-asset-locations.json` matches 49 reference assets to
published WGS 84 site points. Seventeen unmatched assets remain in the directory,
without guessed pins. Their coordinates can be added later with source references.
See [geographic map provenance](GEOGRAPHIC_MAP.md).

Zoom, pointer/keyboard pan, fit, filtering, asset/connection selection and the
existing evidence inspector remain. Selection does not reset the viewport. Counts
identify actually located assets/mapped connections; full inventory totals remain
separate. Location source and precision are inspectable. All 66 assets and 261
connection records remain accessible even when an endpoint cannot be plotted.

Map segments connect recorded endpoints; they are not surveyed transmission-line
routes or power flow. The connectivity simulator retains the backend schematic
layout and its original algorithms; geography is a separate presentation overlay.

The global station-mapping summary, original inventory notes dropdown and its
boundary/telephone note are omitted from the frontend. Station source times and
quality flags remain visible in the inspector. Original notes remain in the
reference dataset. The background-job panel and dependent queue controls are
hidden for now; their backend handlers remain implemented.

## Module responsibilities

| File | Responsibility |
|---|---|
| `dashboard.js` | Existing navigation/theme, published readings, synthetic history/forecasts/scenarios |
| `reference-grid.js` | Geographic map, filters, directories, selection, station evidence |
| `topology-simulation.js` | Backend connectivity stream, disruption controls, Run/Stop, step results |
| `operations.js` | Services/alerts, real demand forecast, advisory/review, investigation and retained job handlers |
| `landing.js` | Visibility-aware Home brand loop |
| `dashboard.css` | Shared theme, headings, layouts, controls, data and responsive states |

Local map coordinates and the library load without an external API key. Street
tiles require internet; tile errors leave the geographic asset layer usable.
The frontend does not calculate model results or replace failed APIs with mock data.

## Verification

The 26 October 2026 map pass ran 121 unit/API tests and 15 browser assertions,
including real tile loading, map selection, zoom/pan, filtering/reset, unlocated
assets, requested removals, zero JavaScript exceptions, and no page overflow at
1440/768/390 px. These are point-in-time software checks, not field validation.
Current infrastructure/port checks are recorded in [verification.md](verification.md).
