"""Scoped runtime guards and opt-in native ECA skill tracing for map3.

Stage once against the current map. Never replay over a newer live baseline.
The logger writes through Y3's existing log action; it owns no files or timers.
"""
from copy import deepcopy as cp
import json
from pathlib import Path
import y3_hero_repair_publish as pub
from y3_sunshangxiang_orbit_fix import Builder, ex, lit, ref, walk, alive, global_int

PHASE = 'skill-trace-20261022'
FUNC = 'f139a470971c40e9a3721668218dca52'
FUNC_FILE = 'global_trigger/function/new/功能执行/英雄技能-运行追踪日志.json'
PREFIX = '技能追踪_'
STAGES = ('命令', '出手', '伤害调用', '状态生效', '减伤', '资源变更', '跳过')
HEROES = {
    '孙尚香': [134219500, 134251304, 134222169, 134219157, 134219344, 134276381],
    '太史慈': [134259517, 134234889, 134273833, 134255952, 134275696, 134267511],
    '黄忠': [134223239, 134278528, 134280536, 134237143, 134266460, 134236877],
}
CORES = {134248740: '孙尚香', 134277456: '太史慈', 134242511: '黄忠'}
GLOBALS = {'BOOLEAN': {PREFIX+'开关': True},
           'STRING': {PREFIX+'英雄筛选': ''},
           'INTEGER': {PREFIX+'每阶段明细上限': 8, PREFIX+'全局序号': 0}}


def sval(s):
    return lit(s, 100003)


def none():
    return ex(100006, 'NONE_UNIT')


def var(kind, name, scope='local'):
    t, s = {'UNIT_ENTITY': (100006, 11), 'ABILITY': (100014, 2),
            'MODIFIER_ENTITY': (100076, 11), 'PROJECTILE_ENTITY': (100077, 'VARIABLE'),
            'BOOLEAN': (100001, 'VARIABLE'), 'INTEGER': (100002, 6),
            'STRING': (100003, 2), 'FLOAT': (100000, 2)}[kind]
    return ex(t, s, {'__tuple__': True, 'items': [kind, name, scope] if scope else [kind, name]})


def glob(kind, name):
    return var(kind, PREFIX+name, '')


def declare(d, tid, kind, suffix):
    name = PREFIX+suffix
    value = False if kind == 'BOOLEAN' else '' if kind == 'STRING' else 0
    data = d['local_variable'][str(tid)]
    assert name not in data['variable_length_dict'], name
    data['variable_dict'].setdefault(kind, {})[name] = value
    data['variable_length_dict'][name] = 0
    vd = d['trigger_dict'][str(tid)]['var_data']
    vd[0].setdefault(kind, {})[name] = value
    vd[1][name] = 0
    vd[2].append(name)
    return var(kind, name)


def branch_else(b, checks, yes, no):
    a = b.branch(checks, yes)
    a['args_list'][2]['args_list'] = no
    return a


def replace_expr(value, replacements):
    if isinstance(value, dict):
        for old, new in replacements:
            if value == old:
                return cp(new)
        return {k: replace_expr(v, replacements) for k, v in value.items()}
    if isinstance(value, list):
        return [replace_expr(v, replacements) for v in value]
    return value


def keyget(obj, key, kind='INTEGER'):
    t, s = {'INTEGER': (100002, 'GET_INTEGER_KV'), 'STRING': (100003, 'GET_STRING_KV'),
            'MODIFIER_ENTITY': (100076, 'GET_MODIFIER_ENTITY_KV')}[kind]
    return ex(t, s, cp(obj), cp(key) if isinstance(key, dict) else sval(key))


def kv(b, obj, key, value):
    return b.node('SET_ENTITY_KV', cp(obj), cp(key) if isinstance(key, dict) else sval(key), cp(value))


