"""Material badge and synchronized reveal transformation helpers.

The initial 2026-10-29 deployment is retired; no map publishing entry point.
"""
from __future__ import annotations
import copy,json,uuid
from pathlib import Path
import y3_forge_command_cards as f
b,r,s=f.b,f.r,f.s
MAP=f.MAP
OFFER='global_trigger/trigger/关卡初始化内容/universe03.json'
SHOW='global_trigger/function/new/UI/军略卡牌合成画面表现处理.json'
NEW='global_trigger/function/new/UI/返回军略卡牌右上角文本.json'
INDEX='global_trigger/function/new/UI/index.txt'
FID=uuid.uuid5(uuid.NAMESPACE_URL,'project01/y3/ui/card-badge-v1').hex
TID=2099949001
SET_COUNT='6f6c399284e011f182d50f76820168d8'
SPEED=2.;FX_STEP=.05/SPEED;REVEAL_DELAY=1.75/SPEED;HOLD=.6;SETTLE=.5/SPEED;FLY_FRAMES=16
def load(p):return json.loads(p.read_text('utf8'))
def encode(d):return (json.dumps(d,ensure_ascii=True,indent=4)+'\n').encode('utf8')
def digest(p):return f.sha(p.read_bytes())if p.is_file()else None
def build_badge():
    e=f.Function(18,[('PLAYER','执行玩家'),('ABILITY_NAME','卡牌类型')],'材料显示实时库存（无实例为0）；其余卡牌保留原set进度。只读取状态，不修改库存或合成。')
    e.oid=TID;e.serial=TID*1000000;e.obj.update(func_id=FID,func_name='返回军略卡牌右上角文本',trigger_name='返回军略卡牌右上角文本',trigger_id=TID,group_id='card_ui_polish_20261029',func_des='返回卡牌角标：玩家{执行玩家}，卡牌{卡牌类型}')
    p=e.var('PLAYER','执行玩家');aid=e.var('ABILITY_NAME','卡牌类型');cfg=e.var('TABLE','玩家卡牌配置');row=e.var('INTEGER','卡牌行');result=e.var('STRING','角标文本');material=e.var('BOOLEAN','属于锻造材料')
    idx=s.foreign('328a949b859611f180c31b625ad74320','INTEGER',aid,cfg,b.text('技能类型'))
    have=s.foreign(SET_COUNT,'INTEGER',aid,p);total=copy.deepcopy(have);total['call_rt_index']=1
    original=f.q.journal.text(have,'/',total)
    return e.finish([e.set(material,r.flag(False)),e.set(cfg,f.config(p)),e.set(row,idx),
      e.branch([e.compare(row,'>',r.i(0))],[e.branch([e.compare(r.get(cfg,row,'升级机制'),'==',b.text('武器锻造'),'STRING_COMPARE'),e.compare(r.get(cfg,row,'子归类'),'==',b.text('材料'),'STRING_COMPARE')],[e.set(material,r.flag(True))])]),
      e.branch([e.yes(material)],[e.set(result,f.q.journal.text('库存：',f.expr(18,'INTEGER',p,aid)))],[e.set(result,original)]),e.ret('STRING',result)])
def patch_text(doc,element):
    node=next(n for n in b.walk(doc)if n.get('element_id')==element);old=copy.deepcopy(node)
    assert node['action_type']=='SET_UI_COMP_TEXT'and 'text_level'in str(node['args_list'][1])
    count=next(n for n in b.walk(node['args_list'][2])if n.get('sub_type')==SET_COUNT)
    aid=copy.deepcopy(count['args_list'][0]);player=copy.deepcopy(node['args_list'][0])
    node['args_list'][2]=s.foreign(FID,'STRING',player,aid)
    return old
def build():
    out={NEW:build_badge()};offer=f.read(OFFER);show=f.read(SHOW)
    oldtext={OFFER:patch_text(offer,1029231331000799),SHOW:patch_text(show,454042343001926)}
    changes={}
    def update(element,location,value):
        n=next(n for n in b.walk(show)if n.get('element_id')==element);part=n
        for k in location[:-1]:part=part[k]
        old=copy.deepcopy(part[location[-1]]);part[location[-1]]=value;changes[str(element)+':'+str(location)]=dict(before=old,after=value)
    # Sequence frames, lifetime and reveal callback use the same 2x factor.
    update(454042343001455,['args_list',0,'op_arg',2,'args_list',0],FX_STEP)
    update(454042343001455,['args_list',0,'op_arg',3,'args_list',0],REVEAL_DELAY)
    update(454042343001470,['args_list',0,'args_list',0],REVEAL_DELAY)
    update(454042343002062,['args_list',6,'args_list',0],SETTLE)
    update(454042343002092,['args_list',0,'args_list',0],HOLD)
    update(454042343002121,['args_list',0,'args_list',0],FLY_FRAMES)
    # The generic helper uses its frame parameter as BOTH playback end-frame and
    # hide-timer length. Passing16 would truncate a31-frame animation. Inline the
    # observed native play action here: retain end31, speed2, one cleanup at16.
    fly=next(n for n in b.walk(show)if n.get('element_id')==454042343002104);original_fly=copy.deepcopy(fly);args=fly['args_list'][0]['args_list']
    helper=f.read('global_trigger/function/new/UI/UI动画展示.json');play=copy.deepcopy(next(n for n in b.walk(helper)if n.get('action_type')=='PLAY_UI_COMP_ANIM_NEW'))
    play['element_id']=fly['element_id'];play['args_list']=[copy.deepcopy(args[0]),copy.deepcopy(args[1])]
    play['op_arg'][1]=r.i(31);play['op_arg'][2]=b.f(SPEED)
    assert play['op_arg_enable']==[True,True,True,True]
    fly.clear();fly.update(play)
    out[OFFER]=offer;out[SHOW]=show;index=f.read(INDEX);assert '返回军略卡牌右上角文本.json'not in index
    index['返回军略卡牌右上角文本.json']=max(index.values())+1;out[INDEX]=index
    return out,{'original_text_nodes':oldtext,'timings':changes,'original_fly_call':original_fly}

if __name__ == '__main__':
    raise SystemExit('Initial map deployment retired; use maintained helpers and read-only regression fixtures.')
