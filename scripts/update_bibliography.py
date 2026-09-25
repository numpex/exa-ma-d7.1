"""Retrieve Zotero references while preserving the document's existing citation keys.

Run: uv run --no-project --python 3.11 --with bibtexparser==1.4.3
     python scripts/update_bibliography.py
"""

import argparse
import copy
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import bibtexparser
from bibtexparser.bparser import BibTexParser


def download(group_id, api_key, user_id=None):
    records = []
    total = None
    version = None
    while total is None or len(records) < total:
        library = f"users/{int(user_id)}" if user_id else f"groups/{int(group_id)}"
        url = f"https://api.zotero.org/{library}/items/top?" + urlencode(
            {
                "format": "json",
                "include": "bibtex",
                "limit": 100,
                "start": len(records),
            }
        )
        headers = {"Zotero-API-Version": "3"}
        if api_key:
            headers["Zotero-API-Key"] = api_key
        for attempt in range(4):
            try:
                with urlopen(Request(url, headers=headers), timeout=60) as response:
                    page = json.load(response)
                    current_version = response.headers["Last-Modified-Version"]
                    page_total = int(response.headers["Total-Results"])
                    backoff = float(response.headers.get("Backoff", 0))
                break
            except HTTPError as error:
                if error.code in (429, 500, 502, 503, 504) and attempt < 3:
                    time.sleep(
                        max(float(error.headers.get("Retry-After", 0)), 2**attempt)
                    )
                    continue
                raise RuntimeError(
                    f"Zotero bibliography request failed: HTTP {error.code}"
                ) from error
        if version is not None and (version != current_version or total != page_total):
            raise ValueError(
                "Zotero changed during download; retry for a consistent snapshot"
            )
        version, total = current_version, page_total
        if not isinstance(page, list) or (not page and len(records) < total):
            raise ValueError("Incomplete Zotero response")
        records.extend(page)
        if len(records) < total and backoff:
            time.sleep(backoff)
    return records


def parse(content):
    parser = BibTexParser()
    parser.ignore_nonstandard_types = False
    database = bibtexparser.loads(content, parser=parser)
    expected = len(
        re.findall(r"(?im)^\s*@(?!(?:comment|string|preamble)\b)[\w-]+\s*[{(]", content)
    )
    if not database.entries or len(database.entries) != expected:
        raise ValueError("Empty or malformed BibTeX export")
    keys = [e["ID"] for e in database.entries]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate citation keys in bibliography")
    return database


def entries(content):
    return {entry["ID"]: entry for entry in parse(content).entries}


def normalized(value):
    return "".join(
        c for c in unicodedata.normalize("NFKD", value).casefold() if c.isalnum()
    )


def doi(entry):
    return re.sub(
        r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)",
        "",
        entry.get("doi", "").strip().lower(),
    )


def signature(entry):
    return json.dumps(
        {k: v for k, v in entry.items() if k not in ("ID", "zotero-key")},
        sort_keys=True,
    )


