"""Inventory contracts and identity safeguards; no network or local PDFs required."""

from copy import deepcopy
import hashlib
import json
import unittest

from prism.config import ROOT
from scripts.build_delhi_node_inventory import (
    bind_alias, decode_html, endpoint_labels, label_key, numbered_rows, validate_inventory,
)


class InventoryExtractionTests(unittest.TestCase):
    def test_typographic_normalization_preserves_identity_distinctions(self):
        self.assertEqual(label_key("R. K. Puram"), label_key("RK Puram"))
        self.assertNotEqual(label_key("PPK-I"), label_key("PPK-II"))
        self.assertNotEqual(label_key("Narela"), label_key("Narela (BBMB)"))
        self.assertNotEqual(label_key("Wazirabad"), label_key("South of Wazirabad"))

    def test_alias_collision_requires_explicit_resolution(self):
        registry = {}
        bind_alias(registry, "Narela", "dtl-narela")
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            bind_alias(registry, "NARELA", "bbmb-narela")

    def test_circuit_labels_split_without_losing_station_roman_suffix(self):
        registry = {label_key("Bamnauli"): "a", label_key("Papankalan-I"): "b"}
        self.assertEqual(endpoint_labels("220kV Bamnauli - Papankalan -I Ckt-II", registry),
                         [("Bamnauli", "a"), ("Papankalan -I", "b")])
        with self.assertRaisesRegex(ValueError, "reconciliation"):
            endpoint_labels("Bamnauli - unknown Ckt-I", registry)

    def test_tables_preserve_source_serial_and_physical_row(self):
        text = '<table><tr><th>No</th><th>Station</th></tr><tr><td>7</td><td>A<br>B &amp; C</td></tr></table>'
        self.assertEqual(numbered_rows(text, 1), [(2, 7, ["7", "A B & C"])])
        encoded = b'<meta charset="iso-8859-1"><p>Copyright \xa9</p>'
        decoded, encoding = decode_html(encoded)
        self.assertIn("©", decoded)
        self.assertEqual(encoding, "iso-8859-1")


class CommittedInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = ROOT / "data/topology/delhi"
        cls.inventory = json.loads((cls.directory / "nodes.json").read_text())
        cls.nodes = {node["id"]: node for node in cls.inventory["nodes"]}
        cls.coverage = json.loads((cls.directory / "coverage.json").read_text())

    def test_all_reviewed_directory_rows_have_unique_records(self):
        rules = json.loads((self.directory / "identity_rules.json").read_text())
        self.assertEqual(len(rules["directory"]), 47)
        self.assertEqual(self.coverage["directory_rows_accounted"], 47)
        for record in rules["directory"]:
            self.assertEqual(self.nodes[record["id"]]["name"], record["expected_name"])
        validate_inventory(self.inventory)

    def test_evidence_is_bound_to_manifest_and_identity_rules(self):
        archive = ROOT / "data/sources/delhi/2026-10-22"
        manifest_bytes = (archive / "manifest.json").read_bytes()
        manifest = json.loads(manifest_bytes)
        sources = {s["id"]: s for s in manifest["sources"]}
        self.assertEqual(self.inventory["source_manifest_sha256"], hashlib.sha256(manifest_bytes).hexdigest())
        self.assertEqual(self.inventory["identity_rules_sha256"], hashlib.sha256((self.directory / "identity_rules.json").read_bytes()).hexdigest())
        for evidence in self.inventory["evidence"].values():
            source = sources[evidence["source_id"]]
            self.assertEqual(evidence["source_sha256"], source["sha256"])
            self.assertEqual(source["status"], "captured")
            self.assertNotEqual(source["role"], "access_probe")

    def test_plant_station_and_other_owner_identities_remain_separate(self):
        for a, b in [("ss-bawana-dtl", "plant-pps3-bawana"),
                     ("ss-pragati", "plant-pps1"),
                     ("ss-narela-dtl", "ss-narela-bbmb"),
                     ("ss-wazirabad", "ss-south-of-wazirabad"),
                     ("ss-dwarka-sector-5", "candidate-dwarka")]:
            self.assertIn(a, self.nodes)
            self.assertIn(b, self.nodes)
            self.assertNotEqual(self.nodes[a]["id"], self.nodes[b]["id"])
        self.assertEqual(self.nodes["candidate-dwarka"]["identity_status"], "unresolved_endpoint")
        self.assertEqual(self.nodes["ss-rajghat"]["kind"], "substation")
        self.assertNotIn("plant-btps", self.nodes)

    def test_source_mentions_have_no_dropped_or_dangling_node_references(self):
        mentions = json.loads((self.directory / "endpoint_mentions.json").read_text())["mentions"]
        self.assertEqual(len(mentions), 2 * self.coverage["current_circuit_source_rows"])
        self.assertEqual(len(mentions), self.coverage["endpoint_occurrences"])
        for mention in mentions:
            node = self.nodes[mention["node_id"]]
            self.assertIn(mention["evidence_id"], node["evidence_ids"])
            self.assertEqual(mention["identity_status"], node["identity_status"])
        transforms = json.loads((self.directory / "transformation_mentions.json").read_text())["observations"]
        self.assertEqual(len(transforms), self.coverage["transformer_rows"])
        pending = [record for record in transforms if record["node_id"] is None]
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["source_name"], "220kV SOW")
        bamnauli = self.nodes["ss-bamnauli"]
        levels = {v for assertion in bamnauli["voltage_assertions"] for v in assertion["levels_kv"]}
        self.assertTrue({400, 220} <= levels)
        self.assertEqual(bamnauli["transformation_observations"][0]["source_total_mva"], 1630)
        self.assertIsNone(bamnauli["available_capacity_mw"])

    def test_unknown_values_and_goal_are_not_inferred_from_record_count(self):
        self.assertFalse(self.coverage["goal_50_verified_nodes_achieved"])
        self.assertIsNone(self.coverage["physical_sites_independently_verified"])
        timarpur = self.nodes["ss-timarpur"]
        self.assertTrue(any(claim["status"] == "conflicted" for claim in timarpur["voltage_assertions"]))
        self.assertTrue(all(node["operational_status"] == "unknown" for node in self.nodes.values()))
        altered = deepcopy(self.inventory)
        altered["nodes"][0]["current_output_mw"] = 100
        with self.assertRaisesRegex(ValueError, "unknown"):
            validate_inventory(altered)


if __name__ == "__main__":
    unittest.main()
