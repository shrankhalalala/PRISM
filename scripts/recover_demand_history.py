"""Recapture incomplete days without modifying frozen source evidence or models."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import ssl
import time
from urllib.request import Request, urlopen
import pandas as pd
import truststore
from prism.data.history import prepare_history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data/sources/delhi/2026-10-23-demand-history'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error('Recovery must use a separate evidence directory')
    frame, before = prepare_history(args.source)
    dates = sorted(set(pd.to_datetime(frame.loc[frame.demand_mw.isna(), 'timestamp'], utc=True).dt.tz_convert('Asia/Kolkata').dt.strftime('%Y-%m-%d')))
    original = json.loads((args.source / 'manifest.json').read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'raw').mkdir(exist_ok=True)
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    records = []
    for record in original['records']:
        copy = dict(record)
        if copy.get('path'):
            copy['path'] = os.path.relpath(args.source / copy['path'], args.output)
        records.append(copy)
    attempts = []
    for index, day in enumerate(dates):
        source = next(r for r in original['records'] if r['date'] == day)
        target = args.output / 'raw' / (day + '.json')
        entry = dict(date=day, url=source['url'], status='failed', retrieved_at=None)
        try:
            if not target.exists():
                with urlopen(Request(source['url'], headers={'Accept': 'application/json', 'User-Agent': 'PRISM-Academic-Prototype/0.3'}), context=context, timeout=15) as response:
                    if response.headers.get_content_type() != 'application/json':
                        raise ValueError('Expected JSON')
                    raw = response.read(2 * 1024 * 1024 + 1)
                if len(raw) > 2 * 1024 * 1024:
                    raise ValueError('Response too large')
                payload = json.loads(raw)
                rows = payload if isinstance(payload, list) else payload['data']
                if not isinstance(rows, list):
                    raise ValueError('Expected row list')
                target.write_bytes(raw)
            raw = target.read_bytes()
            payload = json.loads(raw)
            rows = payload if isinstance(payload, list) else payload['data']
            entry.update(status='captured' if rows else 'empty', path='raw/' + target.name, sha256=sha256(raw).hexdigest(), rows=len(rows), retrieved_at=datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).isoformat())
            # Keep both versions: prepare_history rejects conflicting timestamps.
            records.append(entry)
        except Exception as error:
            entry['error'] = type(error).__name__
        attempts.append(entry)
        (args.output / 'attempts.json').write_text(json.dumps(attempts, indent=2) + '\n')
        if (index + 1) % 10 == 0:
            print(f'Rechecked {index+1}/{len(dates)} days', flush=True)
        time.sleep(1)
    manifest = {**original, 'records': records, 'status': 'recovered_with_gaps', 'parent_manifest_sha256': sha256((args.source / 'manifest.json').read_bytes()).hexdigest()}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    recovered, after = prepare_history(args.output)
    recovered.to_csv(args.output / 'hourly.csv', index=False, float_format='%.6f')
    report = dict(before=before, after=after, recovered_hours=after['eligible_hours']-before['eligible_hours'], attempted_days=len(dates), failed_requests=sum(r['status']=='failed' for r in attempts), hourly_sha256=sha256((args.output/'hourly.csv').read_bytes()).hexdigest(), promoted=False, limitation='Conflicting observations excluded; frozen production history and models unchanged. Recaptures do not create renewable history.')
    (args.output / 'recovery_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:report[k] for k in ('recovered_hours','attempted_days','failed_requests','promoted')}), flush=True)


if __name__ == '__main__':
    main()
