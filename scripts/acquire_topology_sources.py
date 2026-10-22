"""Capture public reference files once, or verify an existing archive offline.

This command collects evidence only. It does not infer assets or update PRISM's
runtime grid. Use a new output directory for each capture; existing snapshots
are never overwritten. Failed requests remain visible in the manifest.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException
import json
from pathlib import Path
import re
import ssl
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import truststore

from prism.config import ROOT

MAX_BYTES = 64 * 1024 * 1024
CATALOG = ROOT / "data/sources/delhi/catalog.json"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def capture_source(source, directory, opener=urlopen):
    """Save untouched successful response bytes and selected public metadata."""
    result = {**source, "attempted_at": utc_now(), "status": "failed",
              "path": None, "sha256": None, "bytes": None}
    try:
        request = Request(source["url"], headers={
            "User-Agent": "PRISM-Research-Archive/0.1 (public topology references)",
            "Accept": "application/pdf,text/html,application/xhtml+xml",
        })
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        with opener(request, timeout=20, context=context) as response:
            result.update(http_status=response.status, final_url=response.geturl(),
                          content_type=response.headers.get_content_type(),
                          last_modified=response.headers.get("Last-Modified"),
                          etag=response.headers.get("ETag"))
            body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("Response exceeds the 64 MiB capture limit")
        if not body:
            raise ValueError("Empty response")
        if source["format"] == "pdf" and not body.startswith(b"%PDF-"):
            raise ValueError("Expected PDF but received a different document")
        if source["format"] == "html" and result["content_type"] not in {
            "text/html", "application/xhtml+xml",
        }:
            raise ValueError("Expected HTML but received a different media type")
        filename = f'raw/{source["id"]}.{source["format"]}'
        path = directory / filename
        with path.open("xb") as stream:
            stream.write(body)
        result.update(status="captured", path=filename, bytes=len(body),
                      sha256=hashlib.sha256(body).hexdigest(), retrieved_at=utc_now())
    except HTTPError as error:
        result.update(http_status=error.code, error=f"HTTP {error.code}")
    except (OSError, HTTPException, ValueError) as error:
        result["error"] = f"{type(error).__name__}: {error}"
    return result


def verify_archive(directory):
    """Detect missing/changed captures without network access or rewriting them."""
    directory = Path(directory).resolve()
    manifest = json.loads((directory / "manifest.json").read_text())
    problems = []
    catalog_bytes = (directory / "catalog.json").read_bytes()
    catalog = json.loads(catalog_bytes)
    if hashlib.sha256(catalog_bytes).hexdigest() != manifest["catalog_sha256"]:
        problems.append("Catalog checksum mismatch")
    catalog_ids = {source["id"] for source in catalog["sources"]}
    if catalog_ids != {source["id"] for source in manifest["sources"]}:
        problems.append("Manifest source set differs from snapshot catalog")
    ids = set()
    for source in manifest["sources"]:
        identifier = source["id"]
        if identifier in ids:
            problems.append(f"{identifier}: duplicate source ID")
        ids.add(identifier)
        if source["status"] != "captured":
            if source.get("required"):
                problems.append(f"{identifier}: required capture failed")
            continue
        try:
            path = (directory / source["path"]).resolve()
            if not path.is_relative_to(directory) or not path.is_file():
                raise ValueError("missing file or path outside archive")
            body = path.read_bytes()
            if len(body) != source["bytes"] or hashlib.sha256(body).hexdigest() != source["sha256"]:
                raise ValueError("byte count/checksum mismatch")
            if source["format"] == "pdf" and not body.startswith(b"%PDF-"):
                raise ValueError("PDF signature missing")
        except (OSError, TypeError, ValueError) as error:
            problems.append(f"{identifier}: {error}")
    locator_path = directory / "locators.json"
    if locator_path.exists():
        captures = {source["id"]: source for source in manifest["sources"]}
        for locator in json.loads(locator_path.read_text())["locators"]:
            source = captures.get(locator["source_id"])
            if (not source or source["status"] != "captured"
                    or locator["source_path"] != source["path"]
                    or locator["source_sha256"] != source["sha256"]):
                problems.append(f'{locator["id"]}: locator does not match captured source')
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output-dir", type=Path, help="New snapshot directory")
    mode.add_argument("--verify", type=Path, help="Existing snapshot; no network requests")
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    args = parser.parse_args()
    if args.verify:
        problems = verify_archive(args.verify)
        print(json.dumps({"problems": problems, "ok": not problems}, indent=2))
        return 1 if problems else 0

    catalog = json.loads(args.catalog.read_text())
    sources = catalog["sources"]
    identifiers = [source["id"] for source in sources]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate catalog IDs")
    for source in sources:
        if not re.fullmatch(r"SRC-\d{2}[A-Z]?", source["id"]):
            raise ValueError("Invalid source identifier")
        if source["format"] not in {"pdf", "html"} or not source["url"].startswith("https://"):
            raise ValueError("Sources must be HTTPS PDF/HTML references")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "raw").mkdir()
    catalog_bytes = args.catalog.read_bytes()
    (args.output_dir / "catalog.json").write_bytes(catalog_bytes)
    started = utc_now()
    # Small parallelism; a single attempt per URL, without retries/login handling.
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(lambda source: capture_source(source, args.output_dir), sources))
    manifest = {"schema_version": "1.0", "scope": catalog["scope"],
                "started_at": started, "completed_at": utc_now(),
                "catalog_sha256": hashlib.sha256(catalog_bytes).hexdigest(),
                "assurance": "Source captures only; suitability requires manual review. No runtime grid changes.",
                "sources": results}
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for source in results:
        print(f'{source["id"]}: {source["status"]} ({source.get("bytes") or 0} bytes)')
    problems = verify_archive(args.output_dir)
    print(json.dumps({"problems": problems, "captured": sum(s["status"] == "captured" for s in results)}, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
