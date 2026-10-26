# Interactive dashboard

## Current workspace

The Flask `/` page opens Home (`#home`), followed by the complete Delhi reference
network, system-wide demand outlook and Research & review. These are regions of one
continuous workspace. Legacy `#overview` and `#live-grid` hashes lead to Home. The
abstract teaching grid remains absent from the website; graph investigation uses
Delhi reference connectivity only.

Research & review has accessible tabs for simulation, policy review, alarm
investigation and models/history, with shared worker activity alongside. `#scenario`
opens simulation; `#measurements` and `#forecast` open models/history. Nested policy
and investigation links open their corresponding panels. Tab changes preserve form
inputs, graph selection and results. Operator tokens remain memory-only.

Synthetic measurements, forecasts, and scenarios retain explicit research labels.
Scenario fault choices still load the teaching fixture through `/api/grid`; they
never inherit selected Delhi station identities. The real 24-hour demand forecast
loads once from `/api/forecast/real`, independently of the selected station, and keeps
its own origin, age and empirical uncertainty semantics.

## Navigation and appearance

- Each workspace destination is a separate hash-routed screen, with one active
  heading. Nested evidence and Operations links keep their existing destinations.
- The Framed sheet design uses self-hosted IBM Plex Sans, neutral light/dark
  surfaces, and compact controls. See FRONTEND_DESIGN.md for the design checks.
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

Navigation follows workspace anchors and research tabs. Legacy Overview hashes redirect to Home. Desktop and mobile layouts retain the collapsible sidebar,
theme preference, keyboard behavior, chart containment, and visible status states.

## Monitoring controls and performance

Collapsed desktop navigation retains labeled-accessible icon destinations. Scroll
position updates the current-region indicator without rewriting browser history.
The existing phone drawer still moves focus into navigation, contains Tab/Shift+Tab
and restores focus on Escape; closed visibility switches immediately.

Home distinguishes individual application services from SLDC source freshness.
Refresh controls remain busy/disabled until their actual requests finish. Previous
readings and forecast previews retain their original provenance while refreshing or
after a failed refresh; errors and retry controls remain visible.

The network fits currently filtered assets, with a larger responsive viewport and
adjacency emphasis. Arrow/pointer panning uses frame-coalesced view updates and
does not repeatedly remeasure labels. Zoom, selection and resize still arrange labels.
All 66 assets and 261 connection evidence records remain individually inspectable
when filters are reset. These are dated reference records, not verified conducting
lines or a geographic/physical-flow model.

## Current Data terminal layout

Home is the network workbench opening: a bare telemetry band leads directly into
the one Delhi network canvas, without a large overview card or duplicate preview.
Network navigation anchors that same DOM. Asset/evidence directories are accessible
through the disclosure under the canvas. The selected station inspector stays beside
the canvas on desktop and follows it on phones.

The header's Services & alerts disclosure retains every diagnostic field and source
note. Its closed summary includes actual service state and alert count. Navigation
is an icon rail on desktop and a four-destination bottom bar on phones; labels and
keyboard links remain available. Demand uses chart/context columns; Research uses
a vertical tool selector plus shared activity rail. Up/Down as well as Left/Right,
Home and End navigate research tools. Light and dark themes share this geometry.


## Home and Delhi connectivity scenarios

Home introduces PRISM (Power Grid Resilience through Intelligent Smart Management),
with direct links to the Delhi reference network and research workspace. Published
readings now sit with the reference network; metric IDs and refresh behavior remain
unchanged. Light and dark themes use restrained blue/teal page gradients while
charts, controls and evidence surfaces remain flat.

The animated PRISM mark uses the actual dependency-free transitions-ui-generation runtime
(vendored with its license under `prism/static/vendor/prism-generation/`). It loops while visible, with one runtime instance and a three-second pause after each full reveal. Font
readiness precedes measurement; resize, hidden documents and offscreen navigation
cancel and clean up the reveal. Reduced-motion users see the static brand. The
animation never blocks navigation, source refreshes or application readiness.

Research → Simulation now opens a Delhi **connectivity** scenario. Outage choices
come from `/api/reference-grid`; the graph is rebuilt from the authoritative assets,
layouts and connections in the backend stream's start event. Run consumes paced
NDJSON snapshots from `/api/topology-scenario/stream`, updates availability colors,
component/isolation counts and a step log, and retains the last received state on
errors or Stop. An interrupted stream cannot be reported as completed. Each model
step represents 15 minutes; the separately selected 100–1000 ms backend interval is
wall-clock pacing. Baseline islands are included in isolation totals; the step log
also reports newly isolated assets beyond the baseline. This is topology research,
not verified Delhi electrical power flow, dispatch or physical equipment operation.

The former aggregate/Q-learning tools retain their original forms, IDs, fixture
choices and results inside the “Advanced aggregate lab · synthetic teaching model”
disclosure. Background job activity refers to durable aggregate, forecast and
retraining jobs; the connectivity stream has separate Run/Stop/status controls.


### Viewport Home and multiple disruptions

Home fills the available viewport after accounting for the header, main inset and
mobile navigation/safe area. It uses a minimum height, allowing natural scrolling
on short devices. The static wordmark and caption remain outside the animated
mark. The actual generation runtime loops only while the mark and document are
visible, rests for three seconds after each completed reveal, pauses on resize/navigation, and remains static for reduced motion. No
Replay control or animation announcements remain.

Connectivity scenarios support up to eight editable disruption rows. Each selects
an actual reference asset or connection and independent start/duration; Run includes
every nonempty row directly. All rows lock during the stream; Stop restores them.
Reload preserves valid choices and visibly clears missing targets. Global step
bounds apply to each row and all selected targets highlight in the schematic.
The backend faults-array contract and electrical-model limitations are unchanged.
