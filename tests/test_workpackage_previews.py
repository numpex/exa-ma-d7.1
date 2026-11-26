"""Cross-PDF references must resolve without stealing local labels or citations."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.workpackage_previews import build, diagnostics, external_labels, read_labels


class WorkPackageTests(unittest.TestCase):
    def test_import_preserves_external_cref_but_excludes_local_labels_and_citations(self):
        report = (
            '\\newlabel{local}{{3.1}{50}{Local}{section.3.1}{}}\n'
            '\\newlabel{local@cref}{{[section][1][3]3.1}{50}}\n'
            '\\newlabel{external}{{9.2}{150}{Other}{section.9.2}{}}\n'
            '\\newlabel{external@cref}{{[section][2][9]9.2}{150}}\n'
            '\\newlabel{LastPage}{{}{499}{}{page.499}{}}\n'
            '\\bibcite{paper}{1}\n\\citation{unrelated}\n')
        local = '\\newlabel{local}{{1.1}{4}{Local}{section.1.1}{}}\n'
        local += '\\newlabel{local@cref}{{[section][1][1]1.1}{4}}\n'
        result = external_labels(report, local)
        self.assertIn('external@cref', result)
        self.assertIn('{section.9.2}', result)
        for excluded in ['{local}', '{local@cref}', 'LastPage', 'bibcite', 'citation']:
            self.assertNotIn(excluded, result)

    def test_scope_change_reclassifies_labels_on_next_build(self):
        report = '\\newlabel{moving}{{3}{10}{Title}{section.3}{}}\n'
        self.assertNotIn('moving', external_labels(report, report))
        self.assertIn('moving', external_labels(report, ''))

    def test_nested_auxiliaries_are_followed_and_cycles_terminate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'main.aux').write_text('\\@input{child.aux}\n\\citation{irrelevant}\n')
            (root / 'child.aux').write_text('\\newlabel{nested}{{2}{3}}\n\\@input{main.aux}\n')
            labels = read_labels(root / 'main.aux')
            self.assertEqual(labels.count('nested'), 1)
            self.assertNotIn('citation', labels)

    def test_real_diagnostics_fail_but_package_information_and_layout_do_not(self):
        for message in ["LaTeX Warning: Reference `long-label'\nundefined on input line 10.",
                        "Package apacite Warning: Citation `paper' undefined.",
                        'Package acronym Warning: Acronym FEM is not defined.',
                        'LaTeX Warning: There were multiply defined labels.',
                        'Package xr Warning: LABELS NOT IMPORTED.',
                        'file.tex:10: LaTeX Error: Missing item.',
                        'Missing character: There is no X in font Y.',
                        'pdfTeX warning: destination with the same identifier (page.1)']:
            with self.subTest(message=message):
                self.assertTrue(diagnostics(message))
        self.assertEqual(diagnostics('Package acronym Info: Label is yet undefined\n\n'
                                     'Overfull \\hbox (2.0pt too wide)\n\n'
                                     'Package fancyhdr Warning: headheight is too small.'), [])

    def test_invalid_report_stops_before_building_or_packaging_wps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'exa-ma-deliverables.log').write_text(
                "LaTeX Warning: Reference `missing' undefined.\n")
            with patch('scripts.workpackage_previews.run') as runner:
                with self.assertRaisesRegex(ValueError, 'Invalid PDF'):
                    build(root=root, wps=[4])
                self.assertEqual(runner.call_count, 1)
            self.assertEqual(list(root.rglob('*.zip')), [])


if __name__ == '__main__':
    unittest.main()
