"""Reference schema contracts and separation from the operational teaching model."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

import networkx as nx

from prism.grid.model import synthetic_grid, validate_grid
from prism.grid.reference import DIRECTORY, build_reference, canonical, fingerprint, validate_reference
from prism.grid.reference_store import entity_rows


def reseal(payload):
    payload.pop('dataset',None)
    payload.pop('content_sha256',None)
    payload['content_sha256']=fingerprint(payload)
    payload['dataset']='delhi_reference_'+payload['content_sha256']
    return payload


class ReferenceGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload=build_reference()

    def test_deterministic_export_and_snapshot_identity(self):
        saved=json.loads((DIRECTORY/'reference_dataset.json').read_text())
        self.assertEqual(saved,self.payload)
        self.assertEqual(build_reference(),self.payload)
        self.assertEqual(validate_reference(self.payload).number_of_edges(),261)
        changed=deepcopy(self.payload)
        changed['assurance']+=' Updated review.'
        reseal(changed)
        self.assertNotEqual(changed['dataset'],self.payload['dataset'])

    def test_parallel_observations_unknowns_and_islands_are_preserved(self):
        graph=validate_reference(self.payload)
        self.assertIsInstance(graph,nx.MultiGraph)
        self.assertEqual(graph.number_of_nodes(),66)
        self.assertEqual(graph.number_of_edges(),261)
        self.assertNotIn('ss-wazirabad',graph)
        self.assertGreater(graph.number_of_edges('ss-south-of-wazirabad','ss-mandola-pgcil'),1)
        self.assertEqual(graph.degree('ss-timarpur'),0)
        self.assertIsNone(graph.nodes['ss-timarpur']['current_output_mw'])
        with self.assertRaises(ValueError): validate_grid(self.payload)
        self.assertEqual(validate_grid(synthetic_grid()).number_of_edges(),12)

    def test_corroboration_resolves_only_supported_metadata(self):
        assets={a['id']:a for a in self.payload['assets']}
        timarpur=assets['ss-timarpur']
        self.assertEqual(timarpur['corroborated_nominal_voltage_kv'],220)
        self.assertEqual(timarpur['operational_status'],'unknown')
        self.assertNotIn('NODE-TIMARPUR-VOLTAGE',timarpur['open_issue_ids'])
        sow=assets['ss-south-of-wazirabad']
        self.assertTrue(any(o.get('reconciliation_id')=='REC-SOW' and o['node_id']==sow['id'] for o in sow['transformation_observations']))
        self.assertEqual(self.payload['remaining_node_issue_ids'],[])
        self.assertIn('NODE-BUDELLA-STATUS',self.payload['resolved_reference_issue_ids'])
        self.assertEqual(assets['ss-budella']['reference_classification'],'planned_as_of_2025_06_25')
        # Source extraction remains unchanged; corroboration is a separate overlay.
        original=json.loads((DIRECTORY/'transformation_mentions.json').read_text())
        self.assertIsNone(next(o for o in original['observations'] if o['source_id']=='SRC-06' and o['source_serial']==35)['node_id'])

    def test_circuit_multiplicity_does_not_rewrite_source_labels(self):
        rows=[r for r in self.payload['circuit_observations'] if r['source_id']=='SRC-04']
        for serial in [27,40,41,57]:
            row=next(r for r in rows if r['source_serial']==serial)
            self.assertIsNone(row['circuit_label'])
            self.assertEqual(row['source_declared_multiplicity'],'single')
        for serial in [88,89]:
            row=next(r for r in rows if r['source_serial']==serial)
            self.assertEqual(row['circuit_label'],'I')
            self.assertEqual(row['source_declared_multiplicity'],'double')

    def test_corrupt_or_resealed_invalid_data_is_rejected(self):
        bad=deepcopy(self.payload);bad['assets'][0]['name']='changed'
        with self.assertRaisesRegex(ValueError,'fingerprint'): validate_reference(bad)
        for target,field,value in [('assets','simulation_eligible',True),('assets','current_output_mw',0),('assets','kind','load'),('circuit_observations','thermal_limit_mw',200),('circuit_observations','endpoint_node_ids',['missing','ss-bamnauli']),('circuit_observations','direction','directed')]:
            with self.subTest(field=field):
                bad=deepcopy(self.payload);bad[target][0][field]=value;reseal(bad)
                with self.assertRaises(ValueError):validate_reference(bad)
        for target in ['assets','circuit_observations']:
            bad=deepcopy(self.payload);bad[target].append(deepcopy(bad[target][0]));reseal(bad)
            with self.assertRaises(ValueError):validate_reference(bad)

    def test_neo4j_property_encoding_is_lossless_and_has_two_endpoints(self):
        entities,endpoints=entity_rows(self.payload)
        self.assertEqual(len(entities),327)
        self.assertEqual(len(endpoints),522)
        self.assertEqual({json.loads(e['record_json'])['id'] for e in entities},{e['id'] for e in entities})
        source={a['id']:a for a in self.payload['assets']}
        for entity in entities:
            if entity['entity_type']=='asset':self.assertEqual(json.loads(entity['record_json']),source[entity['id']])
        for row in self.payload['circuit_observations']:
            links=[e for e in endpoints if e['circuit_id']==row['id']]
            self.assertEqual([e['position'] for e in links],[1,2])
            self.assertEqual([e['asset_id'] for e in links],row['endpoint_node_ids'])

    def test_identity_aliases_redirect_without_discarding_source_records(self):
        assets={a['id']:a for a in self.payload['assets']}
        aliases=self.payload['identity_resolution']['aliases']
        self.assertEqual(aliases,{'candidate-dwarka':'ss-dwarka-sector-5','candidate-ballabhgarh-400':'ss-samaypur-pgcil','ss-wazirabad':'ss-south-of-wazirabad'})
        for old,new in aliases.items():
            self.assertNotIn(old,assets)
            self.assertIn(old,assets[new]['merged_inventory_ids'])
            self.assertTrue(any(r['id']==old for r in assets[new]['merged_source_records']))
        self.assertTrue(any('candidate-dwarka' in c.get('source_endpoint_node_ids',[]) for c in self.payload['circuit_observations']))
        original=json.loads((DIRECTORY/'nodes.json').read_text())
        self.assertEqual(len(original['nodes']),64)
        self.assertIn('candidate-dwarka',{a['id'] for a in original['nodes']})
        self.assertTrue(all(not set(c['endpoint_node_ids']) & aliases.keys() for c in self.payload['circuit_observations']))

    def test_owner_sections_and_external_voltage_identities_are_distinct(self):
        assets={a['id']:a for a in self.payload['assets']}
        self.assertEqual(assets['ss-narela-dtl']['reference_site_group'],assets['ss-narela-bbmb']['reference_site_group'])
        self.assertIn('ss-ballabhgarh-bbmb',assets)
        self.assertIn('ss-samaypur-pgcil',assets)
        self.assertIn('ss-dadri-ntpc',assets)
        self.assertIn('ss-dadri-pgcil',assets)
        narela=next(i for i in self.payload['topology_interfaces'] if i['id']=='interface-narela-extended-bus')
        self.assertEqual(narela['kind'],'bus_extension')

    def test_report_counts_assets_without_counting_aliases_plans_or_external_nodes(self):
        coverage=self.payload['topology_coverage']
        counted=coverage['counted_delhi_asset_ids']
        self.assertEqual(len(set(counted)),50)
        self.assertNotIn('ss-narela-bbmb',counted)
        self.assertNotIn('ss-budella',counted)
        self.assertNotIn('plant-jhajjar',counted)
        self.assertIn('plant-pps1',counted)
        self.assertIsNone(coverage['physical_site_count'])
        self.assertFalse(coverage['complete_current_operating_network_verified'])
        self.assertEqual(coverage['historical_comparison_findings_accounted'],15)
        self.assertEqual(len(coverage['endpoint_issue_ids_reconciled']),12)

    def test_plant_interfaces_preserve_historical_terminal_details(self):
        interfaces={i['id']:i for i in self.payload['topology_interfaces']}
        self.assertIn('Bay 419',interfaces['interface-pps3-bawana']['detail'])
        self.assertEqual(interfaces['interface-pps1-pragati']['endpoint_node_ids'],['plant-pps1','ss-pragati'])
        self.assertIn('Bus-I',interfaces['interface-pps1-pragati']['detail'])
        self.assertEqual(interfaces['interface-jhajjar-mundka']['endpoint_node_ids'],['plant-jhajjar','ss-tikri-kalan'])
        self.assertEqual(interfaces['interface-btps-alwar']['kind'],'historical_isolated_line')
        bad=deepcopy(self.payload);bad['topology_interfaces'][0]['measured_flow_mw']=20;reseal(bad)
        with self.assertRaises(ValueError):validate_reference(bad)

    def test_identity_evidence_checksum_mismatch_is_rejected(self):
        from tempfile import TemporaryDirectory
        from prism.grid.reconciliation import apply_identity_review
        review=json.loads((DIRECTORY/'identity_resolution.json').read_text())
        review['identity_resolutions'][0]['evidence'][0]['sha256']='0'*64
        with TemporaryDirectory() as tmp:
            directory=Path(tmp)
            (directory/'identity_resolution.json').write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):
                apply_identity_review(deepcopy(self.payload),directory)


if __name__=='__main__': unittest.main()
