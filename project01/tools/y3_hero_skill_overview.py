"""Targeted portrait / six-skill / core-mechanism UI upgrade.

Runtime display reads the live unit-skill and core tables and object metadata.
It does not duplicate skill descriptions or alter unlock/combat/save rules.
"""
from __future__ import annotations
import argparse,copy,json,shutil,uuid,os
from pathlib import Path
import y3_hero_detail_restore as h
from safezone_ui_fixtures import retired_publish
b=h.b;ROOT=b.ROOT;PROJECT=b.PROJECT;MAP=b.MAP
WORK=Path(os.environ.get('Y3_HERO_OVERVIEW_STAGE',str(ROOT/'tmp/hero-six-skill-overview-20261119')))
NAME='刷新安全区英雄技能全览';FID=uuid.uuid5(uuid.NAMESPACE_URL,'project01/ui/hero-six-skill-overview/20261119').hex
FN=b.FD+NAME+'.json';BASE=2101120100;EVENT='安全区英雄全览_'
SKILLS=MAP+'tables/单位技能配置表.json';CORES=MAP+'tables/技能特有循环机制表.json'
SKILL_TID='4fa9acec-f1cb-4435-afe7-b721f8c6825d';CORE_TID='a5dd0f31-d460-4e61-b898-1c2a05c8f3f6'
DESC=MAP+'tables/技能作用描述表.json';LANG=MAP+'zhlanguage.json'
EMPTY=134255698;SLOTS=[1,5,2,6,3,7]
OUTPUTS=[b.UI,h.SELECT,b.OLD,FN,b.FI]
EXTRA='hero/v2/explanation'

def ui(key):return b.u(b.uid(key))
def ability(n):return b.ex(100039,'VARIABLE',b.tup('ABILITY_NAME',n,'local'))
def modifier(n):return b.ex(100046,2,b.tup('MODIFIER',n,'local'))
def declare(d,kind,name):
    if kind in b.s.TYPES:return b.s.declare(d,kind,name)
    d['var_data'][0].setdefault(kind,{})[name]=0;d['var_data'][1][name]=0;d['var_data'][2].append(name)
    return ability(name)if kind=='ABILITY_NAME'else modifier(name)
def table(kind,tid,row,key):
    typ={'ABILITY_NAME':100039,'MODIFIER':100046,'UNIT_NAME':100116}[kind]
    return b.ex(typ,'GET_'+kind+'_TABLE_VAR_ND',b.lit(100011,tid),row,b.text(key))
def traverse(n,tid,actions):return n.act('TRAVERSE_TABLE_NEW',b.lit(100011,tid),b.ex(100022,1,*actions),op_arg=[b.boolean(True)],op_arg_enable=[True])
def draw(n,p,key,value):return n.act('SET_UI_COMP_IMAGE_NEW',p,ui(key),value)
def title_of(skill):return b.ex(100003,'GET_ABILITY_CONF_STR_ATTR',skill,b.lit(100221,'name'))
def full_description(skill):return b.ex(100003,'GET_ABILITY_CONF_STR_ATTR',skill,b.lit(100221,'description'))
def valid_skill(n,s):return[n.cmp(s,'!=',b.lit(100039,EMPTY),'ABILITY_COMPARE'),n.cmp(s,'!=',b.ex(100039,'NONE_ABILITY_KEY'),'ABILITY_COMPARE')]
def detach(doc,node):
    parent=next(n for n in b.walk(doc)if node in n.get('children',[]));parent['children'].remove(node)

