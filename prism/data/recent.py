"""Bounded hourly refresh of three public demand days; separate from frozen training."""
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import json
from pathlib import Path
import ssl
import time
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo
import truststore
from prism.config import ROOT
from prism.data.history import prepare_history,store_hourly


def refresh_recent():
    today=datetime.now(ZoneInfo('Asia/Kolkata')).date();root=ROOT/'artifacts/recent-history';(root/'raw').mkdir(parents=True,exist_ok=True)
    manifest=dict(status='captured',requested_start=(today-timedelta(days=2)).isoformat(),requested_end=today.isoformat(),records=[])
    context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    for offset in range(2,-1,-1):
        day=today-timedelta(days=offset);url='https://delhisldc.org/api/load-curve-discom?'+urlencode({'fordate':day.strftime('%d/%m/%Y'),'entity':'Delhi'})
        with urlopen(Request(url,headers={'Accept':'application/json','User-Agent':'PRISM-Academic-Prototype/0.3'}),context=context,timeout=8) as response:
            if response.headers.get_content_type()!='application/json':raise ValueError('Expected JSON')
            raw=response.read(2097153)
        if len(raw)>2097152:raise ValueError('Response too large')
        rows=json.loads(raw);rows=rows if isinstance(rows,list) else rows['data']
        if not isinstance(rows,list):raise ValueError('Invalid rows')
        digest=sha256(raw).hexdigest();path='raw/'+day.isoformat()+'-'+digest+'.json';(root/path).write_bytes(raw)
        manifest['records'].append(dict(date=day.isoformat(),url=url,path=path,sha256=digest,status='captured' if rows else 'empty',retrieved_at=datetime.now(timezone.utc).isoformat(),rows=len(rows)))
        if offset:time.sleep(1)
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    frame,report=prepare_history(root);target=ROOT/'artifacts/delhi_demand_recent.csv';temp=target.with_suffix('.tmp');frame.to_csv(temp,index=False,float_format='%.6f');temp.replace(target)
    from prism.streaming.store import connections
    r,db=connections()
    try:store_hourly(frame,sha256(target.read_bytes()).hexdigest(),db)
    finally:db.close();r.close()
    return report
