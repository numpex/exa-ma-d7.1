#!/usr/bin/env python3
"""Check or prepare local release metadata. Never commits, tags, or pushes."""
import argparse
import difflib
import re
import subprocess
import sys
import tomllib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(alpha|beta|preview|rc)\.(0|[1-9]\d*))?")
TAG = re.compile(r"v\d+\.\d+\.\d+(?:-(?:alpha|beta|preview|rc)\.\d+)?")


def find_repository(path):
    path = Path(path).resolve()
    for candidate in (path, *path.parents):
        if (candidate / "pyproject.toml").is_file() and any(
            (candidate / name).is_file()
            for name in ("exa-ma-deliverables.tex", "exa-ma-d7.1.tex")
        ):
            return candidate
    raise ValueError(f"No deliverable checkout found from {path}; use --repo PATH")


def normalize(value):
    value = value.removeprefix("v")
    if not VERSION.fullmatch(value):
        raise ValueError("Use X.Y.Z or X.Y.Z-{alpha,beta,preview,rc}.N")
    return value


def main_document(root):
    for name in ("exa-ma-deliverables.tex", "exa-ma-d7.1.tex"):
        if (root / name).is_file():
            return root / name
    raise ValueError("No main deliverable TeX entry point found")


def current_version(root):
    doc = main_document(root)
    match = re.findall(r"(?m)^\\delivVersion\{v?([^}]+)\}", doc.read_text())
    if len(match) != 1:
        raise ValueError(f"Expected one active delivVersion in {doc.name}")
    version = normalize(match[0])
    project = normalize(tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"])
    if version != project:
        raise ValueError(f"Version mismatch: {doc.name}={version}, pyproject.toml={project}")
    return version


def tex(value):
    escapes = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}",
               "%": r"\%", "&": r"\&", "#": r"\#", "_": r"\_",
               "$": r"\$", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(escapes.get(c, c) for c in value)


def order(version):
    major, minor, patch, kind, number = VERSION.fullmatch(version).groups()
    return int(major), int(minor), int(patch), kind is None, kind or "", int(number or 0)


def identity_paths(root):
    return [main_document(root), *sorted(root.glob("standalone-wp*.tex")),
            *[root / name for name in ("chapters/applications/registry.tex", "chapters/training.tex")
              if (root / name).exists()]]


def identity_line(path, line):
    stripped = line.lstrip()
    if stripped.startswith("%"):
        return False
    return ("pdftitle=" in line or stripped.startswith(r"\delivVersion{")
            or stripped.startswith(r"\textit{v") or stripped.startswith(r"\large Exa-MA")
            or (path.name == "registry.tex" and stripped.startswith(r"\caption{Application registry reconciled for the v"))
            or (path.name == "training.tex" and re.match(r"The v\d+\.\d+\.\d+.* integration draft", stripped)))


def lock_identity(root, version=None):
    """Read/update only the local project's uv.lock version, never dependencies."""
    path = root / "uv.lock"
    if not path.exists():
        return None
    source = path.read_text()
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]["name"]
    canonical = lambda name: re.sub(r"[-_.]+", "-", name).lower()
    for match in re.finditer(r"(?ms)^\[\[package\]\]\n.*?(?=^\[\[package\]\]|\Z)", source):
        package = tomllib.loads(match[0])["package"][0]
        local = package.get("source", {})
        if canonical(package["name"]) == canonical(project) and (
            local.get("editable") == "." or local.get("virtual") == "."
        ):
            if version is None:
                return package["version"]
            block, count = re.subn(r'(?m)^version\s*=\s*"[^"]+"',
                                  'version = "' + version + '"', match[0])
            if count != 1:
                raise ValueError("Expected one local project version in uv.lock")
            return source[:match.start()] + block + source[match.end():]
    raise ValueError("uv.lock has no local project entry; regenerate/review it explicitly")


def check(root, tag=None):
    version = current_version(root)
    history = re.search(r"(?m)^\\istChange\{[^}]+\}\{([^}]+)\}", main_document(root).read_text())
    if not history or history[1] != "v" + version:
        raise ValueError("The newest changelog entry must identify the current deliverable version")
    for path in identity_paths(root):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            match = TAG.search(line) if identity_line(path, line) else None
            if match and match[0] != "v" + version:
                raise ValueError(f"Stale release identity: {path.relative_to(root)}:{number} has {match[0]}, expected v{version}")
    locked = lock_identity(root)
    if locked is not None and locked != version:
        raise ValueError(f"Version mismatch: uv.lock={locked}, deliverable={version}")
    identity = root / "standalone/identity-data.tex"
    if identity.exists():
        match = re.search(r"\\def\\FicheDeliverableVersion\{v([^}]+)\}", identity.read_text())
        if not match or match[1] != version:
            raise ValueError("Stale identity version: regenerate standalone identities")
    if tag is not None and tag != "v" + version:
        raise ValueError(f"Release tag mismatch: {tag}, expected v{version}")
    return version