def build_ui(doc):
    d=copy.deepcopy(doc);detail=b.find_uid(d,b.DETAIL);bg=b.child(detail,'bg');head=b.child(bg,'headBar')
    assert not any(n.get('uid')==b.uid(EXTRA)for n in b.walk(d)),'Already applied'
    portrait=b.find_uid(d,b.uid('hero/portrait-mask'));detach(d,portrait)
    b.pos(portrait,165,380,300,420);portrait.update(clip_enabled=True,clipping_type=1)
    img=b.find_uid(portrait,b.uid('hero/portrait'));b.pos(img,150,210,300,678);img['anchor']=b.tup(.5,.5)
    detail['children'].insert(1,portrait)
    b.pos(head,490,535,340,120)
    b.font(b.pos(b.child(head,'name'),155,95,280,48),36)
    b.pos(b.child(head,'品质图标'),315,95,30,30)
    b.font(b.pos(b.child(head,'阵营名称'),170,25,320,28),20,b.MUTED)
    b.font(b.pos(b.find_uid(d,b.uid('roster/state')),432,535,182,32),22)
    b.pos(b.find_uid(d,b.uid('roster/deploy')),592,535,126,42)
    b.pos(b.find_uid(d,b.uid('hero/support-entry')),564,625,180,30)
    b.pos(b.find_uid(d,b.uid('hero/support-entry-text')),90,15,174,30)
    # The old widgets keep their UIDs for the original detail refresher.
    for i in range(1,4):b.find_uid(d,b.uid('hero/skill-row/'+str(i)))['visible']=False
    normal=b.find_uid(d,b.uid('hero/skill-row/3'));normal['visible']=True;b.pos(normal,398,625,140,30)
    for c in normal['children']:c['visible']=False
    b.extra(normal,b.label('普攻说明文字','hero/v2/normal-text','普攻说明 ›',70,15,138,30,20,b.MUTED))
    core=h.plain_click('核心循环入口','hero/v2/core',490,450,340,80,EVENT+'7')
    core['children']=[h.image('核心图标边框','hero/v2/core-frame',134241138,42,40,64,64,(16,16,16,16)),
        h.image('核心图标','hero/v2/core-icon',None,42,40,54,54),
        b.label('核心机制名称','hero/v2/core-name','核心机制',202,54,235,34,25),
        b.label('核心机制状态','hero/v2/core-status','点击查看机制',202,21,235,26,19,b.MUTED)]
    b.extra(detail,core)
    b.extra(detail,b.label('主动组标题','hero/v2/active-caption','主动技能 · 1 / 3 / 5 星',490,387,340,28,22))
    b.extra(detail,b.label('被动组标题','hero/v2/passive-caption','被动技能 · 2 / 4 / 6 星',490,245,340,22,22))
    for level in range(1,7):
        active=level%2==1;column=(level-1)//2
        tile=h.plain_click(f'{level}星技能入口',f'hero/v2/skill/{level}',375+column*115,310 if active else 177,110,116,EVENT+str(level))
        tile['children']=[h.image('图标边框',f'hero/v2/skill-frame/{level}',134241138,55,87,62,62,(16,16,16,16)),
            h.image('技能图标',f'hero/v2/skill-icon/{level}',None,55,87,54,54),
            b.label('技能名称',f'hero/v2/skill-name/{level}','',55,38,108,40,20),
            b.label('解锁状态',f'hero/v2/skill-state/{level}','',55,8,108,18,18,b.MUTED)]
        b.extra(detail,tile)
    panel=b.find_uid(d,h.PANEL)
    common=b.newnode('六技能与核心说明',EXTRA,480,320,880,500);common['visible']=False
    common['children']=[h.image('说明图标','hero/v2/detail-icon',None,52,445,72,72),
        b.label('条目名称','hero/v2/detail-name','',480,450,720,46,32),
        b.label('解锁说明','hero/v2/detail-state','',440,392,820,34,24,b.MUTED)]
    source=b.find_uid(d,b.uid('hero/skill-scroll/1'));scroll=copy.deepcopy(source)
    scroll.update(uid=b.uid('hero/v2/detail-scroll'),name='完整说明滚动区',prefab_sub_key=None,children=[])
    b.pos(scroll,440,196,840,350)
    text=b.label('完整内容','hero/v2/detail-description','',410,450,820,900,25)
    text.update(alignment=b.tup(1,8),over_pattern=True);scroll['children']=[text];common['children'].append(scroll)
    panel['children'].append(common)
    return d

