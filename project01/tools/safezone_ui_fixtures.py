"""Read-only frozen regression inputs; no live editor or historical tmp needed."""
from __future__ import annotations
import atexit,json,tempfile,zipfile,hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'tests/fixtures/safezone-ui-20261119/fixtures.zip'
_runtime=None;_loaded=set();_verified=False

def _extract(prefix):
    global _runtime,_verified
    if not _verified:
        manifest=json.loads(PACKAGE.with_name('manifest.json').read_bytes())
        if hashlib.sha256(PACKAGE.read_bytes()).hexdigest()!=manifest['archive_sha256']:raise ValueError('Fixture archive checksum mismatch')
        _verified=True
    if _runtime is None:
        _runtime=tempfile.TemporaryDirectory(prefix='project01-safezone-tests-')
        atexit.register(_runtime.cleanup)
    base=Path(_runtime.name)
    if prefix not in _loaded:
        with zipfile.ZipFile(PACKAGE)as archive:
            for info in archive.infolist():
                if not info.filename.startswith(prefix+'/'):continue
                target=(base/info.filename).resolve()
                if not target.is_relative_to(base.resolve()):raise ValueError('Unsafe fixture path')
                if not info.is_dir():
                    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(info))
        _loaded.add(prefix)
    return base/prefix

def stage(name):return _extract('stages/'+name)
def reference():return _extract('reference')
def namespace():return json.loads((reference()/'namespace.json').read_bytes())
def result_path(name):
    dest=ROOT/'deliverables/evidence/safezone-closeout-20261119/regression'
    dest.mkdir(parents=True,exist_ok=True);return dest/(name+'.json')

def retired_publish():
    raise RuntimeError('This 2026-11-19 migration/publish entry is retired. Use a new scoped maintenance patch against the current map; see deliverables/安全区界面实装复盘与清理-2026-11-19.md')
