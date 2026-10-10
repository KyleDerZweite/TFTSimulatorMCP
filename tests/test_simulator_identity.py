"""Installed provenance identifies the simulator independently of MCP and host Git."""

import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from tft_mcp import session


def installed_digest():
    import Simulator

    root = Path(Simulator.__file__).resolve().parent
    digest = hashlib.sha256()
    for source in sorted(root.rglob('*.py')):
        digest.update(str(source.relative_to(root)).encode())
        digest.update(source.read_bytes())
    return digest.hexdigest()


def distribution_provenance(monkeypatch, provenance):
    real_distribution = session.metadata.distribution

    def distribution(name):
        original = real_distribution(name)
        if name == 'tft-simulator':
            return SimpleNamespace(version=original.version, read_text=lambda filename: provenance if filename == 'direct_url.json' else original.read_text(filename))
        return original

    monkeypatch.setattr(session.metadata, 'distribution', distribution)


def test_installed_git_commit_overrides_conflicting_revision_hint(monkeypatch):
    commit = '33c2c6eb873da1aaf319dc0c36bcbec1ad20c48d'
    distribution_provenance(monkeypatch, json.dumps({'vcs_info': {'vcs': 'git', 'commit_id': commit}}))
    monkeypatch.setenv('TFT_MCP_SIMULATOR_REVISION', 'unrelated-mcp-revision')
    identity = session.simulator_identity()
    assert identity['revision'] == commit
    assert identity['source_sha256'] == installed_digest()


def test_source_inside_unrelated_git_repository_uses_digest(monkeypatch, tmp_path):
    import Simulator

    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    subprocess.run(['git', '-C', str(tmp_path), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                    'commit', '--allow-empty', '-qm', 'Unrelated host repository'], check=True)
    source = tmp_path / 'venv/lib/python/site-packages/Simulator'
    source.mkdir(parents=True)
    (source / '__init__.py').write_text('# Source without Git provenance\n')
    monkeypatch.setattr(Simulator, '__file__', str(source / '__init__.py'))
    distribution_provenance(monkeypatch, None)
    monkeypatch.delenv('TFT_MCP_SIMULATOR_REVISION', raising=False)
    parent_head = subprocess.run(['git', '-C', str(source), 'rev-parse', 'HEAD'],
                                 check=True, capture_output=True, text=True).stdout.strip()
    identity = session.simulator_identity()
    assert identity['revision'] == 'sha256:' + installed_digest()
    assert identity['revision'] != parent_head


@pytest.mark.parametrize('provenance', [None, '{broken', '{}', '{"archive_info": {}}'])
def test_missing_vcs_provenance_retains_archive_hint_and_actual_digest(monkeypatch, provenance):
    distribution_provenance(monkeypatch, provenance)
    monkeypatch.setenv('TFT_MCP_SIMULATOR_REVISION', 'explicit-archive-revision')
    identity = session.simulator_identity()
    assert identity['revision'] == 'explicit-archive-revision'
    assert identity['source_sha256'] == installed_digest()
    monkeypatch.delenv('TFT_MCP_SIMULATOR_REVISION')
    assert session.simulator_identity()['revision'] == 'sha256:' + installed_digest()


def test_acceptance_identity_allows_installed_venv_beneath_checkout(monkeypatch, tmp_path):
    import sys
    import test_acceptance
    from support import started_session

    checkout = Path(sys.prefix).resolve().parent
    root = Path(session.metadata.distribution('tft-simulator').locate_file('Simulator')).resolve()
    assert root.is_relative_to(checkout)
    monkeypatch.setattr(test_acceptance, '__file__', str(checkout / 'tests/test_acceptance.py'))
    game = started_session(tmp_path)
    try:
        events = [json.loads(line) for line in (tmp_path / 'audit.jsonl').read_text().splitlines()]
        start = next(event for event in events if event['event'] == 'game_started')
        test_acceptance.check_start_identity(start)
    finally:
        game.close_game()
