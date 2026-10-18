"""One native log directory per game, in-place rollback, and legacy copy cleanup."""

import json
import os

import pytest

from support import started_session
from tft_mcp.errors import SessionError
from tft_mcp.native_logs import main
from tft_mcp.session import GameSession


def test_actions_write_one_native_directory(tmp_path):
    session = started_session(tmp_path)
    directory = session.native_dir
    with pytest.raises(SessionError) as masked:
        session.move_unit(source={'kind': 'bench', 'slot': 8}, target={'kind': 'bench', 'slot': 8})
    assert masked.value.code == 'masked' and 'native_log_dir' not in masked.value.details
    session.end_turn()
    session.end_turn()
    assert session.native_dir == directory == tmp_path / 'native' / session.game_id
    assert sorted(path.name for path in (tmp_path / 'native').iterdir()) == [session.game_id]
    records = [json.loads(line) for line in session.audit_path.read_text().splitlines()]
    assert {record['native_log_dir'] for record in records if 'native_log_dir' in record} == {str(directory)}


def test_failed_commit_restores_native_log_in_place(tmp_path, monkeypatch):
    session = started_session(tmp_path)
    log = session.native_dir / 'log.txt'
    accepted = log.read_bytes()
    written = []

    def failed_publish(current):
        written.append(log.read_bytes())
        (current.native_dir / 'stray.txt').write_text('uncommitted')
        raise SessionError('log_unavailable', 'Injected audit failure.')

    with monkeypatch.context() as patch:
        patch.setattr(GameSession, 'publish_audit', failed_publish)
        with pytest.raises(SessionError) as failed:
            session.end_turn()
    assert failed.value.code == 'log_unavailable'
    assert written and written[0] != accepted
    assert log.read_bytes() == accepted
    assert sorted(path.name for path in session.native_dir.iterdir()) == ['log.txt']
    assert sorted(path.name for path in (tmp_path / 'native').iterdir()) == [session.game_id]
    session.end_turn()
    assert log.read_bytes().startswith(accepted) and log.read_bytes() != accepted


def legacy_layout(root, game_id, copies, recorded, closed=True):
    native = root / 'native'
    names = [game_id] + [f'{game_id}-{index:032x}' for index in range(1, copies + 1)]
    for offset, name in enumerate(names):
        (native / name).mkdir(parents=True)
        (native / name / 'log.txt').write_text(f'{name}\n')
        os.utime(native / name / 'log.txt', (1000 + offset, 1000 + offset))
    records = [{'event': 'game_started', 'game_id': game_id, 'native_log_dir': str(native / game_id)},
               {'event': 'progression', 'game_id': game_id, 'native_log_dir': str(native / names[recorded])}]
    if closed:
        records.append({'event': 'game_closed', 'game_id': game_id, 'native_log_dir': str(native / names[recorded])})
    (root / 'audit.jsonl').write_text(''.join(json.dumps(record) + '\n' for record in records))
    return native, names


def test_cleanup_keeps_the_last_recorded_copy(tmp_path, capsys):
    game_id = 'a' * 32
    native, names = legacy_layout(tmp_path, game_id, copies=3, recorded=2)
    other = native / ('b' * 32)
    other.mkdir()
    (native / 'unrelated').mkdir()
    assert main([str(native), '--dry-run']) == 0
    assert len(list(native.iterdir())) == 6
    assert main([str(native)]) == 0
    assert sorted(path.name for path in native.iterdir()) == sorted([game_id, 'b' * 32, 'unrelated'])
    assert (native / game_id / 'log.txt').read_text() == f'{names[2]}\n'
    assert f'merged {game_id}' in capsys.readouterr().out


def test_cleanup_skips_open_games_unless_requested(tmp_path):
    game_id = 'c' * 32
    native, names = legacy_layout(tmp_path, game_id, copies=2, recorded=1, closed=False)
    assert main([str(native)]) == 0
    assert len(list(native.iterdir())) == 3
    assert main([str(native), '--include-open']) == 0
    assert [path.name for path in native.iterdir()] == [game_id]
    assert (native / game_id / 'log.txt').read_text() == f'{names[1]}\n'


def test_cleanup_without_audit_keeps_the_newest_log(tmp_path):
    game_id = 'd' * 32
    native, names = legacy_layout(tmp_path, game_id, copies=2, recorded=0)
    (tmp_path / 'audit.jsonl').unlink()
    assert main([str(native), '--include-open']) == 0
    assert (native / game_id / 'log.txt').read_text() == f'{names[2]}\n'
