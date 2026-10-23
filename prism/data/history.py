"""Audit original SLDC demand captures; no interpolation or synthetic filling."""
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import math
import pandas as pd


def prepare_history(root):
    root=Path(root);manifest=json.loads((root/'manifest.json').read_text())
    points={};conflicts=set();invalid=0;captured=0;days=Counter()
    for record in manifest['records']:
        days[record['status']]+=1
        if record['status'] not in {'captured','empty'}:continue
        raw=(root/record['path']).read_bytes()
        if sha256(raw).hexdigest()!=record['sha256']:raise ValueError('Raw source checksum mismatch')
        rows=json.loads(raw);rows=rows if isinstance(rows,list) else rows['data'];captured+=len(rows)
        for row in rows:
            try:
                local=datetime.strptime(row['FORDATE']+' '+row['TIMESLOT'],'%d/%m/%Y %H:%M').replace(tzinfo=ZoneInfo('Asia/Kolkata'))
                if local.astimezone(timezone.utc)>datetime.now(timezone.utc)+timedelta(seconds=120):raise ValueError('Future observation')
                value=row['VALUE']
                if row['ENTITY']!='Delhi' or row['TYPE']!='MW' or local.date().isoformat()!=record['date'] or local.minute%5:
                    raise ValueError('Unexpected source domain')
                if value is None or isinstance(value,bool) or not math.isfinite(float(value)) or float(value)<0:raise ValueError('Invalid value')
                stamp=pd.Timestamp(local).tz_convert('UTC');value=float(value)
                if stamp in points and points[stamp]!=value:conflicts.add(stamp)
                else:points[stamp]=value
            except (KeyError,TypeError,ValueError,OverflowError):invalid+=1
    for stamp in conflicts:points.pop(stamp,None)
    # IST hours start at half past UTC, so aggregate in local time, then convert.
    buckets=defaultdict(list)
    for stamp,value in points.items():buckets[stamp.tz_convert('Asia/Kolkata').floor('h').tz_convert('UTC')].append(value)
    first=pd.Timestamp(manifest['requested_start'],tz='Asia/Kolkata').tz_convert('UTC')
    last=(pd.Timestamp(manifest['requested_end'],tz='Asia/Kolkata')+pd.Timedelta(hours=23)).tz_convert('UTC')
    records=[]
    for stamp in pd.date_range(first,last,freq='h'):
        values=buckets[stamp];eligible=len(values)>=10
        records.append(dict(timestamp=stamp.isoformat(),demand_mw=sum(values)/len(values) if eligible else None,
            sample_count=len(values),quality='observed_hourly_mean' if eligible else 'insufficient_observations'))
    frame=pd.DataFrame(records)
    report=dict(source='delhi_sldc',target='demand_mw',geography='Delhi system aggregate',
        source_url='https://delhisldc.org/api/load-curve-discom',timezone_assumption='Asia/Kolkata for FORDATE/TIMESLOT',
        manifest_sha256=sha256((root/'manifest.json').read_bytes()).hexdigest(),
        requested_start=manifest['requested_start'],requested_end=manifest['requested_end'],
        requested_days=(last-first).days+1,acquisition_status=manifest['status'],day_statuses=dict(days),
        raw_rows=captured,valid_unique_5min_observations=len(points),invalid_rows=invalid,conflicting_timestamps=len(conflicts),
        expected_hours=len(frame),eligible_hours=int(frame.demand_mw.notna().sum()),missing_hours=int(frame.demand_mw.isna().sum()),
        minimum_samples_per_hour=10,expected_samples_per_hour=12,imputation=False,
        renewable_history={'solar_mw':'unavailable: no audited two-year source','wind_mw':'unavailable: no audited two-year source'},
        limitation='Two-year requested range does not mean complete measurements. Hourly means require at least 10 distinct five-minute observations; gaps remain missing.')
    return frame,report


def store_hourly(frame,dataset_hash,database):
    database.execute('''CREATE TABLE IF NOT EXISTS prism_hourly_history (
        dataset_hash text NOT NULL, timestamp timestamptz NOT NULL, demand_mw double precision,
        sample_count integer NOT NULL, quality text NOT NULL, PRIMARY KEY(dataset_hash,timestamp))''')
    with database.cursor() as cursor:
        cursor.executemany('INSERT INTO prism_hourly_history VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
            [(dataset_hash,r.timestamp,None if pd.isna(r.demand_mw) else r.demand_mw,int(r.sample_count),r.quality) for r in frame.itertuples()])
    database.commit()
