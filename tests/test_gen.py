"""Framework metadata generation must preserve authored science and source values."""
import csv
import subprocess
import sys

import pytest

from scripts.sync_frameworks import GENERATED, ROOT, items, plan, tex


def test_current_metadata_matches_snapshot():
    changes = plan(ROOT, ROOT / "data/frameworks.csv", "feelpp")
    assert len(changes) == 1
    for target, content in changes.items():
        assert target.read_text() == content
        assert content.startswith(GENERATED)
        assert "C++23" in content and "preCICE" in content and "CodeMeta" in content
        assert "Benchmark coverage" in content and "B9 - Resilience" in content


def test_generation_only_targets_metadata_and_preserves_editorial(tmp_path):
    target = tmp_path / "software/feelpp"
    target.mkdir(parents=True)
    editorial = target / "feelpp.tex"
    editorial.write_text("Authored scientific text and equations.")
    (tmp_path / "templates").symlink_to(ROOT / "templates", target_is_directory=True)
    changes = plan(tmp_path, ROOT / "data/frameworks.csv", "feelpp")
    assert set(changes) == {target / "metadata.tex"}
    assert editorial.read_text() == "Authored scientific text and equations."
    (target / "metadata.tex").write_text("Unmarked hand-written metadata.")
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        plan(tmp_path, ROOT / "data/frameworks.csv", "feelpp")


@pytest.mark.parametrize("name", ["../feelpp", "Feel++", "/tmp/feelpp", "feelpp/other"])
def test_framework_id_cannot_escape_metadata_directory(name):
    with pytest.raises(ValueError, match="safe lowercase"):
        plan(ROOT, ROOT / "data/frameworks.csv", name)


def test_duplicate_rows_are_rejected(tmp_path):
    with (ROOT / "data/frameworks.csv").open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        row = next(r for r in reader if r["Name"] == "Feel++")
    snapshot = tmp_path / "duplicate.csv"
    with snapshot.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows([row, row])
    with pytest.raises(ValueError, match="Expected one entry"):
        plan(ROOT, snapshot, "feelpp")


def test_tex_special_characters_are_escaped_without_expanding_commands():
    assert tex(r"a_b & 50% #1 {x} \input") == r"a\_b \& 50\% \#1 \{x\} \textbackslash{}input"


def test_quoted_topics_retain_their_internal_commas():
    assert items('"ROM-DA: GEIM PBDW, ...",\nROM: NIRB, "ROM: RB, POD, ..."') == [
        "ROM-DA: GEIM PBDW, ...", "ROM: NIRB", "ROM: RB, POD, ..."]


def test_cli_check_is_read_only_and_legacy_overwrite_is_disabled():
    fiche = ROOT / "software/feelpp/feelpp.tex"
    before = fiche.read_bytes()
    checked = subprocess.run([sys.executable, str(ROOT / "gen.py"), "--framework",
                              "feelpp", "--check"], cwd=ROOT, capture_output=True)
    assert checked.returncode == 0, checked.stderr.decode()
    legacy = subprocess.run([sys.executable, str(ROOT / "gen.py")], cwd=ROOT,
                            capture_output=True)
    assert legacy.returncode != 0
    assert b"protect authored fiches" in legacy.stderr
    assert fiche.read_bytes() == before
