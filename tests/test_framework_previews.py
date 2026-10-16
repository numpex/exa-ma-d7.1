import tempfile
import unittest
from pathlib import Path
from scripts.framework_previews import frameworks, selected, sync, wrapper


class FrameworkPreviewTests(unittest.TestCase):
    def test_discovers_fiches_not_metadata_or_implementation_fragments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'software/example'
            folder.mkdir(parents=True)
            for name in ('example', 'metadata', 'implementation'):
                (folder / (name + '.tex')).write_text('authored text')
            self.assertEqual(frameworks(root), {'example': 'software/example/example.tex'})

    def test_software_and_wrapper_changes_select_only_affected_frameworks(self):
        catalogue = {'feelpp': '', 'funtides': '', 'samurai': ''}
        self.assertEqual(selected(['software/feelpp/implementation-2026.tex',
                                   'standalone/frameworks/samurai.tex'], catalogue),
                         ['feelpp', 'samurai'])
        self.assertEqual(selected(['standalone-funtides.tex'], catalogue), ['funtides'])

    def test_former_maphys_name_selects_composyx_without_duplicate(self):
        self.assertEqual(selected(['software/maphyspp/maphyspp.tex'],
                                  {'composyx': ''}), ['composyx'])
        self.assertNotIn('maphyspp', frameworks())
        self.assertIn('composyx', frameworks())
        self.assertNotIn('pbb', frameworks())

    def test_report_scope_excludes_arcane_mahyco_and_pbb_but_keeps_trust(self):
        catalogue = frameworks()
        for slug in ('arcane-framework', 'mahyco', 'pbb'):
            self.assertNotIn(slug, catalogue)
            self.assertEqual(selected([f'software/{slug}/{slug}.tex'], catalogue), [])
        self.assertIn('trust-platform', catalogue)
        self.assertEqual(selected(['software/trust-platform/trust-platform.tex'], catalogue),
                         ['trust-platform'])

    def test_shared_dependencies_and_release_select_all(self):
        catalogue = {'samurai': '', 'feelpp': ''}
        for paths in (None, ['defs.tex'], ['references.bib'], ['graphics/common.png'],
                      ['.github/workflows/latex.yml'], ['standalone/framework-preamble.tex']):
            self.assertEqual(selected(paths, catalogue), ['feelpp', 'samurai'])
        self.assertEqual(selected([], catalogue), [])

    def test_unrelated_chapter_and_readme_do_not_expand_selection(self):
        self.assertEqual(selected(['software/feelpp/feelpp.tex', 'chapters/WP1/WP1.tex',
                                   'README.adoc'], {'feelpp': '', 'samurai': ''}), ['feelpp'])
        self.assertEqual(selected(['chapters/WP1/WP1.tex'], {'feelpp': ''}), [])

    def test_deleted_framework_is_not_built(self):
        self.assertEqual(selected(['software/removed/removed.tex'], {'feelpp': ''}), [])

    def test_wrappers_preserve_editorial_source_and_refuse_authored_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'software/example/example.tex'
            path.parent.mkdir(parents=True)
            path.write_text('existing scientific text')
            catalogue = frameworks(root)
            self.assertTrue(sync(root, catalogue))
            self.assertEqual(sync(root, catalogue, write=True), [])
            self.assertEqual(sync(root, catalogue), [])
            self.assertEqual(path.read_text(), 'existing scientific text')
            target = root / 'standalone/frameworks/example.tex'
            self.assertEqual(target.read_text(), wrapper('example'))
            target.write_text('custom authored wrapper')
            with self.assertRaises(ValueError):
                sync(root, catalogue, write=True)

    def test_orphan_wrapper_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'standalone/frameworks'
            folder.mkdir(parents=True)
            (folder / 'missing.tex').write_text(wrapper('missing'))
            self.assertIn('Orphan wrapper', sync(root, {})[0])

    def test_repository_wrappers_are_current(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(sync(root, frameworks(root)), [])
