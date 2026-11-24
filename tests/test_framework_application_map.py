"""Navigation must reflect catalogue associations, publication scope and fiche aliases."""
import csv
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import framework_application_map as mapping

ROOT = Path(__file__).resolve().parents[1]


class FrameworkApplicationMapTests(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory)
        for name in ('data/frameworks.csv', 'data/applications.csv',
                     'data/application-reconciliation-v3.csv', 'chapters/software.tex'):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        shutil.copytree(ROOT / 'software', root / 'software')
        shutil.copytree(ROOT / 'chapters/applications/specs', root / 'chapters/applications/specs')
        return root

    def update(self, root, name, mutate):
        path = root / 'data' / name
        fields, rows = mapping.read_csv(path)
        mutate(rows)
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_aliases_resolve_to_real_fiches_and_no_benchmark_evidence_is_invented(self):
        text = mapping.render(ROOT)
        self.assertIn(r'\hyperref[sec:app:specs:app-feelpp-thermoelectric-1]', text)
        self.assertIn(r'\hyperref[sec:app:specs:app-composyx-diffusion]', text)
        self.assertIn(r'\hyperref[chap:wp7]', text)
        self.assertIn('Specification', text)
        self.assertNotIn('CPU+GPU demonstrators', text)
        self.assertEqual((ROOT / mapping.TARGET).read_text(), text)

    def test_catalogue_edit_changes_association_wp_and_stage_without_editing_fiche(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            source = root / 'chapters/applications/specs/app-feelpp-distance.tex'
            before = source.read_bytes()
            def change(rows):
                app = next(row for row in rows if row['id'] == 'app-feelpp-distance')
                app.update(Framework='Uranie', work_package='WP6', status='brainstorming',
                           name='Changed catalogue title')
            self.update(root, 'applications.csv', change)
            text = mapping.render(root)
            row = next(line for line in text.splitlines() if 'Changed catalogue title' in line)
            self.assertIn(r'\hyperref[sec:Uranie:software]', row)
            self.assertIn(r'\hyperref[chap:wp6]', row)
            self.assertIn('Concept', row)
            self.assertEqual(source.read_bytes(), before)

    def test_disabled_framework_is_removed_and_reactivation_restores_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            def disable(rows):
                next(row for row in rows if row['Name'] == 'Feel++')['Include in deliverable'] = 'FALSE'
            self.update(root, 'frameworks.csv', disable)
            self.assertNotIn(r'\hyperref[sec:Feelpp:software]', mapping.render(root))
            def enable(rows):
                next(row for row in rows if row['Name'] == 'Arcane')['Include in deliverable'] = 'TRUE'
            self.update(root, 'frameworks.csv', enable)
            self.assertIn(r'\hyperref[sec:Arcane Framework:software]', mapping.render(root))

    def test_missing_association_is_reported_not_guessed_from_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            def change(rows):
                app = next(row for row in rows if row['id'] == 'app-feelpp-distance')
                app.update(Framework='', name='Feel++ application without a Framework field')
            self.update(root, 'applications.csv', change)
            text = mapping.render(root)
            tail = text.split('Catalogue associations to complete.')[1]
            self.assertIn('Feel++ application without a Framework field', tail)
            self.assertNotIn('Feel++ application without a Framework field', text.split(r'\end{longtable}')[0])

    def test_missing_fiche_label_fails_instead_of_emitting_broken_hyperlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            (root / 'chapters/applications/specs/app-feelpp-distance.tex').write_text('Unlabelled fiche')
            with self.assertRaisesRegex(ValueError, 'No application navigation label'):
                mapping.render(root)

    def test_authored_output_is_protected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            (root / mapping.TARGET).write_text('An authored table')
            with self.assertRaisesRegex(ValueError, 'Refusing to overwrite'):
                mapping.sync(root)


if __name__ == '__main__':
    unittest.main()
