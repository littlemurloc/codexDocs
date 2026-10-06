"""Show semantic JSON differences between a staged tree and a live map tree."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def differences(left, right, where=""):
    if type(left) is not type(right):
        yield where, left, right
    elif isinstance(left, dict):
        for key in sorted(left.keys() | right.keys()):
            path = f"{where}/{key}"
            if key not in left or key not in right:
                yield path, left.get(key, "<missing>"), right.get(key, "<missing>")
            else:
                yield from differences(left[key], right[key], path)
    elif isinstance(left, list):
        if len(left) != len(right):
            yield f"{where}/length", len(left), len(right)
        for index, (a, b) in enumerate(zip(left, right)):
            yield from differences(a, b, f"{where}/{index}")
    elif left != right:
        yield where, left, right


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("map", type=Path)
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()
    for staged in sorted(args.candidate.rglob("*.json")):
        relative = staged.relative_to(args.candidate)
        live = args.map / relative
        with staged.open(encoding="utf-8") as file:
            a = json.load(file)
        with live.open(encoding="utf-8") as file:
            b = json.load(file)
        changes = list(differences(a, b))
        print(f"{relative}: {len(changes)} semantic differences")
        for path, old, new in changes[:args.limit]:
            print(f"  {path}: staged={old!r} live={new!r}")
