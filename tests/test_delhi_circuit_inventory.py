"""Offline circuit and audit contracts; official source originals are not required."""

from copy import deepcopy
import hashlib
import json
import unittest

from scripts.build_delhi_circuit_inventory import circuit_label, numeric_length, validate_circuits
from scripts.build_delhi_node_inventory import DEFAULT_ARCHIVE, DEFAULT_OUTPUT


class DelhiCircuitInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads((DEFAULT_OUTPUT/'circuits.json').read_text())
        cls.nodes = json.loads((DEFAULT_OUTPUT/'nodes.json').read_text())
        cls.audit = json.loads((DEFAULT_OUTPUT/'topology_audit.json').read_text())
        cls.issues = json.loads((DEFAULT_OUTPUT/'circuit_issues.json').read_text())['issues']
        cls.rows = cls.document['circuits']

    def test_portion_lengths_are_not_whole_routes_or_ratings(self):
        self.assertIsNone(numeric_length('5.544 (DTL) + 28.791 (Powergrid)'))
        self.assertIsNone(numeric_length('---'))
        self.assertIsNone(numeric_length('\ufeff---\ufeff'))
        self.assertEqual(numeric_length('0'), 0)
        self.assertEqual(numeric_length('40.905'), 40.905)
        row = next(r for r in self.rows if r['source_id']=='SRC-03' and r['source_serial']==5)
        self.assertIsNone(row['source_reported_lengths']['total_numeric_km'])
        self.assertIn('portion', row['source_reported_lengths']['scope'])
        self.assertIsNone(row['thermal_limit_mw'])

    def test_circuit_suffixes_do_not_invent_missing_numbers(self):
        self.assertEqual(circuit_label('Wazirabad - Mandaula Ckt-IV'), 'IV')
        self.assertEqual(circuit_label('Peeragarhi - Wazirpur Ckt.-II'), 'II')
        self.assertIsNone(circuit_label('Gazipur - Patparganj Ckt-'))
        self.assertIsNone(circuit_label('Naraina - Ridge Valley Ckt'))

    def test_exact_source_row_coverage_with_parallel_circuits(self):
        for sid, voltage, count in [('SRC-03',400,14), ('SRC-04',220,115), ('SRC-01',400,12), ('SRC-01',220,101)]:
            rows = [r for r in self.rows if r['source_id']==sid and r['voltage_kv']==voltage]
            self.assertEqual(sorted(r['source_serial'] for r in rows), list(range(1,count+1)))
        parallel = [r for r in self.rows if r['source_id']=='SRC-04' and r['source_serial'] in [107,108,109,110]]
        self.assertEqual({r['circuit_label'] for r in parallel}, {'I','II','III','IV'})
        self.assertEqual(len({tuple(r['endpoint_node_ids']) for r in parallel}), 1)
        self.assertEqual(len({r['id'] for r in parallel}), 4)

    def test_source_duplicate_is_preserved_and_flagged(self):
        pair = [r for r in self.rows if r['source_id']=='SRC-04' and r['source_serial'] in [88,89]]
        self.assertEqual([r['circuit_label'] for r in pair], ['I','I'])
        duplicate = next(i for i in self.issues if i['id'].startswith('DUPLICATE-'))
        self.assertEqual(set(duplicate['circuit_observation_ids']), {r['id'] for r in pair})
        self.assertTrue(all(duplicate['id'] in r['issue_ids'] for r in pair))

    def test_every_observation_has_source_hash_and_locator(self):
        manifest = json.loads((DEFAULT_ARCHIVE/'manifest.json').read_text())
        sources = {s['id']:s for s in manifest['sources']}
        for row in self.rows:
            ev = self.document['evidence'][row['evidence_id']]
            self.assertEqual(ev['source_sha256'], sources[row['source_id']]['sha256'])
            self.assertTrue(ev['locator'])
            self.assertTrue(ev['retrieved_at'])
        for filename, field in [('nodes.json','nodes_sha256'),('historical_circuit_review.json','historical_review_sha256'),('supplemental_connection_review.json','supplemental_review_sha256')]:
            self.assertEqual(hashlib.sha256((DEFAULT_OUTPUT/filename).read_bytes()).hexdigest(), self.document[field])
        self.assertEqual(hashlib.sha256((DEFAULT_ARCHIVE/'manifest.json').read_bytes()).hexdigest(),self.document['source_manifest_sha256'])
        self.assertEqual(hashlib.sha256((DEFAULT_OUTPUT/'circuits.json').read_bytes()).hexdigest(),self.audit['circuit_document_sha256'])

    def test_cross_date_observations_and_owner_endpoints_remain_separate(self):
        later = next(r for r in self.rows if r['source_id']=='SRC-03' and r['source_serial']==11)
        older = next(r for r in self.rows if r['source_id']=='SRC-01' and r['voltage_kv']==400 and r['source_serial']==7)
        self.assertIn('candidate-ballabhgarh-400', later['endpoint_node_ids'])
        self.assertIn('ss-samaypur-pgcil', older['endpoint_node_ids'])
        self.assertNotEqual(older['temporal_class'],later['temporal_class'])
        bbmb = [r for r in self.rows if r['source_id']=='SRC-13']
        self.assertEqual(len(bbmb),3)
        self.assertTrue(all('ss-narela-bbmb' in r['endpoint_node_ids'] for r in bbmb))
        self.assertTrue(all('ss-narela-dtl' not in r['endpoint_node_ids'] for r in bbmb))

    def test_unresolved_rows_and_disconnected_nodes_are_visible(self):
        self.assertEqual(self.audit['later_rows_with_unresolved_endpoints'],12)
        self.assertEqual(len([i for i in self.issues if i['id'].startswith('CIRCUIT-LABEL-')]),4)
        isolated = self.audit['later_table_adjacency']['isolated_node_ids']
        self.assertIn('plant-pps3-bawana',isolated)
        self.assertIn('ss-dwarka-sector-5',isolated)
        components = self.audit['later_table_adjacency']['connected_components']
        flattened = [node for component in components for node in component]
        self.assertEqual(set(flattened),{n['id'] for n in self.nodes['nodes']})
        self.assertEqual(len(flattened),len(set(flattened)))

    def test_audit_does_not_certify_record_counts_or_electrical_readiness(self):
        self.assertEqual(self.audit['integration_gate'],'not_passed')
        self.assertFalse(self.audit['full_reference_completeness_verified'])
        self.assertFalse(self.audit['goal_50_verified_delhi_nodes_achieved'])
        self.assertIsNone(self.audit['independently_verified_delhi_physical_site_count'])
        self.assertTrue(self.audit['remaining_evidence_tasks'])
        validate_circuits(self.document,self.nodes)
        for field,value in [('thermal_limit_mw',300),('simulation_eligible',True),('operational_status','online'),('endpoint_node_ids',['missing','ss-bamnauli']),('evidence_id','missing')]:
            with self.subTest(field=field):
                bad = deepcopy(self.document)
                bad['circuits'][0][field]=value
                with self.assertRaises(ValueError): validate_circuits(bad,self.nodes)

    def test_reference_narratives_do_not_create_inferred_circuits(self):
        claims = json.loads((DEFAULT_OUTPUT/'reference_connection_claims.json').read_text())
        self.assertEqual(len(claims['reference_connection_claims']),7)
        for claim in claims['reference_connection_claims']:
            self.assertFalse(claim['electrical_edges_created'])
            self.assertIn(claim['evidence_id'],self.document['evidence'])
        self.assertEqual(claims['unreconciled_map_scope']['status'],'not_fully_reconciled')


if __name__=='__main__': unittest.main()
