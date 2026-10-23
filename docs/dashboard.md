# Interactive dashboard

## Current grid view

The website opens on the Delhi source-referenced grid (`#reference-grid`). Legacy
`#overview` bookmarks redirect there, including later hash changes. The abstract teaching grid is no longer a
website view, and graph investigation uses Delhi reference connectivity only.
Synthetic measurements, forecasts, and scenarios remain explicitly labeled research
labs; scenario fault choices still load the simulation fixture through `/api/grid`.


The Flask `/` page serves a responsive operator workspace without external assets or a frontend build step. Start the application using the root README and visit `http://localhost:5050`.

## Navigation and appearance

- The topbar navigation toggle remains available when the sidebar is collapsed. Desktop collapse persists in local storage. On mobile, navigation becomes a drawer that closes using the toggle, Escape, the backdrop, or a navigation link. Hidden navigation is inert and removed from keyboard navigation.
- The light/dark button persists an explicit theme preference. Without a saved preference, the page follows the operating system and subsequent OS theme changes. Storage errors do not prevent use.
- Motion is restrained and disabled when reduced motion is requested.

## Delhi grid exploration

- The default grid loads `/api/reference-grid`, with dated source evidence and
  separate mapped station readings. The 66 asset identities and 261 connection
  evidence records remain individually inspectable.
- Filter the asset and connection directories, select a record, and inspect its
  source evidence. Pan/zoom the schematic or use keyboard controls and native
  selectors. Reference connectivity does not establish current switching or flow.
- Reload reference retries the inventory independently. Synthetic lab refresh and
  fault-injection asset loading do not depend on a grid overview being present.

## Measurement exploration

- Demand, Solar, and Wind controls redraw an SVG chart from actual API records.
- The 24 hours and 7 days controls request `/api/measurements?limit=24` and `?limit=168`. Controls indicate the successfully loaded range. Loading and failures are announced; failures preserve the previous chart.
- Chart axes and captions explicitly use UTC. The caption includes observation count, time span, and peak. Hovering a point reveals its timestamp and value.
- The expandable measurement table provides every loaded observation with all three measurement series, frequency, and quality flags. The table and mobile chart scroll inside their panels.

All observations in the measurement lab remain explicitly synthetic. The interface contains no fake live stream, randomized metrics, electrical-flow animation, or claims of trained dispatch. Contribution sections and the foundation-mode banner remain removed.

## Verification checklist

1. Toggle the sidebar and reload on desktop; verify persistence. At mobile width, verify Escape/backdrop close and hidden links are not focusable.
2. Change theme and reload; verify persistence and sufficient contrast in both themes.
3. Filter Delhi reference assets and connections; verify the inspector shows the selected identity and source evidence.
4. Switch Demand/Solar/Wind and 24 hours/7 days; compare values and record counts with the corresponding API response.
5. Expand the table, then check a 375px viewport for page overflow.
6. Block a measurement request and change range; verify the visible failure message and retained chart. Unblock and Refresh measurements to recover.

## Phase 2 completion

The Forecast Lab selects demand, solar, or wind; persistence, autoregression, or
LSTM; and a one-to-24-hour horizon. It renders an SVG result chart and a complete
numeric prediction list, with loading, validation, and failure announcements.

The Scenario Lab selects the rule baseline or reviewed Q-learning policy, one to
96 steps, and an optional node or line outage with start and duration. Results show
return, unserved and curtailed energy, synthetic cost, emissions, demand and
generation trajectories, actions, rewards, and active faults. Policy output remains
non-operational and the page states the aggregate simulator boundary.

Navigation follows the current hash across the Delhi grid, live readings, synthetic
research labs and Operations. Legacy Overview hashes redirect to the Delhi grid. Desktop and mobile layouts retain the collapsible sidebar,
theme preference, keyboard behavior, chart containment, and visible status states.
