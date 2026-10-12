from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_dependencies import inventory, scan, is_informational

class DependencyAuditTests(unittest.TestCase):
    def test_inventory_resolves_catalog_aliases_and_excludes_local_crates(self):
        catalog = dict(versions=dict(v='1.0'), libraries=dict(a={'module':'g:a','version':{'ref':'v'}}, b={'module':'g:a','version':'1.0'}))
        cargo = {'package':[{'name':'r','version':'2','source':'registry+https://github.com/rust-lang/crates.io-index'}, {'name':'local','version':'1'}]}
        queries = inventory(catalog, cargo)
        self.assertEqual(len(queries), 2)
        self.assertEqual(queries[0]['version'], '1.0')

    def test_pagination_keeps_result_mapping(self):
        queries = [dict(package=dict(name='a'),version='1'),dict(package=dict(name='b'),version='2')]
        calls=[]
        def fetch(path, payload=None):
            calls.append((path,payload))
            if path.startswith('vulns/'):
                return dict(id=path.split('/')[-1], affected=[{}])
            if len(calls)==1:
                return {'results':[{'vulns':[{'id':'ONE'}], 'next_page_token':'next'},{}]}
            self.assertEqual(payload['queries'],[dict(queries[0], page_token='next')])
            return {'results':[{'vulns':[{'id':'TWO'}]}]}
        rows,details=scan(queries,fetch)
        self.assertEqual(rows[0]['advisory_ids'],['ONE','TWO'])
        self.assertEqual(rows[1]['advisory_ids'],[])
        self.assertEqual(set(details),{'ONE','TWO'})

    def test_rejects_incomplete_network_response(self):
        with self.assertRaises(ValueError):
            scan([{}],lambda *args: {'results':[]})

    def test_rejects_repeating_page_tokens(self):
        with self.assertRaisesRegex(ValueError,'pagination'):
            scan([{}],lambda *args: {'results':[{'next_page_token':'same'}]})

    def test_maintenance_notice_does_not_hide_vulnerability(self):
        self.assertTrue(is_informational({'affected':[{'database_specific':{'informational':'unmaintained'}}]}))
        self.assertFalse(is_informational({'affected':[{'database_specific':{'informational':'unmaintained'}},{}]}))
        self.assertFalse(is_informational({'affected':[]}))