def plan(root, version, authors="", summary="", day=None):
    old, version = check(root), normalize(version)
    if order(version) <= order(old):
        raise ValueError(f"New version must be greater than {old}")
    day = day or datetime.now(ZoneInfo("Europe/Paris")).date()
    doc = main_document(root)
    paths = identity_paths(root)
    changes = {}
    for path in paths:
        source = path.read_text()
        lines = source.splitlines(keepends=True)
        updated = []
        for line in lines:
            stripped = line.lstrip()
            if identity_line(path, line):
                line = TAG.sub("v" + version, line, count=1)
            if path == doc and stripped.startswith(r"\ActualDate{"):
                line = re.sub(r"\d{2}/\d{2}/\d{4}", day.strftime("%d/%m/%Y"), line, count=1)
            if path.name.startswith("standalone-wp") and stripped.startswith(r"\date{"):
                line = r"\date{" + day.strftime("%d/%m/%Y") + "}\n"
            updated.append(line)
        result = "".join(updated)
        if path == doc and authors and summary:
            entry = (r"\istChange{" + day.strftime("%d/%m/%Y") + "}{v" + version
                     + "}{" + tex(authors) + "}{" + tex(summary) + "}\n")
            first = re.search(r"(?m)^\\istChange\{", result)
            if not first:
                raise ValueError("No active changelog entry found; add the changelog explicitly")
            result = result[:first.start()] + entry + result[first.start():]
        if source != result:
            changes[path] = result
    project = root / "pyproject.toml"
    source = project.read_text()
    start = source.index("[project]") + len("[project]")
    following = re.search(r"(?m)^\[", source[start:])
    end = start + following.start() if following else len(source)
    block, count = re.subn(r'(?m)^version\s*=\s*"[^"]+"',
                          'version = "' + version + '"', source[start:end])
    if count != 1:
        raise ValueError("Expected one project version")
    changes[project] = source[:start] + block + source[end:]
    locked = lock_identity(root, version)
    if locked is not None:
        changes[root / "uv.lock"] = locked
    return changes


def main(argv=None):
    parser = argparse.ArgumentParser(prog="exa-ma-version", description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Deliverable checkout (default: current directory)")
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("check", help="Verify document, package, lockfile and preview versions")
    verify.add_argument("--tag", help="Also require this publication tag to match (vX.Y.Z)")
    prepare = commands.add_parser("bump", aliases=["prepare"], help="Prepare a version bump; dry run by default")
    prepare.add_argument("version")
    prepare.add_argument("--authors", default="")
    prepare.add_argument("--summary", default="")
    prepare.add_argument("--write", action="store_true")
    prepare.add_argument("--diff", action="store_true", help="Show the proposed source diff")
    args = parser.parse_args(argv)
    try:
        root = find_repository(args.repo)
        version = current_version(root)
        if args.command == "check":
            check(root, args.tag)
            print(f"{root}\n{main_document(root).name}: v{version}; release identities consistent")
            return
        if args.write and (not args.authors or not args.summary):
            parser.error("--write requires --authors and --summary for the changelog")
        changes = plan(root, args.version, args.authors, args.summary)
        identity = root / "standalone/identity-data.tex"
        generator = root / "scripts/generate_fiche_identities.py"
        if identity.exists() and not generator.exists():
            raise ValueError("Cannot regenerate standalone identities: generator missing")
        if identity.exists() and not identity.read_text().startswith("% Generated by scripts/generate_fiche_identities.py;"):
            raise ValueError("Refusing to overwrite unmarked standalone identity data")
        print(f"Prepare v{version} -> v{normalize(args.version)} in {root}")
        for path, content in changes.items():
            print(("Write: " if args.write else "Would update: ") + str(path.relative_to(root)))
            if args.diff:
                print("".join(difflib.unified_diff(path.read_text().splitlines(True), content.splitlines(True),
                                                fromfile=str(path.relative_to(root)), tofile=str(path.relative_to(root)))), end="")
        if generator.exists():
            print(("Regenerate: " if args.write else "Would regenerate: ") + "standalone/identity-data.tex")
        if args.write:
            originals = {path: path.read_bytes() for path in changes}
            originals[identity] = identity.read_bytes() if identity.exists() else None
            try:
                for path, content in changes.items():
                    path.write_text(content)
                if generator.exists():
                    subprocess.run([sys.executable, str(generator)], cwd=root, check=True)
                check(root)
            except (OSError, ValueError, subprocess.CalledProcessError) as error:
                for path, content in originals.items():
                    if content is None:
                        path.unlink(missing_ok=True)
                    else:
                        path.write_bytes(content)
                raise ValueError(f"Release preparation failed; original metadata restored: {error}") from error
        print("No commit, tag, push or publication performed.")
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
