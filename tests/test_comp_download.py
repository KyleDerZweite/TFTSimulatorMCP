import hashlib
import zipfile

import pytest

from tft_mcp.comp_download import fetch


def archive_of(tmp_path, member, content):
    path = tmp_path / 'source.zip'
    with zipfile.ZipFile(path, 'w') as bundle:
        bundle.writestr(member, content)
    return path.as_uri()


def test_fetch_keeps_only_the_pinned_member(tmp_path):
    url = archive_of(tmp_path, 'games.csv', b'placement\n1\n')
    target = tmp_path / 'out' / 'games.csv'
    fetch(url, 'games.csv', target, hashlib.sha256(b'placement\n1\n').hexdigest())
    assert target.read_bytes() == b'placement\n1\n'
    assert sorted(path.name for path in target.parent.iterdir()) == ['games.csv']


def test_fetch_rejects_a_changed_member(tmp_path):
    url = archive_of(tmp_path, 'games.csv', b'placement\n2\n')
    target = tmp_path / 'out' / 'games.csv'
    with pytest.raises(ValueError, match='does not match'):
        fetch(url, 'games.csv', target, hashlib.sha256(b'placement\n1\n').hexdigest())
    assert list(target.parent.iterdir()) == []


def test_fetch_skips_a_verified_file(tmp_path):
    target = tmp_path / 'games.csv'
    target.write_bytes(b'placement\n1\n')
    fetch('file:///missing.zip', 'games.csv', target, hashlib.sha256(b'placement\n1\n').hexdigest())
    assert target.read_bytes() == b'placement\n1\n'
