# Geographic asset map

The Network evidence view uses a local Leaflet 1.9.4 library and an OpenStreetMap
street basemap. This is a geographic presentation layer; backend reference records,
schematic simulation positions, connectivity algorithms and API schemas are unchanged.

`prism/static/delhi-asset-locations.json` contains 49 sourced WGS 84 site points:

- 41 from [OpenCity's Delhi station table](https://data.opencity.in/dataset/delhi-electricity-data/resource/e4a0101a-73f8-4fb2-92ef-783efe90bd97), based on DTL's station inventory. Public-domain licence; coordinate table updated 25 November 2025.
- 5 from the [Ministry of Power / GatiShakti substation extract](https://github.com/ramSeraph/indian_power_infra/releases/tag/power-stations), via DataMeet. CC0; record IDs and extract SHA-256 recorded in the JSON.
- 3 from the [ISRO VEDAS plant-location extract](https://github.com/ramSeraph/indian_power_infra/releases/tag/power-sources), via DataMeet. CC0; record IDs and extract SHA-256 recorded in the JSON.

Coordinates locate published station/site points, not surveyed individual busbars or
equipment. Connections join known endpoints; displayed segments do not claim actual
transmission-line routes or power flows. Asset selection preserves map zoom and pan.
The default view fits Delhi assets; Fit also includes located external interfaces.
All 66 assets and all 261 connection records remain accessible in the directories.
The 17 assets below have no matched location and are not assigned guessed coordinates:

- `plant-jhajjar` — Jhajjar (APCL) generation interface
- `ss-alwar-rvpn` — Alwar (RVPN interface)
- `ss-ballabhgarh-bbmb` — Ballabhgarh (BBMB 220 kV)
- `ss-budella` — Budella
- `ss-dadri-ntpc` — Dadri (NTPC switchyard interface)
- `ss-dadri-pgcil` — Dadri (PGCIL interface)
- `ss-dev-nagar` — Dev Nagar
- `ss-dwarka-sector-5` — Dwarka, Sec-05
- `ss-narela-bbmb` — Narela (BBMB)
- `ss-noida` — Noida (map endpoint)
- `ss-noida-62` — Noida 62 (map endpoint)
- `ss-panipat-bbmb` — Panipat (BBMB)
- `ss-ridge-valley` — Ridge Valley
- `ss-rohtak-road-bbmb` — Rohtak Road (BBMB)
- `ss-sgtn` — Sanjay Gandhi Transport Nagar
- `ss-south-of-wazirabad` — South of Wazirabad
- `ss-timarpur` — Timarpur

Street tiles require internet; bundled coordinates and selection continue to work if
tiles fail. The inspector shows the location source and precision. Original inventory
notes remain in the backend dataset but are omitted from the frontend as requested.

The background-job panel and its dependent queue controls are temporarily hidden.
No durable-job handlers or backend functionality were deleted. Headings are stronger
without changing the application navigation or overall layout.

## Application services

The canonical application is now the complete Docker stack at localhost:5050.
The earlier unconfigured standalone Flask preview and Docker web port 5053 are
retired. `make up` supplies PostgreSQL/Redis/Neo4j connections inside Docker; host
research scripts use the published service ports in `.env.example`.

The 17 assets listed above remain directory-only by user decision until coordinate
sources become available. No town-centre guesses or schematic fallback pins are used.
