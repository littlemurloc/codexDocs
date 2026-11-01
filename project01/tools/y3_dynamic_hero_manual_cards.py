"""Append late-joined hero abilities to the existing manual-card pool only."""
from __future__ import annotations
import copy
import y3_main_hud_hero_layout as h

def patched(original):
    d=copy.deepcopy(original);n=h.Nodes(2099951001000000)
    p=h.ref('PLAYER','执行玩家');u=h.ref('UNIT_ENTITY','玩家队伍单位')
    ability=h.declare(d,'ABILITY','军略登记_当前技能')
    exists=h.declare(d,'BOOLEAN','军略登记_已存在')
    row=h.declare(d,'INTEGER','军略登记_新增行')
    pool=h.ex(100011,'VARIABLE',h.tuple_('TABLE','卡牌技能池-表'),h.pindex(p))
    key=h.ex(100002,'ITER_TABLE_KEY_INT')
    owner=h.ex(100006,'GET_UNIT_ENTITY_TABLE_VAR_ND',pool,key,h.txt('归属单位'))
    old=h.ex(100014,'GET_ABILITY_TABLE_VAR_ND',pool,key,h.txt('技能'))
    fields=[('技能',ability),('归属单位',u),('是否已抽取',h.flag(False)),
      ('是否上锁',h.kv('BOOLEAN',u,'自动施法')),('归属单位名称',h.ex(100003,'GET_UNIT_NAME',u)),
      ('技能释放类型',h.lit(100219,2))]
    append=[n.set(row,h.ex(100002,'INT_PLUS_ONE',h.ex(100002,'GET_TABLE_LENGTH',pool)))]+[
      n.act('SET_TABLE_VALUE_ND',pool,row,h.txt(k),v)for k,v in fields]
    inspect=[n.set(ability,h.ex(100014,'FOR_EACH_SELECTED_ABILITY')),
      n.branch([n.exists(ability)],[n.branch([n.cmp(h.ex(100039,'ABILITY_NAME_OF_ABILITY',ability),'!=',h.lit(100039,134255698),'ABILITY_COMPARE')],[
        n.set(exists,h.flag(False)),n.traverse(pool,[n.branch([n.cmp(owner,'==',u,'UNIT_COMPARE')],[
          n.branch([n.cmp(old,'==',ability,'ABILITY_ENTITY_COMPARE')],[n.set(exists,h.flag(True)),n.act('BREAK_LOOP')])])]),
        n.branch([n.cmp(exists,'==',h.flag(False),'BOOL_COMPARE')],append)])])]
    block=n.box('登记新队长技能到现有军略池（仅追加，按实例去重）',[
      n.branch([n.exists(u)],[n.branch([n.cmp(h.ex(100025,'OWNER_PLAYER',u),'==',p,'PLAYER_COMPARE')],[
        n.branch([n.cond('UNIT_IN_GROUP',u,h.group(p))],[n.act('ITER_ABILITY_DO',u,h.lit(100182,3),h.ex(100022,1,*inspect))])])])])
    # All skill grants/core initialization and group membership precede this.
    tail=d['action'][-1];assert tail['action_type']=='CALL_TRIGGER_FUNC'and tail['args_list'][0]['sub_type']==h.FID1
    assert not any(x.get('element_id')==block['element_id']for x in h.walk(d))
    d['action'].insert(len(d['action'])-1,block)
    return d


if __name__=='__main__':
    raise SystemExit('Historical publisher removed. Run test_y3_dynamic_hero_manual_cards.py for read-only regression.')
