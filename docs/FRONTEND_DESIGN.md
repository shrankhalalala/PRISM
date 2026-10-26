# PRISM frontend design

The dashboard uses the Framed sheet app direction (seed 309864271), with no redraws.
The cool frame holds navigation; the inset sheet holds the working data. IBM Plex
Sans is self-hosted under the included SIL Open Font License. Teal belongs to grid
selection, plotted data, status and the small PRISM mark; navigation remains neutral.

The main question is: which Delhi assets connect, and which source evidence and
published readings support them? The signature element is the actual Delhi
schematic beside its evidence inspector. Search, selection and source inspection
remain functional. No stock imagery, generated measurements or new sample records
were introduced for the redesign.

The workspace is now continuous: Home brings together aggregate Delhi readings,
application service status and a full-access alert disclosure. The network remains
visible with its docked station/evidence rail; the system-wide demand outlook follows
nearby and loads once automatically. Research & review uses keyboard-accessible tabs
for simulation, policy review, supplied-alarm investigation, and models/history.
Worker progress and results stay beside the selected tool. Inputs and node selection
remain in the DOM when tabs change. Old hashes open the relevant panel; Home and
legacy overview links lead to `#home`.

The user explicitly approved a professional blue/teal palette over the earlier
monochrome/3% color restriction. Home uses a soft sky-blue field, deep blue ink and
teal on data; amber/red retain their source-quality meanings. Dark surfaces remain
neutral. This is a deliberate user palette override, not a new direction draw.

Motion uses 150 ms close/control feedback and 250 ms tab/drawer controls with smooth-out
easing, without entrance animation or blur. The deterministic mobile drawer focus,
Tab containment, Escape and reduced-motion behavior remain intact. Technical IDs,
model hashes and audit record payloads are available in disclosures.

The synthetic measurement, forecasting and scenario tools retain their research
labels. Dated topology, current station measurements and electrical eligibility
retain their existing distinctions.

## Previous restyle checks

The requested app-screen inspector measured the built Docker preview at 1440,
768 and 390 pixels. Before the redesign, the Delhi screen reported six failures
and two warnings. The restyled Delhi and Operations screens each reported zero
failures and zero warnings at those widths.

| Check | Before | After |
|---|---|---|
| Desktop title | 43 px | 24 px |
| Phone title | 32 px | 22 px |
| Tracked uppercase labels | 37 reported | None reported |
| Text below 11 px | 618 blocks reported | None reported |
| Dark theme | Blue-toned surfaces with failed contrast checks | Neutral surfaces; contrast checks pass |
| Operations alert history | Ten full rows ahead of the forecast | Forecast first; two recent alerts plus complete history disclosure |

The source lint reports no failures. Its two warnings are intentional: monospace
is reserved for identifiers and code, and em dashes represent missing observations
and empty numeric cells. No inspector rules were waived. All 108 automated tests
passed; JavaScript syntax and rendered interaction checks accompany the restyle.

The design uses no found photographs, clips or replacement sample data. The
existing labeled synthetic examples remain research fixtures. The dense Delhi
schematic still benefits from zoom and asset search; its positions are schematic,
not geographic.