def join(*parts):
    parts = [sval(v) if isinstance(v, str) else ex(100003, 'ANY_VAR_TO_STR', cp(v)) for v in parts]
    def balanced(values):
        if len(values)==1:return values[0]
        mid=len(values)//2
        return ex(100003,'STR_JOIN',balanced(values[:mid]),balanced(values[mid:]))
    return balanced(parts)


def trace(b, owner, ability, label, stage, target=None, value=None, detail=''):
    call = ex(100177, FUNC, cp(owner), cp(ability), sval(label), sval(stage),
              cp(target) if target is not None else none(),
              cp(value) if value is not None else lit(0.0, 100000), sval(detail))
    call.update(op_arg=[], op_arg_enable=[])
    # Do not evaluate diagnostic arguments when tracing is disabled.
    payload = b.node('CALL_TRIGGER_FUNC', call)
    if ability.get('sub_type') != 'NONE_ABILITY':
        payload = b.exists(ability, [payload])
    return b.branch([b.cmp(glob('BOOLEAN', '开关'), '==', lit(True, 100001), 'BOOL_COMPARE')], [payload])


def combat(b, skill, owner, target, body, skipped=None):
    checks = [*alive(b, owner), *alive(b, target), b.cond('IS_ENEMY', target, owner),
              b.cmp(global_int('当前游戏进程阶段'), '==', lit(2))]
    inner = branch_else(b, checks, body, skipped or [])
    return branch_else(b, [b.cond('TYPE_IS_EXIST',v)for v in (skill,owner,target)], [inner], skipped or [])


def patch_warning(source):
    d = cp(source); b = Builder(d)
    timer = next(n for n in walk(d['trigger_dict']['1959489540']['action'])
                 if n.get('action_type') == 'RUN_LOOP_TIMER')
    body = timer['args_list'][3]['args_list']
    old = next(n for n in walk(body) if n.get('action_type') == 'IF_THEN_ELSE'
               and any(c.get('element_id') == 1959489540974493 for c in n['args_list'][0]['args_list']))
    core = declare(d, '1959489540', 'MODIFIER_ENTITY', '自动施法循环')
    check = next(n for n in old['args_list'][0]['args_list'] if n.get('element_id') == 1959489540974493)
    lookup = cp(check['args_list'][0]['args_list'][0])
    check['args_list'][0]['args_list'][0] = cp(core)
    skill, owner = ex(100014, 'CUR_ABILITY'), ex(100006, 'ABILITY_OWNER')
    timer['args_list'][3]['args_list'] = [b.exists(skill, [b.exists(owner, [
        b.set(core, lookup), b.exists(core, [old])])])]
    return d