def reconcile(old, records):
    """Keep local keys, deduplicate identical exports, retain unmatched local sources.

    A Zotero item key provides stable identity after the first retrieval. Bootstrap
    matches use DOI, URL, or title/year; ambiguous matches retain existing entries.
    """
    groups = {}
    skipped_empty = 0
    for record in sorted(records, key=lambda r: r["key"]):
        text = record.get("bibtex", "").strip()
        if not text or re.fullmatch(r"@\w+\s*\{[^,{}\n]+,\s*\}", text):
            skipped_empty += 1
            continue
        parsed = entries(text)
        if len(parsed) != 1:
            raise ValueError("Expected one BibTeX entry per Zotero item")
        entry = next(iter(parsed.values()))
        group = groups.setdefault(
            signature(entry), {"entry": entry, "keys": [], "citation_keys": set()}
        )
        group["keys"].append(record["key"])
        group["citation_keys"].add(entry["ID"])
    if not groups:
        raise ValueError("Zotero exported no valid bibliography entries")
    result = copy.deepcopy(old)
    proposals = defaultdict(list)
    conflicts = []
    for group in groups.values():
        entry, keys = group["entry"], group["keys"]
        matches = [key for key, value in old.items() if value.get("zotero-key") in keys]
        if not matches:
            matches = [
                key
                for key in group["citation_keys"]
                if key in old
                and not (doi(entry) and doi(old[key]) and doi(entry) != doi(old[key]))
            ]
        if not matches and doi(entry):
            matches = [key for key, value in old.items() if doi(value) == doi(entry)]
        if not matches and entry.get("url"):
            matches = [
                key
                for key, value in old.items()
                if value.get("url", "").rstrip("/") == entry["url"].rstrip("/")
            ]
        if not matches and entry.get("title"):
            matches = [
                key
                for key, value in old.items()
                if normalized(value.get("title", "")) == normalized(entry["title"])
                and value.get("year", "") == entry.get("year", "")
            ]
        if len(matches) > 1:
            conflicts.append(
                {
                    "zotero_keys": keys,
                    "citation_keys": sorted(matches),
                    "reason": "multiple existing entries match; retained unchanged",
                }
            )
            continue
        updated = copy.deepcopy(entry)
        updated["zotero-key"] = keys[0]
        if matches:
            updated["ID"] = matches[0]
            # Keep the previously chosen item if its duplicate is still present.
            if old[matches[0]].get("zotero-key") in keys:
                updated["zotero-key"] = old[matches[0]]["zotero-key"]
            proposals[matches[0]].append(updated)
        else:
            key = updated["ID"]
            if key in result:
                key += "_" + keys[0]
            if key in result:
                raise ValueError(f"Unresolved citation-key collision: {key}")
            updated["ID"] = key
            result[key] = updated
    for key, candidates in proposals.items():
        if len({signature(candidate) for candidate in candidates}) == 1:
            result[key] = candidates[0]
        else:
            conflicts.append(
                {
                    "citation_keys": [key],
                    "reason": "conflicting Zotero metadata; retained unchanged",
                    "zotero_keys": [c["zotero-key"] for c in candidates],
                }
            )
    report = {
        "zotero_items": len(records),
        "empty_items_skipped": skipped_empty,
        "identical_duplicates_collapsed": len(records) - skipped_empty - len(groups),
        "references": len(result),
        "added": len(set(result) - set(old)),
        "updated": sum(result[k] != old[k] for k in old),
        "conflicts": conflicts,
    }
    return result, report


def update(output, records, *, check=False, report_path=None):
    old_text = output.read_text(encoding="utf-8") if output.exists() else ""
    database = (
        parse(old_text) if old_text.strip() else bibtexparser.bibdatabase.BibDatabase()
    )
    old = {entry["ID"]: entry for entry in database.entries}
    new, report = reconcile(old, records)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"Validated {len(new)} references: {report['added']} new, {report['updated']} updated, "
        f"{len(report['conflicts'])} ambiguous matches retained unchanged"
    )
    if old == new:
        print("Bibliography unchanged")
        return False
    if check:
        print("Check only: bibliography was not changed")
        return True
    database.entries = list(new.values())
    content = bibtexparser.dumps(database)
    entries(content)  # Validate serialization before replacement.
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output.parent,
            prefix=output.name + ".",
            delete=False,
        ) as temp:
            temp_name = temp.name
            temp.write(content)
            temp.flush()
            os.fsync(temp.fileno())
        os.chmod(temp_name, output.stat().st_mode & 0o777 if output.exists() else 0o644)
        os.replace(temp_name, output)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    print(f"Updated {output}")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--group-id",
        type=int,
        default=int(os.environ.get("ZOTERO_GROUP_ID") or 5582837),
    )
    parser.add_argument(
        "--user-id", type=int, help="Use a personal library instead of the group"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(os.environ.get("BIBTEX_FILE", "references.bib")),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate without replacing the bibliography",
    )
    parser.add_argument(
        "--report", type=Path, help="Write reconciliation details as JSON"
    )
    args = parser.parse_args()
    try:
        records = download(
            args.group_id, os.environ.get("ZOTERO_API_KEY"), args.user_id
        )
        update(args.output, records, check=args.check, report_path=args.report)
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f"Bibliography update failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