The font files are the Regular, Medium and SemiBold WOFF2 distributions from
[IBM Plex](https://github.com/IBM/plex/tree/master/packages/plex-sans/fonts/complete/woff2).
The original license is included at `prism/static/plex-LICENSE.txt`.

A subjective final screenshot critique scored design 7.8, usability 8.0,
creativity 7.0 and content 8.5 (weighted overall 7.8/10). Remaining tradeoffs are
schematic density at fit scale and lengthy technical evidence on phones; search,
zoom, native selectors and evidence disclosures preserve access to every record.
The design has no photography or entrance-animation requirement because it is a
working app screen.

During the October 25, 2026 browser check, the real-demand forecast endpoint
returned HTTP 503. Its unavailable/retry presentation was verified; successful
real-demand predictions were not asserted for that session. Synthetic lab
forecasts and scenarios were checked separately. Runtime source availability is
separate from the frontend design checks.

## Unified workspace verification

The unified implementation passes all three JavaScript syntax checks, DOM ID
validation and source diff checks. App lint reports zero failures; the two retained
warnings concern identifiers/code in monospace and missing-value em dashes. Built
responsive and backend checks are performed separately by the integration workflow;
previous screen-route screenshot scores above do not certify this new composition.

The rebuilt continuous workspace was then inspected at 1440, 768 and 390 pixels:
zero failures, zero warnings, zero horizontal page overflow and no browser console
errors. All seven screenshots were reviewed, plus the light-theme desktop preview.
The final visual critique scored 7.6/10; the complete workspace is intentionally
long, and the phone research tab strip scrolls. Keyboard tab focus was repaired
using History API navigation and explicit focus retention.

## Professional monitoring refinement

The current pass keeps the continuous Home, Network, Demand outlook and Research
architecture, IBM Plex Sans and the real SVG network. Its direction is a precision
monitoring instrument: charcoal surfaces, cyan/teal data, accessible muted text and
semantic success/warning/error states, with a coherent light theme. The user allows
subtle shadows and broader monitoring color use; earlier monochrome/color-budget
restrictions do not apply to this pass.

Rendered public pages at Linear, Grafana Labs and Vercel were inspected on October
25, 2026. These were their marketing websites, not authenticated dashboards. The
references informed control consistency, monitoring hierarchy and surface discipline;
no branding, layouts, screenshots or assets were copied. The actual baseline is saved
at `/tmp/prism-polish-NbVa83V5/before.png`. Its main issues were hidden destinations
when navigation collapsed, service states compressed into prose, a small network
canvas, fixed fit bounds and collision measurement on each pan event.

The refinement adds an accessible desktop icon rail and current-region highlighting
on scroll, individual API-derived PostgreSQL/Redis/worker indicators, a source-state
badge and true refresh busy states. Existing observations and forecasts remain on
screen during refresh. Failure is explicit; retained observations keep their original
source time. A failed health check marks individual states unknown rather than
asserting every service is down. No extra polling was added.

Network pan/view writes are coalesced by animation frame. Translation-only pan
skips collision layout; zoom, selection, hover, font readiness and resize still update
labels. Label writes, rectangle reads and collision visibility writes are batched.
Search is debounced by 100 ms and unchanged result identities avoid graph/ledger
rebuilds. Fit uses visible asset positions and the actual canvas aspect; the viewport
is 520 px on desktop and 390 px on phones. Adjacency emphasis means connectivity,
never current electrical flow. All asset and evidence selectors remain available.

Controls use shared spacing, radius, shadow and motion roles. Feedback is limited to
hover, active, focus and real request loading. The Transitions UI Generation skill
was reviewed but not installed: a simulated generation reveal is inappropriate for
a frequently used monitoring tool. Native disclosures stay immediate. Reduced-motion
rules remain in force, and no metric-number or artificial power-flow animation was
introduced.

Source verification for this milestone consists of JavaScript syntax, DOM identity,
HTML balance and diff checks. Built browser and backend checks are reported by the
integration workflow after rebuilding; previous screenshot scores are not new-pass
certification.

The rebuilt refinement passed responsive inspection with zero findings, overflow
or console errors at 1440/768/390. Independent browser review covered 1024 as well,
the light/dark layouts, icon rail and phone focus behavior, graph fit/pan/zoom and
search/reset, research keyboard/history, and refresh failure/recovery. All 66 assets
and 261 evidence records remained available. The real demand endpoint returned
24 predictions with original provenance. These point-in-time checks do not establish
physical Delhi validation or long-term service uptime.

## Data terminal redesign — current composition

The substantial redesign selects **Data terminal, seed 33077025**. It replaces the
Framed sheet direction rather than refining its padding. The signature is the actual
Delhi evidence network as the first-screen working canvas, with a compact selected
station inspector. The earlier large Home banner, boxed KPI strip, wide sidebar and
enclosing rounded sheet have been removed. No new data or physical-flow model was
introduced.

Desktop navigation is a 56 px icon rail with names/tooltips and optional expansion.
The 48 px header carries PRISM and its Delhi scope; phones use four labeled bottom
destinations. Bare demand-led telemetry sits above the network, while source/service
diagnostics live in an accessible header disclosure whose closed summary still shows
actual service status and alert count. Failures remain visible, not cosmetically
reclassified. Network counts are metadata beside search/filter controls; full native
asset and evidence directories remain below the canvas in a disclosure.

Demand uses a two-column composition: the forecast chart and hourly predictions
alongside source, model and uncertainty context, all within the existing result
wrapper. Research uses a vertical tool selector beside a form/results work area and
shared worker activity rail. Existing IDs, inputs, hashes, validation and result
states remain in place. These three compositions stack on phones without cloning
or replacing any of the data controls.

Public Sans Regular, Medium and SemiBold are self-hosted WOFF2 files downloaded
from the [USWDS Public Sans distribution](https://github.com/uswds/public-sans/tree/develop/fonts/webfonts).
The original license is included as `prism/static/public-sans-LICENSE.md`. Colors
use neutral terminal grounds, darker working panels and the product's teal for the
shared selection line. This replaces the dealt blue with PRISM's existing hue; it
does not invent electricity-flow direction or causal meaning.

The corrected filtered-fit, frame-coalesced pan, batched label collision, debounce
and complete ledger behavior from the preceding implementation are retained. A
150 ms opacity update on deliberate inspector selection respects reduced motion.
No decorative entrance, generation reveal or live-value animation is used.

Source checks pass for all three JavaScript files, unique DOM IDs, required targets,
one Home h1, HTML nesting and whitespace. First-fold geometry, responsive screenshots,
font loading and interaction checks must be confirmed on the rebuilt preview; earlier
Framed sheet scores do not certify this new layout.

The rebuilt Data terminal layout passed the final Taste inspector at 1440, 768
and 390 px with zero failures/warnings; all six final screenshots and a light-theme
preview were reviewed. At 1440×900 the canvas begins at 366 px versus approximately
860 px before. Public Sans was confirmed loaded. The final app critique scored
7.8/10; dense smaller-screen graphs still benefit from zoom and native pickers.
Independent browser checks passed inventory/evidence access, research state/history,
real forecast provenance, failure presentation and tooltip focus visibility.


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

The logo reveal targets only the SVG mark; the PRISM wordmark and caption remain
visible. Phones arrange them horizontally, with a smaller target on narrow screens.
The actual Transitions UI Generation runtime, styles and license are bundled locally
without timing changes. Gradients explicitly follow the user's request. The larger
Home headline is intentional introductory landing content; the app-title warning is
retained rather than reducing it to a dashboard label. Final responsive checks pass
with no failures at 1440, 768 and 390 px, allowing only the requested gradient rule.


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
