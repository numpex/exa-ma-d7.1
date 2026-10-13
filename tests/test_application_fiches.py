"""Application presentation uses four sections without copying pending work."""
import csv
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADINGS = ["Description of the benchmark", "Benchmarking methodology",
            "Input/Output Dataset Description", "Results summary"]
# These specifications are supplied by PRs #115 and #135. Other omissions fail.
DEFERRED = {"app-samurai-burgers-2d", "app-samurai-euler-dmr",
            "app-kinetic-moment-closure", "app-parabolic-terminal-constraint"}


class ApplicationFicheTests(unittest.TestCase):
    def test_local_fiches_have_dedicated_sources_and_common_structure(self):
        with (ROOT / "data/application-reconciliation-v3.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        paths = set()
        for row in rows:
            source = ROOT / row["latex_spec"]
            with self.subTest(application=row["application_id"]):
                if source.parent != ROOT / "chapters/applications/specs":
                    source = ROOT / "chapters/applications/specs" / (row["application_id"] + ".tex")
                if not source.exists():
                    self.assertIn(row["application_id"], DEFERRED,
                                  "Missing specification is not a known pending contribution")
                    metadata = ROOT / "chapters/applications/metadata" / (row["application_id"] + ".tex")
                    self.assertTrue(metadata.exists(), "Pending contribution needs a catalogue preview")
                    continue
                self.assertNotIn(source, paths)
                paths.add(source)
                content = source.read_text()
                self.assertIn(row["application_id"], content)
                self.assertEqual(re.findall(r"\\subsection\{([^\n]+)\}", content), HEADINGS)

    def test_chapter_includes_each_catalogue_application_once_in_id_order(self):
        with (ROOT / "data/application-reconciliation-v3.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        sources = {Path(row["latex_spec"]).stem: row["application_id"] for row in rows
                   if Path(row["latex_spec"]).parent == Path("chapters/applications/specs")}
        chapter = (ROOT / "chapters/applications.tex").read_text()
        included = re.findall(r"\\import\{chapters/applications/specs/\}\{([^}]+)\}", chapter)
        ids = [sources.get(name, name) for name in included if name != "app-proposed"]
        self.assertEqual(ids, sorted(row["application_id"] for row in rows),
                         "Every fiche, including pending placeholders, must appear exactly once in ID order")

    def test_shared_results_are_present_and_included_once(self):
        references = []
        for source in (ROOT / "chapters/applications/specs").glob("*.tex"):
            references.extend(re.findall(r"\\ApplicationBenchmarkResults\{([^}]+)\}", source.read_text()))
        self.assertEqual(len(references), len(set(references)), "Results must not appear in two fiches")
        actual = {source.stem for source in (ROOT / "chapters/applications/results").glob("*.tex")}
        self.assertEqual(set(references), actual, "A result file is missing or omitted from its fiche")

    def test_planning_notes_do_not_duplicate_application_bodies(self):
        content = (ROOT / "chapters/applications/specs/app-proposed.tex").read_text()
        self.assertIn(r"\subsection{Development Timeline}", content)
        self.assertNotIn("%<*app-", content)
        self.assertEqual(len(re.findall(r"\\import\{chapters/applications/specs/\}\{app-", content)), 0)


if __name__ == "__main__":
    unittest.main()
