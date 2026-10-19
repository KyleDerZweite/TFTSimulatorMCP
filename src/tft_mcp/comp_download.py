"""Download the public Set 4 sources that rebuild the comp index.

The Challenger CSV is too large to commit. Kaggle serves the dataset bundle
without an API key. Riot's Fates archive supplies the item names. Only the
extracted files are kept, and each must match its pinned SHA-256.
"""

import argparse
import os
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.request
import zipfile

from tft_mcp.comp_index import (
    OFFICIAL_CSV_SHA256, default_csv_path, default_items_path, file_sha256,
)


KAGGLE_URL = ('https://www.kaggle.com/api/v1/datasets/download/'
              'mariuszmackowski/teamfight-tactics-fates-challenger-euw-rank-games')
KAGGLE_MEMBER = 'TFT_set4_euw_challanger_games.csv'
RIOT_URL = 'https://static.developer.riotgames.com/docs/tft/set4.zip'
RIOT_MEMBER = 'items.json'
RIOT_ITEMS_SHA256 = 'f8c7c36a9d52caeab2ccd33fb6c0c224f246b35ff074bdce21d64d4661ac46f0'


def fetch(url, member, target, sha256):
    """Download the zip at `url` and keep only `member`, written to `target`."""
    target = Path(target)
    if target.is_file() and file_sha256(target) == sha256:
        print(f'{target} is already present')
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.tmp')
    try:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'archive.zip'
            print(f'downloading {url}')
            request = urllib.request.Request(url, headers={'User-Agent': 'tft-mcp'})
            with urllib.request.urlopen(request) as response, open(archive, 'wb') as handle:
                shutil.copyfileobj(response, handle, 1024 * 1024)
            with zipfile.ZipFile(archive) as bundle, bundle.open(member) as source, \
                    open(temporary, 'wb') as handle:
                shutil.copyfileobj(source, handle, 1024 * 1024)
        digest = file_sha256(temporary)
        if digest != sha256:
            raise ValueError(f'{member} sha256 {digest} does not match the pinned {sha256}.')
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    print(f'wrote {target}')


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Download the Set 4 Challenger CSV and Fates item list for the comp index.')
    parser.add_argument('--csv', type=Path, default=default_csv_path())
    parser.add_argument('--items', type=Path, default=default_items_path())
    args = parser.parse_args(argv)
    try:
        fetch(KAGGLE_URL, KAGGLE_MEMBER, args.csv, OFFICIAL_CSV_SHA256)
        fetch(RIOT_URL, RIOT_MEMBER, args.items, RIOT_ITEMS_SHA256)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
