"""Read verified, compressed regression inputs; never map deployment payloads.

Frozen 2026-10-29/30 examples survive cleanup of transient candidates/backups.
No extraction into tmp and no writes to fixtures or original acceptance receipts.
"""
from copy import deepcopy
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'tests/fixtures/y3-recent-work'


@lru_cache(maxsize=5)
def _read(name):
    assert name in ('damage-context','combat-batch02','combat-batch03','forge','card-ui')
    manifest=json.loads((ROOT/'manifest.json').read_text('utf8'))
    entry=manifest['files'][name]
    raw=(ROOT/entry['file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==entry['sha256'],'Fixture changed; review its provenance'
    doc=json.loads(gzip.decompress(raw))
    assert doc['schema']==1 and doc['purpose']=='read-only regression input'
    return doc


def load(name):
    return deepcopy(_read(name))


def document(name,section,relative):
    return deepcopy(_read(name)[section][relative])


def manifest(name):
    return deepcopy(_read(name)['manifest'])
