from pathlib import Path
import tempfile
import unittest

from scripts.audit_dependencies import inventory, scan


class DependencyAuditTests(unittest.TestCase):
    def test_inventory_resolves_refs_and_records_omitted_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'gradle').mkdir()
            (root / 'Cargo.lock').write_text('''[[package]]
name = "registry-crate"
version = "1.2.3"
source = "registry+https://github.com/rust-lang/crates.io-index"
[[package]]
name = "git-crate"
version = "1.0.0"
source = "git+https://example.invalid/source"
[[package]]
name = "private-registry"
version = "2.0.0"
source = "registry+https://example.invalid/index"
''')
            (root / 'gradle/libs.versions.toml').write_text('''[versions]
okhttp = "5.5.0"
[libraries]
client = { module = "com.squareup.okhttp3:okhttp", version.ref = "okhttp" }
duplicate = { module = "com.squareup.okhttp3:okhttp", version = "5.5.0" }
bom-managed = { module = "example:managed" }
''')
            queries, hashes, omitted = inventory(root)
            self.assertEqual(len(queries), 2)
            self.assertEqual(queries[1]['version'], '5.5.0')
            self.assertEqual(len(omitted), 3)
            self.assertEqual(len(hashes['Cargo.lock']), 64)

    def test_all_batches_are_scanned_without_dropping_matches(self):
        queries = [{'version': str(n)} for n in range(205)]
        sizes = []
        def request(batch):
            sizes.append(len(batch))
            return {'results': [{'vulns': [{'id': 'example-' + q['version']}]} for q in batch]}
        results = scan(queries, request)
        self.assertEqual(sizes, [100, 100, 5])
        self.assertEqual(results[-1]['advisories'][0]['id'], 'example-204')

    def test_partial_paginated_and_malformed_responses_fail_closed(self):
        for response in ({}, {'results': []}, {'results': [None]},
                         {'results': [{'next_page_token': 'more'}]},
                         {'results': [{'error': 'failed'}]},
                         {'results': [{'vulns': [{}]}]}):
            with self.subTest(response=response), self.assertRaises(ValueError):
                scan([{'version': '1'}], lambda _: response)

    def test_empty_osv_result_means_no_known_advisory(self):
        self.assertEqual(scan([{'version': '1'}], lambda _: {'results': [{}]})[0]['advisories'], [])