def patch_ranged(source):
    d = cp(source); b = Builder(d); tid = '1644036097'
    t = d['trigger_dict'][tid]
    skill = declare(d, tid, 'ABILITY', '普攻技能快照')
    owner = declare(d, tid, 'UNIT_ENTITY', '普攻来源快照')
    core = declare(d, tid, 'MODIFIER_ENTITY', '普攻循环快照')
    has_core = declare(d, tid, 'BOOLEAN', '普攻曾有循环')
    old = cp(t['action']); target = cp(old[0]['args_list'][0])
    target['arg_type'] = 100006; target['sub_type'] = 11
    old = replace_expr(old, [(ex(100014, 'CUR_ABILITY'), skill), (ex(100006, 'ABILITY_OWNER'), owner)])
    timer = old[1]; mover = next(n for n in walk(timer) if n.get('action_type') == 'CREATE_CHASING_MOVER')
    projectile = cp(mover['args_list'][0])
    damage, hit, delete = cp(mover['args_list'][5]['args_list'])

    def bound(actions):
        current = keyget(owner, '能力循环机制', 'MODIFIER_ENTITY')
        permit=declare(d,tid,'BOOLEAN','普攻回调允许'+str(b.index))
        same = b.exists(core, [b.branch([b.cond('HAS_KV_ANY',owner,sval('能力循环机制'))],[
            b.branch([b.cmp(current,'==',core,'MODIFIER_COMPARE')],[b.set(permit,lit(True,100001))])])])
        return b.node('STORAGE_BOX',sval('校验本次普攻弹道所属循环'),ex(100022,1,b.set(permit,lit(False,100001)),
            branch_else(b,[b.cmp(has_core,'==',lit(True,100001),'BOOL_COMPARE')],
                [same],[b.set(permit,lit(True,100001))]),
            b.branch([b.cmp(permit,'==',lit(True,100001),'BOOL_COMPARE')],actions)))

    # A removed skill or a newly granted loop must not receive old impact damage.
    impact = combat(b, skill, owner, target, [bound([damage,
        combat(b, skill, owner, target, [hit])])])
    mover['args_list'][5]['args_list'] = [impact, b.exists(projectile, [delete])]
    tick_body = timer['args_list'][3]['args_list']
    create_index = next(i for i,n in enumerate(tick_body) if n.get('element_id') == 1644036097970755)
    create, chase = tick_body[create_index:create_index+2]
    guarded_tick = cp(tick_body[:create_index]) + [create, b.exists(projectile, [chase])]
    # Native timer self-cleanup remains outside the guarded shooting sequence.
    timer['args_list'][3]['args_list'] = [combat(b, skill, owner, target, [bound(guarded_tick)]), *tick_body[create_index+2:]]
    init_core = b.branch([b.cond('HAS_KV_ANY', owner, sval('能力循环机制'))], [
        b.set(core, keyget(owner, '能力循环机制', 'MODIFIER_ENTITY')),
        b.exists(core, [b.set(has_core, lit(True, 100001))])])
    t['action'] = [b.set(skill, ex(100014, 'CUR_ABILITY')),
        b.set(owner, ex(100006, 'ABILITY_OWNER')), b.set(has_core, lit(False, 100001)),
        b.exists(skill, [b.exists(owner, [old[0], init_core,
            combat(b, skill, owner, target, [timer])])])]
    return d


def patch_huang(source):
    d = cp(source); b = Builder(d); tid = '893440004'; t = d['trigger_dict'][tid]
    old = cp(t['action'])
    skill = declare(d, tid, 'ABILITY', '定军技能快照')
    owner = declare(d, tid, 'UNIT_ENTITY', '定军来源快照')
    target = declare(d, tid, 'UNIT_ENTITY', '定军目标快照')
    core = declare(d, tid, 'MODIFIER_ENTITY', '定军蓄势快照')
    had_core = declare(d, tid, 'BOOLEAN', '定军曾有蓄势')
    actor_target = ref('UNIT_ENTITY', '目标单位', 'actor')
    old = replace_expr(old, [(ex(100014, 'CUR_ABILITY'), skill), (ex(100006, 'ABILITY_OWNER'), owner)])
    original_assignment = old.pop(0)
    old = replace_expr(old, [(actor_target, target)])
    mover = next(n for n in walk(old) if n.get('element_id') == 476327941000043)
    projectile = cp(mover['args_list'][0]); callback = mover['args_list'][5]['args_list']
    calc, damage, delete = cp(callback)
    lookup = ex(100076, 'GET_LAST_MODIFIER_INSTANCE', cp(owner), lit(134242511, 100046))
    calc = replace_expr(calc, [(lookup, core)])
    # No loop is a valid unenhanced shot, never a dereference of an empty Buff.
    base = cp(calc['args_list'][2]['args_list'])
    calc = branch_else(b, [b.cond('TYPE_IS_EXIST', core)], [calc], base)
    skipped = [trace(b, owner, skill, '黄忠/定军箭#134223239', '跳过', detail='目标失效、假死、换波或旧技能回调')]
    permitted=declare(d,tid,'BOOLEAN','定军回调允许')
    unchanged = b.exists(core, [b.branch([b.cmp(lookup, '==', core, 'MODIFIER_COMPARE')], [b.set(permitted,lit(True,100001))])])
    valid_effect = b.node('STORAGE_BOX',sval('校验定军箭所属循环'),ex(100022,1,b.set(permitted,lit(False,100001)),
        branch_else(b,[b.cmp(had_core,'==',lit(True,100001),'BOOL_COMPARE')],[unchanged],[b.set(permitted,lit(True,100001))]),
        branch_else(b,[b.cmp(permitted,'==',lit(True,100001),'BOOL_COMPARE')],[calc,damage],skipped)))
    mover['args_list'][5]['args_list'] = [combat(b, skill, owner, target, [valid_effect], skipped),
                                         b.exists(projectile, [delete])]
    # Validate immediately before querying target position or creating a mover.
    safe_visual = old[:-1] + [b.exists(projectile, [old[-1]])]
    t['action'] = [b.set(skill, ex(100014, 'CUR_ABILITY')), b.set(owner, ex(100006, 'ABILITY_OWNER')),
        b.exists(skill, [b.exists(owner, [original_assignment,
            b.set(target, actor_target), b.set(had_core, lit(False, 100001)),
            combat(b, skill, owner, target, [b.set(core, lookup),
                b.exists(core, [b.set(had_core, lit(True, 100001))]), *safe_visual], skipped)])])]
    # Keep the original selection policy and native target-unit command option.
    auto = next(n for n in walk(d['trigger_dict']['1959489540']['action']) if n.get('action_type') == 'RUN_LOOP_TIMER')
    body = auto['args_list'][3]['args_list']; command = next(n for n in walk(body) if n.get('action_type')=='UNIT_RELEASE_COMMAND')
    def protect(items):
        result=[]
        for n in items:
            if not isinstance(n,dict):result.append(n);continue
            if n is command:
                result.append(combat(b, ex(100014,'CUR_ABILITY'), ex(100006,'ABILITY_OWNER'), actor_target, [n]));continue
            for a in n.get('args_list',[]):
                if isinstance(a,dict)and a.get('arg_type')==100022:a['args_list']=protect(a['args_list'])
            result.append(n)
        return result
    body=protect(body)
    auto['args_list'][3]['args_list']=[b.exists(ex(100014,'CUR_ABILITY'),[
        b.exists(ex(100006,'ABILITY_OWNER'),body)])]
    return d


