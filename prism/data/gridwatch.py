"""Read-only Delhi SLDC adapter; cached per process, independent of fixtures."""

from copy import deepcopy
from datetime import datetime, timezone
from http.client import HTTPException
import json
import math
import ssl
from threading import Lock
from time import monotonic
from urllib.request import Request, urlopen

import truststore

SOURCE_URL = "https://delhisldc.org/grid-watch/"
FEED_URL = "https://delhisldc.org/api/dynamic-data"
FIELDS = {
    "demand_mw": "DD_CURR_LOAD",
    "frequency_hz": "DD_FREQUENCY",
    "drawal_mw": "DD_DRAWAL",
    "schedule_mw": "DD_CURR_SCHEDULE",
}


def parse_reading(payload, now):
    """Require a complete, finite reading and a timezone-qualified source time."""
    try:
        row = payload["data"][0]
        observed = datetime.fromisoformat(row["DD_DATE"].replace("Z", "+00:00"))
        if observed.tzinfo is None or (observed - now).total_seconds() > 120:
            raise ValueError("Invalid source timestamp")
        values = {}
        for field, source_field in FIELDS.items():
            raw = row[source_field]
            if isinstance(raw, bool) or raw is None:
                raise ValueError("Invalid measurement")
            value = float(raw)
            if not math.isfinite(value) or value < 0:
                raise ValueError("Invalid measurement")
            values[field] = value
        if not 40 <= values["frequency_hz"] <= 60:
            raise ValueError("Invalid frequency")
        return dict(observed_at=observed.astimezone(timezone.utc).isoformat(), **values)
    except (KeyError, IndexError, TypeError, ValueError, AttributeError, OverflowError) as error:
        raise ValueError("Grid Watch returned an invalid measurement record") from error


def fetch_payload():
    request = Request(FEED_URL, headers={
        "Accept": "application/json",
        "User-Agent": "PRISM-Academic-Prototype/0.3 (read-only Grid Watch collector)",
    })
    # Scope native certificate verification to this request; do not alter global SSL.
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    with urlopen(request, timeout=8, context=context) as response:
        if response.headers.get_content_type() != "application/json":
            raise ValueError("Grid Watch did not return JSON")
        raw = response.read(65537)
        if len(raw) > 65536:
            raise ValueError("Grid Watch response exceeded the size limit")
        return json.loads(raw)


class GridWatchClient:
    """Coalesce browser requests and throttle successes AND failures to once/minute."""

    def __init__(self, fetch=fetch_payload, clock=None, timer=monotonic):
        self.fetch = fetch
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.timer = timer
        self.lock = Lock()
        self.next_fetch = 0
        self.reading = None
        self.fetched_at = None
        self.error = None

    def snapshot(self):
        with self.lock:
            if self.timer() >= self.next_fetch:
                try:
                    payload = self.fetch()
                    now = self.clock()
                    reading = parse_reading(payload, now)
                    if self.reading and reading["observed_at"] < self.reading["observed_at"]:
                        raise ValueError("Grid Watch timestamp moved backwards")
                    self.reading = reading
                    self.fetched_at = now.isoformat()
                    self.error = None
                except (OSError, HTTPException, ValueError, TypeError):
                    self.error = "Source unavailable or returned an invalid reading."
                finally:
                    self.next_fetch = self.timer() + 60
            now = self.clock()
            age = None
            if self.reading:
                observed = datetime.fromisoformat(self.reading["observed_at"])
                age = max(0, (now - observed).total_seconds())
            status = "unavailable" if self.reading is None else (
                "stale" if self.error or age > 300 else "live"
            )
            return {
                "data_source": "delhi_sldc",
                "source_url": SOURCE_URL,
                "feed_url": FEED_URL,
                "status": status,
                "reading": deepcopy(self.reading),
                "fetched_at": self.fetched_at,
                "checked_at": now.isoformat(),
                "age_seconds": round(age, 1) if age is not None else None,
                "refresh_seconds": 60,
                "stale_after_seconds": 300,
                "error": self.error,
            }
