from datetime import datetime,timezone
import unittest
from prism.streaming.store import event,validate_event

class EventTests(unittest.TestCase):
    def test_identity_and_revisions(self):
        t=datetime.now(timezone.utc).isoformat()
        a=event('ss-pragati',t,{'mw':-4,'mvar':-2},'https://delhisldc.org/api/grid-loading')
        self.assertEqual(validate_event(a),a)
        self.assertEqual(event('ss-pragati',t,{'mvar':-2,'mw':-4},a['source_url'])['event_id'],a['event_id'])
        self.assertNotEqual(event('ss-pragati',t,{'mw':-5},a['source_url'])['event_id'],a['event_id'])
        a['values']['mw']=1
        with self.assertRaises(ValueError):validate_event(a)

    def test_reject_invalid(self):
        t=datetime.now(timezone.utc).isoformat()
        for values in [{'mw':float('nan')},{'mw':True},{'capacity_mw':2},{'voltage_kv':-1}]:
            with self.assertRaises(ValueError):event('asset',t,values,'https://delhisldc.org')
        with self.assertRaises(ValueError):event('asset','2026-01-01T00:00:00',{'mw':1},'https://delhisldc.org')
