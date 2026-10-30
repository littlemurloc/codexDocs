"""Core UI presentation transformations and exact diagnostic helpers.

Initial batch03 staging/publication retired after 2026-10-30 delivery.
Frozen regression inputs preserve its behavior without old map backups.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import y3_damage_context_optimization as base
import y3_combat_optimization_batch02 as batch02

MAP, PROJECT = base.MAP, Path(__file__).resolve().parents[1]
UI = 'global_trigger/function/new/UI/刷新单位能量机制循环能量格子.json'
REBUILD = 'global_trigger/function/new/功能执行/根据拥有技能赋予能力循环机制.json'
FID = '4dfeaa39752111f1851e19023354d96d'
LEGACY = PROJECT / 'tools/data/y3-legacy-skill-diagnostics-registry.json'
PREFIX = '能量UI_'
load, encode, sha, walk, at, ex = base.load, base.encode, base.sha, base.walk, base.at, base.expr


def ref(kind, name):
    typ, sub = {'UNIT_ENTITY': (100006, 11), 'MODIFIER_ENTITY': (100076, 11),
                'INTEGER': (100002, 6), 'BOOLEAN': (100001, 'VARIABLE'),
                'TEXTURE': (100115, 2)}[kind]
    return ex(typ, sub, {'__tuple__': True, 'items': [kind, name, 'local']})


def call(unit, buff):
    return dict(action_type='CALL_TRIGGER_FUNC', args_list=[dict(arg_type=100177,
        sub_type=FID, args_list=[unit, buff], op_arg=[], op_arg_enable=[])],
        bp=False, enable=True, call_rt_arg_idxes=[])


class Nodes:
    def __init__(self): self.next = 2099947201000000
    def node(self, field, name, *args, **meta):
        self.next += 1
        result = dict(args_list=list(args), element_id=self.next, enable=True, **meta)
        result[field] = name
        if field == 'action_type': result['bp'] = False
        return result
    def act(self, name, *args, **meta): return self.node('action_type', name, *args, **meta)
    def cond(self, name, *args): return self.node('condition_type', name, *args)
    def branch(self, conditions, yes, no=()):
        return self.act('IF_THEN_ELSE', ex(100021, 1, *conditions),
                        ex(100022, 1, *yes), ex(100022, 1, *no))
    def box(self, title, actions):
        return self.act('STORAGE_BOX', ex(100021, 1), ex(100022, 1, *actions),
                        ex(100022, 1), ex(100003, 1, title))
    def assign(self, target, value):
        return self.act('SET_VARIABLE', ex(100030, 1, *copy.deepcopy(target['args_list'])), value)
    def exists(self, obj): return self.cond('TYPE_IS_EXIST', copy.deepcopy(obj))
    def has(self, obj, key): return self.cond('HAS_KV_ANY', copy.deepcopy(obj), ex(100003, 1, key))
    def put(self, obj, key, value):
        return self.act('SET_ENTITY_KV', copy.deepcopy(obj), ex(100003, 1, key), value)
    def get(self, obj, kind, key):
        typ, sub = {'BOOLEAN': (100001, 'GET_BOOLEAN_KV'),
                    'INTEGER': (100002, 'GET_INTEGER_KV'),
                    'TEXTURE': (100115, 'GET_TEXTURE_KV')}[kind]
        return ex(typ, sub, copy.deepcopy(obj), ex(100003, 1, key))
    def compare(self, kind, a, op, b):
        names = {'num': ('FLOAT_COMPARE',100015), 'bool': ('BOOL_COMPARE',100035),
                 'any': ('ANY_COMPARE',100035), 'modifier': ('MODIFIER_COMPARE',100035)}
        name, typ = names[kind]
        return self.cond(name, copy.deepcopy(a), ex(typ,1,op), copy.deepcopy(b))
    def bool(self, value): return self.compare('bool',value,'==',ex(100001,1,True))


def build_ui(original, sample_text, n):
    """One captured unit/Buff per queued callback; cache belongs to that Buff."""
    d = copy.deepcopy(original)
    assert d['func_id'] == FID and len(d['action']) == 2
    assert PREFIX not in str(original), 'Already patched; do not rerun old transformations'
    unit, buff = ref('UNIT_ENTITY','执行单位'), ref('MODIFIER_ENTITY','能力机制')
    current = ex(100076,'GET_MODIFIER_ENTITY_KV',unit,ex(100003,1,'能力循环机制'))
    table = ex(100011,'GET_TABLE_KV',unit,ex(100003,1,'能量格数据表'))
    count = ref('INTEGER','本次可见点数')
    old = ref('INTEGER','上次可见点数')
    image = ref('TEXTURE','本次充能图片')
    oldimage = ref('TEXTURE','上次充能图片')
    owner = ex(100002,'PLAYER_ID_NUMBER',ex(100025,'OWNER_PLAYER',unit))
    initialized = ref('BOOLEAN','已有显示缓存')
    changed = ref('BOOLEAN','本次显示有变化')
    rowchanged = ref('BOOLEAN','本格需要刷新')
    complete = ref('BOOLEAN','本次格子全部有效')
    valid = ref('BOOLEAN','延迟显示对象有效')
    index = ex(100002,'ITER_TABLE_KEY_INT')
    for kind, name, default in [('INTEGER','本次可见点数',0),('INTEGER','上次可见点数',0),
        ('TEXTURE','本次充能图片',0),('TEXTURE','上次充能图片',0),
        ('BOOLEAN','已有显示缓存',False),('BOOLEAN','本次显示有变化',False),
        ('BOOLEAN','本格需要刷新',False),('BOOLEAN','本次格子全部有效',False),
        ('BOOLEAN','延迟显示对象有效',False)]:
        assert name not in d['var_data'][1]
        d['var_data'][0].setdefault(kind,{})[name]=default
        d['var_data'][1][name]=0;d['var_data'][2].append(name)

    # Retain each original image setter's recipient and prefab path verbatim.
    traversal = copy.deepcopy(original['action'][1])
    filled, empty = traversal['args_list'][1]['args_list']
    setters = [v for _,v in walk(traversal,active=True) if v.get('action_type')=='SET_UI_COMP_IMAGE_NEW']
    assert len(setters)==4
    for setter in setters[:2]: setter['args_list'][2]=copy.deepcopy(image)
    filled['args_list'][0]['args_list']=[n.compare('num',index,'<=',count)]
    empty['args_list'][0]['args_list']=[n.compare('num',index,'>',count)]
    prefab = copy.deepcopy(setters[0]['args_list'][1]['args_list'][0])
    # No shared TABLE literal cache: clearing/rebuilding this UI invalidates the
    # Buff's presentation flag at the sole lifecycle builder below.
    force_row = n.assign(rowchanged,ex(100001,1,True))
    def force(): return n.assign(rowchanged,ex(100001,1,True))
    decision = n.branch([n.bool(initialized)], [
        n.branch([n.compare('num',index,'<=',count)], [
            n.branch([n.compare('num',index,'>',old)], [force()], [
                n.branch([n.compare('any',image,'!=',oldimage)],[force()])])
        ], [n.branch([n.compare('num',index,'<=',old)],[force()])])
    ], [force_row])
    traversal['args_list'][1]['args_list']=[
        n.assign(rowchanged,ex(100001,1,False)), decision,
        n.branch([n.bool(rowchanged)],[n.branch([n.exists(prefab)],[filled,empty],
            [n.assign(complete,ex(100001,1,False))])])]
    # Preserve traversal optional-argument semantics and old disabled actions.
    text=copy.deepcopy(sample_text)
    for _, v in list(walk(text)):
        if v.get('sub_type')=='MODIFIER_OWNER': v.clear();v.update(copy.deepcopy(unit))
    text['args_list'][2]=ex(100003,'ANY_VAR_TO_STR',count)
    text['element_id']=n.next+1;n.next+=1
    textcomp=copy.deepcopy(text['args_list'][1])

    flush = [
        n.box('② 延后一帧只读取最新显示；层数、伤害、属性联动不延后',[
            n.assign(count,ex(100002,'MATH_OPERATION',ex(100002,'GET_MOD_STACK',buff),
                ex(100016,1,'-'),ex(100002,1,1))),
            n.assign(image,dict(arg_type=100115,sub_type='cbedcbf9752611f1b98019023354d96d',
                args_list=[unit],call_rt_index=0,op_arg=[],op_arg_enable=[])),
            n.assign(initialized,ex(100001,1,False)),
            n.branch([n.has(buff,PREFIX+'已绘制')],[
                n.assign(initialized,n.get(buff,'BOOLEAN',PREFIX+'已绘制'))]),
            n.assign(changed,ex(100001,1,True)),
            n.branch([n.bool(initialized)],[
                n.branch([n.compare('num',owner,'!=',n.get(buff,'INTEGER',PREFIX+'所属玩家编号'))],[
                    n.assign(initialized,ex(100001,1,False))])]),
            n.branch([n.bool(initialized)],[
                n.assign(old,n.get(buff,'INTEGER',PREFIX+'点数')),
                n.assign(oldimage,n.get(buff,'TEXTURE',PREFIX+'充能图片')),
                n.assign(changed,ex(100001,1,False)),
                n.branch([n.compare('num',count,'!=',old)],[n.assign(changed,ex(100001,1,True))]),
                n.branch([n.compare('any',image,'!=',oldimage)],[n.assign(changed,ex(100001,1,True))])])]),
        n.branch([n.bool(changed)],[n.box('③ 只更新状态变化的格子；文字仅在点数变化或重建后写入',[
            n.assign(complete,ex(100001,1,True)),
            n.branch([n.bool(initialized)],[
                n.branch([n.compare('num',count,'!=',old)],[text])], [copy.deepcopy(text)]),
            traversal,
            n.put(buff,PREFIX+'点数',count),n.put(buff,PREFIX+'充能图片',image),
            n.put(buff,PREFIX+'所属玩家编号',owner),
            n.put(buff,PREFIX+'已绘制',complete)])])]
    # The two text branches are exclusive, but editor element IDs must differ.
    texts=[v for _,v in walk(flush) if v.get('action_type')=='SET_UI_COMP_TEXT']
    assert len(texts)==2
    texts[1]['element_id']=n.next+1;n.next+=1
    def invalid():return n.assign(valid,ex(100001,1,False))
    # Separate ordered gates keep dependencies explicit without a deeply nested
    # callback. No return-value action is used as an invented early exit.
    callback=[
        n.assign(valid,ex(100001,1,False)),
        n.branch([n.exists(buff)],[n.put(buff,PREFIX+'待刷新',ex(100001,1,False)),
            n.branch([n.exists(unit)],[n.assign(valid,ex(100001,1,True))])]),
        n.branch([n.bool(valid)],[n.branch([n.has(unit,'能力循环机制')],[
            n.branch([n.exists(current)],[
                n.branch([n.compare('modifier',buff,'==',current)],[],[invalid()])], [invalid()])], [invalid()])]),
        n.branch([n.bool(valid)],[n.branch([n.cond('IS_UNIT_ALIVE',unit),
            n.cond('BOOL_NOT',ex(100001,'UNIT_HAS_TAG',unit,ex(100003,1,'已死亡')))],[],[invalid()])]),
        n.branch([n.bool(valid)],[n.branch([n.has(unit,'能量格数据表'),n.has(unit,'循环机制面板')],[],[invalid()])]),
        n.branch([n.bool(valid)],[n.branch([n.exists(textcomp)],flush)]),
        n.act('DELETE_TIMER',ex(100181,'CURRENT_EXPIRED_TIMER'))]
    timer=n.act('RUN_ONCE_TIMER_BY_FRAME_NO_SAVE',ex(100002,1,1),ex(100022,1,*callback),
                local_var={'__tuple__':True,'items':[{},{}]})
    schedule=[n.put(buff,PREFIX+'待刷新',ex(100001,1,True)),timer]
    queue=[n.branch([n.has(buff,PREFIX+'待刷新')],[],
                   [n.put(buff,PREFIX+'待刷新',ex(100001,1,False))]),
        n.branch([n.compare('bool',n.get(buff,'BOOLEAN',PREFIX+'待刷新'),'==',ex(100001,1,False))],schedule)]
    d['action']=[n.box('① 同一循环最多一个待处理显示刷新；延迟对象逐层校验',[
        n.branch([n.exists(unit)],[n.branch([n.exists(buff)],queue)])])]
    d['func_comment']=d.get('func_comment','')+'\n2026-10-30：能量格与积累文字按实例合并到下一帧，只绘制差异；重建显式使缓存失效。飘字及玩法动作保持原时序。'
    # All original IDs not intentionally removed remain byte-for-byte native;
    # no signature, function ID or directory registration is changed.
    return d


def patch_rebuild(original,n):
    d=copy.deepcopy(original)
    assert d['func_id']=='249a7f506a0511f1acc343869eb6b152'
    assert PREFIX not in str(original)
    unit=ref('UNIT_ENTITY','执行单位');buff=ref('MODIFIER_ENTITY','能力循环机制buff')
    edits=[]
    for p,v in list(walk(d)):
        if v.get('element_id')!=1935909566000306:continue
        parent=at(d,p[:-1]);assert isinstance(parent,list)
        actions=[n.put(buff,PREFIX+'已绘制',ex(100001,1,False)),call(unit,buff)]
        actions[1]['element_id']=n.next+1;n.next+=1
        parent[p[-1]+1:p[-1]+1]=actions
        edits.append(dict(parent=list(p[:-1]),index=p[-1]+1,count=2))
    assert len(edits)==1
    return d,edits


def patch_core(original):
    d=copy.deepcopy(original);edits=[]
    for tid,t in d['trigger_dict'].items():
        if not any(v.get('sub_type')==FID for _,v in walk(t,active=True)):continue
        assert len(t['event'])==1 and t['event'][0]['event_type']=='MODIFIER_LAYER_CHANGE'
        texts=[(p,v) for p,v in walk(t,active=True) if v.get('action_type')=='SET_UI_COMP_TEXT']
        assert len(texts)==1
        p,text=texts[0]
        assert '特殊能力循环机制面板.bg.积累' in str(text)
        edits.append(dict(path=['trigger_dict',tid,*p],before=True));text['enable']=False
    assert len(edits)==1
    return d,edits


def legacy_registry():
    registry=load(LEGACY)
    assert registry['schema']==1 and registry['map_identity']=='ProjectMonster02/map3'
    return registry


def toggle_legacy(original,records,enabled):
    d=copy.deepcopy(original);edits=[]
    for r in records:
        matches=[(p,v) for p,v in walk(d) if v.get('element_id')==r['element_id']]
        assert len(matches)==1
        p,v=matches[0]
        assert v.get('action_type')=='PRINT_MESSAGE_ACTION_TO_DIALOG' and v['args_list']==r['args_list']
        assert r['label'].startswith('[技能排查/20261024')
        edits.append(dict(path=list(p),before=v['enable']));v['enable']=enabled
    return d,edits


def undo_flags(d,edits):
    d=copy.deepcopy(d)
    for r in edits:at(d,r['path'])['enable']=r['before']
    return d


def restore(candidate,row,original):
    d=undo_flags(candidate,row.get('legacy_edits',[]))
    if row['kind']=='ui':
        d['action']=copy.deepcopy(original['action']);d['var_data']=copy.deepcopy(original['var_data'])
        d['func_comment']=original.get('func_comment','')
    elif row['kind']=='rebuild':
        for e in reversed(row['edits']):del at(d,e['parent'])[e['index']:e['index']+e['count']]
    elif row['kind']=='core':d=undo_flags(d,row['edits'])
    return d

if __name__ == '__main__':
    raise SystemExit('Initial map deployment retired; use maintained helpers and read-only regression fixtures.')
