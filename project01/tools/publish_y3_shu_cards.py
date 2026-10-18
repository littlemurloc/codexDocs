"""Publish only the reviewed Shu manifest, with hashes, backup and rollback."""
from __future__ import annotations
import argparse,json,os,zipfile
from pathlib import Path
import y3_shu_command_cards as s

def preflight():
    assert s.MAP.resolve()==Path('D:/littl/testTempFile/ProjectMonster02/maps/map3').resolve()
    manifest=json.loads((s.WORK/'manifest.json').read_text('utf8'))
    specs=json.loads((s.WORK/'specs.json').read_text('utf8'))
    assert json.loads((s.WORK/'scope.json').read_text('utf8'))['require_level5'] is True
    allowed={f'{folder}/{aid}.json' for folder in ('ability','editor_table/abilityall') for aid in specs}
    allowed|={f'{folder}/{oid}.json' for folder in ('modifier','editor_table/modifierall') for oid in (s.CONTROL,s.ARMY)}
    allowed|={f'{s.FOLDER}/{name}.json' for name in s.NAMES.values()}
    allowed|={s.FOLDER+'/index.txt','global_trigger/function/new/index.txt',
      'editor/folderinfo/folderinfo_ability_all.json','editor/folderinfo/folderinfo_modifier_all.json','customevent.json','zhlanguage.json',
      'tables/军令卡牌技能表.json','tables/蜀国temp.json','tables/技能作用描述表.json',
      'global_trigger/function/new/功能执行/3选1军略卡牌处理.json',
      'global_trigger/function/new/功能执行/军略3选1-处理合成的新卡牌.json'}
    assert set(manifest)==allowed and len(manifest)==99
    with zipfile.ZipFile(s.WORK/'before-shu.zip') as backup:
        for rel,rec in manifest.items():
            dest=(s.MAP/rel).resolve();assert s.MAP.resolve() in dest.parents
            before=dest.read_bytes() if dest.exists() else None
            assert (s.sha(before) if before is not None else None)==rec['before'],'Live changed: '+rel
            if before is not None:assert s.sha(backup.read(rel))==rec['before']
            raw=(s.STAGE/rel).read_bytes();assert s.sha(raw)==rec['after'];after=json.loads(raw)
            if rel.endswith(('3选1军略卡牌处理.json','军略3选1-处理合成的新卡牌.json')):
                calls=[a for a in after['action'] if a.get('action_type')=='CALL_TRIGGER_FUNC' and a['args_list'][0]['sub_type']==s.FIDS[14]]
                assert len(calls)==1
                assert {**after,'action':[a for a in after['action'] if a not in calls]}==json.loads(before)
    return manifest

def publish(apply=False):
    manifest=preflight();protected={}
    for folder in ['ability','modifier','editor_table','tables','global_trigger']:
        for p in (s.MAP/folder).rglob('*.json'):
            rel=p.relative_to(s.MAP).as_posix()
            if rel not in manifest:protected[rel]=s.sha(p.read_bytes())
    print('Preflight passed:',len(manifest),'reviewed files;',len(protected),'protected files; six sets + level5 required.')
    if not apply:return
    assert not (s.WORK/'published.json').exists(),'Already published'
    done=[]
    try:
        for rel in manifest:
            dest=(s.MAP/rel).resolve();dest.parent.mkdir(parents=True,exist_ok=True)
            pending=dest.with_name(dest.name+'.codex-shu-pending');assert not pending.exists()
            try:pending.write_bytes((s.STAGE/rel).read_bytes());os.replace(pending,dest)
            finally:
                if pending.exists():pending.unlink()
            done.append(rel)
        for rel,rec in manifest.items():assert s.sha((s.MAP/rel).read_bytes())==rec['after'],rel
        for rel,expected in protected.items():assert s.sha((s.MAP/rel).read_bytes())==expected,'Protected changed: '+rel
    except BaseException:
        with zipfile.ZipFile(s.WORK/'before-shu.zip') as backup:
            for rel in reversed(done):
                dest=s.MAP/rel
                if manifest[rel]['before'] is None:dest.unlink()
                else:dest.write_bytes(backup.read(rel))
        raise
    (s.WORK/'protected-hashes.json').write_text(json.dumps(protected,ensure_ascii=False,indent=2),encoding='utf8')
    (s.WORK/'published.json').write_text(json.dumps({'map':str(s.MAP),'manifest':manifest,'editor_verified':False,'game_verified':False},ensure_ascii=False,indent=2),encoding='utf8')
    print('Published and hash-verified 99 files; unrelated cards, heroes and global triggers preserved.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');publish(parser.parse_args().apply)
