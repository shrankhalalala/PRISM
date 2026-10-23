"""Web readers use durable history; only the dedicated collector polls upstream."""
from copy import deepcopy
from datetime import datetime,timezone
from threading import Lock
from time import monotonic
from prism.streaming.store import connections
import json
from prism.data.stations import REGISTRY


class DurableLiveClient:
    def __init__(self,station=False):
        self.station=station;self.lock=Lock();self.next_read=0;self.last=None;self.error=None

    def snapshot(self):
        with self.lock:
            now=datetime.now(timezone.utc)
            if monotonic()>=self.next_read:
                r=db=None
                try:
                    r,db=connections()
                    if self.station:
                        rows=db.execute("SELECT DISTINCT ON(asset_id) payload FROM prism_measurements WHERE source='delhi_sldc' AND asset_id<>'delhi-system' ORDER BY asset_id,observed_at DESC,ingested_at DESC,event_id DESC").fetchall()
                        eligible={mapping['asset_id'] for mapping in json.loads(REGISTRY.read_text())['mappings'].values()}
                        readings=[]
                        for (p,) in rows:
                            if p['asset_id'] not in eligible:continue
                            context=p.get('context',{})
                            readings.append(dict(asset_id=p['asset_id'],source_label=context.get('source_label',p['asset_id']),
                                observed_at=p['observed_at'],**p['values'],measurement_role='station_loading',
                                source_status_raw=context.get('source_status_raw'),quality_flags=context.get('quality_flags',['power_sign_convention_unverified']),source_url=p['source_url']))
                        if not readings:raise ValueError('No durable station observations')
                        self.last=dict(readings=readings,unmatched_labels=[],rejected_labels=[],expected_source_stations=49,source_rows=len(readings),
                            source_url='https://delhisldc.org/api/grid-loading',limitation='Station loading is not generator output or line limits. Collector source quality is retained.')
                    else:
                        row=db.execute("SELECT payload FROM prism_measurements WHERE source='delhi_sldc' AND asset_id='delhi-system' ORDER BY observed_at DESC,ingested_at DESC,event_id DESC LIMIT 1").fetchone()
                        if row is None:raise ValueError('No durable aggregate observation')
                        p=row[0];self.last=dict(reading=dict(observed_at=p['observed_at'],**p['values']),source_url='https://delhisldc.org/grid-watch/',feed_url=p['source_url'],fetched_at=now.isoformat())
                    quality=db.execute('SELECT payload FROM prism_collector_status WHERE source_key=%s',('stations' if self.station else 'aggregate',)).fetchone()
                    self.error=None
                    if quality:
                        q=quality[0]
                        if self.station:
                            for key in ('unmatched_labels','rejected_labels','source_rows','expected_source_stations'):
                                if key in q:self.last[key]=q[key]
                        checked=datetime.fromisoformat(q['checked_at'])
                        if q.get('status')!='live' or (now-checked).total_seconds()>180:
                            self.error='Collector source check failed or heartbeat expired.'
                    else:self.error='Collector health has not been recorded.'
                except Exception:self.error='Durable measurements unavailable.'
                finally:
                    if db:db.close()
                    if r:r.close()
                    self.next_read=monotonic()+6
            result=deepcopy(self.last) if self.last else ({'readings':[],'unmatched_labels':[],'rejected_labels':[]} if self.station else {'reading':None})
            readings=result.get('readings',[]) if self.station else [result['reading']] if result.get('reading') else []
            for reading in readings:
                age=max(0,(now-datetime.fromisoformat(reading['observed_at'])).total_seconds())
                reading.update(age_seconds=round(age,1),status='stale' if self.error or age>300 else 'live')
            result.update(status='unavailable' if not self.last else 'stale' if self.error or any(r['status']=='stale' for r in readings) else 'live',
                data_source='delhi_sldc',transport='postgres_durable_history',checked_at=now.isoformat(),refresh_seconds=60,stale_after_seconds=300,error=self.error)
            if not self.station:result['age_seconds']=readings[0]['age_seconds'] if readings else None
            return result
