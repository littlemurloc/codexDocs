"""Load compact, read-only military-card regression fixtures.

These are test inputs, not importable map backups or publication candidates.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'tests/fixtures/y3-command-cards'

def load(name):
    assert name in ('wei','qun','journal')
    return json.loads((ROOT/(name+'.json')).read_text('utf8'))
