"""Live ingestion contracts use fixed source records; tests never need the network."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from email.message import Message
from http.client import IncompleteRead
import json
import ssl
import unittest
from unittest.mock import Mock, patch

from prism import create_app
from prism.data.gridwatch import GridWatchClient, fetch_payload, parse_reading


class GridWatchTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 22, 5, 25, tzinfo=timezone.utc)
        self.tick = 0
        self.payload = {"data": [{
            "DD_DATE": "2026-10-22T05:24:30.000Z", "DD_CURR_LOAD": 4600.5,
            "DD_FREQUENCY": 49.975, "DD_DRAWAL": 4200, "DD_CURR_SCHEDULE": 4300,
        }]}
        self.fetch = Mock(return_value=self.payload)
        self.source = GridWatchClient(self.fetch, lambda: self.now, lambda: self.tick)

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)
        self.tick += seconds

    def test_mapping_and_source_timestamp(self):
        result = self.source.snapshot()
        self.assertEqual(result['status'], 'live')
        self.assertEqual(result['age_seconds'], 30)
        self.assertEqual(result['reading']['demand_mw'], 4600.5)
        self.assertEqual(result['reading']['frequency_hz'], 49.975)
        self.assertEqual(result['reading']['observed_at'], '2026-10-22T05:24:30+00:00')

    def test_concurrent_requests_share_cache_and_cannot_mutate_it(self):
        with ThreadPoolExecutor(max_workers=8) as executor:
            snapshots = list(executor.map(lambda _: self.source.snapshot(), range(20)))
        self.fetch.assert_called_once()
        snapshots[0]['reading']['demand_mw'] = 0
        self.assertEqual(self.source.snapshot()['reading']['demand_mw'], 4600.5)
        self.advance(60)
        self.source.snapshot()
        self.assertEqual(self.fetch.call_count, 2)

    def test_outage_preserves_last_good_record_and_recovers(self):
        first = self.source.snapshot()
        self.advance(60)
        self.fetch.side_effect = TimeoutError('timeout')
        failed = self.source.snapshot()
        self.assertEqual(failed['status'], 'stale')
        self.assertEqual(failed['reading'], first['reading'])
        self.assertEqual(failed['fetched_at'], first['fetched_at'])
        self.source.snapshot()
        self.assertEqual(self.fetch.call_count, 2)
        self.advance(60)
        self.fetch.side_effect = None
        self.assertEqual(self.source.snapshot()['status'], 'live')

    def test_old_source_record_stays_stale_even_after_successful_fetch(self):
        self.advance(301)
        result = self.source.snapshot()
        self.assertEqual(result['status'], 'stale')
        self.assertIsNone(result['error'])

    def test_backward_timestamp_cannot_replace_last_good_reading(self):
        first = self.source.snapshot()
        self.advance(60)
        self.payload['data'][0]['DD_DATE'] = '2026-10-22T04:00:00Z'
        result = self.source.snapshot()
        self.assertEqual(result['reading'], first['reading'])
        self.assertEqual(result['status'], 'stale')

    def test_reject_malformed_measurements_and_timestamps(self):
        cases = [{}, {'data': []}, {'data': None}, {'data': [None]}]
        for field, value in [
            ('DD_CURR_LOAD', None), ('DD_CURR_LOAD', True), ('DD_CURR_LOAD', -1),
            ('DD_CURR_LOAD', 'NaN'), ('DD_CURR_LOAD', 'Infinity'),
            ('DD_FREQUENCY', 0), ('DD_DATE', '2026-10-22T05:25:00'),
            ('DD_DATE', '2026-10-23T05:25:00Z'), ('DD_DATE', 'bad'),
        ]:
            payload = deepcopy(self.payload)
            payload['data'][0][field] = value
            cases.append(payload)
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                parse_reading(payload, self.now)

    def test_http_response_validation_and_timeout(self):
        response = Mock()
        response.headers = Message()
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.read.return_value = json.dumps(self.payload).encode()
        context = Mock()
        context.__enter__ = Mock(return_value=response)
        context.__exit__ = Mock(return_value=False)
        with patch('prism.data.gridwatch.urlopen', return_value=context) as opened:
            self.assertEqual(fetch_payload(), self.payload)
            self.assertEqual(opened.call_args.kwargs['timeout'], 8)
            self.assertEqual(opened.call_args.kwargs['context'].verify_mode, ssl.CERT_REQUIRED)
            response.read.return_value = b'x' * 65537
            with self.assertRaises(ValueError):
                fetch_payload()
            response.headers.replace_header('Content-Type', 'text/html')
            with self.assertRaises(ValueError):
                fetch_payload()

    def test_api_unavailable_then_recovers_without_changing_synthetic_data(self):
        self.fetch.side_effect = OSError('offline')
        client = create_app({'TESTING': True, 'GRIDWATCH_CLIENT': self.source}).test_client()
        result = client.get('/api/live/gridwatch')
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.json['status'], 'unavailable')
        self.assertIsNone(result.json['reading'])
        self.assertEqual(result.headers['Cache-Control'], 'no-store')
        client.get('/api/live/gridwatch')
        self.fetch.assert_called_once()
        self.advance(60)
        self.fetch.side_effect = None
        result = client.get('/api/live/gridwatch')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['data_source'], 'delhi_sldc')
        self.assertEqual(client.get('/api/measurements?limit=1').json['data_source'], 'synthetic')
        self.assertIn(b'id="live-grid"', client.get('/').data)

    def test_truncated_http_response_is_reported_unavailable(self):
        self.fetch.side_effect = IncompleteRead(b'{')
        self.assertEqual(self.source.snapshot()['status'], 'unavailable')


if __name__ == '__main__':
    unittest.main()
