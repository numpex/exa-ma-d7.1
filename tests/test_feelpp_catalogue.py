import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import feelpp_catalogue as catalogue

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def data():
    return json.loads((ROOT/'data/feelpp-mesh-catalogue.json').read_text())


def test_generated_material_is_current_and_all_fiches_import_it(data):
    catalogue.validate(data)
    assert catalogue.sync(catalogue.local_outputs(data), ROOT) == []
    for app in data['applications']:
        source = (ROOT/app['fiche_source']).read_text()
        assert source.count('\\input{chapters/applications/meshes/' + app['id'] + '}') == 1


@pytest.mark.parametrize('change', ['duplicate', 'unknown-mesh', 'unsafe-path', 'invented-count', 'missing-app', 'wrong-fiche'])
def test_reject_inconsistent_catalogue(data, change):
    broken = copy.deepcopy(data)
    if change == 'duplicate':
        broken['families'].append(broken['families'][0])
    elif change == 'unknown-mesh':
        broken['applications'][0]['mesh_families'] = ['missing']
    elif change == 'unsafe-path':
        broken['applications'][0]['existing_paths'] = ['../secret']
    elif change == 'invented-count':
        broken['families'][0]['mesh_counts'] = {'M1': 1000}
    elif change == 'missing-app':
        broken['applications'].pop()
    else:
        broken['applications'][0]['fiche_source'] = 'missing.tex'
    with pytest.raises(ValueError):
        catalogue.validate(broken)


def test_application_sources_cannot_be_overwritten_by_deliverable_export(tmp_path):
    owned = tmp_path/'apps/example/README.adoc'
    owned.parent.mkdir(parents=True)
    owned.write_text('Application-owned case description\n')
    result = subprocess.run([sys.executable, str(ROOT/'scripts/feelpp_catalogue.py'),
                             '--write', '--export-repo', str(tmp_path)],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert 'apps-feelpp owns its application layout' in result.stderr
    assert owned.read_text() == 'Application-owned case description\n'
    assert not (tmp_path/'data').exists()


def test_preserve_authored_files(data, tmp_path):
    target = tmp_path/'reviews/feelpp-fiche-todo.adoc'
    target.parent.mkdir()
    target.write_text('Authored application guide\n')
    with pytest.raises(ValueError, match='authored file'):
        catalogue.sync(catalogue.local_outputs(data), tmp_path, write=True)
    assert target.read_text() == 'Authored application guide\n'


def test_preserve_unrelated_json(tmp_path):
    target = tmp_path/'data/feelpp-mesh-catalogue.json'
    target.parent.mkdir()
    target.write_text('{"other": true}')
    with pytest.raises(ValueError, match='unrelated catalogue'):
        catalogue.sync({Path('data/feelpp-mesh-catalogue.json'): '{}'}, tmp_path, write=True)
