"""Preserve citation keys and valid snapshots during unattended Zotero retrieval."""

import json
from unittest.mock import patch

import pytest

from scripts.update_bibliography import download, entries, update

BIB = "@article{stable_key, title={An article}, author={Doe, Jane}, year={2026}, doi={10.123/test}}\n"


def record(text=BIB, key="ZOTERO1"):
    return {"key": key, "bibtex": text}


def test_same_entries_do_not_rewrite_file(tmp_path):
    output = tmp_path / "references.bib"
    update(output, [record()])
    before = output.stat().st_mtime_ns
    assert not update(output, [record("% New timestamp\n" + BIB)])
    assert output.stat().st_mtime_ns == before


@pytest.mark.parametrize(
    "content",
    ["", "<html>API error</html>", BIB + BIB, BIB + "\n@article{broken,title={oops"],
)
def test_invalid_export_preserves_previous_bibliography(tmp_path, content):
    output = tmp_path / "references.bib"
    output.write_text(BIB)
    with pytest.raises(ValueError):
        update(output, [record(content)])
    assert output.read_text() == BIB


def test_changed_export_key_preserves_cited_key_and_updates_metadata(tmp_path):
    output = tmp_path / "references.bib"
    output.write_text(BIB)
    renamed = BIB.replace("stable_key", "renamed_key").replace(
        "An article", "Corrected title"
    )
    update(output, [record(renamed)])
    result = entries(output.read_text())
    assert set(result) == {"stable_key"}
    assert result["stable_key"]["title"] == "Corrected title"
    assert not update(output, [record(renamed)])


def test_absent_local_reference_is_retained(tmp_path):
    output = tmp_path / "references.bib"
    output.write_text(BIB)
    new = (
        BIB.replace("stable_key", "new_key")
        .replace("An article", "Another article")
        .replace("10.123/test", "10.123/new")
    )
    update(output, [record(new)])
    assert set(entries(output.read_text())) == {"stable_key", "new_key"}


def test_identical_duplicates_and_empty_placeholders(tmp_path):
    output = tmp_path / "references.bib"
    update(
        output, [record(), record(key="ZOTERO2"), record("@misc{empty,\n}", "EMPTY")]
    )
    assert set(entries(output.read_text())) == {"stable_key"}
    assert not update(output, [record(), record(key="ZOTERO2")])


def test_conflicting_duplicate_key_has_stable_suffix(tmp_path):
    output = tmp_path / "references.bib"
    rows = [record(), record(BIB.replace("Doe, Jane", "Doe, John"), "ZOTERO2")]
    update(output, rows)
    assert set(entries(output.read_text())) == {"stable_key", "stable_key_ZOTERO2"}
    assert not update(output, rows)


def test_bibtex_case_insensitive_collision_gets_stable_zotero_suffix(tmp_path):
    output = tmp_path / "references.bib"
    rows = [
        record(BIB.replace("stable_key", "MixedCase"), "FIRST"),
        record(
            BIB.replace("stable_key", "mixedcase")
            .replace("An article", "A different article")
            .replace("10.123/test", "10.123/other"),
            "SECOND",
        ),
    ]
    update(output, rows)
    assert set(entries(output.read_text())) == {"MixedCase", "mixedcase_SECOND"}
    assert not update(output, rows)


def test_case_insensitive_duplicate_keys_are_rejected():
    with pytest.raises(ValueError, match="case is ignored"):
        entries(BIB + BIB.replace("stable_key", "STABLE_KEY"))


def test_zenodo_deposit_without_journal_is_exported_as_misc(tmp_path):
    output = tmp_path / "references.bib"
    deposit = (
        "@article{zenodo_deposit, title={A deposited work}, "
        "author={Doe, Jane}, year={2024}, publisher={Zenodo}, "
        "doi={10.5281/zenodo.12345}}\n"
    )
    update(output, [record(deposit)])
    assert entries(output.read_text())["zenodo_deposit"]["ENTRYTYPE"] == "misc"


def test_unicode_given_name_initials_are_bibtex_safe(tmp_path):
    output = tmp_path / "references.bib"
    accented = (
        "@article{initials, title={Names}, "
        "author={Jensen, Øyvind and Vázquez Mayagoitia, Álvaro}, "
        "year={2026}, journal={Example}}\n"
    )
    update(output, [record(accented)])
    authors = entries(output.read_text())["initials"]["author"]
    assert r"Jensen, {\O}yvind" in authors
    assert r"Vázquez Mayagoitia, {\'A}lvaro" in authors
    assert not update(output, [record(accented)])


def test_conflicting_updates_leave_existing_entry_unchanged(tmp_path):
    output = tmp_path / "references.bib"
    output.write_text(BIB)
    rows = [record(), record(BIB.replace("Doe, Jane", "Doe, John"), "ZOTERO2")]
    assert not update(output, rows)
    assert output.read_text() == BIB


def test_check_only_and_atomic_replacement(tmp_path):
    output = tmp_path / "references.bib"
    output.write_text(BIB)
    assert update(output, [record()], check=True)
    assert output.read_text() == BIB
    assert update(output, [record()])
    assert list(tmp_path.iterdir()) == [output]


class Response:
    def __init__(self, rows, version="1"):
        self.rows = rows
        self.headers = {"Total-Results": "2", "Last-Modified-Version": version}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return json.dumps(self.rows).encode()


def test_pagination_counts_api_objects():
    with patch(
        "scripts.update_bibliography.urlopen",
        side_effect=[Response([record()]), Response([record(key="SECOND")])],
    ) as get:
        assert len(download(1, None)) == 2
        assert "start=1" in get.call_args_list[1].args[0].full_url


def test_snapshot_changes_abort_download():
    with patch(
        "scripts.update_bibliography.urlopen",
        side_effect=[Response([record()]), Response([record()], "2")],
    ):
        with pytest.raises(ValueError, match="changed"):
            download(1, None)


def test_short_response_aborts_download():
    with patch(
        "scripts.update_bibliography.urlopen",
        side_effect=[Response([record()]), Response([])],
    ):
        with pytest.raises(ValueError, match="Incomplete"):
            download(1, None)


def test_legacy_user_library_is_supported():
    with patch(
        "scripts.update_bibliography.urlopen",
        side_effect=[Response([record(), record(key="SECOND")])],
    ) as get:
        download(None, None, user_id=42)
        assert "/users/42/items/top?" in get.call_args.args[0].full_url
