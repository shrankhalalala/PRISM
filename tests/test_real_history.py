from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import pandas as pd
from prism import create_app
from prism.data.history import prepare_history
from prism.forecasting.models import contiguous_endpoints,AutoregressiveForecaster
from scripts.evaluate_real_forecasting import origins

class HistoryTests(unittest.TestCase):
    def test_missing_and_conflicting_samples_never_filled(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);rows=[dict(FORDATE='01/01/2025',TIMESLOT=f'00:{i*5:02d}',ENTITY='Delhi',TYPE='MW',VALUE=100+i) for i in range(12)]
            rows.append({**rows[0],'VALUE':500})
            raw=json.dumps(rows).encode();(root/'day.json').write_bytes(raw)
            manifest=dict(requested_start='2025-01-01',requested_end='2025-01-01',status='captured',records=[dict(date='2025-01-01',status='captured',path='day.json',sha256=sha256(raw).hexdigest())])
            (root/'manifest.json').write_text(json.dumps(manifest));frame,report=prepare_history(root)
            self.assertEqual(report['conflicting_timestamps'],1);self.assertEqual(report['eligible_hours'],1)
            self.assertEqual(frame.sample_count.iloc[0],11);self.assertEqual(frame.demand_mw.iloc[0],106)
            self.assertTrue(frame.demand_mw.iloc[1:].isna().all())
            self.assertTrue(frame.timestamp.iloc[0].startswith('2024-12-31T18:30'))
            (root/'day.json').write_bytes(b'changed')
            with self.assertRaises(ValueError):prepare_history(root)

    def test_windows_do_not_bridge_timestamp_gaps(self):
        f=pd.DataFrame({'timestamp':pd.date_range('2025-01-01',periods=80,freq='h',tz='UTC'),'demand_mw':np.arange(80)+1})
        f=f.drop(index=30).reset_index(drop=True)
        endpoints=contiguous_endpoints(f,24)
        self.assertNotIn(31,endpoints);self.assertIn(55,endpoints)
        m=AutoregressiveForecaster().fit(f,'demand_mw')
        with self.assertRaises(ValueError):m.predict(f.iloc[:40],24)
        self.assertEqual(len(m.predict(f.tail(24),24)),24)
        f.loc[60,'demand_mw']=np.nan
        self.assertEqual(origins(f,24,79),[24] if not f.iloc[:48].demand_mw.isna().any() and (pd.Timestamp(f.timestamp.iloc[47])-pd.Timestamp(f.timestamp.iloc[0]))==pd.Timedelta(hours=47) else [])

    def test_renewable_gate(self):
        c=create_app({'TESTING':True}).test_client()
        self.assertEqual(c.get('/api/forecast/real?target=solar_mw').status_code,422)
        self.assertEqual(c.get('/api/forecast/real?target=bogus').status_code,400)

    def test_recaptures_count_days_once_and_reject_conflicts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            rows=[dict(FORDATE='01/01/2025',TIMESLOT=f'00:{i*5:02d}',ENTITY='Delhi',TYPE='MW',VALUE=100) for i in range(12)]
            records=[]
            for index in range(2):
                if index: rows[0]['VALUE']=200
                raw=json.dumps(rows).encode();name=f'{index}.json';(root/name).write_bytes(raw)
                records.append(dict(date='2025-01-01',status='captured',path=name,sha256=sha256(raw).hexdigest()))
            (root/'manifest.json').write_text(json.dumps(dict(requested_start='2025-01-01',requested_end='2025-01-01',status='recovered_with_gaps',records=records)))
            frame,report=prepare_history(root)
            self.assertEqual(report['day_statuses'],{'captured':1})
            self.assertEqual(report['capture_statuses'],{'captured':2})
            self.assertEqual(report['conflicting_timestamps'],1)
            self.assertEqual(frame.sample_count.iloc[0],11)