def make_function(template):
    old=b.s.FIDS.get(NAME);b.s.FIDS[NAME]=FID
    try:d=b.s.function(template,NAME,BASE,[('PLAYER','执行玩家'),('INTEGER','说明序号')],
        '仅展示：从实时单位技能表读取3主动3被动，关联循环表读取核心；未解锁可预览，不赋技能、不扣费、不写存档。')
    finally:
        if old is None:b.s.FIDS.pop(NAME,None)
        else:b.s.FIDS[NAME]=old
    n=b.Nodes(BASE);p=b.ref('PLAYER','执行玩家');mode=b.ref('INTEGER','说明序号')
    row=declare(d,'INTEGER','武将行号');star=declare(d,'INTEGER','当前星级');unit=declare(d,'UNIT_NAME','武将类型')
    found=declare(d,'BOOLEAN','已找到配置');core_found=declare(d,'BOOLEAN','已找到循环');core=declare(d,'MODIFIER','循环类型')
    core_star=declare(d,'INTEGER','循环星级');skillvars=[declare(d,'ABILITY_NAME','技能'+str(i))for i in range(1,7)]
    key=b.ex(100003,'ITER_TABLE_KEY_STR');ci=b.ex(100002,'ITER_TABLE_KEY_INT')
    init=[n.vis(p,b.uid(EXTRA),False),n.set(row,b.kv(p,b.SELECT)),n.set(star,b.save(p,16,row,'当前升星进度')),
          n.set(unit,b.tab('UNIT_NAME',b.TABLE,row,'单位类型')),n.set(found,b.boolean(False)),n.set(core_found,b.boolean(False)),
          n.set(core,b.ex(100046,'NONE_MODIFIER_KEY')),n.set(core_star,b.integer(0))]
    for level,s in enumerate(skillvars,1):
        init +=[n.set(s,b.ex(100039,'NONE_ABILITY_KEY')),draw(n,p,f'hero/v2/skill-icon/{level}',b.lit(100115,999)),
            n.label(p,ui(f'hero/v2/skill-name/{level}'),'暂无配置'),n.label(p,ui(f'hero/v2/skill-state/{level}'),f'{level}星'),
            b.color(n,p,ui(f'hero/v2/skill-state/{level}'),b.MUTED)]
    init +=[draw(n,p,'hero/v2/core-icon',b.lit(100115,999)),n.label(p,ui('hero/v2/core-name'),'核心机制'),
            n.label(p,ui('hero/v2/core-status'),'暂无配置，点击查看')]
    lookup=[n.set(s,table('ABILITY_NAME',SKILL_TID,key,'技能'+str(slot)))for s,slot in zip(skillvars,SLOTS)]
    lookup +=[n.set(found,b.boolean(True))]
    init.append(traverse(n,SKILL_TID,[n.branch([n.cmp(table('UNIT_NAME',SKILL_TID,key,'单位类型'),'==',unit,'UNIT_CLASS_COMPARE')],lookup)]))
    # Match the actual associated skills; empty slots never participate.
    core_search=[]
    for level,s in enumerate(skillvars,1):
        matches=[n.cmp(table('ABILITY_NAME',CORE_TID,ci,'关联技能'+str(i)),'==',s,'ABILITY_COMPARE')for i in range(1,4)]
        core_search.append(n.branch([*valid_skill(n,s),b.bcmp(n,core_found,False),n.cond('OR',b.ex(100021,1,*matches))],[
            n.set(core,table('MODIFIER',CORE_TID,ci,'能力循环机制BUFF')),n.set(core_star,b.integer(level)),n.set(core_found,b.boolean(True))]))
    init.append(n.branch([b.bcmp(n,found,True)],[traverse(n,CORE_TID,core_search)]))
    def show_header():return[n.vis(p,h.POPUP,True),n.vis(p,'e3911e6a-9735-44c6-a3a2-9d33c8a0aeee',False),
        n.vis(p,'fd0111ad-1b15-4c77-b75d-04a280b33ecf',False),n.vis(p,b.uid(EXTRA),True),
        n.label(p,ui('hero/dialog-hero'),b.tab('STRING',b.TABLE,row,'仆从名称')),
        n.label(p,ui('hero/v2/detail-description'),'暂未配置说明。')]
    for level,s in enumerate(skillvars,1):
        text=f'{level}星'+('主动'if level%2 else'被动')
        on=n.cmp(star,'>=',b.integer(level));hero_unlocked=b.bcmp(n,b.save(p,16,row,'是否解锁','BOOLEAN'),True)
        states=n.branch([on,hero_unlocked],[n.label(p,ui(f'hero/v2/skill-state/{level}'),f'{level}星已解锁'),b.color(n,p,ui(f'hero/v2/skill-state/{level}'),b.GREEN)],
            [n.label(p,ui(f'hero/v2/skill-state/{level}'),f'{level}星未解锁'),b.color(n,p,ui(f'hero/v2/skill-state/{level}'),b.MUTED)])
        # The state branch is cloned so element IDs stay unique in each action site.
        init +=[n.branch(valid_skill(n,s),[draw(n,p,f'hero/v2/skill-icon/{level}',b.ex(100115,'GET_ICON_BY_ABILITY_TYPE',s)),
            n.label(p,ui(f'hero/v2/skill-name/{level}'),title_of(s)),states])]
        dialog=show_header()+[n.label(p,ui('hero/dialog-title'),'英雄技能 · 完整说明'),
            n.label(p,ui('hero/v2/detail-name'),'暂无配置'),n.label(p,ui('hero/v2/detail-state'),text+' · 暂无配置'),
            draw(n,p,'hero/v2/detail-icon',b.lit(100115,999)),
            n.branch(valid_skill(n,s),[n.label(p,ui('hero/v2/detail-name'),title_of(s)),
                draw(n,p,'hero/v2/detail-icon',b.ex(100115,'GET_ICON_BY_ABILITY_TYPE',s)),
                n.label(p,ui('hero/v2/detail-description'),full_description(s)),
                n.branch([n.cmp(star,'>=',b.integer(level)),b.bcmp(n,b.save(p,16,row,'是否解锁','BOOLEAN'),True)],
                    [n.label(p,ui('hero/v2/detail-state'),text+' · 已解锁')],[n.label(p,ui('hero/v2/detail-state'),text+' · 未解锁，可预览')])])]
        init.append(n.branch([n.cmp(mode,'==',b.integer(level))],dialog))
    core_name=b.ex(100003,'GET_NAME_OF_MODIFIER_KEY',core)
    init +=[n.branch([b.bcmp(n,core_found,True)],[
        draw(n,p,'hero/v2/core-icon',b.ex(100115,'GET_ICON_BY_BUFF_TYPE',core)),
        n.label(p,ui('hero/v2/core-name'),b.join('核心 · ',core_name)),
        n.branch([n.cmp(star,'>=',core_star),b.bcmp(n,b.save(p,16,row,'是否解锁','BOOLEAN'),True)],
            [n.label(p,ui('hero/v2/core-status'),'已开启 · 点击查看机制')],
            [n.label(p,ui('hero/v2/core-status'),b.join(b.intstr(core_star),'星开启 · 可预览'))])])]
    init +=[n.branch([n.cmp(mode,'==',b.integer(7))],show_header()+[
        n.label(p,ui('hero/dialog-title'),'核心机制 · 专属循环'),n.label(p,ui('hero/v2/detail-name'),'核心机制'),
        n.label(p,ui('hero/v2/detail-state'),'暂无配置'),draw(n,p,'hero/v2/detail-icon',b.lit(100115,999)),
        n.branch([b.bcmp(n,core_found,True)],[n.label(p,ui('hero/v2/detail-name'),core_name),
            draw(n,p,'hero/v2/detail-icon',b.ex(100115,'GET_ICON_BY_BUFF_TYPE',core)),
            n.label(p,ui('hero/v2/detail-description'),b.ex(100003,'GET_DES_ID_BY_MODIFIER_TYPE',core)),
            n.branch([n.cmp(star,'>=',core_star),b.bcmp(n,b.save(p,16,row,'是否解锁','BOOLEAN'),True)],
                [n.label(p,ui('hero/v2/detail-state'),'专属循环 · 已开启')],
                [n.label(p,ui('hero/v2/detail-state'),b.join(b.intstr(core_star),'星开启 · 未解锁，可预览'))])])])]
    d['action']=[n.branch([n.cond('HAS_KV_ANY',p,b.text(b.SELECT))],[n.branch([n.cmp(b.kv(p,b.SELECT),'>',b.integer(0))],init)])]
    return d

