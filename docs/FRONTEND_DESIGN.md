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
