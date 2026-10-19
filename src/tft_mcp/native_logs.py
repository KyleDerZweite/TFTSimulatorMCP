"""Merge legacy per-action native log copies into one directory per game."""

import argparse
import json
from pathlib import Path
import re
import shutil
import sys


GAME_DIRECTORY = re.compile(r'^([0-9a-f]{32})(?:-[0-9a-f]{32})?$')


def audit_games(audit_path):
    """Last recorded native directory name and closed flag for each audited game."""
    games = {}
    if audit_path is None or not audit_path.is_file():
        return games
    with audit_path.open(encoding='utf-8') as stream:
        for line in stream:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            game_id = record.get('game_id')
            if not isinstance(game_id, str):
                continue
            game = games.setdefault(game_id, {'directory': None, 'closed': False})
            if isinstance(record.get('native_log_dir'), str):
                game['directory'] = Path(record['native_log_dir']).name
            if record.get('event') == 'game_closed':
                game['closed'] = True
    return games


def log_mtime(directory):
    log = directory / 'log.txt'
    return log.stat().st_mtime if log.is_file() else 0.0


def plan(native_root, audit_path):
    """Yield (game_id, kept directory, all directories, closed) for games with copies."""
    groups = {}
    for path in native_root.iterdir():
        match = GAME_DIRECTORY.match(path.name)
        if match and (path.is_dir() or path.is_symlink()):
            groups.setdefault(match.group(1), []).append(path)
    recorded = audit_games(audit_path)
    for game_id, directories in sorted(groups.items()):
        if all(directory.name == game_id for directory in directories):
            continue
        game = recorded.get(game_id, {'directory': None, 'closed': False})
        by_name = {directory.name: directory for directory in directories}
        keep = by_name.get(game['directory']) or max(directories, key=log_mtime)
        yield game_id, keep, sorted(directories), game['closed']


def _files(directory):
    """Inventory regular files without following any symlinks."""
    files = {}
    pending = [directory]
    while pending:
        parent = pending.pop()
        for path in parent.iterdir():
            if path.is_symlink():
                raise ValueError(f'symlink in native logs: {path}')
            if path.is_dir():
                pending.append(path)
            elif path.is_file():
                files[path.relative_to(directory)] = path
            else:
                raise ValueError(f'not a regular native log file: {path}')
    return files


def _is_prefix(source, kept):
    with source.open('rb') as original, kept.open('rb') as accepted:
        while chunk := original.read(65536):
            if accepted.read(len(chunk)) != chunk:
                return False
    return True


def _validate_consolidation(native_root, game_id, keep, directories):
    """Prove every file to be removed is already represented in the kept copy."""
    if not re.fullmatch(r'[0-9a-f]{32}', game_id):
        raise ValueError(f'invalid game ID: {game_id}')
    if keep not in directories or len(set(directories)) != len(directories):
        raise ValueError('kept directory must be one of the distinct native copies')
    root = native_root.resolve()
    for directory in directories:
        match = GAME_DIRECTORY.fullmatch(directory.name)
        if (not match or match.group(1) != game_id or directory != root / directory.name
                or directory.is_symlink() or not directory.is_dir()):
            raise ValueError(f'unsafe native copy: {directory}')
    target = native_root / game_id
    if target.is_symlink() or (target.exists() and target not in directories):
        raise ValueError(f'unsafe canonical target collision: {target}')
    kept_files = _files(keep)
    for directory in directories:
        if directory == keep:
            continue
        for relative, source in _files(directory).items():
            accepted = kept_files.get(relative)
            if accepted is None:
                raise ValueError(f'unique file would be removed: {source}')
            if relative != Path('log.txt') and source.stat().st_size != accepted.stat().st_size:
                raise ValueError(f'divergent file would be removed: {source}')
            if not _is_prefix(source, accepted):
                raise ValueError(f'divergent file would be removed: {source}')


def consolidate(native_root, game_id, keep, directories):
    _validate_consolidation(native_root, game_id, keep, directories)
    target = native_root / game_id
    for directory in directories:
        if directory != keep:
            shutil.rmtree(directory)
    if keep != target:
        keep.rename(target)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='python -m tft_mcp.native_logs',
        description='Merge per-action native log copies into native/<game_id>/. '
                    'Keeps the copy the audit last recorded as accepted. '
                    'Removes other copies only when every file is redundant.')
    parser.add_argument('native_dir', type=Path, help='TFT_MCP_NATIVE_LOG_DIR of the installation.')
    parser.add_argument('--audit', type=Path, help='Audit log. Defaults to audit.jsonl beside native_dir.')
    parser.add_argument('--dry-run', action='store_true', help='Print the plan without changing files.')
    parser.add_argument('--include-open', action='store_true',
                        help='Also merge games without a game_closed record. Stop their server first.')
    args = parser.parse_args(argv)
    native_root = args.native_dir.resolve()
    if not native_root.is_dir():
        print(f'not a directory: {native_root}', file=sys.stderr)
        return 1
    audit_path = args.audit or native_root.parent / 'audit.jsonl'
    eligible = []
    try:
        for game_id, keep, directories, closed in plan(native_root, audit_path):
            removed = len(directories) - 1
            if not closed and not args.include_open:
                print(f'skip {game_id}: no game_closed record, {removed} copies left (use --include-open)')
                continue
            _validate_consolidation(native_root, game_id, keep, directories)
            eligible.append((game_id, keep, directories))
    except (OSError, ValueError) as error:
        print(f'refused native log cleanup: {error}', file=sys.stderr)
        return 1
    for game_id, keep, directories in eligible:
        removed = len(directories) - 1
        if args.dry_run:
            print(f'would merge {game_id}: keep {keep.name}, remove {removed}')
            continue
        try:
            target = consolidate(native_root, game_id, keep, directories)
        except (OSError, ValueError) as error:
            print(f'refused native log cleanup: {error}', file=sys.stderr)
            return 1
        print(f'merged {game_id}: kept {keep.name} as {target.name}, removed {removed}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