def make_logger(template):
    d = cp(template)
    d.update(action=[], condition=[], event=[], func_id=FUNC, func_name='英雄技能-运行追踪日志',
        trigger_name='英雄技能-运行追踪日志', trigger_id=2099983001, func_return=False,
        func_rtv_name_list=[], func_des='记录技能追踪：{执行单位} {资源名} {阶段}',
        func_comment='只写原生运行日志，不创建或清理文件。全局变量 技能追踪_开关/英雄筛选/每阶段明细上限 控制输出；默认每阶段前8条，失去时输出累计汇总。伤害调用不代表最终伤害。单位号/批次号是追踪号，不是引擎实体ID。')
    types={'执行单位':'UNIT_ENTITY','技能实例':'ABILITY','资源名':'STRING','阶段':'STRING',
           '目标':'UNIT_ENTITY','数值':'FLOAT','详情':'STRING','单位文本':'STRING','目标文本':'STRING',
           '级别':'INTEGER','次数':'INTEGER','批次':'INTEGER','键前缀':'STRING','计数键':'STRING','汇总文本':'STRING'}
    defaults={k:(0.0 if v=='FLOAT' else '' if v=='STRING' else 0) for k,v in types.items()}
    vd={}
    for k,v in types.items():vd.setdefault(v,{})[k]=defaults[k]
    d['var_data']=[vd,{k:0 for k in types},list(types)]
    d['func_param_list']=[{'__tuple__':True,'items':[k,True]}for k in list(types)[:7]]
    b=Builder(d); b.index=2099983001100000
    p={k:var(v,k) for k,v in types.items()}
    owner,ability,stage=p['执行单位'],p['技能实例'],p['阶段']
    prefix=p['键前缀']; countkey=p['计数键']
    def stagekey(s):return join(prefix,s)
    def count(s):return keyget(owner,stagekey(s))
    def setcount(s,val):return kv(b,owner,stagekey(s),val)
    def incval(v):return ex(100002,'INT_PLUS_ONE',cp(v))
    def stringcmp(a,op,c):return b.cmp(a,op,c,'STRING_COMPARE')
    def ensure_unit_id(unit):
        return branch_else(b,[b.cond('HAS_KV_ANY',unit,sval(PREFIX+'单位号'))],[],[
            b.set(glob('INTEGER','全局序号'),incval(glob('INTEGER','全局序号'))),
            kv(b,unit,PREFIX+'单位号',glob('INTEGER','全局序号'))])
    initialize=[b.set(glob('INTEGER','全局序号'),incval(glob('INTEGER','全局序号'))),
        kv(b,owner,stagekey('批次'),glob('INTEGER','全局序号')),
        *[setcount(s,lit(0))for s in STAGES]]
    # A lifecycle reset is explicit and independent from the wave number.
    gain=b.cond('OR',ex(100021,1,stringcmp(stage,'==',sval('获得')),stringcmp(stage,'==',sval('循环建立'))))
    ensure=branch_else(b,[b.cond('HAS_KV_ANY',owner,stagekey('批次'))],[],cp(initialize))
    summary=[]
    for s in STAGES:
        summary.append(b.set(p['汇总文本'],join(p['汇总文本'],s+'=',count(s),' ')))
    printed=b.node('PRINT_MESSAGE_ACTION_TO_DIALOG',lit(3,100175),join(
        '[技能追踪] ',p['资源名'],' | 波次=',global_int('当前进程所在波次编号'),
        ' | 批次=',p['批次'],' | 单位=',p['单位文本'],' | 阶段=',stage,
        ' | 等级=',p['级别'],' | 目标=',p['目标文本'],' | 数值=',p['数值'],
        ' | ',p['详情'],' | ',p['汇总文本']))
    output=[b.set(p['级别'],lit(0)),b.exists(ability,[b.set(p['级别'],ex(100002,'GET_ABILITY_INT_ATTR',cp(ability),lit('ability_level',100079)))]),
        b.set(p['目标文本'],sval('无/已失效')),b.exists(p['目标'],[ensure_unit_id(p['目标']),b.set(p['目标文本'],join(ex(100003,'GET_UNIT_NAME',cp(p['目标'])), '#',keyget(p['目标'],PREFIX+'单位号')))]),
        printed]
    process=[ensure_unit_id(owner),b.set(prefix,join('技能追踪/',p['资源名'],'/')),ensure,
        b.branch([gain],cp(initialize)),b.set(p['批次'],keyget(owner,stagekey('批次'))),
        b.set(p['单位文本'],join(ex(100003,'GET_UNIT_NAME',cp(owner)),'#',keyget(owner,PREFIX+'单位号'))),
        b.set(p['汇总文本'],sval('')),
        branch_else(b,[stringcmp(stage,'==',sval('汇总'))],summary+cp(output),[
            b.set(countkey,join(prefix,stage)),
            branch_else(b,[b.cond('HAS_KV_ANY',owner,countkey)],[],[kv(b,owner,countkey,lit(0))]),
            b.set(p['次数'],incval(keyget(owner,countkey))),kv(b,owner,countkey,p['次数']),
            b.branch([b.cmp(p['次数'],'<=',glob('INTEGER','每阶段明细上限'))],cp(output))])]
    filter_check=b.cond('OR',ex(100021,1,stringcmp(glob('STRING','英雄筛选'),'==',sval('')),
        stringcmp(glob('STRING','英雄筛选'),'==',ex(100003,'GET_UNIT_NAME',cp(owner)))))
    d['action']=[b.branch([b.cmp(glob('BOOLEAN','开关'),'==',lit(True,100001),'BOOL_COMPARE')],[
        b.exists(owner,[b.branch([filter_check],process)])])]
    return d


