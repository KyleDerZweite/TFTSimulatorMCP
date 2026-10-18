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
        if match and path.is_dir():
            groups.setdefault(match.group(1), []).append(path)
    recorded = audit_games(audit_path)
    for game_id, directories in sorted(groups.items()):
        if all(directory.name == game_id for directory in directories):
            continue
        game = recorded.get(game_id, {'directory': None, 'closed': False})
        by_name = {directory.name: directory for directory in directories}
        keep = by_name.get(game['directory']) or max(directories, key=log_mtime)
        yield game_id, keep, sorted(directories), game['closed']


def consolidate(native_root, game_id, keep, directories):
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
                    'Keeps the copy the audit last recorded as accepted and removes the rest.')
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
    for game_id, keep, directories, closed in plan(native_root, audit_path):
        removed = len(directories) - 1
        if not closed and not args.include_open:
            print(f'skip {game_id}: no game_closed record, {removed} copies left (use --include-open)')
            continue
        if args.dry_run:
            print(f'would merge {game_id}: keep {keep.name}, remove {removed}')
            continue
        target = consolidate(native_root, game_id, keep, directories)
        print(f'merged {game_id}: kept {keep.name} as {target.name}, removed {removed}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
