"""Bounded, resumable public SLDC daily load-curve acquisition; originals preserved."""
import argparse
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
import ssl,truststore,json,hashlib,time

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--start',type=date.fromisoformat,default=date(2024,10,22))
parser.add_argument('--end',type=date.fromisoformat,default=date(2026,10,21))
parser.add_argument('--output',type=Path,default=Path('data/sources/delhi/2026-10-23-demand-history'))
parser.add_argument('--retry-failed',action='store_true')
args=parser.parse_args()
if args.end<args.start or (args.end-args.start).days>1095:parser.error('Require an ordered range of at most three years')
root=args.output
root.mkdir(exist_ok=True,parents=True);(root/'raw').mkdir(exist_ok=True)
manifest_path=root/'manifest.json'
manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else dict(schema_version='1.0',status='collecting',source='delhi_sldc_load_curve',timezone_assumption='Asia/Kolkata for published local FORDATE/TIMESLOT',records=[])
known={r['date']:r for r in manifest['records']}
context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
start=args.start;end=args.end
for offset in range((end-start).days+1):
 day=start+timedelta(days=offset);label=day.isoformat()
 if label in known:
  previous=known[label]
  if previous['status'] in {'captured','empty'}:
   target=root/previous['path']
   if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=previous['sha256']:
    raise ValueError('Archived bytes missing or checksum mismatch: '+label)
   continue
  if not args.retry_failed:continue
  manifest['records']=[r for r in manifest['records'] if r['date']!=label]
 url='https://delhisldc.org/api/load-curve-discom?'+urlencode({'fordate':day.strftime('%d/%m/%Y'),'entity':'Delhi'})
 entry=dict(date=label,url=url,status='failed',retrieved_at=None,sha256=None,path=None,rows=0)
 for attempt in range(2):
  try:
   with urlopen(Request(url,headers={'Accept':'application/json','User-Agent':'PRISM-Academic-Prototype/0.3 (bounded historical demand audit)'}),context=context,timeout=15) as response:
    if response.headers.get_content_type()!='application/json':raise ValueError('Expected JSON')
    raw=response.read(2*1024*1024+1)
   if len(raw)>2*1024*1024:raise ValueError('Response size limit')
   payload=json.loads(raw);rows=payload if isinstance(payload,list) else payload['data']
   if not isinstance(rows,list):raise ValueError('Expected rows')
   relative='raw/'+label+'.json';target=root/relative
   # Preserve bytes if a run was interrupted between capture and manifest write.
   if target.exists():
    raw=target.read_bytes();payload=json.loads(raw);rows=payload if isinstance(payload,list) else payload['data']
   else:target.write_bytes(raw)
   entry.update(status='captured' if rows else 'empty',retrieved_at=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(raw).hexdigest(),path=relative,bytes=len(raw),rows=len(rows))
   break
  except Exception as error:
   entry['error']=type(error).__name__
   if attempt==0:time.sleep(2)
 manifest['records'].append(entry);known[label]=entry
 manifest['completed_days']=len(known);manifest['requested_start']=start.isoformat();manifest['requested_end']=end.isoformat()
 manifest['updated_at']=datetime.now(timezone.utc).isoformat()
 temp=manifest_path.with_suffix('.tmp');temp.write_text(json.dumps(manifest,indent=2)+'\n');temp.replace(manifest_path)
 if (offset+1)%25==0:print('Captured/audited',offset+1,'of',((end-start).days+1),'days',flush=True)
 time.sleep(1)
manifest['status']='captured_with_gaps' if any(r['status']!='captured' for r in manifest['records']) else 'captured'
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
print('Complete:',len(manifest['records']),'days; noncaptured:',sum(r['status']!='captured' for r in manifest['records']),flush=True)