def instrument_ability(source, label):
    d=cp(source);b=Builder(d);owner=ex(100006,'ABILITY_OWNER');skill=ex(100014,'CUR_ABILITY')
    def rewrite(items,tid):
        result=[]
        for n in items:
            if not isinstance(n,dict)or n.get('enable')is False:result.append(n);continue
            # Never instrument logger argument trees, disabled actions, or functions.
            if n.get('action_type')=='CALL_TRIGGER_FUNC' and n['args_list'][0].get('sub_type')==FUNC:
                result.append(n);continue
            for a in n.get('args_list',[]):
                if isinstance(a,dict)and a.get('arg_type')==100022:a['args_list']=rewrite(a['args_list'],tid)
            kind=n.get('action_type')
            if kind=='UNIT_RELEASE_COMMAND' and n['args_list'][1].get('sub_type')=='UNIT_COMMAND_USE_SKILL':
                cmd=n['args_list'][1];opts=cmd.get('op_arg',[]);enabled=cmd.get('op_arg_enable',[])
                t=opts[2] if len(opts)>2 and len(enabled)>2 and enabled[2] else None
                result += [trace(b,owner,skill,label,'命令',t,detail='已下达施法命令，不等于实际出手'),n]
            elif kind=='ADD_MODIFIER':
                buff=declare(d,tid,'MODIFIER_ENTITY','状态结果'+str(n['element_id']))
                expr=cp(n);expr.pop('element_id',None);expr.pop('enable',None);expr.pop('bp',None)
                expr.pop('action_type');expr.update(arg_type=100076,sub_type='ADD_MODIFIER')
                result += [b.set(buff,expr),branch_else(b,[b.cond('TYPE_IS_EXIST',buff)],
                    [trace(b,owner,skill,label,'状态生效',n['args_list'][0],
                        detail='已获得Buff实例；Buff='+str(n['args_list'][1].get('args_list')))],
                    [trace(b,owner,skill,label,'跳过',detail='未获得Buff实例')])]
            else:
                result.append(n)
                if kind=='APPLY_DAMAGE':
                    result.append(trace(b,owner,skill,label,'伤害调用',n['args_list'][2],
                        detail='伤害动作已返回；非最终结算伤害；节点='+str(n['element_id'])))
                elif kind=='SET_CUR_DAMAGE':
                    result.append(trace(b,owner,skill,label,'减伤',detail='已修改本次伤害事件数值；非最终结算'))
                elif kind in ['SET_BUFF_STACK','ADD_BUFF_STACK']:
                    result.append(trace(b,owner,skill,label,'资源变更',detail='已调用层数变更；节点='+str(n['element_id'])))
        return result
    for tid,t in d['trigger_dict'].items():
        # Dynamic child triggers are intentionally disabled until registration.
        # Their bodies still execute and need effect-level instrumentation.
        t['action']=rewrite(t['action'],tid)
        ev={e.get('event_type')for e in t.get('event',[])}
        if 'ABILITY_OBTAIN'in ev:t['action'].insert(0,trace(b,owner,skill,label,'获得',detail='技能入口已建立；不代表被动已生效'))
        if 'ABILITY_SP_END'in ev:t['action'].insert(0,trace(b,owner,skill,label,'出手',detail='实际进入出手事件'))
        if 'ABILITY_LOSE'in ev:t['action'].insert(0,trace(b,owner,skill,label,'汇总',detail='技能失去/换波累计；明细超限仍累计'))
    return d


