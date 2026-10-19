"""One native log directory per game, in-place rollback, and legacy copy cleanup."""

import json
import os

import pytest

from support import started_session
from tft_mcp.errors import SessionError
from tft_mcp.native_logs import consolidate, main
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
        (native / name / 'log.txt').write_text(''.join(f'round {index}\n' for index in range(offset + 1)))
        os.utime(native / name / 'log.txt', (1000 + offset, 1000 + offset))
    records = [{'event': 'game_started', 'game_id': game_id, 'native_log_dir': str(native / game_id)},
               {'event': 'progression', 'game_id': game_id, 'native_log_dir': str(native / names[recorded])}]
    if closed:
        records.append({'event': 'game_closed', 'game_id': game_id, 'native_log_dir': str(native / names[recorded])})
    with (root / 'audit.jsonl').open('a') as audit:
        audit.writelines(json.dumps(record) + '\n' for record in records)
    return native, names


def test_cleanup_keeps_the_last_recorded_copy(tmp_path, capsys):
    game_id = 'a' * 32
    native, names = legacy_layout(tmp_path, game_id, copies=3, recorded=2)
    # A later failed action left only bytes already in the accepted copy.
    (native / names[3] / 'log.txt').write_text('round 0\n')
    for name in names:
        (native / name / 'nested').mkdir()
        (native / name / 'nested' / 'metadata.bin').write_bytes(b'\x00\xffsame')
    (native / names[2] / 'accepted-only.txt').write_text('preserved')
    accepted = snapshot(native / names[2])
    other = native / ('b' * 32)
    other.mkdir()
    (native / 'unrelated').mkdir()
    before = snapshot(tmp_path)
    assert main([str(native), '--dry-run']) == 0
    assert snapshot(tmp_path) == before
    assert main([str(native)]) == 0
    assert sorted(path.name for path in native.iterdir()) == sorted([game_id, 'b' * 32, 'unrelated'])
    assert snapshot(native / game_id) == accepted
    assert f'merged {game_id}' in capsys.readouterr().out


def test_cleanup_skips_open_games_unless_requested(tmp_path):
    game_id = 'c' * 32
    native, names = legacy_layout(tmp_path, game_id, copies=2, recorded=1, closed=False)
    (native / names[2] / 'log.txt').write_text('round 0\n')
    accepted = (native / names[1] / 'log.txt').read_bytes()
    assert main([str(native)]) == 0
    assert len(list(native.iterdir())) == 3
    assert main([str(native), '--include-open']) == 0
    assert [path.name for path in native.iterdir()] == [game_id]
    assert (native / game_id / 'log.txt').read_bytes() == accepted


def test_cleanup_without_audit_keeps_the_newest_log(tmp_path):
    game_id = 'd' * 32
    native, names = legacy_layout(tmp_path, game_id, copies=2, recorded=0)
    accepted = (native / names[2] / 'log.txt').read_bytes()
    (tmp_path / 'audit.jsonl').unlink()
    assert main([str(native), '--include-open']) == 0
    assert (native / game_id / 'log.txt').read_bytes() == accepted


def snapshot(root):
    return {str(path.relative_to(root)): ('link', os.readlink(path)) if path.is_symlink()
            else ('directory',) if path.is_dir() else ('file', path.read_bytes())
            for path in root.rglob('*')}


def test_cleanup_compares_binary_log_prefixes_across_chunks(tmp_path):
    game_id = 'e' * 32
    native, names = legacy_layout(tmp_path, game_id, copies=1, recorded=1)
    prefix = b'\x00\xff' * 40000
    accepted = prefix + b'accepted tail'
    (native / names[1] / 'log.txt').write_bytes(accepted)
    (native / game_id / 'log.txt').write_bytes(prefix)
    assert main([str(native)]) == 0
    assert [path.name for path in native.iterdir()] == [game_id]
    assert (native / game_id / 'log.txt').read_bytes() == accepted


@pytest.mark.parametrize('damage', ['divergent-log', 'divergent-chunk', 'longer-log', 'unique-file', 'different-file',
                                  'missing-kept-log', 'log-symlink', 'nested-symlink',
                                  'kept-log-symlink', 'copy-symlink', 'target-symlink',
                                  'broken-target', 'target-file'])
@pytest.mark.parametrize('dry_run', [False, True])
def test_cleanup_refuses_unsafe_copies_without_partial_deletion(tmp_path, capsys, damage, dry_run):
    # The valid earlier game must survive preflight failure in the later game.
    legacy_layout(tmp_path, 'a' * 32, copies=1, recorded=1)
    game_id = 'f' * 32
    native, names = legacy_layout(tmp_path, game_id, copies=3, recorded=3)
    source, keep, target = native / names[2], native / names[3], native / game_id
    external = tmp_path / 'external'
    external.mkdir()
    (external / 'log.txt').write_bytes(b'external evidence\x00')
    if damage == 'divergent-log':
        (source / 'log.txt').write_text('different history\n')
    elif damage == 'divergent-chunk':
        prefix = b'\x00\xff' * 40000
        for name in names:
            (native / name / 'log.txt').write_bytes(prefix)
        (keep / 'log.txt').write_bytes(prefix + b'accepted tail')
        (source / 'log.txt').write_bytes(prefix[:-1] + b'X')
    elif damage == 'longer-log':
        (source / 'log.txt').write_bytes((keep / 'log.txt').read_bytes() + b'unaccepted\n')
    elif damage == 'unique-file':
        (source / 'evidence.bin').write_bytes(b'unique\x00')
    elif damage == 'different-file':
        (source / 'metadata').write_text('original')
        (keep / 'metadata').write_text('modified')
    elif damage == 'missing-kept-log':
        (keep / 'log.txt').unlink()
    elif damage == 'log-symlink':
        (source / 'log.txt').unlink()
        (source / 'log.txt').symlink_to(external / 'log.txt')
    elif damage == 'kept-log-symlink':
        (keep / 'log.txt').unlink()
        (keep / 'log.txt').symlink_to(external / 'log.txt')
    elif damage == 'nested-symlink':
        (source / 'nested').symlink_to(external, target_is_directory=True)
    elif damage == 'copy-symlink':
        (source / 'log.txt').unlink()
        source.rmdir()
        source.symlink_to(external, target_is_directory=True)
    else:
        (target / 'log.txt').unlink()
        target.rmdir()
        if damage == 'target-file':
            target.write_text('canonical evidence')
        else:
            target.symlink_to(external if damage == 'target-symlink' else tmp_path / 'missing',
                              target_is_directory=True)
    before = snapshot(tmp_path)
    assert main([str(native), *(['--dry-run'] if dry_run else [])]) == 1
    assert snapshot(tmp_path) == before
    assert 'refused native log cleanup' in capsys.readouterr().err


def test_direct_consolidation_refuses_unlisted_canonical_target(tmp_path):
    game_id = 'a' * 32
    native, names = legacy_layout(tmp_path, game_id, copies=2, recorded=2)
    copies = [native / name for name in names[1:]]
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match='canonical target collision'):
        consolidate(native, game_id, copies[-1], copies)
    assert snapshot(tmp_path) == before
