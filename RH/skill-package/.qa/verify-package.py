import hashlib
import json
import sys
import zipfile
from pathlib import Path

root = Path('D:/codex/RH/skill-package/fc-season-web-demo')
archive = Path('D:/codex/RH/FC赛季活动网页工坊-Skill.zip')
files = {p.relative_to(root).as_posix(): p for p in root.rglob('*') if p.is_file()}
with zipfile.ZipFile(archive) as z:
    entries = {i.filename.replace('\\', '/'): i for i in z.infolist() if not i.is_dir()}
    expected = {'fc-season-web-demo/' + name for name in files}
    assert set(entries) == expected, (set(entries) - expected, expected - set(entries))
    for name, file in files.items():
        assert z.read('fc-season-web-demo/' + name) == file.read_bytes(), name
    assert z.testzip() is None
if len(sys.argv) > 1:
    installed = Path(sys.argv[1])
    installed_files = {p.relative_to(installed).as_posix(): p for p in installed.rglob('*') if p.is_file()}
    assert set(installed_files) == set(files)
    for name, file in files.items():
        assert installed_files[name].read_bytes() == file.read_bytes(), name
print(json.dumps({'fileCount': len(files), 'zipBytes': archive.stat().st_size,
                  'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                  'archiveMatchesSource': True, 'installedMatchesSource': len(sys.argv) > 1}, ensure_ascii=False))
