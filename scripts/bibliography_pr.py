#!/usr/bin/env python3
"""Read-only decisions for the bibliography PR workflow; never publish changes."""
import argparse
import base64
import json
import os
import subprocess
from pathlib import Path

BRANCH = "automation-zotero-bibliography"
COPILOT = {"copilot-pull-request-reviewer", "copilot-pull-request-reviewer[bot]",
           "copilot", "Copilot"}


def gh_json(repo, arguments):
    return json.loads(subprocess.check_output(["gh", *arguments, "--repo", repo], text=True))


def api_json(endpoint):
    return json.loads(subprocess.check_output(["gh", "api", endpoint], text=True))


def needs_update(main_bib, exported_bib, previous_bib, previous_base, main_head):
    if previous_bib is None:
        return exported_bib != main_bib
    # Let create-pull-request close a pending PR whose delta has reached main.
    return (exported_bib == main_bib or exported_bib != previous_bib
            or previous_base != main_head)


def followups(previous_head, pr, latex_runs):
    if pr is None:
        return {"run_checks": False, "request_review": False, "enable_auto_merge": False}
    if [file["path"] for file in pr["files"]] != ["references.bib"]:
        raise ValueError("Bibliography automation PR must change only references.bib")
    head = pr["headRefOid"]
    changed = head != previous_head
    requested = any(user.get("login") in COPILOT for user in pr["reviewRequests"])
    reviewed = any(review["author"]["login"] in COPILOT
                   and review["commit"]["oid"] == head for review in pr["reviews"])
    return {"number": pr["number"], "url": pr["url"], "head": head,
            # Queued, running, successful and failed runs all count. Do not retry
            # a failed build every hour; an explicit rerun remains possible.
            "run_checks": not latex_runs,
            "request_review": changed and not requested and not reviewed,
            "enable_auto_merge": pr["autoMergeRequest"] is None}


def open_pr(repo):
    matches = gh_json(repo, ["pr", "list", "--head", BRANCH, "--base", "main",
                            "--state", "open", "--json", "number,headRefOid"])
    if len(matches) > 1:
        raise ValueError("Multiple open bibliography PRs found")
    return matches[0] if matches else None


def inspect(repo):
    main_head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    main_bib = subprocess.check_output(["git", "show", "HEAD:references.bib"])
    exported_bib = Path("references.bib").read_bytes()
    pr = open_pr(repo)
    previous_bib = previous_base = None
    if pr:
        data = api_json(f"repos/{repo}/contents/references.bib?ref={pr['headRefOid']}")
        previous_bib = base64.b64decode(data["content"])
        commit = api_json(f"repos/{repo}/git/commits/{pr['headRefOid']}")
        # The managed PR is a single bibliography commit on top of main.
        parents = commit["parents"]
        previous_base = parents[0]["sha"] if len(parents) == 1 else None
    return {"previous_head": pr["headRefOid"] if pr else "",
            "update_needed": needs_update(main_bib, exported_bib, previous_bib,
                                          previous_base, main_head)}


def plan(repo, previous_head):
    pr = open_pr(repo)
    if not pr:
        return followups(previous_head, None, [])
    detail = gh_json(repo, ["pr", "view", str(pr["number"]), "--json",
                           "number,url,headRefOid,files,reviewRequests,reviews,autoMergeRequest"])
    runs = gh_json(repo, ["run", "list", "--workflow", "latex.yml", "--commit",
                         detail["headRefOid"], "--limit", "1", "--json", "databaseId,status"])
    return followups(previous_head, detail, runs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["inspect", "plan"])
    parser.add_argument("--previous-head", default="")
    args = parser.parse_args()
    repo = os.environ["GH_REPO"]
    values = inspect(repo) if args.mode == "inspect" else plan(repo, args.previous_head)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
            for name, value in values.items():
                stream.write(f"{name}={str(value).lower() if isinstance(value, bool) else value}\n")
    print(json.dumps(values))


if __name__ == "__main__":
    main()
