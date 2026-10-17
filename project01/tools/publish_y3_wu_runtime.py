"""Hash-checked migration, including three narrowly identified obsolete files."""
from __future__ import annotations
import argparse,hashlib,json,os,zipfile
from pathlib import Path
import y3_wu_runtime_tables as d
def sha(raw):return hashlib.sha256(raw).hexdigest()
def publish(apply=False):
    root=d.b.MAP.resolve();stage=d.STAGE.resolve()
    assert root==Path(r'D:\littl\testTempFile\ProjectMonster02\maps\map3').resolve()
    manifest=json.loads((d.WORK/'manifest.json').read_text('utf8'))
    object_ids={int(Path(rel).stem) for rel in manifest if rel.startswith('editor_table/abilityall/')}
    assert len(object_ids)==31
    allowed={f'ability/{aid}.json' for aid in object_ids}|{f'editor_table/abilityall/{aid}.json' for aid in object_ids}
    allowed|={f'modifier/{oid}.json' for oid in (d.b.CONTROL,d.b.ARMY)}
    allowed|={f'{d.r.FOLDER}/{name}.json' for name in d.NAMES.values()}
    allowed|={d.r.FOLDER+'/'+d.r.NAMES[11]+'.json',d.r.FOLDER+'/index.txt','editor/tableeditorgroupinfo.json',
        'global_trigger/function/new/功能执行/3选1军略卡牌处理.json',
        'global_trigger/function/new/功能执行/军略3选1-处理合成的新卡牌.json'}
    removed={rel for rel,v in manifest.items() if v['after'] is None}
    assert len(removed)==3
    allowed|=removed
    assert set(manifest)==allowed and len(manifest)==85
    with zipfile.ZipFile(d.WORK/'before-runtime.zip') as backup:
        for rel,record in manifest.items():
            dest=(root/rel).resolve();assert root in dest.parents
            before=dest.read_bytes() if dest.exists() else None
            assert (sha(before) if before is not None else None)==record['before'],'Live changed: '+rel
            if before is not None:assert sha(backup.read(rel))==record['before']
            if record['after'] is None:
                obj=json.loads(before)
                if rel.startswith('tables/'):assert obj['tid'] in (d.r.CARD_TID,d.r.FIELD_TID)
                else:assert obj['func_id']==d.r.FIDS[11] and rel==d.r.FOLDER+'/'+d.r.NAMES[11]+'.json'
                continue
            candidate=(stage/rel).resolve();assert stage in candidate.parents
            raw=candidate.read_bytes();assert sha(raw)==record['after'];after=json.loads(raw)
            if rel.startswith('editor_table/abilityall/'):
                original=json.loads(before);kv=after['kv'];stripped={k:v for k,v in kv.items() if k not in (d.FACTION,d.IDENTITY)}
                assert stripped==original['kv'];after_compare={**after,'kv':stripped};assert after_compare==original
            if rel in ('global_trigger/function/new/功能执行/3选1军略卡牌处理.json','global_trigger/function/new/功能执行/军略3选1-处理合成的新卡牌.json'):
                original=json.loads(before);calls=[a for a in after['action'] if a.get('action_type')=='CALL_TRIGGER_FUNC' and a['args_list'][0].get('sub_type')==d.FIDS[14]]
                assert len(calls)==1
                stripped={**after,'action':[a for a in after['action'] if a is not calls[0]]};assert stripped==original
    # Guard all external references and numeric/game resources against unintended edits.
    protected={}
    for folder in ['ability','modifier','editor_table','tables','global_trigger']:
        for path in (root/folder).rglob('*.json'):
            rel=str(path.relative_to(root)).replace('\\','/')
            if rel in manifest:continue
            raw=path.read_bytes();protected[rel]=sha(raw)
            assert d.r.CARD_TID.encode() not in raw and d.r.FIELD_TID.encode() not in raw, 'External preset-table reference: '+rel
            if any(fid.encode() in raw for fid in (d.FIDS[3],d.FIDS[4],d.FIDS[11])):
                raise AssertionError('External call to changed private function: '+rel)
    print('Preflight passed: 85 paths; 3 obsolete files; object values and existing acquisition logic preserved;',len(protected),'protected resources.')
    if not apply:return
    (d.WORK/'protected-hashes.json').write_text(json.dumps(protected,ensure_ascii=False,indent=2),encoding='utf8')
    completed=[]
    try:
        for rel,record in manifest.items():
            dest=(root/rel).resolve();assert root in dest.parents
            if record['after'] is None:
                # Individually verified files only. No recursive filesystem operation.
                dest.unlink()
            else:
                dest.parent.mkdir(parents=True,exist_ok=True);pending=dest.with_name(dest.name+'.codex-runtime-pending')
                assert not pending.exists()
                try:pending.write_bytes((stage/rel).read_bytes());os.replace(pending,dest)
                finally:
                    if pending.exists():pending.unlink()
            completed.append(rel)
        for rel,record in manifest.items():
            dest=root/rel;assert (sha(dest.read_bytes()) if dest.exists() else None)==record['after']
        for rel,expected in protected.items():assert sha((root/rel).read_bytes())==expected, 'Protected file changed: '+rel
    except BaseException:
        with zipfile.ZipFile(d.WORK/'before-runtime.zip') as backup:
            for rel in reversed(completed):
                dest=(root/rel).resolve();assert root in dest.parents
                if manifest[rel]['before'] is None:
                    if dest.exists():dest.unlink()
                else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(backup.read(rel))
        raise
    (d.WORK/'published.json').write_text(json.dumps({'paths':manifest,'map':str(root),
        'protected_count':len(protected),'editor_verified':False,'game_verified':False},ensure_ascii=False,indent=2),encoding='utf8')
    print('Published migration; all changed paths and protected resources verified.')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');publish(parser.parse_args().apply)