def build(src):
    ui_doc=build_ui(src[b.UI]);select=copy.deepcopy(src[h.SELECT]);n=b.Nodes(BASE+1)
    for part in b.walk(select):
        if part.get('action_type')=='SET_UI_COMP_SIZE'and part['args_list'][1]==ui('hero/portrait'):
            a=part['args_list'];a[2]=b.integer(300);a[3]=b.integer(round(a[3]['args_list'][0]*300/170))
    details=next(z for z in select['action']if z.get('action_type')=='IF_THEN_ELSE')['args_list'][1]['args_list']
    details.append(n.call(FID,b.ref('PLAYER','执行玩家'),b.integer(0)))
    trigger=copy.deepcopy(src[b.OLD]);p=b.ex(100025,'TRIGGER_PLAYER')
    # Existing normal-attack and support dialogs remain reachable without stale overlay.
    for sid in [b.TID+121,b.TID+122,b.TID+123,h.NTID+2]:
        trigger['sub_trigger'][str(sid)]['action'].insert(0,n.vis(p,b.uid(EXTRA),False))
    for i in range(1,8):
        sid=BASE+100+i;n=b.Nodes(sid);assert str(sid)not in trigger['sub_trigger']
        trigger['sub_trigger'][str(sid)]=dict(action=[n.call(FID,p,b.integer(i))],condition=[],enabled=False,call_enabled=True,valid=True,
            is_conf=True,p_trigger_id=trigger['trigger_id'],group_id=0,trigger_id=sid,trigger_name='英雄全览-'+str(i),var_data=[{},{},[]],
            event=[n.node('event_type','TRIGGER_COMPONENT_EVENT',b.lit(100067,EVENT+str(i)))])
        trigger['action'].append(sid)
    index=copy.deepcopy(src[b.FI]);assert NAME+'.json'not in index;index[NAME+'.json']=max(index.values())+1
    return{b.UI:ui_doc,h.SELECT:select,b.OLD:trigger,FN:make_function(src[h.SELECT]),b.FI:index}