def instrument_core(source,label):
    d=cp(source);b=Builder(d);owner=ex(100006,'MODIFIER_OWNER');skill=ex(100014,'NONE_ABILITY')
    mod=ex(100076,'CUR_MODIFIER')
    for t in d['trigger_dict'].values():
        ev={e.get('event_type')for e in t.get('event',[])}
        if 'OBTAIN_MODIFIER'in ev:t['action'].append(trace(b,owner,skill,label,'循环建立',detail='本循环新批次开始'))
        if 'MODIFIER_LAYER_CHANGE'in ev:t['action'].append(b.exists(mod,[trace(b,owner,skill,label,'资源变更',
            value=ex(100000,'ARITHMETIC_OPERATION',ex(100002,'GET_MOD_STACK',cp(mod)),lit('-',100017),lit(1)),
            detail='数值为玩家可见点数；内部层数减1')]))
        if 'LOSS_MODIFIER'in ev:t['action'].insert(0,trace(b,owner,skill,label,'汇总',detail='核心循环失去/重建'))
    return d


def build(root):
    read=lambda rel:json.loads((root/rel).read_text('utf-8-sig'))
    assert not (root/FUNC_FILE).exists(), 'Already installed; do not replay migration'
    out={}
    for oid in [134222927,134260801]:out[f'ability/{oid}.json']=patch_warning(read(f'ability/{oid}.json'))
    out['ability/134270652.json']=patch_ranged(read('ability/134270652.json'))
    out['ability/134223239.json']=patch_huang(read('ability/134223239.json'))
    language=read('zhlanguage.json')
    for hero,ids in HEROES.items():
        for oid in ids:
            rel=f'ability/{oid}.json';name=language[str(read(f'editor_table/abilityall/{oid}.json')['name'])]
            out[rel]=instrument_ability(out.get(rel,read(rel)),hero+'/'+name+'#'+str(oid))
    for oid,hero in CORES.items():
        rel=f'modifier/{oid}.json';out[rel]=instrument_core(read(rel),hero+'/核心循环#'+str(oid))
    template=read('global_trigger/function/new/功能执行/英雄主动技能-检查自动施法动作状态.json')
    # Native function namespace and directory registration, no shared gameplay edit.
    for f in (root/'global_trigger/function').rglob('*.json'):
        if f.name=='index.txt':continue
        d=json.loads(f.read_text('utf-8-sig'))
        assert d.get('func_id')!=FUNC and d.get('trigger_id')!=2099983001
    out[FUNC_FILE]=make_logger(template)
    idx='global_trigger/function/new/功能执行/index.txt';v=read(idx)
    v[Path(FUNC_FILE).name]=max(v.values())+1;out[idx]=v
    g=read('globaltriggervariable.json')
    for kind,values in GLOBALS.items():
        for name,default in values.items():
            assert name not in g['variable_length_dict']
            g['variable_dict'].setdefault(kind,{})[name]=default
            g['variable_length_dict'][name]=0
            g['variable_group_info'].append({'__tuple__':True,'items':[name,name]})
    out['globaltriggervariable.json']=g
    for rel,d in list(out.items()):
        if 'trigger_dict' not in d and rel!=FUNC_FILE:continue
        # JSON is a tree. Break Python object aliases before assigning fresh IDs.
        d=json.loads(json.dumps(d,ensure_ascii=False));out[rel]=d
        original=read(rel) if (root/rel).exists() else {}
        counts={}
        for n in walk(original):
            if 'element_id'in n:counts[n['element_id']]=counts.get(n['element_id'],0)+1
        seen={};next_id=max((n.get('element_id',0)for n in walk(d)),default=0)
        for n in walk(d):
            if 'element_id'not in n:continue
            oid=n['element_id'];seen[oid]=seen.get(oid,0)+1
            if seen[oid]>max(1,counts.get(oid,0)):
                next_id+=1;n['element_id']=next_id
    return out,[dict(status='ready',scope='2 runtime errors, 2 warning nodes; 18 skills and 3 loops traced',
        limits='Native log action only; no deletion, file writer or polling timer. No post-settlement damage claim. Gameplay verification pending.')]


if __name__=='__main__':
    assert not (pub.WORK/PHASE/'WITHDRAWN.json').exists(), 'Withdrawn after startup failure; do not replay'
    original_map_files = pub.map_files
    def map_files_with_trace_globals():
        yield from original_map_files()
        yield pub.MAP/'globaltriggervariable.json'
    pub.map_files = map_files_with_trace_globals
    pub.stage(PHASE,['y3_skill_trace_repair'])
