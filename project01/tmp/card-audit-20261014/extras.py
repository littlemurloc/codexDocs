from pathlib import Path
import json
ROOT=Path(r'D:\littl\testTempFile\ProjectMonster02\maps\map3')
OUT=Path(__file__).resolve().parent
INV=json.loads((OUT/'inventory.json').read_text('utf8'))
def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)
for c in INV['cards']:
    if c['name'] in ['连环令','焚舟令']:print(c['name'],c['kv'])
data=json.loads((ROOT/'global_trigger/trigger/关卡初始化内容/universe03.json').read_text('utf8'))
videos=[]
for n in walk(data):
    if n.get('action_type')=='PLAY_UI_VIDEO_COMP':
        val=n['args_list'][-1]['args_list'][0]
        videos.append((val,(ROOT.parent.parent/'custom/Video'/val).exists()))
print('VIDEOS',videos)
samples=[]
for c in INV['cards']:
    if c['set']=='独立':
        p=ROOT/'ability'/(str(c['id'])+'.json')
        d=json.loads(p.read_text('utf8'))
        samples.append({k:{field:v.get(field) for field in ['action','event','condition']} for k,v in d['trigger_dict'].items()})
print('six independent action/event/condition bodies identical:',all(s==samples[0] for s in samples))
extras={'videos':videos,'independent_identical':all(s==samples[0] for s in samples)}
(OUT/'extras.json').write_text(json.dumps(extras,ensure_ascii=False,indent=2),encoding='utf8')
