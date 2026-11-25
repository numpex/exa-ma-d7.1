"""Catalogue-driven composition must preserve shared scientific sources and link scope."""
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.framework_portfolios import (ROOT, build_issues, external_labels, portfolios,
                                          render_index, render_sections, sync)


class PortfolioTests(unittest.TestCase):
    def test_all_active_frameworks_have_a_portfolio_including_empty_ones(self):
        result = portfolios()
        from scripts.framework_previews import frameworks
        self.assertEqual(set(result), set(frameworks()))
        self.assertEqual(result['funtides'], [])
        self.assertEqual(result['trust-platform'], [])
        self.assertEqual(result['uranie'], [])
        for excluded in ['arcane-framework', 'mahyco', 'manta', 'maphyspp', 'pbb']:
            self.assertNotIn(excluded, result)

    def test_every_explicit_sheet_association_is_included_once(self):
        result = portfolios()
        with (ROOT / 'data/applications.csv').open() as stream:
            apps = list(csv.DictReader(stream))
        from scripts.framework_publication import framework_id
        with (ROOT / 'data/frameworks.csv').open() as stream:
            names = {r['Name'].casefold(): framework_id(r['Name']) for r in csv.DictReader(stream)}
        for key, records in result.items():
            ids = [record['id'] for record in records]
            self.assertEqual(len(ids), len(set(ids)))
            expected = {row['id'] for row in apps
                        if key in {names.get(name.strip().casefold()) for name in row['Framework'].split(',')}}
            self.assertEqual(set(ids) - {'app-feelpp-discr-2'}, expected)
        shared = 'app-feelpp-ktirio-geom'
        self.assertIn(shared, [app['id'] for app in result['cgal']])
        self.assertIn(shared, [app['id'] for app in result['feelpp']])

    def test_feelpp_and_freefem_parmmg_are_distinct_applications(self):
        result = portfolios()
        feelpp = {app['id']: app for app in result['feelpp']}
        self.assertNotIn('app-freefem-parmmg', feelpp)
        self.assertIn('app-feelpp-parmmg', feelpp)
        self.assertEqual(feelpp['app-feelpp-parmmg']['status'], 'spec-only')
        self.assertEqual(feelpp['app-feelpp-parmmg']['Responsible (Permanent)'], '')
        self.assertEqual(feelpp['app-feelpp-parmmg']['evidence'], 'No benchmark record')
        self.assertIn('app-freefem-parmmg', [app['id'] for app in result['freefempp']])
        self.assertNotIn('app-feelpp-parmmg', [app['id'] for app in result['freefempp']])
        self.assertIn('app-feelpp-parmmg', [app['id'] for app in result['mmg-parmmg']])

    def test_parmmg_membership_is_grounded_in_the_sheet_snapshot(self):
        with (ROOT / 'data/applications.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        by_id = {row['id']: row for row in rows}
        self.assertNotIn('Feel++', by_id['app-freefem-parmmg']['Framework'])
        self.assertEqual(by_id['app-feelpp-parmmg']['Framework'], 'Feel++, MMG/ParMMG')
        self.assertEqual(by_id['app-feelpp-parmmg']['status'], 'spec-only')
        self.assertFalse((ROOT / 'data/standalone-application-review.json').exists())
        self.assertIn(r'\input{chapters/applications/metadata/app-feelpp-parmmg}',
                      (ROOT / 'chapters/applications/specs/app-feelpp-parmmg.tex').read_text())

    def test_repository_only_source_and_filename_alias_are_preserved(self):
        apps = {app['id']: app for app in portfolios()['feelpp']}
        self.assertEqual(apps['app-feelpp-discr-2']['status'], 'repository-only')
        self.assertEqual(apps['app-feelpp-thermoelectric-1']['spec'], 'app-feelpp-thermoelectric')
        self.assertEqual(apps['app-feelpp-rb']['status'], 'benchmark-ready')
        self.assertIn('validation pending', apps['app-feelpp-rb']['evidence'])
        index = render_index(list(apps.values()))
        self.assertIn('Repository only', index)
        self.assertIn(r'\hyperref[sec:app:specs:app-feelpp-rb]', index)
        self.assertIn('Catalogue stage', index)
        self.assertIn('Benchmark status', index)

    def test_generated_sections_reuse_sources_without_scientific_text(self):
        apps = portfolios()['cgal']
        content = render_sections(apps)
        self.assertEqual(content.count(r'\PortfolioApplication{'), len(apps))
        self.assertIn(r'\PortfolioApplication{app-feelpp-ktirio-geom}{app-feelpp-ktirio-geom}{}', content)
        self.assertNotIn('documentclass', content)
        self.assertNotIn('bibliography', content)

    def test_external_reference_import_excludes_all_local_and_cleveref_labels(self):
        report = ('\\newlabel{chap:wp1}{{1}{2}{WP1}{chapter.1}{}}\n'
                  '\\newlabel{app:fiche:shared}{{4}{99}{App}{section.4}{}}\n'
                  '\\newlabel{app:fiche:shared@cref}{{[section][4][]4}{99}}\n'
                  '\\citation{unrelated}\n')
        local = ('\\newlabel{app:fiche:shared}{{2}{4}{App}{section.2}{}}\n'
                 '\\newlabel{app:fiche:shared@cref}{{[section][2][]2}{4}}\n')
        filtered = external_labels(report, local)
        self.assertIn('chap:wp1', filtered)
        self.assertNotIn('shared', filtered)
        self.assertNotIn('citation', filtered)

    def test_generated_files_are_current(self):
        self.assertEqual(sync(), [])

    def test_reference_checks_distinguish_package_info_from_real_warnings(self):
        self.assertEqual(build_issues("Package acronym Info: Label is newly defined\nalthough it is yet undefined\n"), [])
        self.assertTrue(build_issues("LaTeX Warning: Reference `very-long-label'\nundefined on input line 50.\n"))
        self.assertTrue(build_issues("Package acronym Warning: Acronym exama is not defined on input line 50.\n"))
        self.assertTrue(build_issues("Missing character: There is no X in font\n"))

    def test_sync_refuses_authored_overwrites_and_removes_only_managed_orphans(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'sections').mkdir()
            (root / 'sections/abbreviations.tex').write_text(
                '\\begin{acronym}\\acro{FEM}{Finite element method}\\end{acronym}')
            with patch('scripts.framework_portfolios.portfolios', return_value={'example': []}):
                self.assertTrue(sync(root))
                self.assertEqual(sync(root, write=True), [])
                self.assertEqual(sync(root), [])
                target = root / 'standalone/portfolios/example-index.tex'
                target.write_text('An authored editorial contribution')
                with self.assertRaisesRegex(ValueError, 'Refusing to overwrite'):
                    sync(root, write=True)
                self.assertEqual(target.read_text(), 'An authored editorial contribution')

    def test_standalone_engine_does_not_load_another_document_or_per_app_bibliography(self):
        body = (ROOT / 'standalone/framework.tex').read_text()
        self.assertIn(r'\input{standalone/application-content}', body)
        self.assertEqual(body.count(r'\bibliography{references}'), 1)
        self.assertNotIn('standalone/application}', body)
        main = (ROOT / 'exa-ma-deliverables.tex').read_text()
        self.assertNotIn('standalone/portfolios', main)
        self.assertNotIn('standalone/framework', main)


if __name__ == '__main__':
    unittest.main()
