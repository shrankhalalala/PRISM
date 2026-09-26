# Interactive dashboard

The Flask `/` page serves a responsive operator workspace without external assets or a frontend build step. Start the application using the root README and visit `http://localhost:5050`.

## Navigation and appearance

- The topbar navigation toggle remains available when the sidebar is collapsed. Desktop collapse persists in local storage. On mobile, navigation becomes a drawer that closes using the toggle, Escape, the backdrop, or a navigation link. Hidden navigation is inert and removed from keyboard navigation.
- The light/dark button persists an explicit theme preference. Without a saved preference, the page follows the operating system and subsequent OS theme changes. Storage errors do not prevent use.
- Motion is restrained and disabled when reduced motion is requested.

## Network exploration

- Refresh loads `/api/grid` and the selected measurement range independently, with timeouts, loading feedback, and endpoint-specific errors. Previously loaded values are labeled potentially stale after a failure.
- Click a schematic node, or focus it and press Enter/Space, to inspect its properties. The node's connections are highlighted; this represents connectivity, not simulated flow.
- All assets/Plants/Substations/Loads filters dim other kinds and select a matching node. Dimmed nodes remain inspectable.
- Narrow screens stack the inspector below the schematic. The network preserves its full width inside a horizontal scroller, with a labeled native asset selector as an alternative.

## Measurement exploration

- Demand, Solar, and Wind controls redraw an SVG chart from actual API records.
- The 24 hours and 7 days controls request `/api/measurements?limit=24` and `?limit=168`. Controls indicate the successfully loaded range. Loading and failures are announced; failures preserve the previous chart.
- Chart axes and captions explicitly use UTC. The caption includes observation count, time span, and peak. Hovering a point reveals its timestamp and value.
- The expandable measurement table provides every loaded observation with all three measurement series, frequency, and quality flags. The table and mobile chart scroll inside their panels.

All observations remain explicitly synthetic. The interface contains no fake live stream, randomized metrics, electrical-flow animation, or claims of trained dispatch. Contribution sections and the foundation-mode banner remain removed.

## Verification checklist

1. Toggle the sidebar and reload on desktop; verify persistence. At mobile width, verify Escape/backdrop close and hidden links are not focusable.
2. Change theme and reload; verify persistence and sufficient contrast in both themes.
3. Select a network kind and asset; verify the inspector and connected edges update.
4. Switch Demand/Solar/Wind and 24 hours/7 days; compare values and record counts with the corresponding API response.
5. Expand the table, then check a 375px viewport for page overflow.
6. Block a measurement request and change range; verify the visible failure message and retained chart. Unblock and Refresh data to recover.

## Phase 2 completion

The Forecast Lab selects demand, solar, or wind; persistence, autoregression, or
LSTM; and a one-to-24-hour horizon. It renders an SVG result chart and a complete
numeric prediction list, with loading, validation, and failure announcements.

The Scenario Lab selects the rule baseline or reviewed Q-learning policy, one to
96 steps, and an optional node or line outage with start and duration. Results show
return, unserved and curtailed energy, synthetic cost, emissions, demand and
generation trajectories, actions, rewards, and active faults. Policy output remains
non-operational and the page states the aggregate simulator boundary.

Navigation follows the current hash across Overview, Measurements, Forecast, and
Scenario sections. Desktop and mobile layouts retain the collapsible sidebar,
theme preference, keyboard behavior, chart containment, and visible status states.
