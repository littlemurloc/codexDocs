"""Restore the approved roster/detail composition from the CURRENT map snapshot.

This is a targeted maintenance patch, independent of the earlier whole-page
generator. It retains business handlers, prefab keys, all existing component
identities and troop-cultivation subtrees. Publication is hash guarded.
"""
from __future__ import annotations
import argparse,copy,json,shutil,os
from pathlib import Path
import y3_safezone_inner_pages as b
from safezone_ui_fixtures import retired_publish

ROOT=b.ROOT;PROJECT=b.PROJECT;MAP=b.MAP
WORK=Path(os.environ.get('Y3_HERO_REVIEW_STAGE',str(ROOT/'tmp/hero-detail-restore-20261119')))
SELECT=b.FD+b.NAMES[0]+'.json';OPERATE=b.FD+b.NAMES[1]+'.json'
OUTPUTS=[b.UI,b.ROW,SELECT,OPERATE,b.OLD,b.ROUTE]
TEMPLATE=MAP+'ui/prefab/装备对比界面.json'
EVENT='安全区详情_'
POPUP=b.uid('hero/dialog');PANEL=b.uid('hero/dialog-panel')
NTID=2101119700

def image(name,key,texture,x,y,w,h,cap=(0,0,0,0)):
    z=b.s.image(name,key,texture,x,y,w,h,cap);z['uid']=b.uid(key);z['size_adaptive']=False;return z
def title(name,key,value,x,y,w=270,h=50):
    z=image(name,key,134237694,x,y,w,h,(86,22,86,22))
    z['children']=[b.label('标题',key+'/text',value,w/2,h/2,w-30,h-10,28)]
    return z
def place(n,x,y,w,h):return b.pos(n,x,y,w,h)
def hidden(n):n['visible']=False;return n
def as_layout(n):
    n.update(type=7,comp_type='Layout')
    for k in ['image','cap_insets','is_scale9_enable','size_adaptive']:n.pop(k,None)
    return n
def child(n,name):return b.child(n,name)
def ui(key):return b.u(b.uid(key))
def component_path(p,root,parts):return b.ex(100070,'GET_UI_COMP_BY_PATH',p,root,b.text(parts))
def save_string(p,row,col):return b.ex(100003,'GET_PLAYER_SAVE_TABLE_VALUE_STRING',p,b.lit(100247,16),row,
    op_arg=[b.text(col),None],op_arg_enable=[True,False])
def rule(parent,key,y,w=630):
    b.extra(parent,b.label('分隔线',key,'─'*42,w/2,y,w,12,14,(151,137,103,120)))
def plain_click(name,key,x,y,w,h,evt):
    z=b.button(name,key,'',x,y,w,h,evt);z['touch_scale']=b.tup(1,1)
    for state in ['normal','disabled','suspend','press']:
        z[state+'_picture']=999 if state in ['normal','disabled'] else 134241138
        z[state+'_color']=b.tup(255,255,255,0 if state in ['normal','disabled'] else 100)
        z[state+'_cap_insets']=b.tup(22,12,22,12)
    return z

def build_row(doc):
    d=copy.deepcopy(doc);r=d['data'];n=r['children'][0]
    place(r,230,53,460,106);place(n,230,53,460,106)
    b.skinimg(place(child(n,'bg'),230,53,458,104),134241138,(24,18,24,18))
    place(child(n,'头像裁切'),60,53,84,84)
    info=child(n,'信息');place(info,190,53,180,82)
    name=child(info,'name_bg');place(name,90,41,180,50)
    b.font(place(child(name,'name'),90,25,170,46),30)
    hidden(child(info,'starList'));hidden(child(info,'starsCount'))
    hidden(child(n,'兵种'));hidden(child(n,'选中标记'))
    place(child(n,'详情bt'),230,53,460,106)
    b.font(place(child(n,'上阵状态'),390,53,120,36),24,b.MUTED)
    b.extra(n,b.label('列表星级','hero/row-star','',292,53,80,36,24),True)
    frame=image('整行选中框','hero/row-selected',904162,230,53,460,106,(16,16,16,16))
    frame['visible']=False;b.extra(n,frame,True)
    return d

