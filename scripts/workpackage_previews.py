#!/usr/bin/env python3
"""Build WP contributions and a companion report with checked cross-PDF references.

Run from any directory with Python 3.11+. No scientific source is generated or
rewritten. A first standalone pass discovers local labels (including cleveref
metadata); a second imports only the remaining labels from the full report.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tomllib
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABEL = re.compile(r'^\\newlabel\{([^}]+)\}', re.M)


def external_labels(report, local):
    """Preserve local numbers, destinations and @cref metadata; omit citations."""
    local_names = set(LABEL.findall(local))
    # Never import LastPage: it belongs to this PDF even on a first pass.
    local_names.update({'LastPage', 'LastPage@cref'})
    return '\n'.join(line for line in report.splitlines()
                     if (match := LABEL.match(line)) and match[1] not in local_names) + '\n'


def read_labels(path):
    """Flatten label records, including auxiliaries written by LaTeX include."""
    seen = set()

    def visit(aux):
        aux = aux.resolve()
        if aux in seen:
            return ''
        seen.add(aux)
        lines = []
        for line in aux.read_text().splitlines():
            if LABEL.match(line):
                lines.append(line)
            elif match := re.match(r'\\@input\{([^}]+)\}', line):
                lines.append(visit(aux.parent / match[1]))
        return '\n'.join(lines) + '\n'

    return visit(path)


def diagnostics(log):
    """Fail on broken references, citations, glyphs or PDF destinations, not layout warnings."""
    issues = [p.strip() for p in re.split(r'\n\s*\n', log)
              if 'Warning:' in p and re.search(
                  r'undefined|not defined|multiply defined|LABELS NOT IMPORTED|not prepared', p)]
    if re.search(r'^!|LaTeX Error:|Package [^\n]+ Error:|Undefined control sequence|'
                 r'Missing character:|destination with the same identifier', log, re.M):
        issues.append('LaTeX error, missing glyph or duplicate PDF destination')
    return issues


def check_log(path):
    if problems := diagnostics(path.read_text(errors='replace')):
        raise ValueError(f'Invalid PDF: {path}\n' + '\n'.join(problems))


def run(command, root, transcript):
    with transcript.open('w') as stream:
        result = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f'Build failed; see {transcript}\n'
                           + transcript.read_text(errors='replace')[-8000:])


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root=ROOT, wps=range(1, 8), ref='local-review', jobs=1):
    wps = sorted(set(wps))
    if not wps or set(wps) - set(range(1, 8)) or jobs < 1:
        raise ValueError('Select WP1 to WP7 and a positive job count')
    suffix = re.sub(r'[^A-Za-z0-9._-]', '-', ref)
    if not suffix or suffix in {'.', '..'}:
        raise ValueError('Invalid build ref')
    output = root / 'output/pdf/workpackages'
    output.mkdir(parents=True, exist_ok=True)
    flags = ['latexmk', '--shell-escape', '-pdf', '-halt-on-error',
             '-interaction=nonstopmode', '-synctex=1']
    print('Building and checking the consolidated report', flush=True)
    run(flags + ['exa-ma-deliverables.tex'], root, output / 'report-build.log')
    check_log(root / 'exa-ma-deliverables.log')
    report = read_labels(root / 'exa-ma-deliverables.aux')
    shutil.copy2(root / 'exa-ma-deliverables.pdf', output / 'exa-ma-deliverables.pdf')

    def build_one(wp):
        print(f'Building WP{wp}: discovering local labels', flush=True)
        job = f'exa-ma-wp{wp}'
        entry = f'standalone-wp{wp}.tex'
        # Compile in the source directory so minted 2 can find its Pygments input.
        command = flags + [f'-jobname={job}', '-g']
        # Disable any previous import: a label removed from this WP must become
        # external again, and a newly local label must no longer be imported.
        run(command + [r'-usepretex=\def\WPReferenceAux{}', entry], root,
            output / f'wp{wp}-local-build.log')
        local = read_labels(root / f'{job}.aux')
        reference = output / f'wp{wp}-references.aux'
        reference.write_text(external_labels(report, local))
        # xr-hyper's explicit PDF target is relative to the distributed WP PDF.
        relative = reference.relative_to(root).with_suffix('').as_posix()
        run(command + [r'-usepretex=\def\WPReferenceAux{' + relative + '}', entry], root,
            output / f'wp{wp}-build.log')
        check_log(root / f'{job}.log')
        for extension in ('pdf', 'fls', 'log'):
            name = f'{job}.{extension}'
            shutil.copy2(root / name, output / name)
        print(f'WP{wp}: references and citations resolved', flush=True)
        return {'pdf': f'{job}.pdf', 'entry_point': entry,
                'local_label_count': len(LABEL.findall(local)),
                'external_label_count': len(LABEL.findall(reference.read_text()))}

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        records = dict(zip((f'WP{wp}' for wp in wps), executor.map(build_one, wps)))
    pdfs = [output / value['pdf'] for value in records.values()]
    pdfs.append(output / 'exa-ma-deliverables.pdf')
    sources = {}
    for recorder in [root / 'exa-ma-deliverables.fls',
                     *(output / f'exa-ma-wp{wp}.fls' for wp in wps)]:
        for line in recorder.read_text().splitlines():
            if not line.startswith('INPUT '):
                continue
            path = (root / line[6:]).resolve()
            if (path.is_relative_to(root) and not path.is_relative_to(root / 'output')
                    and path.is_file() and path.suffix in {'.tex', '.sty', '.bib'}):
                sources[path.relative_to(root).as_posix()] = sha256(path)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True)
    manifest = {'report_version': tomllib.loads((root / 'pyproject.toml').read_text())['project']['version'],
                'revision': revision, 'ref': ref, 'working_tree': 'modified' if status else 'clean',
                'workpackages': records, 'companion_report': 'exa-ma-deliverables.pdf',
                'sha256': {path.name: sha256(path) for path in pdfs},
                'source_sha256': dict(sorted(sources.items()))}
    manifest_path = output / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    archive = output / f'exa-ma-workpackages-{suffix}.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in pdfs + [manifest_path]:
            bundle.write(path, path.name)
    print(f'Bundle: {archive}', flush=True)
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wp', type=int, choices=range(1, 8), action='append',
                        help='Build one WP (repeatable); by default build WP1 to WP7')
    parser.add_argument('--ref', default='local-review', help='Archive suffix and manifest build ref')
    parser.add_argument('--jobs', type=int, default=1, help='Concurrent WP builds; report is built once')
    args = parser.parse_args()
    try:
        build(wps=args.wp or range(1, 8), ref=args.ref, jobs=args.jobs)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
