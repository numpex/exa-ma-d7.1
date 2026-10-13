"""Catalogue refresh must preserve authored content and benchmark evidence."""
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sync_applications", ROOT / "scripts/sync_applications.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class CatalogueRefreshTests(unittest.TestCase):
    def test_safe_repeatable_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename in ["data/application-reconciliation-v3.csv", "data/benchmark-registry-v3.csv",
                             "chapters/applications/registry.tex", "chapters/applications/cross-wp-matrix.tex",
                             "chapters/applications/benchmark-index.tex"]:
                target = root / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / filename, target)
            snapshot = ROOT / "data/applications.csv"
            initial = sync.plan(root, snapshot, ["app-samurai-cwipi"])
            self.assertFalse(any("/specs/" in str(path) for path in initial))
            self.assertFalse(any(path.name == "AGENTS.md" for path in initial))
            _, old_benchmarks = sync.read_csv(root / "data/benchmark-registry-v3.csv")
            for path, content in initial.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            self.assertEqual(initial, sync.plan(root, snapshot, ["app-samurai-cwipi"]))
            _, new_benchmarks = sync.read_csv(root / "data/benchmark-registry-v3.csv")
            self.assertEqual({r["benchmark_id"] for r in old_benchmarks},
                             {r["benchmark_id"] for r in new_benchmarks})
            for before, after in zip(old_benchmarks, new_benchmarks):
                for field in before:
                    if field not in {"responsible", "contributing_wps", "known_limitations"}:
                        self.assertEqual(before[field], after[field])
            metadata = root / "chapters/applications/metadata/app-samurai-cwipi.tex"
            metadata.write_text("Authored content: preserve me.\n")
            with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
                sync.plan(root, snapshot, ["app-samurai-cwipi"])
            self.assertEqual(metadata.read_text(), "Authored content: preserve me.\n")

    def test_invalid_snapshot_and_tex_escaping(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "invalid.csv"
            fields = ["id", "name", *dict.fromkeys(sync.FIELDS.values())]
            row = {field: "" for field in fields}
            row.update(id="app-a", name="A")
            snapshot.write_text(sync.csv_text(fields, [row, row]))
            with self.assertRaises(ValueError):
                sync.plan(ROOT, snapshot, [])
        self.assertEqual(sync.tex("50% & a_b #1"), r"50\% \& a\_b \#1")

    def test_missing_field_context_does_not_change_note_text(self):
        output = sync.metadata({"id": "app-samurai-cwipi"})
        self.assertIn(r"\todo[app-samurai-cwipi / WP7 Engineer]{Sheet field missing.}", output)
        self.assertIn(r"\todo[app-samurai-cwipi / repo\_url]{Sheet field missing.}", output)
        self.assertNotIn(r"\todo{Sheet field missing.}", output)

    def test_every_application_has_a_protected_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename in ["data/application-reconciliation-v3.csv", "data/benchmark-registry-v3.csv",
                             "chapters/applications/registry.tex", "chapters/applications/cross-wp-matrix.tex",
                             "chapters/applications/benchmark-index.tex"]:
                target = root / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / filename, target)
            source_dir = root / "chapters/applications/specs"
            source_dir.mkdir(parents=True)
            for source in (ROOT / "chapters/applications/specs").glob("*.tex"):
                shutil.copyfile(source, source_dir / source.name)
            snapshot = ROOT / "data/applications.csv"
            planned = sync.plan(root, snapshot, [], standalone=True)
            _, applications = sync.read_csv(root / "data/application-reconciliation-v3.csv")
            previews = {p.stem for p in planned if p.parent == root / "standalone/applications"}
            self.assertEqual(previews, {r["application_id"] for r in applications})
            self.assertIn(r"\def\ApplicationSpec{app-feelpp-thermoelectric}",
                          planned[root / "standalone/applications/app-feelpp-thermoelectric-1.tex"])
            self.assertIn(r"\def\ApplicationSpec{app-scimba-plasma}",
                          planned[root / "standalone/applications/app-scimba-plasma.tex"])
            self.assertNotIn("ApplicationGroupedSource",
                             planned[root / "standalone/applications/app-scimba-plasma.tex"])
            self.assertIn(root / "chapters/applications/metadata/app-kinetic-moment-closure.tex", planned)
            for path, content in planned.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            self.assertEqual(planned, sync.plan(root, snapshot, [], standalone=True))
            authored = root / "standalone/applications/app-samurai-cwipi.tex"
            authored.write_text("Custom preview: preserve me.\n")
            with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
                sync.plan(root, snapshot, [], standalone=True)
            self.assertEqual(authored.read_text(), "Custom preview: preserve me.\n")


if __name__ == "__main__":
    unittest.main()
