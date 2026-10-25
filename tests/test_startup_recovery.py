"""Readiness must recover when a model dependency starts after the web process."""
import os
import threading
import unittest
from unittest.mock import Mock, patch
from prism import create_app
from prism.startup import ModelWarmup


class StartupRecoveryTests(unittest.TestCase):
    def test_failed_startup_recovers_on_readiness_without_restart(self):
        clock = Mock(return_value=0)
        initialize = Mock(side_effect=[OSError('dependency offline'), None])
        warmup = ModelWarmup(initialize=initialize, clock=clock)
        with patch.dict(os.environ, {'PRISM_WARM_MODELS': '1', 'PRISM_REQUIRE_SERVICES': '0'}), patch('prism.startup.ModelWarmup', return_value=warmup):
            app = create_app({'TESTING': True})
            client = app.test_client()
            self.assertEqual(client.get('/api/readiness').status_code, 503)
            self.assertEqual(initialize.call_count, 1)
            clock.return_value = 6
            response = client.get('/api/readiness')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['checks']['models'], 'ready')
            client.get('/api/readiness')
            self.assertEqual(initialize.call_count, 2)

    def test_concurrent_probes_do_not_duplicate_initialization(self):
        entered, release = threading.Event(), threading.Event()
        def initialize():
            entered.set()
            release.wait(timeout=2)
        warmup = ModelWarmup(initialize=initialize)
        worker = threading.Thread(target=warmup.attempt)
        worker.start()
        self.assertTrue(entered.wait(timeout=2))
        try:
            self.assertEqual(warmup.attempt()['status'], 'unavailable')
        finally:
            release.set()
            worker.join(timeout=2)
        self.assertEqual(warmup.state['status'], 'ready')

    def test_repeated_failure_is_throttled_and_does_not_expose_exception(self):
        clock = Mock(return_value=0)
        initialize = Mock(side_effect=OSError('private connection details'))
        warmup = ModelWarmup(initialize=initialize, clock=clock)
        warmup.attempt()
        clock.return_value = 1
        self.assertEqual(warmup.attempt()['status'], 'unavailable')
        self.assertEqual(initialize.call_count, 1)
        self.assertNotIn('private', str(warmup.state))
        clock.return_value = 5
        warmup.attempt()
        self.assertEqual(initialize.call_count, 2)