def build_ui(doc,scroll_template):
    d=copy.deepcopy(doc);body=b.find_uid(d,b.CONTENT);detail=b.find_uid(d,b.DETAIL)
    assert not any(n.get('uid')==POPUP for n in b.walk(d)),'Already restored; use a new maintenance patch'
    # Widths and content blocks follow the approved 1920x1080 reference.
    b.grid(b.find_uid(d,b.GRID),270,410,468,570,460,106)
    left=image('武将列表底板','hero/list-panel',134232249,270,435,500,660,(88,58,88,58))
    left['children']=[title('武将列表标题','hero/list-title','武将列表',180,610)]
    body['children'].insert(0,left)
    place(detail,880,435,680,660)
    bg=child(detail,'bg');b.skinimg(place(bg,340,330,680,660))
    head=child(bg,'headBar');as_layout(place(head,340,510,630,190))
    b.font(place(child(head,'name'),325,150,300,52),40)
    role=child(head,'阵营图标');hidden(role)
    role_text=child(role,'阵营名称');role['children'].remove(role_text);head['children'].append(role_text)
    b.font(place(role_text,320,50,240,34),20,b.MUTED)
    place(child(head,'品质图标'),520,50,38,38)
    portrait=b.newnode('身份肖像裁切','hero/portrait-mask',105,100,170,185)
    portrait.update(clip_enabled=True,clipping_type=1)
    portrait_image=image('所选武将半身像','hero/portrait',None,85,92.5,170,384)
    portrait_image['anchor']=b.tup(.5,.70);portrait['children']=[portrait_image];head['children'].insert(0,portrait)
    detail['children'].append(title('武将详情标题','hero/detail-title','武将详情',170,625))
    b.font(place(b.find_uid(d,b.uid('roster/state')),350,510,290,38),26,b.INK)
    place(b.find_uid(d,b.uid('roster/deploy')),575,510,160,56)
    b.extra(detail,plain_click('带兵与收益入口','hero/support-entry',550,425,200,30,EVENT+'补充'))
    b.extra(b.find_uid(d,b.uid('hero/support-entry')),b.label('文字','hero/support-entry-text','带兵与收益 ›',100,15,190,30,20,b.MUTED))
    hidden(b.find_uid(d,b.uid('roster/skill-hint')))
    # Move existing description/CD widgets into a dialog. Their UIDs are the
    # direct targets of the existing detail function and remain unchanged.
    skills=child(detail,'技能列表');detail['children'].remove(skills)
    attrs=child(detail,'属性加成');detail['children'].remove(attrs)
    popup=b.newnode('武将说明与收益弹窗','hero/dialog',960,540,1920,1080);popup['visible']=False
    shade=b.button('点击背景关闭','hero/dialog-shade','',960,540,1920,1080,EVENT+'关闭背景')
    for state in ['normal','disabled','suspend','press']:
        shade[state+'_picture']=134269414;shade[state+'_color']=b.tup(255,255,255,170)
        shade[state+'_cap_insets']=b.tup(0,0,0,0)
    shade['touch_scale']=b.tup(1,1)
    panel=b.newnode('说明内容','hero/dialog-panel',960,540,960,700)
    panel['swallow_touches']=True
    panel['children']=[image('说明底板','hero/dialog-bg',134232249,480,350,960,700,(88,58,88,58)),
        title('说明标题条','hero/dialog-title-bar','',440,650,760,58),
        b.label('说明标题','hero/dialog-title','',440,650,680,46,30),
        b.label('所选武将','hero/dialog-hero','',200,590,300,38,27),
        b.button('关闭说明','hero/dialog-close','关闭',865,650,110,52,EVENT+'关闭按钮')]
    place(skills,480,320,880,500)
    panel['children'].append(skills)
    for i,skill in enumerate(skills['children'],1):
        place(skill,440,250,880,500);skill['visible']=False
        icon=child(skill,'icon');skill['children'].remove(icon);icon['event_list']=[]
        hidden(child(skill,'技能类型'))
        row=plain_click('技能入口'+str(i),'hero/skill-row/'+str(i),340,365-(i-1)*82,630,72,
                        '安全区内页_技能说明_'+str(i))
        row['children']=[image('技能图标边框','hero/skill-frame/'+str(i),134241138,48,36,72,72,(16,16,16,16)),
                         place(icon,48,36,62,62),
                         b.label('技能类别','hero/skill-label/'+str(i),['主动技能','被动技能','普通攻击'][i-1],230,36,270,40,30),
                         b.label('完整说明入口','hero/skill-read/'+str(i),'查看完整说明',500,36,200,34,23),
                         b.label('箭头','hero/skill-arrow/'+str(i),'›',612,36,28,42,36,(131,107,58,255))]
        rule(row,'hero/skill-rule/'+str(i),0)
        detail['children'].append(row)
        content=child(skill,'content');skill['children'].remove(content)
        markers=[n for n in content.get('children',[])if n.get('name')=='进池标记']
        for marker in markers:
            content['children'].remove(marker);b.font(place(marker,440,24,820,38),20,b.RED);skill['children'].append(marker)
        scroll=copy.deepcopy(scroll_template);scroll.update(uid=b.uid('hero/skill-scroll/'+str(i)),prefab_sub_key=None,
             name='完整技能说明滚动区',children=[content],event_list=[],skip_invisible=True,scroll_bar_enable=True,
             scroll_bar_thickness=6,swallow_touches=True)
        place(scroll,440,285,840,390)
        b.font(place(content,410,450,820,900),24);content.update(alignment=b.tup(1,8),over_pattern=True)
        skill['children'].append(scroll)
        cd=child(skill,'CD');as_layout(place(cd,170,66,300,36))
        for c in cd.get('children',[]):
            b.font(c,22)
            if c['name'].endswith('_1'):place(c,80,18,150,36)
            else:place(c,230,18,140,36)
    # The existing yield section remains available in a secondary dialog.
    place(attrs,480,320,880,500);attrs['visible']=False;panel['children'].append(attrs)
    own=child(attrs,'拥有属性title');place(own,220,280,370,44)
    for c in own.get('children',[]):b.font(place(c,185,22,360,42),26)
    hidden(child(attrs,'title'));place(child(attrs,'starList'),680,280,190,36)
    star_grid=child(child(attrs,'starList'),'grid_view');b.stargrid(star_grid,95,18,190,36,32)
    b.grid(child(attrs,'grid_view'),440,140,820,200,400,46)
    child(attrs,'grid_view')['grid_count']=b.tup(0,2)
    child(attrs,'grid_view')['scroll_bar_enable']=True
    b.extra(attrs,b.label('带兵标题','hero/troop-caption','带领兵种',150,450,240,42,30))
    b.extra(attrs,b.label('当前兵种','hero/current-troop','',580,450,520,38,24,b.MUTED))
    for i,troop in enumerate(['刀兵','弓兵','枪兵','盾兵','骑兵']):
        b.extra(attrs,b.button('选择'+troop,'hero/troop/'+str(i),troop,110+i*160,380,140,60,EVENT+'兵种_'+str(i)))
    popup['children']=[shade,panel];b.find_uid(d,b.s.SAFE_ROOT)['children'].append(popup)
    # Complete, separate upgrade block, driven by actual selected-hero data.
    detail['children'].append(title('武将升星标题','hero/upgrade-title','武将升星',160,142,270,40))
    b.extra(detail,b.label('升星阶段','hero/upgrade-level','',340,100,620,34,26))
    b.extra(detail,image('升星材料图标','hero/material-icon',None,65,52,54,54))
    b.font(place(b.find_uid(d,b.uid('roster/material')),270,52,330,36),24)
    place(b.find_uid(d,b.uid('roster/upgrade')),550,55,180,54)
    b.font(place(b.find_uid(d,b.uid('roster/reason')),550,17,230,22),19)
    # Align adjacent panels/footer without changing the formation index direction.
    formation=b.find_uid(d,'7da52980-11af-4acf-ae4d-6f338b1eb7ba')
    place(formation,1510,435,540,660);b.skinimg(place(child(formation,'bg'),270,330,540,660))
    place(b.find_uid(d,b.uid('roster/formation-title')),270,610,470,44)
    grid=child(formation,'阵型9宫格区域');place(grid,270,355,390,390)
    for i,cell in enumerate(grid['children']):
        x=325-(i//3)*130;y=325-(i%3)*130;place(cell,x,y,130,130)
        frame=child(cell,'frameIMG');place(frame,65,65,120,120)
        place(child(frame,'numIMG'),60,60,108,108)
        place(child(frame,'阵位编号'),60,9,110,18)
    b.font(place(b.find_uid(d,b.uid('roster/formation-hint')),270,85,480,90),21,b.MUTED)
    currency=b.find_uid(d,'f8aa4548-91d6-44f2-b5b4-fd57abfad729');place(currency,640,49,450,70)
    child(currency,'title')['text']=b.tup('招募材料',False)
    right=child(body,'右侧区域');right['children'].append(title('武将招募标题','hero/recruit-title','武将招募',190,49,280,50))
    return d

def rewrite_select(doc,portraits):
    d=copy.deepcopy(doc);n=b.Nodes(NTID);p=b.ref('PLAYER','执行玩家')
    each=b.ex(100070,'FOR_EACH_UI_COMP');row=b.ref('INTEGER','遍历编号')
    chosen=b.ref('INTEGER','有效编号');unit=b.ref('UNIT_NAME','武将类型')
    have=b.ref('INTEGER','材料数量');cost=b.ref('INTEGER','所需数量')
    current=b.ref('UI_COMP','当前行');ins=b.prefab(p,current)
    body=d['action'][1]['args_list'][2]['args_list'][0]['args_list'][1]['args_list']
    body += [n.vis(p,b.pp(b.prefab(p,each),'伙伴元素.整行选中框'),False),
             n.label(p,b.pp(b.prefab(p,each),'伙伴元素.列表星级'),b.join(b.intstr(b.save(p,16,row,'当前升星进度')),'星'))]
    for part in b.walk(body):
        if part.get('action_type')=='SET_UI_COMP_IMAGE_NEW'and '伙伴元素.bg'in str(part['args_list'][1]):part['args_list'][2]=b.lit(100115,134241138)
    details=d['action'][2]['args_list'][1]['args_list']
    for part in b.walk(d):
        if part.get('action_type')=='SET_UI_COMP_VISIBLE'and '伙伴元素.选中标记'in str(part['args_list'][2]):part['args_list'][1]=b.boolean(False)
    d['action'].insert(0,n.vis(p,POPUP,False))
    details += [n.vis(p,b.pp(ins,'伙伴元素.整行选中框'),True),
        n.act('SET_UI_COMP_IMAGE_NEW',p,ui('hero/portrait'),b.ex(100115,'GET_TEXTURE_KV',unit,b.text('头像'))),
        n.act('SET_UI_COMP_SIZE',p,ui('hero/portrait'),b.integer(170),b.integer(384)),
        n.act('SET_UI_COMP_IMAGE_NEW',p,ui('hero/material-icon'),b.ex(100115,'GET_ICON_BY_UNIT_TYPE',unit)),
        n.label(p,ui('hero/dialog-hero'),b.tab('STRING',b.TABLE,chosen,'仆从名称')),
        n.label(p,ui('hero/upgrade-level'),b.join(b.join('当前 '+'' ,b.join(b.intstr(b.save(p,16,chosen,'当前升星进度')),'星  →  ')),
            b.join('下一阶段 ',b.join(b.intstr(b.math(b.save(p,16,chosen,'当前升星进度'),'+',b.integer(1))),'星')))),
        n.label(p,ui('hero/current-troop'),b.join('当前带领：',save_string(p,chosen,'带领兵种')))]
    for unit_id,height in portraits.items():
        details.append(n.branch([n.cmp(unit,'==',b.lit(100116,unit_id),'ANY_COMPARE')],[
            n.act('SET_UI_COMP_SIZE',p,ui('hero/portrait'),b.integer(170),b.integer(height))]))
    for part in b.walk(d):
        if part.get('action_type')=='SET_UI_COMP_TEXT':
            target=part['args_list'][1]
            if target==b.u(b.uid('roster/material')):
                part['args_list'][2]=b.join(b.join(b.tab('STRING',b.TABLE,chosen,'仆从名称'),'材料  '),b.join(b.intstr(have),b.join(' / ',b.intstr(cost))))
            elif target==b.u(b.uid('roster/state')):
                part['args_list'][2]=b.join(b.intstr(b.save(p,16,chosen,'当前升星进度')),'星')
            elif target==b.u(b.uid('roster/reason'))and part['args_list'][2]==b.text('材料充足，可培养'):
                part['args_list'][2]=b.text('材料充足')
    base=b.join(b.intstr(b.save(p,16,chosen,'当前升星进度')),'星  |  ')
    details += [n.branch([b.bcmp(n,b.save(p,16,chosen,'是否解锁','BOOLEAN'),False)],
        [n.label(p,ui('roster/state'),b.join(base,'未解锁'))],
        [n.branch([b.bcmp(n,b.save(p,16,chosen,'是否上阵','BOOLEAN'),True)],
            [n.label(p,ui('roster/state'),b.join(base,'已上阵'))],[n.label(p,ui('roster/state'),b.join(base,'未上阵'))])])]
    # Apply readable typography to original attribute instances in the dialog.
    attrs=next(z for z in b.walk(d)if z.get('action_type')=='ITER_UI_COMP_DO'and z['args_list'][1]==b.u('2a546ba7-95ab-4f6c-9eda-ca6cabdb310f'))
    for path in ['单位属性条目.属性名称','单位属性条目.属性数值']:
        attrs['args_list'][2]['args_list'].append(n.act('SET_UI_COMP_FONT_SIZE',p,b.pp(b.prefab(p,each),path),b.integer(24)))
    return d

def rewrite_operations(doc):
    d=copy.deepcopy(doc);n=b.Nodes(NTID+1);p=b.ref('PLAYER','执行玩家')
    each=b.ex(100070,'FOR_EACH_UI_COMP');row=b.ref('INTEGER','行号');op=b.ref('INTEGER','操作')
    ins=b.prefab(p,each)
    branch=next(z for z in b.walk(d)if z.get('action_type')=='IF_THEN_ELSE'and any(
        c.get('args_list',[None,None,None])[0]==row and '安全区内页_武将编号'in str(c)for c in z['args_list'][0]['args_list']))
    for i,troop in enumerate(['刀兵','弓兵','枪兵','盾兵','骑兵']):
        branch['args_list'][1]['args_list'].append(n.branch([n.cmp(op,'==',b.integer(i+3))],[
            b.event(n,p,b.pp(ins,'伙伴元素.兵种.'+troop),'选中兵种'),
            n.label(p,ui('hero/current-troop'),b.join('当前带领：',save_string(p,row,'带领兵种')))]))
    return d

def rewrite_events(doc,ui_doc):
    d=copy.deepcopy(doc);p=b.ex(100025,'TRIGGER_PLAYER')
    panels=[z['uid']for z in b.find_uid(ui_doc,'e3911e6a-9735-44c6-a3a2-9d33c8a0aeee')['children']]
    attr='fd0111ad-1b15-4c77-b75d-04a280b33ecf'
    def show(n,mode):
        a=[n.vis(p,POPUP,True),n.label(p,ui('hero/dialog-title'),
           ['主动技能 · 完整说明','被动技能 · 完整说明','普通攻击 · 完整说明','带兵与星级收益'][mode-1]),
           n.vis(p,'e3911e6a-9735-44c6-a3a2-9d33c8a0aeee',mode<4),n.vis(p,attr,mode==4)]
        return a+[n.vis(p,key,mode==i)for i,key in enumerate(panels,1)]
    for i in range(1,4):
        sub=d['sub_trigger'][str(b.TID+120+i)];n=b.Nodes(NTID+10+i)
        sub['action']=show(n,i);sub['trigger_name']='武将详情-点击完整说明'+str(i)
    close=d['sub_trigger'][str(b.TID+124)];n=b.Nodes(NTID+14)
    # Hover tooltips were retired, including their UI event declarations.
    # Retaining listeners for those removed event declarations makes this
    # configured trigger invalid on native saving. Retire the old call too.
    close['action']=[n.vis(p,POPUP,False)]
    close['event'] = [n.node('event_type','TRIGGER_COMPONENT_EVENT',b.lit(100067,EVENT+'关闭背景')),
                       n.node('event_type','TRIGGER_COMPONENT_EVENT',b.lit(100067,EVENT+'关闭按钮'))]
    def register(offset,name,events,actions):
        sid=NTID+offset;n=b.Nodes(sid)
        assert str(sid)not in d['sub_trigger']
        d['sub_trigger'][str(sid)]=dict(action=actions(n),condition=[],enabled=False,call_enabled=True,
            valid=True,is_conf=True,p_trigger_id=d['trigger_id'],group_id=0,trigger_id=sid,
            trigger_name=name,var_data=[{},{},[]],event=events(n))
        d['action'].append(sid)
    register(1,'武将详情-Esc关闭说明',lambda n:[n.node('event_type','KEYBOARD_KEY_UP_EVENT',b.lit(200220,1))],
             lambda n:[n.vis(p,POPUP,False)])
    register(2,'武将详情-带兵与收益',lambda n:[n.node('event_type','TRIGGER_COMPONENT_EVENT',b.lit(100067,EVENT+'补充'))],lambda n:show(n,4))
    for i in range(5):
        register(3+i,'武将详情-选择兵种'+str(i),lambda n,i=i:[n.node('event_type','TRIGGER_COMPONENT_EVENT',b.lit(100067,EVENT+'兵种_'+str(i)))],
                 lambda n,i=i:[b.call(n,b.NAMES[1],p,b.integer(i+3))])
    return d

def renumber_new_actions(d,initial_ids,base):
    serial=base*1000000
    for n in b.walk(d):
        if'element_id'in n and n['element_id']not in initial_ids:serial+=1;n['element_id']=serial

def build(src,portraits):
    scroll=next(z for z in b.walk(src[TEMPLATE])if z.get('comp_type')=='ScrollView')
    out={b.UI:build_ui(src[b.UI],scroll),b.ROW:build_row(src[b.ROW]),
         SELECT:rewrite_select(src[SELECT],portraits),OPERATE:rewrite_operations(src[OPERATE])}
    out[b.OLD]=rewrite_events(src[b.OLD],out[b.UI])
    route=copy.deepcopy(src[b.ROUTE]);route['action'].insert(0,b.Nodes(NTID+40).vis(b.ref('PLAYER','执行玩家'),POPUP,False));out[b.ROUTE]=route
    for path,d in out.items():
        if'global_trigger'in path:
            ids={n['element_id']for n in b.walk(src[path])if'element_id'in n}
            renumber_new_actions(d,ids,NTID+50+OUTPUTS.index(path))
    return out

def collect():
    inputs=OUTPUTS+[TEMPLATE,b.HD]
    table=next(p for p in(PROJECT/MAP/'tables').glob('*.json')if b.load(p).get('tid')==b.TABLE)
    inputs.append(table.relative_to(PROJECT).as_posix());rows=b.load(table)['table_data']['data'];mapping={}
    for row in rows[2:]:
        rec=dict(zip(rows[0],row));unit=int(rec['单位类型']);unitfile=MAP+'editor_table/editorunit/'+str(unit)+'.json'
        inputs.append(unitfile);meta=b.load(PROJECT/unitfile);texture=meta.get('kv',{}).get('头像',{}).get('value')
        if texture:
            iconfile='editor_table/editoricon/'+str(texture)+'.json'
            if(PROJECT/iconfile).exists():
                inputs.append(iconfile);size=b.load(PROJECT/iconfile).get('size','').upper().split('X')
                if len(size)==2 and int(size[0])>0:mapping[unit]=round(170*int(size[1])/int(size[0]))
    return list(dict.fromkeys(inputs)),mapping

def stage():
    """Retired after closeout; never publish a historical stage again."""
    retired_publish()
def publish():
    """Retired after closeout; never publish a historical stage again."""
    retired_publish()

def repair_close_stage():
    """Retired after closeout; never publish a historical stage again."""
    retired_publish()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['stage','publish','repair-close-stage']);args=p.parse_args()
    if args.mode=='stage':stage()
    elif args.mode=='repair-close-stage':repair_close_stage()
    else:publish()
