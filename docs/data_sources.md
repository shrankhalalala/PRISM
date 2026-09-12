# Source assessment — Phase 1

Assessment date: 2026-09-12. No external measurement dataset has been imported.
Source availability, terms, geography, timestamps, and completeness must be verified
before a production collector or model-training dataset is selected.

| Candidate | Intended use | Evidence / remaining checks |
|---|---|---|
| Delhi SLDC Grid Watch | Delhi demand and frequency | Proposed by Review-II: https://delhisldc.org/grid-watch/ . This audit has not confirmed an accessible historical export or sampling guarantee. Treat as unverified. |
| Ember | Historical electricity context | Official API documentation https://api.ember-energy.org/docs describes API-key access. Methodology https://files.ember-energy.org/public-downloads/ember_electricity_data_methodology.pdf discusses monthly/annual data. Verify dataset-specific resolution; do not assume hourly Delhi solar/wind history. |
| NITI Aayog ICED | Plant capacities and metadata | Official https://www.iced.niti.gov.in/energy/ lists power plant details and generation. Export availability, terms and field coverage remain to be checked. |
| CEA Power Maps | Reference topology | Official https://www.cea.nic.in/old/powermaps.html lists transmission maps. Requires manual validation/digitization, voltage and asset matching; map lines alone do not supply electrical impedances. |

Acceptance gate for real forecasting data: timestamped power observations with
known units and cadence, suitable geographic aggregation, permitted reuse,
provenance and coverage audit. For real topology: asset identifiers, verified
connectivity, ratings, and (before power-flow analysis) electrical parameters.
Until then, use the committed synthetic fixtures, clearly labeled in the UI.
