from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from prism.forecasting.registry import active_bundle,promote,rollback,verify_bundle


def fixture(root,rmse):
    # Registry mechanics only: synthetic metadata must never enter deployed registry.
    report={'selected_on_validation':'autoregressive','validation_origins':12,'metrics':{'autoregressive':{'validation':{'rmse':rmse}}}}
    files={'lstm.json':'{}','autoregressive.json':'{}','forecast_report.json':json.dumps(report)}
    hashes={name:sha256(content.encode()).hexdigest() for name,content in files.items()}
    version=sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest();folder=root/version;folder.mkdir()
    for name,content in files.items():(folder/name).write_text(content)
    (folder/'manifest.json').write_text(json.dumps({'files':hashes}));return version


class RegistryTests(unittest.TestCase):
    def test_reject_promote_rollback_and_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);a=fixture(root,100);b=fixture(root,90);worse=fixture(root,110)
            self.assertTrue(promote(a,120,root=root)['promoted'])
            self.assertFalse(promote(worse,100,root=root)['promoted']);self.assertEqual(active_bundle(root)['version'],a)
            self.assertTrue(promote(b,100,root=root)['promoted']);self.assertEqual(active_bundle(root)['version'],b)
            self.assertTrue(rollback(root)['rolled_back']);self.assertEqual(active_bundle(root)['version'],a)
            (root/a/'autoregressive.json').write_text('tampered')
            with self.assertRaises(ValueError):verify_bundle(a,root)
            with self.assertRaises(ValueError):verify_bundle('../bad',root)
