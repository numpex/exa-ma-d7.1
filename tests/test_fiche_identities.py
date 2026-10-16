"""Standalone identities cover catalogue entries without changing embedded science."""
import re
import io
from contextlib import redirect_stderr
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate_fiche_identities as identities

ROOT = identities.ROOT


class FicheIdentityTests(unittest.TestCase):
    def test_every_application_preview_has_an_identity(self):
        content = identities.render(ROOT)
        declared = re.findall(r"\\DeclareFicheIdentity\{([^}]+)\}", content)
        self.assertEqual(len(declared), len(set(declared)))
        for wrapper in (ROOT / "standalone/applications").glob("*.tex"):
            self.assertIn(wrapper.stem, declared)
            self.assertIn(r"\input{standalone/application}", wrapper.read_text())
        self.assertIn("feelpp", declared)
        self.assertEqual((ROOT / "standalone/identity-data.tex").read_text(), content)

    def test_special_characters_and_non_url_access_notes(self):
        self.assertEqual(identities.tex(r"50% & a_b #1 \input"),
                         r"50\% \& a\_b \#1 \textbackslash{}input")
        self.assertEqual(identities.link("private, access on request", "Repository"), "")
        self.assertEqual(identities.link("https://example.org/a_b?q=50%25#x", "Code"),
                         r"\href{https://example.org/a_b?q=50\%25\#x}{Code}")
        self.assertEqual(identities.cell(""), "Not recorded")

    def test_unmarked_standalone_data_is_protected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "standalone").mkdir()
            target = root / "standalone/identity-data.tex"
            target.write_text("Hand-written identity data\n")
            with patch.object(identities, "ROOT", root), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                identities.main([])
            self.assertEqual(target.read_text(), "Hand-written identity data\n")


if __name__ == "__main__":
    unittest.main()
