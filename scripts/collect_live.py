"""Run one dedicated minute-cadence collector and recoverable durable consumer."""
import argparse
import signal
import time
from prism.data.gridwatch import GridWatchClient
from prism.data.stations import StationClient
from prism.streaming.store import DurableStream,connections,event


def collect(stream,grid,stations):
    count=0
    snapshot=grid.snapshot()
    if snapshot['status']=='live':
        r=snapshot['reading']
        stream.publish(event('delhi-system',r['observed_at'],{k:r[k] for k in ('demand_mw','frequency_hz','drawal_mw','schedule_mw')},snapshot['feed_url'],context={'measurement_role':'city_aggregate'}))
        count+=1
    snapshot=stations.snapshot()
    for r in snapshot['readings']:
        if r['status']=='live':
            stream.publish(event(r['asset_id'],r['observed_at'],{k:r[k] for k in ('mw','mvar','voltage_kv')},snapshot['source_url'],context={k:r[k] for k in ('measurement_role','source_label','quality_flags','source_status_raw')}))
            count+=1
    return count


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--once',action='store_true');args=parser.parse_args()
    client,db=connections();stream=DurableStream(client,db);stream.setup()
    grid,stations=GridWatchClient(),StationClient();running=True;next_fetch=0;failures=0
    def stop(*_):
        nonlocal running
        running=False
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        while running:
            try:
                if time.monotonic()>=next_fetch:
                    collect(stream,grid,stations);next_fetch=time.monotonic()+60
                stream.consume();stream.trim();failures=0
                if args.once:break
                time.sleep(1)
            except Exception as exc:
                try:db.rollback()
                except Exception:pass
                failures+=1
                # Log only class; database/Redis exceptions can contain credentials.
                print('Collector retry:',type(exc).__name__,flush=True)
                if args.once:raise RuntimeError('Collector failed') from None
                time.sleep(min(30,2**min(failures,5)))
                try:
                    db.close();client.close()
                    client,db=connections();stream=DurableStream(client,db);stream.setup()
                except Exception:pass
    finally:db.close();client.close()

if __name__=='__main__':main()
