"""Stage Da Qiao's approved six skills and dew loop against the current map."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import zipfile

MAP = Path(r'D:\littl\testTempFile\ProjectMonster02\maps\map3')
ROOT = Path(__file__).resolve().parent
STAGE = ROOT / 'staged'
BACKUP = ROOT / 'before-daqiao.zip'
UNIT = 134230459
SKILLS = list(range(134284040, 134284046))
CORE, DOWN, BOOST, SHIELD = range(134284046, 134284050)
FIRST, HEALED = 2099456002, 2099456003
GAIN, LEVEL, CAST, LOSS = 1959489540, 26066946, 893440004, 225054724
RESPONSE = 1051000836
MGAIN, MLOSS, MLAYER, MCAST = 1485688834, 594665475, 1050472449, 2011996165
SHARED = ('tables/单位技能配置表.json', 'tables/技能特有循环机制表.json',
          'tables/技能作用描述表.json', 'zhlanguage.json', 'customevent.json',
          'editor/folderinfo/folderinfo_ability_all.json',
          'editor/folderinfo/folderinfo_modifier_all.json')
NAMES = ('细雨回春', '伞上凝露', '骤雨压阵', '雨润同袍', '广伞庇军', '双枝承雨')
DESCS = (
    '治疗生命比例最低的受伤友方队长，恢复其最大生命14%。冷却8秒。',
    '我方队长施放主动后获得1滴凝露，每2秒最多1次。下次普攻击中消耗凝露，治疗最低生命比例的受伤队长5%最大生命；无人受伤则保留。',
    '对当前目标及附近最多3名敌人造成120%攻击的法术伤害，降低攻击20%，持续5秒。冷却11秒。',
    '凝露治疗的队长攻击提高12%，持续4秒。',
    '有友方队长生命低于70%时，为全体友方队长施加12%最大生命护盾，持续6秒。冷却15秒。',
    '消耗凝露时改为治疗生命比例最低的最多2名受伤友方队长，每人恢复5%最大生命。')
PARAMS = ({'治疗比例': .14}, {'治疗比例': .05, '凝露间隔': 2.},
          {'伤害系数': 1.2, '减攻比例': 20., '减攻时长': 5., '目标上限': 3., '范围半径': 260.},
          {'增攻比例': 12., '增攻时长': 4.},
          {'触发血线': .7, '护盾比例': .12, '护盾时长': 6.},
          {'治疗比例': .05, '额外治疗人数': 1.})


def read(relative):
    return json.loads((MAP / relative).read_bytes())


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def n(kind, subtype, *args, **extra):
    return dict(arg_type=kind, args_list=list(args), sub_type=subtype, **extra)


def lit(kind, value):
    return n(kind, 1, value)


def f(value):
    return lit(100000, float(value))


def text(value):
    return lit(100003, value)


def unit(subtype):
    return n(100006, subtype)


def ability():
    return n(100014, 'CUR_ABILITY')


def buff():
    return n(100076, 'CUR_MODIFIER')


def av(kind, name, subtype, category):
    return n(kind, subtype, {'__tuple__': True, 'items': [category, name, 'actor']})


def target():
    return av(100006, '目标单位', 11, 'UNIT_ENTITY')


def player(u):
    return n(100025, 'OWNER_PLAYER', u)


def attr(u, name):
    return n(100000, 'GET_UNIT_ATTR', u, lit(100301, 'ATTR_RESULT'), lit(100042, name))


def math(a, op, b):
    return n(100000, 'ARITHMETIC_OPERATION', a, lit(100017, op), b)


def ratio(u):
    return math(n(100000, 'GET_HP_CUR', u), '/', attr(u, 'hp_max'))


def kv(entity, key):
    return n(100000, 'GET_FLOAT_KV', entity, text(key))


def ukv(entity, key):
    return n(100006, 'GET_UNIT_ENTITY_KV', entity, text(key))


def skill(u, aid):
    return n(100014, 'GET_ABILITY_BY_AID', u, lit(100182, 2), lit(100039, aid))


def core(u):
    return n(100076, 'GET_LAST_MODIFIER_INSTANCE', u, lit(100046, CORE))


def captains(u):
    return n(100026, '6570be50be1a11f1916d7b0e2885c54e', player(u),
             lit(100001, False), text('所有队长'), call_rt_index=0, op_arg=[], op_arg_enable=[])


class Eca:
    def __init__(self, oid, modifier=False):
        self.oid = oid
        self.modifier = modifier
        self.serial = oid * 1000000
        self.obj = {k: copy.deepcopy(v) for k, v in read('ability/134284020.json').items()
                    if k not in ('trigger_dict', 'local_variable', 'trigger_group_info',
                                 'variable_dict', 'variable_group_info', 'variable_length_dict')}
        self.obj.update(trigger_dict={}, local_variable={}, trigger_group_info=[],
                        variable_dict={}, variable_group_info=[], variable_length_dict={})

    def newid(self):
        self.serial += 1
        return self.serial

    def action(self, kind, *args, **extra):
        value = dict(action_type=kind, args_list=list(args), bp=False,
                     element_id=self.newid(), enable=True, **extra)
        if kind == 'IF_THEN_ELSE':
            value['fake_op'] = []
        return value

    def condition(self, kind, *args):
        return dict(condition_type=kind, args_list=list(args), element_id=self.newid(), enable=True)

    def compare(self, a, op, b, kind='FLOAT_COMPARE'):
        return self.condition(kind, a, lit(100015 if kind == 'FLOAT_COMPARE' else 100035, op), b)

    def exists(self, obj):
        return self.condition('TYPE_IS_EXIST', obj)

    def alive(self, u):
        return self.condition('IS_UNIT_ALIVE', u)

    def branch(self, checks, yes, no=()):
        return self.action('IF_THEN_ELSE', n(100021, 1, *checks), n(100022, 1, *yes), n(100022, 1, *no))

    def setkv(self, obj, key, value):
        return self.action('SET_ENTITY_KV', obj, text(key), value)

    def setvar(self, key, value):
        return self.action('SET_VARIABLE', av(100030, key, 1, 'UNIT_ENTITY'), value)

    def pick(self, group, actions):
        return self.action('PICK_UNIT_DO_ACTION', group, n(100022, 1, *actions))

    def var(self, category, name, value):
        self.obj['variable_dict'].setdefault(category, {})[name] = value
        self.obj['variable_length_dict'][name] = 0
        self.obj['variable_group_info'].append({'__tuple__': True, 'items': [name, name]})

    def trigger(self, tid, name, event_type, actions, conditions=(), event_args=(), parent=None, handle=None):
        t = dict(action=list(actions), call_enabled=True, condition=list(conditions), enabled=parent is None,
                 event=[dict(args_list=list(event_args), element_id=self.newid(), enable=True, event_type=event_type)],
                 group_id=self.oid, p_trigger_id=parent, trigger_id=tid, trigger_name=name, valid=True, var_data=[{}, {}, []])
        if parent is not None:
            t['is_conf'] = True
            t['sub_trigger_owner_set_var_action'] = self.action(
                'SET_VARIABLE', av(100178, handle, 'VARIABLE', 'DYNAMIC_TRIGGER_INSTANCE'),
                n(100178, 'REG_MODIFIER_TRIGGER' if self.modifier else 'REG_ABILITY_TRIGGER',
                  lit(100069 if self.modifier else 100068, tid)))
        self.obj['trigger_dict'][str(tid)] = t
        self.obj['local_variable'][str(tid)] = dict(variable_dict={}, variable_length_dict={})
        return t

    def done(self):
        self.obj['trigger_group_info'] = [dict(_trigger_group_=True, key=self.oid, name=str(self.oid),
            group=[{'__tuple__': True, 'items': [int(k), t['trigger_name']]}
                   for k, t in self.obj['trigger_dict'].items()])]
        return self.obj

    def oncefx(self, u, effect, duration=1., scale=1.):
        return self.action('CREATE_SFX_ON_POINT_NEW', lit(100066, effect), n(100004, 'UNIT_ENTITY_POINT', u),
             op_arg=[None, None, None, f(duration), lit(100001, True), lit(100001, True), lit(100001, True),
                     f(scale), f(scale), f(scale)],
             op_arg_enable=[False, False, False, True, True, False, False, True, True, True])

    def deletefx(self, name):
        return self.action('DELETE_SFX_ENTITY', av(100148, name, 4, 'SFX_ENTITY'),
                           op_arg=[lit(100001, True)], op_arg_enable=[True])

    def attachfx(self, u, effect, name='特效表现', scale=1.):
        return self.action('SET_VARIABLE', av(100148, name, 4, 'SFX_ENTITY'),
            n(100148, 'CREATE_SFX_ON_UNIT', lit(100066, effect), u, text('root'),
              lit(100001, True), lit(100001, True), op_arg=[f(scale), None, None, None],
              op_arg_enable=[True, False, False, False]))

    def heal(self, u, source, linked, amount):
        return self.action('CURE_UNIT', u, amount, lit(100001, True),
                           op_arg=[linked, source, None, None, None], op_arg_enable=[True, True, False, False, False])

    def addbuff(self, u, bid, source, linked, duration):
        return self.action('ADD_MODIFIER', u, lit(100046, bid),
                           op_arg=[source, linked, duration, None, None, None],
                           op_arg_enable=[True, True, True, False, False, False])

    def send(self, eid, owner, patient):
        return self.action('SEND_CUSTOM_EVENT', lit(100238, eid), owner, patient)

    def cancel(self):
        return self.action('IMMEDIATELY_CLEAR_CD', ability())


def find_min(e, owner, storage, threshold, *, variable=False, exclude=None):
    chosen = target() if variable else ukv(storage, '治疗目标')
    assign = e.setvar('目标单位', unit('FOR_EACH_SELECTED_UNIT')) if variable else e.setkv(storage, '治疗目标', unit('FOR_EACH_SELECTED_UNIT'))
    reset = e.setvar('目标单位', unit('NONE_UNIT')) if variable else e.setkv(storage, '治疗目标', unit('NONE_UNIT'))
    selected = unit('FOR_EACH_SELECTED_UNIT')
    checks = [e.alive(selected), e.compare(attr(selected, 'hp_max'), '>', f(0))]
    if exclude is not None:
        checks.append(e.compare(selected, '!=', exclude, 'UNIT_COMPARE'))
    choose = e.branch([e.compare(ratio(selected), '<', kv(storage, '最低生命比例'))],
                     [assign, e.setkv(storage, '最低生命比例', ratio(selected))])
    return [reset, e.setkv(storage, '最低生命比例', threshold),
            e.pick(captains(owner), [e.branch(checks, [choose])])], chosen


def lifecycle(e, params, event=None, response=(), conditions=()):
    current = ability()
    writes = lambda: [e.setkv(current, key, f(value)) for key, value in params.items()]
    gain_actions = writes()
    if event:
        e.var('DYNAMIC_TRIGGER_INSTANCE', '被动监听', 0)
        gain_actions += [RESPONSE]
        event_type, event_args = event
        e.trigger(RESPONSE, '被动响应', event_type, response, conditions, event_args,
                  parent=GAIN, handle='被动监听')
    e.trigger(GAIN, '获得技能', 'ABILITY_OBTAIN', gain_actions)
    cases = [e.action('CASE', lit(100002, level), n(100022, 1, *writes(), e.action('BREAK_LOOP'))) for level in range(1, 6)]
    switch = e.action('SWITCH', n(100002, 'GET_ABILITY_INT_ATTR', current, lit(100079, 'ability_level')), n(100022, 1, *cases))
    e.trigger(LEVEL, '等级变化', 'ABILITY_LEVEL_CHANGED', [switch])
    loss = [e.action('UNREG_TRIGGER', av(100178, '被动监听', 'VARIABLE', 'DYNAMIC_TRIGGER_INSTANCE'))] if event else []
    e.trigger(LOSS, '失去技能', 'ABILITY_LOSE', loss)


def active(index):
    oid = SKILLS[index]
    e = Eca(oid)
    current, owner = ability(), unit('ABILITY_OWNER')
    lifecycle(e, PARAMS[index])
    e.var('UNIT_ENTITY', '目标单位', 0)
    e.var('STRING', 'actName', '')
    e.var('NEW_TIMER', '技能自动释放-定时器', -1)
    template = read('ability/134284020.json')
    timers = [v for v in walk(template['trigger_dict'][str(GAIN)]) if v.get('action_type') == 'RUN_LOOP_TIMER']
    timer = copy.deepcopy(timers[0])
    gate = timer['args_list'][3]['args_list'][0]
    gate['args_list'][0]['args_list'].append(e.alive(owner))
    if index in (0, 4):
        threshold = f(1) if index == 0 else kv(current, '触发血线')
        search, _ = find_min(e, owner, current, threshold, variable=True)
    else:
        old = gate['args_list'][1]['args_list']
        search = [e.setvar('目标单位', unit('NONE_UNIT')), copy.deepcopy(old[1])]
    # Command and search consume the same actor-scoped target, not the old local shadow.
    release_branch = copy.deepcopy(gate['args_list'][1]['args_list'][-1])
    release_branch['args_list'][0]['args_list'] = [e.exists(target()), e.alive(target())]
    gate['args_list'][1]['args_list'] = [*search, release_branch]
    slot = ('技能01', None, '技能02', None, '技能03')[index]
    animation_write = copy.deepcopy(template['trigger_dict'][str(GAIN)]['action'][3])
    animation_write['args_list'][1]['args_list'][1] = text(slot)
    gain = e.obj['trigger_dict'][str(GAIN)]
    gain['action'] += [animation_write, timer]
    e.obj['trigger_dict'][str(LEVEL)]['action'].append(copy.deepcopy(animation_write))
    e.obj['trigger_dict'][str(LOSS)]['action'] = [e.action('DELETE_TIMER', av(100181, '技能自动释放-定时器', 'VARIABLE', 'NEW_TIMER')),
                                               e.setvar('目标单位', unit('NONE_UNIT'))]
    manual = copy.deepcopy(template['trigger_dict'][str(CAST)]['action'][0])
    anim = next(copy.deepcopy(v) for v in walk(template['trigger_dict'][str(CAST)]) if v.get('action_type') == 'PLAY_ANIMATION')
    anim['args_list'][2] = f(1)
    checks = [e.exists(target()), e.alive(target())]
    if index == 0:
        body = [e.branch([e.compare(player(target()), '==', player(owner), 'PLAYER_COMPARE'),
                          e.compare(ratio(target()), '<', f(1))],
                         [anim, e.oncefx(owner, 101499, 1.2, .65),
                          e.oncefx(target(), 101428, 1.2, .8),
                          e.heal(target(), owner, current, math(attr(target(), 'hp_max'), '*', kv(current, '治疗比例')))],
                         [e.cancel()])]
    elif index == 2:
        selected = unit('FOR_EACH_SELECTED_UNIT')
        damage_template = next(copy.deepcopy(v) for v in walk(template['trigger_dict'][str(CAST)]) if v.get('action_type') == 'APPLY_DAMAGE')
        damage_template['args_list'] = [owner, current, selected, lit(100064, 1),
            math(attr(owner, 'attack_phy'), '*', kv(current, '伤害系数')), lit(100001, True)]
        damage_template['op_arg_enable'] = [False] * len(damage_template['op_arg_enable'])
        search_shape = next(copy.deepcopy(v) for v in walk(template['trigger_dict'][str(GAIN)]) if v.get('sub_type') == 'UNIT_LIST_IN_SHAPE')
        search_shape['args_list'] = [n(100004, 'UNIT_ENTITY_POINT', target()), n(100211, 'CONST_CIRCULAR_SHAPE', kv(current, '范围半径'))]
        hit = [e.oncefx(selected, 101499, 1.2, .7), damage_template,
               e.branch([e.alive(selected)], [e.addbuff(selected, DOWN, owner, current, kv(current, '减攻时长'))]),
               e.setkv(current, '命中数', math(kv(current, '命中数'), '+', f(1)))]
        # Set main target first, then use the same action sequence for other enemies.
        main_hit = copy.deepcopy(hit)
        for v in walk(main_hit):
            if v.get('sub_type') == 'FOR_EACH_SELECTED_UNIT':
                v.clear(); v.update(target())
        extra = e.branch([e.alive(selected), e.compare(selected, '!=', target(), 'UNIT_COMPARE'),
                          e.compare(kv(current, '命中数'), '<', kv(current, '目标上限'))], hit)
        body = [e.branch([e.compare(player(target()), '!=', player(owner), 'PLAYER_COMPARE')],
                         [anim, e.oncefx(owner, 100763, .8, .75), e.setkv(current, '命中数', f(0)),
                          *main_hit, e.pick(search_shape, [extra])], [e.cancel()])]
    else:
        selected = unit('FOR_EACH_SELECTED_UNIT')
        search, _ = find_min(e, owner, current, kv(current, '触发血线'), variable=True)
        body = [*search, e.branch([e.exists(target())],
            [anim, e.oncefx(owner, 101499, 1.5, 1.), e.pick(captains(owner),
             [e.branch([e.alive(selected)], [e.addbuff(selected, SHIELD, owner, current, kv(current, '护盾时长'))])])], [e.cancel()])]
    e.trigger(CAST, '施法出手', 'ABILITY_SP_END', [manual, e.branch(checks, body, [e.cancel()])])
    return e.done()


def param(name):
    return n(100006, 'GET_CUS_EVENT_PARAM', lit(100240, name))


def passive(index):
    e = Eca(SKILLS[index])
    owner, current = unit('ABILITY_OWNER'), ability()
    if index == 1:
        storage = current
        search, chosen = find_min(e, owner, storage, f(1))
        consume = e.action('SET_BUFF_STACK', core(owner), lit(100002, 1))
        response = [e.branch([e.exists(core(owner))],
            [e.branch([e.compare(n(100002, 'GET_MOD_STACK', core(owner)), '>', f(1))],
                [*search, e.branch([e.exists(chosen)],
                  [consume, e.oncefx(chosen, 101428, 1., .7),
                   e.heal(chosen, owner, current, math(attr(chosen, 'hp_max'), '*', kv(current, '治疗比例'))),
                   e.send(HEALED, owner, chosen), e.send(FIRST, owner, chosen)])])])]
        event = ('SPECIAL_UNIT_EVENT', [owner, lit(100007, 'ET_UNIT_HURT_OTHER')])
        conditions = [e.condition('GET_IS_NORMAL_HIT_FROM_EVENT'), e.alive(owner),
                      e.compare(n(100002, 6, {'__tuple__': True, 'items': ['INTEGER', '当前游戏进程阶段']}), '==', f(2))]
    elif index == 3:
        chosen = param('治疗单位')
        response = [e.branch([e.exists(chosen)], [e.branch([e.alive(chosen)],
                    [e.addbuff(chosen, BOOST, owner, current, kv(current, '增攻时长'))])])]
        event = ('RECEIVE_CUSTOM_EVENT', [lit(100238, HEALED)])
        conditions = [e.compare(param('触发单位'), '==', owner, 'UNIT_COMPARE')]
    else:
        search, chosen = find_min(e, owner, current, f(1), exclude=param('治疗单位'))
        response = [e.branch([e.compare(kv(current, '额外治疗人数'), '>', f(0))],
            [*search, e.branch([e.exists(chosen)],
             [e.oncefx(chosen, 101428, 1., .7),
              e.heal(chosen, owner, current, math(attr(chosen, 'hp_max'), '*', kv(current, '治疗比例'))),
              e.send(HEALED, owner, chosen)])])]
        event = ('RECEIVE_CUSTOM_EVENT', [lit(100238, FIRST)])
        conditions = [e.compare(param('触发单位'), '==', owner, 'UNIT_COMPARE'), e.alive(owner)]
    lifecycle(e, PARAMS[index], event, response, conditions)
    return e.done()


def core_eca():
    e = Eca(CORE, True)
    owner = unit('MODIFIER_OWNER')
    e.var('NEW_TIMER', '凝露冷却计时器', -1)
    e.var('DYNAMIC_TRIGGER_INSTANCE', '施法监听', 0)
    e.var('SFX_ENTITY', '凝露特效', None)
    e.trigger(MGAIN, '获得凝露循环', 'OBTAIN_MODIFIER',
              [e.setkv(buff(), '凝露冷却', f(0)), MCAST])
    emitted = unit('GET_UNIT_FROM_EVENT')
    event_skill = n(100014, 'DAMAGE_ABILITY')
    captain_match = e.branch([e.compare(unit('FOR_EACH_SELECTED_UNIT'), '==', emitted, 'UNIT_COMPARE')],
       [e.action('SET_BUFF_STACK', buff(), lit(100002, 2)),
        e.setkv(buff(), '凝露冷却', kv(skill(owner, SKILLS[1]), '凝露间隔')),
        e.action('RUN_ONCE_TIMER', av(100181, '凝露冷却计时器', 'VARIABLE', 'NEW_TIMER'),
                 kv(skill(owner, SKILLS[1]), '凝露间隔'),
                 n(100022, 1, e.branch([e.exists(buff())], [e.setkv(buff(), '凝露冷却', f(0))])),
                 local_var={'__tuple__': True, 'items': [{}, {}]}),
        e.action('BREAK_LOOP')])
    response = [e.branch([e.exists(event_skill), e.exists(skill(owner, SKILLS[1]))],
        [e.branch([e.condition('ABILITY_CAST_TYPE_COMPARE', n(100219, 'GET_ABILITY_CAST_TYPE', event_skill),
                               lit(100035, '=='), lit(100219, 2))],
                  [e.pick(captains(owner), [captain_match])])])]
    conditions = [e.alive(owner), e.compare(kv(buff(), '凝露冷却'), '<=', f(0)),
                  e.compare(n(100002, 'GET_MOD_STACK', buff()), '<', f(2)),
                  e.compare(n(100002, 6, {'__tuple__': True, 'items': ['INTEGER', '当前游戏进程阶段']}), '==', f(2))]
    e.trigger(MCAST, '友方队长主动出手凝露', 'GENERIC_UNIT_EVENT', response, conditions,
              [n(100008, 'GENERIC_UNIT_EVENT', 'ET_UNIT_RELEASE_ABILITY')], parent=MGAIN, handle='施法监听')
    ui = copy.deepcopy(read('modifier/134242511.json')['trigger_dict'][str(MLAYER)]['action'][1:])
    e.trigger(MLAYER, '凝露层数与表现', 'MODIFIER_LAYER_CHANGE',
       [*ui, e.deletefx('凝露特效'), e.branch([e.compare(n(100002, 'GET_MOD_STACK', buff()), '>', f(1))],
        [e.attachfx(owner, 101099, '凝露特效', .35)])])
    e.trigger(MLOSS, '失去凝露循环', 'LOSS_MODIFIER',
              [e.branch([e.exists(av(100181, '凝露冷却计时器', 'VARIABLE', 'NEW_TIMER'))],
                        [e.action('DELETE_TIMER', av(100181, '凝露冷却计时器', 'VARIABLE', 'NEW_TIMER'))]),
               e.action('UNREG_TRIGGER', av(100178, '施法监听', 'VARIABLE', 'DYNAMIC_TRIGGER_INSTANCE')),
               e.deletefx('凝露特效')])
    return e.done()


def status(bid):
    e = Eca(bid, True)
    e.var('SFX_ENTITY', '特效表现', None)
    linked = n(100014, 'RELATED_ABILITY', buff())
    owner = unit('MODIFIER_OWNER')
    if bid == SHIELD:
        apply = [e.action('SET_BUFF_SHIELD', buff(), math(attr(owner, 'hp_max'), '*', kv(linked, '护盾比例')))]
        effect, scale = 101235, .85
    else:
        key = '减攻比例' if bid == DOWN else '增攻比例'
        value = math(f(0), '-', kv(linked, key)) if bid == DOWN else kv(linked, key)
        apply = [e.action('ADD_MODIFIER_OWNER_ATTR', buff(), lit(100042, 'attack_phy'),
                          lit(100300, 'ATTR_ALL_RATIO'), value)]
        effect, scale = (101499, .65) if bid == DOWN else (101771, .6)
    e.trigger(MGAIN, '获得状态', 'OBTAIN_MODIFIER',
              [e.attachfx(owner, effect, scale=scale), e.branch([e.exists(linked)], apply)])
    loss = [e.deletefx('特效表现')]
    if bid != SHIELD:
        loss.append(e.action('CLEAR_MODIFIER_OWNER_ATTR', buff()))
    e.trigger(MLOSS, '失去状态', 'LOSS_MODIFIER', loss)
    return e.done()


def reid(eca, oid):
    serial = oid * 1000000 + 20000
    for v in walk(eca):
        if 'element_id' in v:
            serial += 1
            v['element_id'] = serial
    return eca


def kvs(values):
    template = next(iter(read('editor_table/abilityall/134284020.json')['kv'].values()))
    result = {}
    for index, (key, value) in enumerate(values.items()):
        field = copy.deepcopy(template)
        field.update(key=key, value=value, sort=index)
        result[key] = field
    return result


def stage():
    fresh = not BACKUP.exists()
    if not fresh:
        audit()
    shared = {path: read(path) for path in SHARED}
    lang = shared['zhlanguage.json']
    serial = 2037100000

    def strings(name, desc):
        nonlocal serial
        while str(serial) in lang or str(serial + 1) in lang:
            serial += 2
        keys = (serial, serial + 1)
        lang[str(keys[0])], lang[str(keys[1])] = name, desc
        serial += 2
        return keys

    def object_(oid, source, name, desc, icon):
        obj = read(source)
        a, b = strings(name, desc)
        obj.update(_ref_=oid, key=oid, uid=str(oid), name=a, desc=b, description=b, suffix='大乔')
        obj['ability_icon' if 'abilityall' in source else 'modifier_icon'] = icon
        return obj

    result = {}
    icon = read(f'editor_table/editorunit/{UNIT}.json')['icon']
    for index, oid in enumerate(SKILLS):
        source = 'editor_table/abilityall/134284020.json' if index % 2 == 0 else 'editor_table/abilityall/134284023.json'
        obj = object_(oid, source, NAMES[index], DESCS[index], icon)
        obj['kv'] = kvs(PARAMS[index])
        obj['tags'] = {'__tuple__': True, 'items': ['小招类技能'] if index % 2 == 0 else []}
        obj['ability_max_level'] = 1
        obj['ability_cast_type'] = 2 if index % 2 == 0 else 3
        if index % 2 == 0:
            obj['cold_down_time']['items'] = [str((8., 11., 15.)[index // 2])]
            obj['ability_cast_range']['items'] = ['10000.0' if index in (0, 4) else '8.0']
            if index in (0, 4):
                healer = read('editor_table/abilityall/134264846.json')
                obj['filter_condition_camp'] = healer['filter_condition_camp']
                obj['filter_condition_type'] = healer['filter_condition_type']
                obj['need_turn_to_target'] = False
            else:
                obj['filter_condition_camp'] = 5
        result[f'editor_table/abilityall/{oid}.json'] = obj
        result[f'ability/{oid}.json'] = reid(active(index) if index % 2 == 0 else passive(index), oid)
    for bid, name, desc in ((CORE, '凝露', '我方队长施放主动后凝露，下一次普攻击中治疗受伤队长。'),
                            (DOWN, '骤雨削攻', '攻击降低20%，持续5秒。'),
                            (BOOST, '雨润增攻', '攻击提高12%，持续4秒。'),
                            (SHIELD, '广伞护盾', '吸收自身最大生命12%的伤害，持续6秒。')):
        source = 'editor_table/modifierall/134284018.json' if bid == SHIELD else 'editor_table/modifierall/134283902.json'
        obj = object_(bid, source, name, desc, icon)
        obj.update(layer_max=2 if bid == CORE else 1, kv={}, shield_value=0.0,
                   same_origin_cover=False if bid != CORE else True,
                   layer_change_of_cover=3 if bid == CORE else 1)
        if bid != SHIELD:
            obj['modifier_type'] = 1
        result[f'editor_table/modifierall/{bid}.json'] = obj
        result[f'modifier/{bid}.json'] = reid(core_eca() if bid == CORE else status(bid), bid)
    rows = shared['tables/单位技能配置表.json']['table_data']['data']
    row = next(r for r in rows if len(r) > 1 and r[1] == UNIT)
    if row[2:10] != [134255698] * 8:
        raise ValueError('Da Qiao slots changed')
    row[2:10] = [SKILLS[0], SKILLS[2], SKILLS[4], 134255698, SKILLS[1], SKILLS[3], SKILLS[5], 134255698]
    rows = shared['tables/技能特有循环机制表.json']['table_data']['data']
    index = next((i for i, r in enumerate(rows[2:], 2) if not r or r[0] in ('', None)), len(rows))
    number = max(int(r[0]) for r in rows[2:] if r and str(r[0]).isdigit()) + 1
    newrow = [str(number), CORE, SKILLS[1], 0, 0] + [None] * (len(rows[0]) - 5)
    if index == len(rows): rows.append(newrow)
    else: rows[index] = newrow
    rows = shared['tables/技能作用描述表.json']['table_data']['data']
    number = max(int(r[0]) for r in rows[2:] if r and str(r[0]).isdigit()) + 1
    for index, oid in enumerate(SKILLS):
        if any(len(r) > 1 and r[1] == oid for r in rows[2:]): raise ValueError('Skill description ID occupied')
        rows.append(([str(number + index), oid, '主动' if index % 2 == 0 else '被动'] + [DESCS[index]] * 11 + [''] * len(rows[0]))[:len(rows[0])])
    custom = shared['customevent.json']
    for eid, name in ((FIRST, '大乔凝露主治疗'), (HEALED, '大乔凝露治疗完成')):
        if str(eid) in custom['conf']: raise ValueError('Custom event ID occupied')
        custom['conf'][str(eid)] = [['触发单位', 100006], ['治疗单位', 100006]]
        custom['group_info'].append({'__tuple__': True, 'items': [eid, name]})

    def folder(name, sourceid, oids, foldername):
        obj = shared[name]
        parentid = obj['d'][str(sourceid)]['items'][0]
        parent = next(v['items'] for v in obj['f'] if v['items'][2] == parentid)
        uid = 'daqiao' + ('ability' if 'ability' in name else 'modifier') + '20261012'
        path = parent[0]
        index = max((v['items'][1] for v in obj['f'] if v['items'][0] == path), default=-1) + 1
        obj['f'].append({'__tuple__': True, 'items': [path, index, uid, foldername]})
        for i, oid in enumerate(oids): obj['d'][str(oid)] = {'__tuple__': True, 'items': [uid, i]}

    # Place abilities beside other heroes, not inside the source hero folder.
    af = shared['editor/folderinfo/folderinfo_ability_all.json']
    sourceid = 134284020
    parentid = af['d'][str(sourceid)]['items'][0]
    parent = next(v['items'] for v in af['f'] if v['items'][2] == parentid)
    uid = 'daqiaoability20261012'
    index = max(v['items'][1] for v in af['f'] if v['items'][0] == parent[0]) + 1
    af['f'].append({'__tuple__': True, 'items': [parent[0], index, uid, '大乔']})
    for i, oid in enumerate(SKILLS): af['d'][str(oid)] = {'__tuple__': True, 'items': [uid, i]}
    mf = shared['editor/folderinfo/folderinfo_modifier_all.json']
    coreparent = mf['d']['134283902']['items'][0]
    index = max(v['items'][1] for v in mf['d'].values() if v['items'][0] == coreparent) + 1
    mf['d'][str(CORE)] = {'__tuple__': True, 'items': [coreparent, index]}
    folder('editor/folderinfo/folderinfo_modifier_all.json', 134283937, [DOWN, BOOST, SHIELD], '大乔')
    result.update(shared)
    manifest = {}
    with zipfile.ZipFile(BACKUP, 'x' if fresh else 'r', compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, obj in result.items():
            path = MAP / relative
            existed = path.exists()
            if existed and relative not in SHARED: raise ValueError('Object ID occupied: ' + relative)
            original = path.read_bytes() if existed else None
            if existed and fresh: archive.writestr(relative, original)
            out = STAGE / relative
            out.parent.mkdir(parents=True, exist_ok=True)
            data = (json.dumps(obj, ensure_ascii=True, indent=4) + '\n').encode()
            out.write_bytes(data)
            manifest[relative] = {'before': hashlib.sha256(original).hexdigest() if existed else None,
                                  'after': hashlib.sha256(data).hexdigest()}
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Staged', len(result), 'files; six skills, four Buffs, three tables, two custom events')
    audit()


def audit(live=False):
    manifest = json.loads((ROOT / 'manifest.json').read_bytes())
    base = MAP if live else STAGE
    for relative, hashes in manifest.items():
        obj = json.loads((base / relative).read_bytes())
        if relative.startswith(('ability/', 'modifier/')):
            for t in obj['trigger_dict'].values():
                if t['valid'] is not True: raise ValueError('Invalid ECA: ' + relative)
                ids = [v['element_id'] for v in walk(t) if 'element_id' in v]
                if len(ids) != len(set(ids)): raise ValueError('Duplicate nodes: ' + relative)
            if live and obj != json.loads((STAGE / relative).read_bytes()):
                raise ValueError('Editor changed final ECA: ' + relative)
    for index, oid in enumerate(SKILLS):
        eca = json.loads((base / f'ability/{oid}.json').read_bytes())
        events = {t['event'][0]['event_type'] for t in eca['trigger_dict'].values()}
        expected = {'ABILITY_OBTAIN', 'ABILITY_LEVEL_CHANGED', 'ABILITY_LOSE'}
        if not expected <= events: raise ValueError('Incomplete lifecycle')
        if index % 2 == 0 and 'ABILITY_SP_END' not in events: raise ValueError('Missing cast')
        writes = [v for v in walk(eca) if v.get('action_type') == 'SET_ENTITY_KV' and v['args_list'][0].get('sub_type') == 'CUR_ABILITY']
        for key in PARAMS[index]:
            if sum(v['args_list'][1].get('args_list') == [key] for v in writes) != 6:
                raise ValueError('Missing obtain/level KV: ' + key)
    coreobj = json.loads((base / f'modifier/{CORE}.json').read_bytes())
    if any(v.get('sub_type') in ('RELATED_ABILITY', 'RELATED_ABILITY_MODIFIER') for v in walk(coreobj)):
        raise ValueError('Public core Buff must not assume an associated skill')
    for relative in manifest:
        if relative.startswith(('ability/', 'modifier/')):
            for v in walk(json.loads((base / relative).read_bytes())):
                if v.get('action_type') == 'CREATE_SFX_ON_POINT_NEW':
                    if not v['op_arg_enable'][3] or not v['op_arg_enable'][4]:
                        raise ValueError('One-shot effect missing duration/destruction')
    if not live:
        for relative, hashes in manifest.items():
            path = MAP / relative
            digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
            if digest != hashes['before']: raise ValueError('Live source changed: ' + relative)
    print('Lifecycle, KV levels, core association, effect cleanup and ECA checked', 'live' if live else 'candidate')


def install():
    audit()
    manifest = json.loads((ROOT / 'manifest.json').read_bytes())
    for relative, hashes in manifest.items():
        data = (STAGE / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != hashes['after']: raise ValueError('Candidate changed')
    for relative in manifest:
        path = MAP / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + '.codex-daqiao-tmp')
        temp.write_bytes((STAGE / relative).read_bytes())
        temp.replace(path)
    print('Installed', len(manifest), 'files')


def prepare_core():
    audit(True)
    relative = f'modifier/{CORE}.json'
    old = (MAP / relative).read_bytes()
    with zipfile.ZipFile(ROOT / 'before-exact-dew-timer.zip', 'x', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(relative, old)
    data = (json.dumps(reid(core_eca(), CORE), ensure_ascii=True, indent=4) + '\n').encode()
    (STAGE / relative).write_bytes(data)
    metadata = {'before': hashlib.sha256(old).hexdigest(), 'after': hashlib.sha256(data).hexdigest()}
    (ROOT / 'core-timer-manifest.json').write_text(json.dumps(metadata))
    manifest = json.loads((ROOT / 'manifest.json').read_bytes())
    manifest[relative]['after'] = metadata['after']
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Prepared single core Buff correction: exact one-shot cooldown from dew acquisition')


def install_core():
    metadata = json.loads((ROOT / 'core-timer-manifest.json').read_bytes())
    relative = f'modifier/{CORE}.json'
    live, candidate = MAP / relative, STAGE / relative
    if hashlib.sha256(live.read_bytes()).hexdigest() != metadata['before']:
        raise ValueError('Core Buff changed during timer staging')
    data = candidate.read_bytes()
    if hashlib.sha256(data).hexdigest() != metadata['after']:
        raise ValueError('Core timer candidate changed')
    temp = live.with_name(live.name + '.codex-daqiao-tmp')
    temp.write_bytes(data)
    temp.replace(live)
    print('Installed exact dew cooldown in one core Buff only')


if __name__ == '__main__':
    {'stage': stage, 'audit': audit, 'install': install, 'verify': lambda: audit(True),
     'prepare-core': prepare_core, 'install-core': install_core}[sys.argv[1]]()
