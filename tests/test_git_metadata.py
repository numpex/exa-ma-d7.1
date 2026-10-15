"""Check that LaTeX reads the hook output belonging to its own worktree."""
import shutil
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("pdflatex"), "pdflatex is required")
class GitMetadataTests(unittest.TestCase):
    def run_command(self, cwd, *args):
        return subprocess.run(args, cwd=cwd, check=True, capture_output=True,
                              text=True, errors="replace").stdout.strip()

    def copy_reader(self, target):
        shutil.copy(ROOT / "git-metadata.tex", target)
        shutil.copy(ROOT / "gitHeadLocal.gin", target)

    def compile_hash(self, target):
        (target / "probe.tex").write_text(
            r"\documentclass{article}" "\n"
            r"\input{git-metadata}\input{git-metadata}" "\n"
            r"\begin{document}\typeout{EXAMA-HEAD=\gitHash}" "\n"
            r"HEAD: \gitHash\end{document}" "\n")
        output = self.run_command(target, "pdflatex", "-no-shell-escape",
                                  "-halt-on-error", "-interaction=nonstopmode",
                                  "probe.tex")
        return next(line.split("=", 1)[1] for line in output.splitlines()
                    if line.startswith("EXAMA-HEAD="))

    def test_regular_and_linked_worktrees(self):
        with tempfile.TemporaryDirectory(prefix="exama git metadata ") as tmp:
            repo = Path(tmp) / "regular checkout"
            repo.mkdir()
            self.run_command(repo, "git", "init", "-q")
            self.run_command(repo, "git", "config", "user.name", "Metadata Test")
            self.run_command(repo, "git", "config", "user.email", "test@example.org")
            self.run_command(repo, "git", "-c", "core.hooksPath=/dev/null",
                             "commit", "-q", "--allow-empty", "-m", "Fixture")
            regular_head = self.run_command(repo, "git", "rev-parse", "HEAD")
            self.copy_reader(repo)
            # A checkout without installed hooks must still use the fallback.
            fallback_hash = self.compile_hash(repo)
            self.assertNotEqual(fallback_hash, regular_head)
            self.run_command(repo, "sh", str(ROOT / "hooks/post-commit"))
            self.assertEqual(self.compile_hash(repo), regular_head)

            linked = Path(tmp) / "linked worktree"
            self.run_command(repo, "git", "-c", "core.hooksPath=/dev/null",
                             "worktree", "add", "-q", "-b", "linked", str(linked))
            self.run_command(linked, "git", "-c", "core.hooksPath=/dev/null",
                             "commit", "-q", "--allow-empty", "-m", "Worktree HEAD")
            linked_head = self.run_command(linked, "git", "rev-parse", "HEAD")
            self.assertNotEqual(linked_head, regular_head)
            self.copy_reader(linked)
            self.assertEqual(self.compile_hash(linked), fallback_hash)
            self.run_command(linked, "sh", str(ROOT / "hooks/post-commit"))
            self.assertEqual(self.compile_hash(linked), linked_head)
            self.assertEqual(self.compile_hash(repo), regular_head)

            # Git may also store a relative administrative-directory pointer.
            pointer = (linked / ".git").read_text().strip().removeprefix("gitdir: ")
            (linked / ".git").write_text(
                "gitdir: " + os.path.relpath(pointer, linked.resolve()) + "\n")
            self.assertEqual(self.compile_hash(linked), linked_head)

    def test_archive_without_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)
            self.copy_reader(archive)
            fallback = (ROOT / "gitHeadLocal.gin").read_text()
            expected = re.search(r"lhash=\{([0-9a-f]+)\}", fallback).group(1)
            self.assertEqual(self.compile_hash(archive), expected)


if __name__ == "__main__":
    unittest.main()
