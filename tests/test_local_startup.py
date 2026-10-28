"""Local web must use host service URLs without overwriting shell settings."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from prism.__main__ import configure_local


class LocalStartupTests(unittest.TestCase):
    def test_loads_env_and_interpolates_password(self):
        with TemporaryDirectory() as directory:
            Path(directory, '.env').write_text(
                'POSTGRES_PASSWORD=local-test-secret\n'
                'PRISM_DATABASE_URL=postgresql://prism:${POSTGRES_PASSWORD}@127.0.0.1:5433/prism\n'
                'PRISM_REDIS_URL=redis://127.0.0.1:6380/0\n')
            with patch('prism.__main__.ROOT', Path(directory)), patch.dict(os.environ, {}, clear=True):
                configure_local()
                self.assertEqual(os.environ['PRISM_DATABASE_URL'], 'postgresql://prism:local-test-secret@127.0.0.1:5433/prism')
                self.assertEqual(os.environ['PRISM_REDIS_URL'], 'redis://127.0.0.1:6380/0')
                self.assertEqual(os.environ['PRISM_USE_DURABLE_LIVE'], '1')
                self.assertEqual(os.environ['PRISM_REQUIRE_SERVICES'], '1')

    def test_explicit_shell_configuration_wins(self):
        with TemporaryDirectory() as directory:
            Path(directory, '.env').write_text('PRISM_REDIS_URL=redis://127.0.0.1:6380/0\n')
            values = {'PRISM_REDIS_URL': 'redis://custom:6379/2', 'PRISM_USE_DURABLE_LIVE': '0',
                      'PRISM_DATABASE_URL': 'postgresql://custom/prism', 'PRISM_REQUIRE_SERVICES': '0'}
            with patch('prism.__main__.ROOT', Path(directory)), patch.dict(os.environ, values, clear=True):
                configure_local()
                for key, value in values.items():
                    self.assertEqual(os.environ[key], value)


if __name__ == '__main__':
    unittest.main()
