import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts import framework_publication as policy
from scripts.framework_previews import frameworks, sync, wrapper


class PublicationTests(unittest.TestCase):
    def catalogue(self, root, flag='TRUE'):
        (root / 'data').mkdir(exist_ok=True)
        with (root / 'data/frameworks.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['Name', 'Description', policy.FIELD])
            writer.writerow(['Example', 'Scientific text, unchanged', flag])

    def test_disable_and_reactivate_preserve_scientific_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'software/example/example.tex'
            source.parent.mkdir(parents=True)
            source.write_text('Scientific content and citation keys')
            self.catalogue(root)
            sync(root, frameworks(root), write=True)
            target = root / 'standalone/frameworks/example.tex'
            self.assertTrue(target.exists())
            self.catalogue(root, 'FALSE')
            self.assertEqual(frameworks(root), {})
            sync(root, frameworks(root), write=True)
            self.assertFalse(target.exists())
            policy.sync(root, write=True)
            self.assertIn(r'ExamaFrameworkIncluded@example\endcsname{0}',
                          (root / 'software/framework-publication.tex').read_text())
            self.catalogue(root)
            sync(root, frameworks(root), write=True)
            self.assertEqual(target.read_text(), wrapper('example'))
            self.assertEqual(source.read_text(), 'Scientific content and citation keys')

    def test_invalid_flags_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for flag in ('', 'maybe'):
                self.catalogue(root, flag)
                with self.assertRaisesRegex(ValueError, 'TRUE or FALSE'):
                    policy.publication_flags(root)
            (root / 'data/frameworks.csv').write_text('Name\nExample\n')
            with self.assertRaisesRegex(ValueError, 'missing'):
                policy.publication_flags(root)

    def test_missing_and_duplicate_names_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.catalogue(root)
            source = root / 'software/unknown/unknown.tex'
            source.parent.mkdir(parents=True)
            source.touch()
            with self.assertRaisesRegex(ValueError, 'missing from the publication catalogue'):
                frameworks(root)
            with (root / 'data/frameworks.csv').open('a') as stream:
                stream.write('Example,duplicate,TRUE\n')
            with self.assertRaisesRegex(ValueError, 'duplicate framework'):
                policy.publication_flags(root)

    def test_authored_inactive_wrapper_is_never_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'standalone/frameworks/example.tex'
            target.parent.mkdir(parents=True)
            target.write_text('Custom authored wrapper')
            with self.assertRaisesRegex(ValueError, 'Refusing to remove authored'):
                sync(root, {}, write=True)
            self.assertEqual(target.read_text(), 'Custom authored wrapper')

    def test_sheet_refresh_changes_only_publication_values(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.catalogue(root)
            provenance = root / 'data/frameworks-source.json'
            provenance.write_text(json.dumps({'spreadsheet_url':
                'https://docs.google.com/spreadsheets/d/example/edit', 'sheet_id': 0}))
            remote = 'Name,Description,Include in deliverable\nExample,unrelated live change,FALSE\n'
            policy.refresh_sheet(root, fetch=lambda url: remote)
            rows = list(csv.DictReader(io.StringIO((root / 'data/frameworks.csv').read_text())))
            self.assertEqual(rows, [{'Name': 'Example', 'Description': 'Scientific text, unchanged',
                                      policy.FIELD: 'FALSE'}])
            self.assertEqual(json.loads(provenance.read_text())['entry_refreshes']
                             ['publication_scope']['changed_fields'], [policy.FIELD])
            before = (root / 'data/frameworks.csv').read_bytes()
            for invalid in (remote.replace('FALSE', ''), remote.replace('Example', 'New example'),
                            remote.replace(policy.FIELD, 'Missing column')):
                with self.assertRaises(ValueError):
                    policy.refresh_sheet(root, fetch=lambda url: invalid)
                self.assertEqual((root / 'data/frameworks.csv').read_bytes(), before)

    def test_repository_publication_policy(self):
        root = Path(__file__).resolve().parents[1]
        flags = policy.publication_flags(root)
        active = frameworks(root)
        for source in (root / 'software').glob('*/*.tex'):
            if source.stem != source.parent.name or source.stem == 'maphyspp':
                continue
            self.assertEqual(source.stem in active, flags[source.stem])
        self.assertEqual({p.stem for p in (root / 'standalone/frameworks').glob('*.tex')},
                         set(active))
        self.assertEqual(policy.sync(root), [])
