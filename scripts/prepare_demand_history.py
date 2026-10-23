"""Verify captures, emit gap-preserving hourly means and optionally persist PostgreSQL."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from prism.data.history import prepare_history,store_hourly


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=Path('data/sources/delhi/2026-10-23-demand-history'));p.add_argument('--postgres',action='store_true');a=p.parse_args()
    frame,report=prepare_history(a.source)
    target=Path('data/processed/delhi_demand_hourly.csv');frame.to_csv(target,index=False,float_format='%.6f')
    report['hourly_sha256']=sha256(target.read_bytes()).hexdigest()
    if a.postgres:
        from prism.streaming.store import connections
        r,db=connections()
        try:
            store_hourly(frame,report['hourly_sha256'],db)
            count=db.execute('SELECT count(*) FROM prism_hourly_history WHERE dataset_hash=%s',(report['hourly_sha256'],)).fetchone()[0]
            assert count==len(frame);report['postgres_verified_rows']=count
        finally:db.close();r.close()
    Path('reports/phase3_history_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
