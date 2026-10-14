from pathlib import Path
import json,re
ROOT=Path(r'D:\littl\testTempFile\ProjectMonster02\maps\map3')
OUT=Path(__file__).resolve().parent
INV=json.loads((OUT/'inventory.json').read_text('utf8'))
REPORT=Path(r'D:\codex\project01\deliverables\军略卡牌功能现状分析报告-2026-10-14.md')
text=REPORT.read_text('utf8')
assert '### 实际文件定位' not in text
def link(rel,needle=None):
    p=ROOT/rel
    assert p.is_file(),p
    suffix=''
    if needle:
        line=next(i for i,s in enumerate(p.read_text('utf8').splitlines(),1) if needle in s)
        suffix=':'+str(line)
    return '['+p.name+'](<'+p.as_posix()+suffix+'>)'
sources=[
 ('正式卡牌表','tables/军令卡牌技能表.json',None),
 ('技能描述表','tables/技能作用描述表.json',None),
 ('购买、替换、选路和演出入口','global_trigger/trigger/关卡初始化内容/universe03.json',None),
 ('战斗卡片与冷却补发','global_trigger/trigger/关卡初始化内容/universe02.json',None),
 ('阶段切换与备战入口','global_trigger/trigger/关卡初始化内容/universe01.json',None),
 ('购买扣款判断','global_trigger/function/new/条件判断/判断是否符合购买军略卡牌条件.json',None),
 ('三格上限统计','global_trigger/function/new/条件判断/判断 军略卡牌是否已达到背包上限.json',None),
 ('随机三个报价','global_trigger/function/new/参数返回/返回【N个军略技能类型】随机卡牌技能池表.json',None),
 ('购买与合成总处理','global_trigger/function/new/功能执行/3选1军略卡牌处理.json',None),
 ('自动结果添加','global_trigger/function/new/功能执行/军略3选1-处理合成的新卡牌.json',None),
 ('旧主动上锁','global_trigger/function/new/功能执行/军略3选1-屏蔽上一级主动卡牌.json',None),
 ('组件折叠','global_trigger/function/new/功能执行/军略3选1-屏蔽已吞噬的卡牌.json',None),
 ('后续 Set 解锁','global_trigger/function/new/功能执行/军略3选1-解锁后续set牌组.json',None),
 ('路线合法目标','global_trigger/function/new/参数返回/返回【合法目标所在方阵编号】上中下路.json',None),
 ('破阵一级系数','ability/134282637.json','0.4'),
 ('火油添加时长/后续移除','ability/134257166.json','10.0'),
 ('灼烧伤害','modifier/134253664.json','APPLY_DAMAGE'),
 ('降攻真实属性','modifier/134256265.json','attack_phy'),
 ('百工真实乘伤','modifier/134235502.json','1.3'),
 ('募卒补员','ability/134220091.json',None),
 ('精兵强军补员','ability/134258455.json',None),
 ('独立卡模板示例','ability/134257459.json',None),
]
text+='\n### 实际文件定位\n\n| 核查项 | 文件入口 |\n| --- | --- |\n'
for name,rel,needle in sources:text+='| '+name+' | '+link(rel,needle)+' |\n'
text+='\n## 附录：正式 Set 与独立卡资源 ID\n\n| Set | 三张组件（名称 / ID） | 自动结果（名称 / ID） |\n| --- | --- | --- |\n'
sets=list(dict.fromkeys(c['set'] for c in INV['cards'] if c['in_formal_pool']))
for s in sets:
    cards=[c for c in INV['cards'] if c['set']==s]
    parts='；'.join(c['name']+' / '+str(c['id']) for c in cards if c['result']=='false')
    result='；'.join(c['name']+' / '+str(c['id']) for c in cards if c['result']=='true')
    text+='| '+s+' | '+parts+' | '+result+' |\n'
text+='\n| 独立卡 | ID | 物编类型 | 状态 |\n| --- | --- | --- | --- |\n'
for c in INV['cards']:
    if not c['in_formal_pool']:
        text+='| '+c['name']+' | '+str(c['id'])+' | '+('主动' if c['cast']==2 else '被动')+' | 资源已建，未入正式市场/描述表，效果为共用模板 |\n'
text+='\n### Buff 支撑索引\n\n以下为 42 个技能的直接引用集合，不把未调用的旧 Buff 也算入已实现内容。\n\n| Buff ID | 名称 |\n| --- | --- |\n'
for b in INV['buffs']:text+='| '+str(b['id'])+' | '+b['name']+' |\n'
assert len(sets)==9 and len(INV['cards'])==42 and len(INV['buffs'])==26
assert all(t['valid'] is True for c in INV['cards'] for t in c['triggers'])
assert sum(len(c['triggers']) for c in INV['cards'])==156
assert sum(c['in_formal_pool'] for c in INV['cards'])==36
assert len([c for c in INV['cards'] if c['in_formal_pool'] and c['cast']==2])==10
REPORT.write_text(text,encoding='utf8')
print(json.dumps({'report':str(REPORT),'characters':len(text),'verified_sources':len(sources),'sets':len(sets),'cards':len(INV['cards'])},ensure_ascii=False))
