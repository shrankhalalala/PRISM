"""Source-qualified SLDC station loading; not generator output or line limits."""
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
from prism.config import ROOT

FEED_URL = 'https://delhisldc.org/api/grid-loading'
REGISTRY = ROOT / 'data/topology/delhi/telemetry_mappings.json'


def fetch_stations():
    req = Request(FEED_URL, headers={'Accept': 'application/json', 'User-Agent': 'PRISM-Academic-Prototype/0.3'})
    with urlopen(req, timeout=8, context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)) as response:
        if response.headers.get_content_type() != 'application/json':
            raise ValueError('Expected JSON')
        raw = response.read(262145)
        if len(raw) > 262144:
            raise ValueError('Response too large')
        return json.loads(raw)


def parse_stations(payload, now, registry=None):
    registry = registry or json.loads(REGISTRY.read_text())
    mappings = registry['mappings']
    rows = payload.get('data')
    if not isinstance(rows, list) or not rows:
        raise ValueError('No station records')
    readings, rejected, unmatched, seen = [], [], [], set()
    for row in rows:
        label = row.get('DG_GRID') if isinstance(row, dict) else None
        if label not in mappings:
            unmatched.append(label)
            continue
        try:
            if label in seen:
                raise ValueError('Duplicate station')
            seen.add(label)
            observed = datetime.fromisoformat(row['DG_DATE'].replace('Z', '+00:00'))
            if observed.tzinfo is None or (observed-now).total_seconds() > 120:
                raise ValueError('Invalid timestamp')
            values = {}
            for field, key in [('mw', 'DG_MW'), ('mvar', 'DG_MVAR'), ('voltage_kv', 'DG_VOLTAGE')]:
                raw = row[key]
                if raw is None or isinstance(raw, bool):
                    raise ValueError('Missing measurement')
                value = float(raw)
                if not math.isfinite(value) or (field == 'voltage_kv' and value < 0):
                    raise ValueError('Invalid measurement')
                values[field] = value
            readings.append(dict(asset_id=mappings[label]['asset_id'], source_label=label,
                observed_at=observed.astimezone(timezone.utc).isoformat(), **values,
                source_status_raw=row.get('DG_STTS'), measurement_role='station_loading',
                source_url=FEED_URL, mapping_evidence=mappings[label]['evidence'],
                quality_flags=['undocumented_rtu_status', 'power_sign_convention_unverified']))
        except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
            rejected.append(label)
    if not readings:
        raise ValueError('No valid mapped station measurements')
    return {'readings': readings, 'rejected_labels': rejected, 'unmatched_labels': unmatched,
            'expected_source_stations': len(mappings), 'source_rows': len(rows)}


class StationClient:
    """Single-flight 60s cache, retained stale data, per-station monotonicity."""
    def __init__(self, fetch=fetch_stations, clock=None, timer=monotonic):
        self.fetch, self.clock, self.timer = fetch, clock or (lambda: datetime.now(timezone.utc)), timer
        self.lock, self.next_fetch, self.last, self.error = Lock(), 0, None, None

    def snapshot(self):
        with self.lock:
            now = self.clock()
            if self.timer() >= self.next_fetch:
                try:
                    candidate = parse_stations(self.fetch(), now)
                    old = {r['asset_id']: r for r in (self.last or {}).get('readings', [])}
                    if any(r['asset_id'] in old and r['observed_at'] < old[r['asset_id']]['observed_at'] for r in candidate['readings']):
                        raise ValueError('Source timestamp moved backwards')
                    self.last, self.error = candidate, None
                except (OSError, HTTPException, ValueError, TypeError):
                    self.error = 'Station source unavailable or invalid.'
                finally:
                    self.next_fetch = self.timer() + 60
            result = deepcopy(self.last) if self.last else {'readings': [], 'rejected_labels': [], 'unmatched_labels': []}
            for reading in result['readings']:
                age = max(0, (now-datetime.fromisoformat(reading['observed_at'])).total_seconds())
                reading.update(age_seconds=round(age, 1), status='stale' if age > 300 or self.error else 'live')
            result.update(status='unavailable' if not self.last else ('stale' if self.error or any(r['status']=='stale' for r in result['readings']) else 'live'),
                          checked_at=now.isoformat(), error=self.error, refresh_seconds=60,
                          source_url=FEED_URL, data_source='delhi_sldc',
                          limitation='Station MW is not plant generation, line flow, available capacity or a verified electrical operating state.')
            return result
