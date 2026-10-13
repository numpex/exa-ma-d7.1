"""Unchanged hourly polls must not republish a PR or repeat CI and review."""
from unittest.mock import patch

import pytest

from scripts.bibliography_pr import followups, needs_update, plan


def pr(head="current", requested=None, reviews=None):
    return {"number": 147, "url": "https://github.com/numpex/exa-ma-d7.1/pull/147",
            "headRefOid": head, "files": [{"path": "references.bib"}],
            "reviewRequests": requested or [], "reviews": reviews or [],
            "autoMergeRequest": {"mergeMethod": "SQUASH"}}


def test_unchanged_export_and_base_leave_existing_pr_alone():
    assert not needs_update(b"main", b"pending", b"pending", "base", "base")
    actions = followups("current", pr(), [{"status": "completed"}])
    assert not actions["run_checks"]
    assert not actions["request_review"]
    assert not actions["enable_auto_merge"]


def test_changed_references_or_main_require_update():
    assert needs_update(b"main", b"new", b"pending", "base", "base")
    assert needs_update(b"main", b"pending", b"pending", "old-base", "new-base")


def test_no_pr_and_no_export_change_do_nothing():
    assert not needs_update(b"same", b"same", None, None, "base")
    assert followups("", None, []) == {
        "run_checks": False, "request_review": False, "enable_auto_merge": False}


def test_new_delta_creates_pr_and_merged_delta_allows_cleanup():
    assert needs_update(b"main", b"new", None, None, "base")
    assert needs_update(b"merged", b"merged", b"merged", "old", "new")


@pytest.mark.parametrize("status", ["queued", "in_progress", "completed"])
def test_existing_run_for_head_prevents_duplicate_dispatch(status):
    assert not followups("current", pr(), [{"status": status}])["run_checks"]


def test_missing_checks_are_repaired_without_repeated_review():
    actions = followups("current", pr(), [])
    assert actions["run_checks"]
    assert not actions["request_review"]


def test_new_head_requests_review_but_already_requested_or_reviewed_does_not():
    assert followups("old", pr(), [])["request_review"]
    requested = [{"login": "copilot-pull-request-reviewer[bot]"}]
    assert not followups("old", pr(requested=requested), [])["request_review"]
    reviews = [{"author": {"login": "Copilot"}, "commit": {"oid": "current"}}]
    assert not followups("old", pr(reviews=reviews), [])["request_review"]
    reviews[0]["commit"]["oid"] = "old"
    assert followups("old", pr(reviews=reviews), [])["request_review"]


def test_missing_auto_merge_is_enabled_once():
    detail = pr()
    detail["autoMergeRequest"] = None
    assert followups("current", detail, [])["enable_auto_merge"]


def test_non_bibliography_pr_fails_closed():
    detail = pr()
    detail["files"].append({"path": "chapters/WP3/WP3.tex"})
    with pytest.raises(ValueError, match="only references.bib"):
        followups("old", detail, [])


def test_ci_lookup_is_scoped_to_exact_pr_head():
    with patch("scripts.bibliography_pr.open_pr", return_value={"number": 147}), \
            patch("scripts.bibliography_pr.gh_json", side_effect=[pr(), []]) as gh:
        assert plan("numpex/exa-ma-d7.1", "current")["run_checks"]
        arguments = gh.call_args_list[1].args[1]
        assert arguments[arguments.index("--commit") + 1] == "current"
