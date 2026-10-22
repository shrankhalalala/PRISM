"""Evidence archive integrity and failure handling, without external requests."""

from copy import deepcopy
from email.message import Message
import hashlib
import json
from pathlib import Path
import ssl
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from scripts.acquire_topology_sources import capture_source, main, verify_archive


class TopologySourceTests(unittest.TestCase):
    def setUp(self):
        self.source = {"id": "SRC-01", "url": "https://example.org/map.pdf",
                       "format": "pdf", "required": True}
        self.body = b"%PDF-1.4\nuntouched reference bytes\n"

    def response(self, body, media="application/pdf"):
        response = Mock()
        response.status = 200
        response.geturl.return_value = self.source["url"]
        response.headers = Message()
        response.headers["Content-Type"] = media
        response.read.return_value = body
        context = Mock()
        context.__enter__ = Mock(return_value=response)
        context.__exit__ = Mock(return_value=False)
        return context

    def archive(self, directory):
        (directory / "raw").mkdir()
        opener = Mock(return_value=self.response(self.body))
        record = capture_source(self.source, directory, opener)
        catalog = json.dumps({"sources": [self.source]}).encode()
        (directory / "catalog.json").write_bytes(catalog)
        manifest = {"catalog_sha256": hashlib.sha256(catalog).hexdigest(), "sources": [record]}
        (directory / "manifest.json").write_text(json.dumps(manifest))
        return record, manifest

    def test_capture_preserves_bytes_and_verified_tls(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "raw").mkdir()
            opener = Mock(return_value=self.response(self.body))
            record = capture_source(self.source, directory, opener)
            self.assertEqual(record["status"], "captured")
            self.assertEqual((directory / record["path"]).read_bytes(), self.body)
            self.assertEqual(record["sha256"], hashlib.sha256(self.body).hexdigest())
            self.assertEqual(opener.call_args.kwargs["context"].verify_mode, ssl.CERT_REQUIRED)
            self.assertEqual(opener.call_args.kwargs["timeout"], 20)

    def test_html_fallback_cannot_become_a_pdf(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "raw").mkdir()
            opener = Mock(return_value=self.response(b"<html>login</html>", "text/html"))
            record = capture_source(self.source, directory, opener)
            self.assertEqual(record["status"], "failed")
            self.assertIsNone(record["path"])
            self.assertEqual(list((directory / "raw").iterdir()), [])

    def test_timeout_and_size_limit_are_visible_failures(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "raw").mkdir()
            timeout = capture_source(self.source, directory, Mock(side_effect=TimeoutError("offline")))
            self.assertIn("TimeoutError", timeout["error"])
            with patch("scripts.acquire_topology_sources.MAX_BYTES", 8):
                oversized = capture_source(self.source, directory, Mock(return_value=self.response(self.body)))
            self.assertEqual(oversized["status"], "failed")
            self.assertIsNone(oversized["path"])

    def test_offline_verification_detects_modified_or_missing_bytes(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            record, _ = self.archive(directory)
            self.assertEqual(verify_archive(directory), [])
            locator = {"id": "map-page", "source_id": "SRC-01",
                       "source_path": record["path"], "source_sha256": record["sha256"]}
            locators = directory / "locators.json"
            locators.write_text(json.dumps({"locators": [locator]}))
            self.assertEqual(verify_archive(directory), [])
            locator["source_sha256"] = "wrong-source-fingerprint"
            locators.write_text(json.dumps({"locators": [locator]}))
            self.assertTrue(any("locator" in message for message in verify_archive(directory)))
            locators.unlink()
            path = directory / record["path"]
            path.write_bytes(self.body.replace(b"reference", b"REFERENCE"))
            self.assertTrue(any("checksum" in message for message in verify_archive(directory)))
            path.unlink()
            self.assertTrue(any("missing file" in message for message in verify_archive(directory)))

    def test_catalog_and_manifest_completeness_are_verified(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            _, manifest = self.archive(directory)
            (directory / "catalog.json").write_text('{"sources": []}')
            issues = verify_archive(directory)
            self.assertIn("Catalog checksum mismatch", issues)
            self.assertIn("Manifest source set differs from snapshot catalog", issues)
            manifest["sources"] = []
            (directory / "manifest.json").write_text(json.dumps(manifest))
            self.assertTrue(verify_archive(directory))

    def test_archive_path_cannot_escape_and_required_failures_are_reported(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            _, manifest = self.archive(directory)
            manifest["sources"][0]["path"] = "../outside.pdf"
            (directory / "manifest.json").write_text(json.dumps(manifest))
            self.assertTrue(any("outside archive" in message for message in verify_archive(directory)))
            record = deepcopy(manifest["sources"][0])
            record.update(status="failed", path=None)
            manifest["sources"] = [record]
            (directory / "manifest.json").write_text(json.dumps(manifest))
            self.assertIn("SRC-01: required capture failed", verify_archive(directory))

    def test_existing_snapshot_is_never_overwritten(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.archive(directory)
            before = (directory / "manifest.json").read_bytes()
            with patch("sys.argv", ["archive", "--output-dir", str(directory),
                                    "--catalog", str(directory / "catalog.json")]):
                with self.assertRaises(FileExistsError):
                    main()
            self.assertEqual((directory / "manifest.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
