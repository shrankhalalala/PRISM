"""Build a source-qualified node inventory offline; never modify the runtime grid."""

import argparse
from collections import Counter
import csv
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import unicodedata

from prism.config import ROOT
from scripts.acquire_topology_sources import verify_archive

DEFAULT_ARCHIVE = ROOT / "data/sources/delhi/2026-10-22"
DEFAULT_OUTPUT = ROOT / "data/topology/delhi"


def label_key(value):
    """Normalize typography only; preserve letters and Roman/digit distinctions."""
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", value).casefold())


def decode_html(body):
    match = re.search(rb"charset\s*=\s*[\"']?([a-zA-Z0-9_-]+)", body[:8192], re.I)
    encoding = match.group(1).decode("ascii") if match else "utf-8"
    return body.decode(encoding), encoding


class Tables(HTMLParser):
    """Keep physical table/TR positions, ignoring scripts and presentation tags."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.depth = 0
        self.ignored_depth = 0
        self.row = None
        self.cell = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.ignored_depth += 1
        if tag == "table":
            self.depth += 1
            if self.depth == 1:
                self.tables.append([])
        elif self.depth == 1 and tag == "tr":
            self.row = []
        elif self.depth == 1 and tag in {"td", "th"}:
            self.cell = []
        elif self.cell is not None and tag == "br":
            self.cell.append(" ")

    def handle_data(self, data):
        if self.cell is not None and not self.ignored_depth:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignored_depth = max(0, self.ignored_depth - 1)
        if self.depth == 1 and tag in {"td", "th"} and self.cell is not None:
            if self.row is not None:
                self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif self.depth == 1 and tag == "tr" and self.row is not None:
            self.tables[-1].append(self.row)
            self.row = None
        elif tag == "table":
            self.depth -= 1


def numbered_rows(text, table):
    rows = Tables(text).tables[table - 1]
    return [(i, int(row[0]), row) for i, row in enumerate(rows, 1)
            if row and row[0].isdigit()]


def bind_alias(registry, label, node_id):
    key = label_key(label)
    if key in registry and registry[key] != node_id:
        raise ValueError(f"Ambiguous explicit alias: {label}")
    registry[key] = node_id


def endpoint_labels(description, registry):
    """Require a unique exact registered-label split; do not fuzzy-match sites."""
    description = re.sub(r"^\s*\d+\s*kV\s*", "", description, flags=re.I)
    description = re.split(r"\s+Ckt\b", description, maxsplit=1, flags=re.I)[0].strip()
    candidates = []
    for match in re.finditer(r"[-–—]", description):
        left, right = description[:match.start()].strip(), description[match.end():].strip()
        if label_key(left) in registry and label_key(right) in registry:
            candidates.append([(left, registry[label_key(left)]), (right, registry[label_key(right)])])
    if len(candidates) != 1:
        raise ValueError(f"Endpoint label needs explicit reconciliation: {description}")
    return candidates[0]


def build_inventory(archive, rules):
    problems = verify_archive(archive)
    if problems:
        raise ValueError(f"Source integrity gate failed: {problems}")
    manifest_bytes = (archive / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    sources = {s["id"]: s for s in manifest["sources"]}
    evidence, nodes, registry, issues = {}, {}, {}, []

    def source_html(source):
        return decode_html((archive / sources[source]["path"]).read_bytes())[0]

    def cite(source, locator, assertion):
        entry = sources[source]
        if entry["status"] != "captured" or entry["role"] == "access_probe":
            raise ValueError(f"Not reference evidence: {source}")
        payload = dict(source_id=source, source_sha256=entry["sha256"],
                       source_url=entry["url"], source_date=entry["source_date"],
                       retrieved_at=entry["retrieved_at"], locator=locator, assertion=assertion)
        identifier = "ev-" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
        evidence[identifier] = payload
        return identifier

    def add_node(identifier, name, kind, scope_role, boundary="unresolved"):
        if identifier in nodes:
            raise ValueError(f"Duplicate node ID: {identifier}")
        nodes[identifier] = dict(
            id=identifier, name=name, kind=kind, scope_role=scope_role,
            boundary_classification=boundary, identity_status="source_referenced",
            operational_status="unknown", latitude=None, longitude=None,
            current_output_mw=None, available_capacity_mw=None,
            simulation_eligible=False, aliases=[], ownership_assertions=[],
            voltage_assertions=[], transformation_observations=[],
            historical_status_assertions=[], evidence_ids=[], issue_ids=[], notes=[],
        )
        bind_alias(registry, name, identifier)
        return nodes[identifier]

    def issue(identifier, node_ids, reason, evidence_ids):
        issues.append(dict(id=identifier, node_ids=node_ids, status="open", reason=reason,
                           evidence_ids=evidence_ids, resolution=None))
        for node_id in node_ids:
            nodes[node_id]["issue_ids"].append(identifier)

    directory_rows = {}
    for table in [1, 2]:
        for physical_row, serial, cells in numbered_rows(source_html("SRC-02"), table):
            directory_rows[(table, serial)] = (physical_row, cells)
    expected = {(s["table"], s["serial"]) for s in rules["directory"]}
    if set(directory_rows) != expected:
        raise ValueError("Directory row set differs from the reviewed identity rules")
    for spec in rules["directory"]:
        physical_row, cells = directory_rows[(spec["table"], spec["serial"])]
        if cells[1] != spec["expected_name"]:
            raise ValueError(f'Source name drift at {spec["id"]}')
        node = add_node(spec["id"], cells[1], "substation", "dtl_directory", "internal")
        locator = dict(table=spec["table"], source_serial=spec["serial"], physical_tr=physical_row)
        ev = cite("SRC-02", locator, "Named DTL station directory entry; voltage heading and address context. No current online status asserted.")
        node["evidence_ids"].append(ev)
        node["ownership_assertions"].append(dict(owner="DTL", scope="directory listing; voltage-specific ownership may differ", evidence_id=ev))
        node["voltage_assertions"].append(dict(levels_kv=[400 if spec["table"] == 1 else 220],
                                               status="conflicted" if spec["id"] == "ss-timarpur" else "source_reported", evidence_id=ev))
        node["notes"].append("Internal boundary classification follows the published Delhi address; exact coordinates are unverified. Telephone numbers are not copied.")
        if spec["id"] == "ss-timarpur":
            issue("NODE-TIMARPUR-VOLTAGE", [node["id"]], "220 kV heading conflicts with 20/33kV address text; no correction inferred.", [ev])

    for spec in rules["supplemental_nodes"]:
        node = add_node(spec["id"], spec["name"], spec["kind"], spec["scope_role"], spec["boundary_classification"])
        basis = spec["basis"]
        ev = cite(basis["source_id"], {k: v for k, v in basis.items() if k != "source_id"},
                  "Manually reviewed supplemental identity/role assertion; not independently verified current asset status.")
        node["evidence_ids"].append(ev)
        node["voltage_assertions"].append(dict(levels_kv=spec["voltage_levels_kv"], status="source_reported", evidence_id=ev))
        if spec["owner"]:
            node["ownership_assertions"].append(dict(owner=spec["owner"], scope="dated source assertion", evidence_id=ev))
        if spec["historical_status"]:
            node["historical_status_assertions"].append(dict(status=spec["historical_status"], evidence_id=ev))
        if spec["notes"]:
            node["notes"].append(spec["notes"])
        if spec["kind"] == "unresolved_asset":
            node["identity_status"] = "unresolved_endpoint"
            issue("IDENTITY-" + spec["id"].upper(), [spec["id"]], spec["notes"], [ev])

    for spec in rules["aliases"]:
        bind_alias(registry, spec["name"], spec["node_id"])
        basis = spec["basis"]
        ev = cite(basis["source_id"], {k: v for k, v in basis.items() if k != "source_id"}, spec["rationale"])
        node = nodes[spec["node_id"]]
        node["aliases"].append(dict(name=spec["name"], status=spec["status"], evidence_id=ev))
        node["evidence_ids"].append(ev)

    for spec in rules["shared_site_claims"]:
        ev = cite(spec["source_id"], dict(physical_pages=spec["physical_pages"]),
                  "Historical 400 kV PGCIL / lower-voltage DTL shared-site interpretation; electrical terminal separation pending.")
        node = nodes[spec["node_id"]]
        node["evidence_ids"].append(ev)
        node["ownership_assertions"].append(dict(owner=spec["owner"], scope="historical 400 kV portion, not exclusive site ownership", evidence_id=ev))
        node["voltage_assertions"].append(dict(levels_kv=spec["voltage_levels_kv"], status="source_reported_historical", evidence_id=ev))

    transformations = []
    unassigned = {label_key(a["name"]): a for a in rules["unassigned_aliases"]}
    for source in ["SRC-05", "SRC-06"]:
        for physical_row, serial, cells in numbered_rows(source_html(source), 1):
            name = re.sub(r"^\s*\d+\s*kV\s*", "", cells[1], flags=re.I)
            ev = cite(source, dict(table=1, source_serial=serial, physical_tr=physical_row), "Historical transformation metadata; MVA is not available generation MW.")
            node_id = registry.get(label_key(name))
            record = dict(source_name=cells[1], source_id=source, source_serial=serial,
                          node_id=node_id, evidence_id=ev, source_cells=cells[2:])
            ratios = [(400, 220)] if source == "SRC-05" else [(220, 66), (220, 33), (66, 33), (66, 11), (33, 11)]
            if len(cells) != len(ratios) + 3:
                raise ValueError(f"Unexpected transformation columns: {source}:{serial}")
            record["configurations"] = [dict(primary_kv=p, secondary_kv=s, source_configuration=value)
                                         for (p, s), value in zip(ratios, cells[2:-1]) if re.search(r"\d", value)]
            total = cells[-1].replace(",", "")
            record["source_total_mva"] = float(total) if re.fullmatch(r"\d+(?:\.\d+)?", total) else None
            if not node_id:
                candidate = unassigned.get(label_key(name))
                if not candidate:
                    raise ValueError(f"Unreviewed transformer station label: {name}")
                record["candidate_node_ids"] = candidate["candidate_node_ids"]
                issue("TRANSFORM-" + source + "-" + str(serial), candidate["candidate_node_ids"], candidate["reason"], [ev])
            else:
                nodes[node_id]["evidence_ids"].append(ev)
                nodes[node_id]["transformation_observations"].append(record)
                levels = sorted({voltage for config in record["configurations"]
                                 for voltage in [config["primary_kv"], config["secondary_kv"]]})
                nodes[node_id]["voltage_assertions"].append(dict(levels_kv=levels, status="source_reported_historical", evidence_id=ev))
            transformations.append(record)

    mentions = []
    circuit_source_rows = 0
    for source, voltage in [("SRC-03", 400), ("SRC-04", 220)]:
        for physical_row, serial, cells in numbered_rows(source_html(source), 1):
            circuit_source_rows += 1
            for side, (name, node_id) in enumerate(endpoint_labels(cells[1], registry), 1):
                ev = cite(source, dict(table=1, source_serial=serial, physical_tr=physical_row, endpoint_position=side),
                          "Named circuit endpoint occurrence; site mapping follows the explicit project rules. Not a validated edge.")
                nodes[node_id]["evidence_ids"].append(ev)
                mentions.append(dict(source_id=source, source_serial=serial, endpoint_position=side,
                                     raw_label=name, node_id=node_id, circuit_voltage_kv=voltage, evidence_id=ev,
                                     identity_status=nodes[node_id]["identity_status"]))

    issue("NODE-NARELA-SITES", ["ss-narela-dtl", "ss-narela-bbmb"],
          "DTL and BBMB owner-qualified identities remain separate; distinct physical-site/co-location relationship is not established.",
          nodes["ss-narela-bbmb"]["evidence_ids"][:1])
    issue("NODE-WAZIRABAD-SITES", ["ss-wazirabad", "ss-south-of-wazirabad"],
          "Do not merge Wazirabad with South of Wazirabad or infer retirement/renaming; independent site reconciliation required.",
          nodes["ss-wazirabad"]["evidence_ids"][:1])
    issue("NODE-BUDELLA-STATUS", ["ss-budella"],
          "Planning/spillover map reference and later circuit mentions do not establish a commissioning date or current online status.",
          nodes["ss-budella"]["evidence_ids"][:1])
    issue("NODE-PLANT-TERMINALS", ["plant-gtps", "plant-pps1", "plant-pps3-bawana", "plant-jhajjar"],
          "Plant identities are distinct from substations; terminal wiring, current availability and some geographic/owner fields remain unknown.",
          nodes["plant-pps1"]["evidence_ids"][:1])

    for node in nodes.values():
        node["evidence_ids"] = sorted(set(node["evidence_ids"]))
        node["aliases"].sort(key=lambda item: label_key(item["name"]))
    inventory = dict(schema_version="1.0", scope=rules["scope"], snapshot=archive.name,
                     source_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
                     assurance="Source-referenced inventory records, not a complete current operating graph. No 50-node verification claim.",
                     nodes=sorted(nodes.values(), key=lambda n: n["id"]), evidence=dict(sorted(evidence.items())))
    coverage = dict(directory_rows=len(directory_rows), directory_rows_accounted=len(rules["directory"]),
                    inventory_records=len(nodes), records_by_kind=dict(Counter(n["kind"] for n in nodes.values())),
                    transformer_rows=len(transformations), transformer_rows_assigned=sum(r["node_id"] is not None for r in transformations),
                    current_circuit_source_rows=circuit_source_rows, endpoint_occurrences=len(mentions),
                    unresolved_endpoint_occurrences=sum(m["identity_status"] == "unresolved_endpoint" for m in mentions),
                    physical_sites_independently_verified=None, goal_50_verified_nodes_achieved=False,
                    note="Record IDs and source row coverage are not verified unique physical site counts. Step 5 edges and Step 6 completeness remain pending.")
    validate_inventory(inventory)
    return {"nodes.json": inventory, "coverage.json": coverage,
            "endpoint_mentions.json": {"scope": rules["scope"], "mentions": mentions},
            "transformation_mentions.json": {"observations": transformations},
            "unresolved.json": {"issues": issues, "excluded_context": rules["excluded_context"]}}


def validate_inventory(inventory):
    nodes = inventory["nodes"]
    identifiers = [node["id"] for node in nodes]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Duplicate inventory IDs")
    for node in nodes:
        if not node["evidence_ids"] or any(e not in inventory["evidence"] for e in node["evidence_ids"]):
            raise ValueError(f'Missing provenance for {node["id"]}')
        if node["simulation_eligible"] or node["operational_status"] != "unknown":
            raise ValueError("Inventory must not imply current operational/simulation verification")
        if any(node[key] is not None for key in ["current_output_mw", "available_capacity_mw", "latitude", "longitude"]):
            raise ValueError("Unverified live/geographic parameters must remain unknown")


def render_outputs(documents, rules_bytes):
    documents["nodes.json"]["identity_rules_sha256"] = hashlib.sha256(rules_bytes).hexdigest()
    rendered = {name: json.dumps(value, indent=2, ensure_ascii=False) + "\n" for name, value in documents.items()}
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["id", "name", "kind", "scope_role", "boundary_classification", "identity_status", "source_reported_voltage_kv", "source_reported_owners", "operational_status", "open_issues"])
    for node in documents["nodes.json"]["nodes"]:
        levels = sorted({v for claim in node["voltage_assertions"] if claim["status"] != "conflicted" for v in claim["levels_kv"]})
        owners = sorted({claim["owner"] for claim in node["ownership_assertions"]})
        writer.writerow([node[k] for k in ["id", "name", "kind", "scope_role", "boundary_classification", "identity_status"]]
                        + [";".join(map(str, levels)), ";".join(owners), node["operational_status"], ";".join(node["issue_ids"])])
    rendered["nodes.csv"] = stream.getvalue()
    return rendered


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rules", type=Path, default=DEFAULT_OUTPUT / "identity_rules.json")
    parser.add_argument("--check", action="store_true", help="Compare regenerated output without writing")
    args = parser.parse_args()
    rules_bytes = args.rules.read_bytes()
    documents = build_inventory(args.archive, json.loads(rules_bytes))
    outputs = render_outputs(documents, rules_bytes)
    if args.check:
        mismatches = [name for name, content in outputs.items()
                      if not (args.output_dir / name).exists() or (args.output_dir / name).read_text() != content]
        if mismatches:
            raise ValueError(f"Inventory output differs: {mismatches}")
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in outputs.items():
            (args.output_dir / name).write_text(content)
    print(json.dumps(documents["coverage.json"], indent=2))


if __name__ == "__main__":
    main()
