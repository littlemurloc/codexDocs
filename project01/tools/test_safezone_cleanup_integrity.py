"""Guard fixed fixtures and permanently retired migration entry points."""
import hashlib,json,tempfile,unittest,zipfile,sys
from pathlib import Path
import safezone_ui_fixtures as f
import y3_safezone_skin_switch as s
import y3_safezone_inner_pages as b
import y3_hero_detail_restore as h
import y3_hero_skill_overview as m
import y3_hero_attribute_display_guard as g

class Integrity(unittest.TestCase):
    def test_archive_and_each_payload_match_manifest(self):
        manifest=json.loads(f.PACKAGE.with_name('manifest.json').read_bytes())
        self.assertEqual(hashlib.sha256(f.PACKAGE.read_bytes()).hexdigest(),manifest['archive_sha256'])
        with zipfile.ZipFile(f.PACKAGE)as archive:
            self.assertEqual(set(archive.namelist()),{r['path']for r in manifest['files']})
            for record in manifest['files']:
                raw=archive.read(record['path']);self.assertEqual(hashlib.sha256(raw).hexdigest(),record['sha256'])
    def test_all_five_fixture_stages_extract_without_historical_tmp(self):
        for name in ['skin','inner','detail','skills','attributes']:
            path=f.stage(name);self.assertTrue((path/'manifest.json').exists());self.assertNotIn(str(f.ROOT/'tmp'),str(path))
        self.assertTrue((f.reference()/'namespace.json').exists())
    def test_retired_entry_points_cannot_revive_without_publish_markers(self):
        modules={s:['stage','publish'],b:['stage','publish'],h:['stage','publish','repair_close_stage'],
                 m:['stage','publish','repair_none_stage'],g:['stage','publish']}
        with tempfile.TemporaryDirectory(prefix='safezone-retired-check-')as temp:
            for module,names in modules.items():
                old=module.WORK;module.WORK=Path(temp)/module.__name__
                try:
                    for name in names:
                        with self.assertRaisesRegex(RuntimeError,'retired'):getattr(module,name)()
                    self.assertFalse(module.WORK.exists())
                finally:module.WORK=old

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]);result=unittest.TextTestRunner(verbosity=2).run(suite)
    f.result_path('cleanup-integrity').write_text(json.dumps(dict(passed=result.wasSuccessful(),tests=result.testsRun),indent=2),encoding='utf-8')
    sys.exit(0 if result.wasSuccessful()else 1)