def inputs():
    paths=[b.UI,h.SELECT,b.OLD,b.FI,SKILLS,CORES,DESC,LANG,b.HD,b.FD+b.NAMES[1]+'.json']
    for p in(PROJECT/MAP/'tables').glob('*.json'):
        if b.load(p).get('tid')==b.TABLE:paths.append(p.relative_to(PROJECT).as_posix())
    rows=b.load(PROJECT/SKILLS)['table_data']['data']
    for row in rows[2:]:
        if not row or not row[0]:continue
        paths.append(MAP+'editor_table/editorunit/'+str(row[1])+'.json')
        for slot in SLOTS:
            sid=int(row[slot+1]or 0)
            if sid not in [0,EMPTY]:paths.append(MAP+'editor_table/abilityall/'+str(sid)+'.json')
    for r in b.load(PROJECT/CORES)['table_data']['data'][2:]:
        if r and r[0]and r[1]:paths.append(MAP+'editor_table/modifierall/'+str(r[1])+'.json')
    return list(dict.fromkeys(p for p in paths if(PROJECT/p).exists()))

def stage():
    """Retired after closeout; never publish a historical stage again."""
    retired_publish()
def publish():
    """Retired after closeout; never publish a historical stage again."""
    retired_publish()
def repair_none_stage():
    """Retired after closeout; never publish a historical stage again."""
    retired_publish()
if __name__=='__main__':
    args=argparse.ArgumentParser();args.add_argument('mode',choices=['stage','publish','repair-none-stage']);mode=args.parse_args().mode
    if mode=='stage':stage()
    elif mode=='repair-none-stage':repair_none_stage()
    else:publish()
