"""Release preparation must synchronize active metadata without rewriting history."""
import tempfile
import shutil
import io
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

from exama_version.cli import check, current_version, find_repository, main, normalize, plan


class ReleasePreparationTests(unittest.TestCase):
    def fixture(self, root):
        (root / "pyproject.toml").write_text('[project]\nname = "report"\nversion = "2.95.0"\n')
        (root / "exa-ma-deliverables.tex").write_text(
            "\\hypersetup{pdftitle={Exa-MA v2.95.0 integration draft for v3.0.0}}\n"
            "\\textit{v2.95.0 integration draft -- final target v3.0.0}\n"
            "\\delivVersion{v2.95.0}\n\\ActualDate{15/10/2026}\n"
            "\\istChange{15/10/2026}{v2.95.0}{Author}{Historical record}\n"
            "\\begin{document}\nMeasured value: 2.95.0 (do not replace)\n")
        (root / "standalone-wp1.tex").write_text(
            "\\large Exa-MA D1.1 v2.95.0 integration draft\n")
        (root / "uv.lock").write_text(
            'version = 1\n[[package]]\nname = "report"\nversion = "2.95.0"\n'
            'source = { editable = "." }\n\n[[package]]\nname = "dependency"\n'
            'version = "1.0.0"\nsource = { registry = "https://pypi.org/simple" }\n')

    def test_dry_run_and_write_plan_preserve_history_and_science(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "exa-ma-deliverables.tex"
            before = path.read_text()
            changes = plan(root, "v2.96.0", "A & B", "Metadata #1", date(2026, 10, 16))
            self.assertEqual(path.read_text(), before)
            self.assertIn(r"\delivVersion{v2.96.0}", changes[path])
            self.assertIn(r"\ActualDate{16/10/2026}", changes[path])
            self.assertIn(r"\istChange{16/10/2026}{v2.96.0}{A \& B}{Metadata \#1}", changes[path])
            self.assertIn(r"\istChange{15/10/2026}{v2.95.0}{Author}{Historical record}", changes[path])
            self.assertIn("Measured value: 2.95.0 (do not replace)", changes[path])
            self.assertIn("final target v3.0.0", changes[path])
            self.assertIn("v2.96.0", changes[root / "standalone-wp1.tex"])
            self.assertIn('version = "2.96.0"', changes[root / "uv.lock"])
            self.assertIn('name = "dependency"\nversion = "1.0.0"', changes[root / "uv.lock"])
            for target, content in changes.items():
                target.write_text(content)
            self.assertEqual(current_version(root), "2.96.0")
            self.assertEqual(check(root, "v2.96.0"), "2.96.0")

    def test_check_rejects_stale_titles_lockfile_and_publication_tag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            with self.assertRaisesRegex(ValueError, "Release tag mismatch"):
                check(root, "v2.96.0")
            for name in ("standalone-wp1.tex", "uv.lock"):
                path = root / name
                before = path.read_text()
                path.write_text(before.replace("2.95.0", "2.90.0"))
                with self.assertRaisesRegex(ValueError, "Stale release identity|Version mismatch"):
                    plan(root, "2.96.0")
                path.write_text(before)

    def test_failed_generation_restores_all_release_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "scripts").mkdir()
            (root / "scripts/generate_fiche_identities.py").write_text("raise SystemExit(1)\n")
            originals = {path: path.read_bytes() for path in root.iterdir() if path.is_file()}
            with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                main(["--repo", str(root), "bump", "2.96.0", "--authors", "A", "--summary", "Update", "--write"])
            for path, content in originals.items():
                self.assertEqual(path.read_bytes(), content)
            self.assertEqual(check(root), "2.95.0")

    def test_bump_cli_regenerates_real_fiche_identities_in_selected_checkout(self):
        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "standalone").mkdir()
            (root / "scripts").mkdir()
            (root / "data").mkdir()
            for name in ("generate_fiche_identities.py", "release.py"):
                shutil.copyfile(repository / "scripts" / name, root / "scripts" / name)
            shutil.copytree(repository / "exama_version", root / "exama_version", ignore=shutil.ignore_patterns("__pycache__"))
            for name in ("fiche-identity-profiles.json", "frameworks-source.json", "frameworks.csv",
                         "applications.csv", "application-reconciliation-v3.csv"):
                shutil.copyfile(repository / "data" / name, root / "data" / name)
            source = root / "chapters/applications/specs/app-feelpp-discr-2.tex"
            source.parent.mkdir(parents=True)
            source.touch()
            training = root / "chapters/training.tex"
            training.write_text("The v2.95.0 integration draft consolidates D7.3 v1.0.0.\n")
            self.assertEqual(find_repository(source.parent), root.resolve())
            args = ["--repo", str(root), "bump", "2.96.0", "--authors", "Author", "--summary", "Update metadata"]
            before = (root / "pyproject.toml").read_text()
            with redirect_stdout(io.StringIO()):
                main(args)
            self.assertEqual((root / "pyproject.toml").read_text(), before)
            with redirect_stdout(io.StringIO()):
                main([*args, "--write"])
            self.assertEqual(check(root, "v2.96.0"), "2.96.0")
            self.assertIn(r"\def\FicheDeliverableVersion{v2.96.0}",
                          (root / "standalone/identity-data.tex").read_text())
            self.assertIn("The v2.96.0 integration draft consolidates D7.3 v1.0.0.", training.read_text())

    def test_mismatched_versions_stop_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / "pyproject.toml").write_text('[project]\nversion = "2.90.0"\n')
            with self.assertRaisesRegex(ValueError, "Version mismatch"):
                current_version(root)

    def test_prereleases_and_non_increasing_versions(self):
        self.assertEqual(normalize("v3.0.0-rc.1"), "3.0.0-rc.1")
        for invalid in ["2.95", "../3.0.0", "03.0.0", "3.0.0-rc", "3.0.0;echo"]:
            with self.assertRaises(ValueError):
                normalize(invalid)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            for version in ["2.94.0", "2.95.0", "2.95.0-rc.1"]:
                with self.assertRaisesRegex(ValueError, "greater than"):
                    plan(root, version)


if __name__ == "__main__":
    unittest.main()
