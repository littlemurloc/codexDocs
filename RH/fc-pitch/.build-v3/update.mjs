import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {GlobalFonts}=require('@napi-rs/canvas');
GlobalFonts.registerFromPath('C:/Windows/Fonts/msyh.ttc','Microsoft YaHei');
const root='D:/codex/RH/fc-pitch',tmp=root+'/.build-v3';
const source=root+'/output/FC mobile-赛季活动合作提案-v2-研究增强版.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const src=[...p.slides.items];
const F='Microsoft YaHei',C={bg:'#09141E',white:'#EDF4F8',body:'#ACBDC9',cyan:'#7CE1E9',gold:'#EDC985',muted:'#74909F'};
const text=(s,name,value,x,y,w,h,size=26,color=C.body,bold=false)=>{
 const o=s.shapes.add({name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 o.text=value;o.text.style={typeface:F,fontSize:size,color,bold,alignment:'left',verticalAlignment:'top',autoFit:'none',insets:0,wrap:'square'};return o;
};
const page=(title,lead='')=>{
 const s=p.slides.add({layoutId:src[1].layoutId});s.background.fill=C.bg;
 text(s,'slide-title',title,72,52,1136,72,44,C.white,true);
 if(lead)text(s,'lead',lead,72,132,1136,68,25);
 text(s,'page-number','00',1170,675,40,25,16,'#537180');return s;
};
const get=(s,n)=>s.shapes.items.find(o=>o.name===n);
const set=(s,n,v)=>{const o=get(s,n);if(o)o.text=v;};
const foot=(s,v)=>text(s,'source-footer',v,76,638,1100,30,18,C.muted);
const canonical=(prefix,id)=>id.startsWith(prefix+'/')?id:prefix+'/'+id;
const img=async(s,f,x,y,w,h,alt)=>s.images.add({blob:await fs.readFile(root+'/.build-v2/assets/'+f),contentType:'image/jpeg',position:{left:x,top:y,width:w,height:h},fit:'contain',alt});

const cover=src[0];
set(cover,'cover-subtitle','从哈兰德主题开始，合作完成一期赛季活动');

const evidence=page('我们研究了 FC 已有的活动','年度最佳和欧冠荣耀，展示了两种不同的参与体验。');
await img(evidence,'toty-overview.jpg',72,214,550,250,'25年度最佳官方活动首页，来源[A]');
await img(evidence,'ucl-finals.jpg',658,214,550,250,'欧冠荣耀冠军巡礼官方界面，来源[D]');
text(evidence,'example-a','年度最佳',76,482,535,43,29,C.white,true);
text(evidence,'example-a-body','每天积累代币，沿奖励路径\n解锁拼图与球员交换。',76,536,540,76,24);
text(evidence,'example-d','欧冠荣耀',662,482,535,43,29,C.white,true);
text(evidence,'example-d-body','重踢经典决赛，赢得球员，\n解锁特价交换。',662,536,540,76,24);
foot(evidence,'官方界面及规则：EA SPORTS 2025.01.26 [A]、FC足球世界 2026.04.15 [D]。');
evidence.speakerNotes.text='这一页以两个官方活动为例说明观察依据。年度最佳的日常代币推进奖励路径，路径节点产出票券，票券用于拼图，累计完成拼图解锁球员特惠交换。欧冠荣耀的冠军巡礼重现决赛赛事，完成后可获得球员奖励并解锁特价交换。主题可以影响参与方式，球员获取则连接各章节。这是设计归纳，不代表内部效果结论。完整四样本对照见附录。\n\n'+src[2].speakerNotes.text+'\n\n'+src[4].speakerNotes.text;

const rhythm=page('玩家熟悉的活动节奏','主题可以变化，参与、推进和领奖需要让玩家看得明白。');
const steps=[
 ['01','被主题吸引','球星、荣誉\n或现实赛事'],
 ['02','每天参与','比赛与任务\n获得活动资源'],
 ['03','看见进度','路径、拼图\n或累计挑战'],
 ['04','拿到球员','领取奖励\n兑换或交换'],
 ['05','补强球队','阵容成长\n与球员收集']
];
steps.forEach(([n,a,b],i)=>{const x=76+i*231;text(rhythm,'step-number-'+i,n,x,242,194,72,54,C.gold,true);text(rhythm,'step-title-'+i,a,x,348,209,56,29,C.white,true);text(rhythm,'step-body-'+i,b,x,431,207,98,25);});
text(rhythm,'design-position','我们的设计重点：让每期主题带来值得参与的比赛和阶段目标。',76,570,1120,52,29,C.cyan,true);
foot(rhythm,'基于公开样本的归纳。各模块可以并行，具体玩法和顺序随活动变化。');
rhythm.speakerNotes.text='用玩家经历说明共同框架，避免将所有活动归为固定线性流程。官方样本的完整对照与来源见附录。设计重点是本提案的主张，尚需FC团队的系统能力与奖励规则评审，不是对现有活动效果的评价。\n\n'+src[6].speakerNotes.text;

const haaland=src[11];
set(haaland,'case-label','原创赛季提案');
set(haaland,'case-promise','跟随一名中锋，从训练走到冠军决战。');
set(haaland,'case-chapters','练习终结，寻找搭档。\n在每周挑战中推进金靴征程，\n最终赢得赛季版哈兰德。');
set(haaland,'case-caveat','原创概念，按六周活动设想。主题视觉为AI生成。');
text(haaland,'page-number','04',1170,675,40,25,16,'#537180');

const gameplay=page('最佳搭档：怎样为哈兰德创造机会','玩家选择进攻路线，完成对应的主题任务。');
const routes=[['地面直塞','接应队友的穿透传球，\n完成单刀破门。'],['边路传中','从边路创造机会，\n在禁区完成抢点。'],['前场压迫','夺回球权，\n在对方重组防线前射门。']];
routes.forEach(([a,b],i)=>{const x=76+i*391;text(gameplay,'route-title-'+i,a,x,267,355,59,36,C.cyan,true);text(gameplay,'route-task-'+i,b,x,363,351,114,27,C.white);});
text(gameplay,'reward-link','比赛所得推动金靴征程，逐步解锁球员奖励。',76,558,1120,52,30,C.white,true);
foot(gameplay,'玩法提案。当前网页原型展示路线选择与奖励结算，具体比赛任务仍需制作。');
gameplay.speakerNotes.text='三条路线来自已有原创方案与网页原型。这里为每条路线补充易理解的任务方向，帮助评审球星特色是否落实到比赛体验。正式设计需要进一步确定关卡条件、次数、难度、重复参与规则及产出。当前原型选择路线不会自动加载不同足球比赛，比赛部分采用简化结果结算，不可表述为全部玩法已实现。';

const prototype=src[14];
set(prototype,'slide-title','核心流程已有可试玩样板');
set(prototype,'lead','可以现场走一遍训练、路线选择和领奖。');
set(prototype,'prototype-caveat','离线原型为简化演示，完整比赛与六周内容仍需制作。');

const calendar=page('六周活动，逐步走向冠军之夜','每个阶段都有新的比赛目标，最后留出完成奖励的时间。');
text(calendar,'calendar-message','从日常训练，\n走到冠军决战。',76,258,515,150,51,C.white,true);
text(calendar,'calendar-context','整期围绕同一名球星展开，\n逐步增加配合与比赛挑战。',78,467,500,100,27);
const weeks=[['第1至2周','练习终结，熟悉主题比赛'],['第3至4周','选择搭档，迎接进阶挑战'],['第5周','参加冠军之夜，冲击核心球员'],['第6周','完成剩余目标与收藏']];
weeks.forEach(([a,b],i)=>{const y=230+i*98;text(calendar,'week-'+i,a,659,y,530,37,25,C.gold,true);text(calendar,'week-goal-'+i,b,659,y+44,540,52,26,C.white);});
foot(calendar,'六周为方案假设，开放时间与奖励进度需结合制作安排及投放确认。');
calendar.speakerNotes.text=src[13].speakerNotes.text+'\n\n此页说明活动运行节奏。项目工期还包括前期设计、开发与美术接入和复盘，不能用六周代替项目总工期。';

const scope=page('我们希望承担的工作');
text(scope,'scope-statement','把一个赛季主题，\n做成完整的活动设计。',76,233,540,165,51,C.white,true);
text(scope,'scope-intro','交到制作团队手中时，\n玩法和实现要求都足够清楚。',78,457,530,103,27);
const deliverables=[['玩法内容','章节、关卡与每日任务'],['奖励设计','产出、消耗与球员获取进度'],['活动页面','操作流程、原型与文案'],['更新安排','开放日历、素材与制作需求']];
deliverables.forEach(([a,b],i)=>{const y=222+i*99;text(scope,'scope-title-'+i,a,665,y,525,42,29,C.cyan,true);text(scope,'scope-desc-'+i,b,665,y+46,535,48,25,C.white);});
foot(scope,'FC团队确认球员投放、系统改动与上线安排。具体分工见附录。');
scope.speakerNotes.text='拟承担活动内容设计，从主题提案到完整制作材料，并配合接入与修订。规则和数值必须对齐FC团队经济约束，系统功能和版本发布由FC团队决定。当前不是交付完成声明，也不承诺未经人员产能核实的范围。\n\n'+src[9].speakerNotes.text;

const pilot=page('先合作一期','用一次完整交付，确认设计方向和合作方式是否合适。');
text(pilot,'design-check','制作方能否照着做',76,280,530,60,34,C.cyan,true);
text(pilot,'design-body','规则、配置和界面状态讲清楚\n开发与美术的工作量提前确认',78,385,530,125,27,C.white);
text(pilot,'play-check','玩家能否顺畅地玩',665,280,530,60,34,C.cyan,true);
text(pilot,'play-body','检查参与、领奖与目标达成情况\n结合历史同类活动完成复盘',667,385,530,125,27,C.white);
foot(pilot,'试点范围、排期与验收标准，双方在启动前约定。');
pilot.speakerNotes.text='试点同时评估交付完整性和线上体验。参与、达成与资源分布等指标需要先确认口径和历史参照，不能把所有波动归因于设计合作。未经真实基线与对照，不承诺留存或收入提升百分比。具体效果评估可以在试点简报中约定，无需在初次pitch中铺陈全部指标。\n\n'+src[17].speakerNotes.text;

const close=page('下一步：选定一个赛季主题');
text(close,'closing-statement','以哈兰德方案为起点，\n一起确定首期合作范围。',76,228,1120,169,55,C.white,true);
text(close,'closing-action','确认可用系统与奖励边界后，\n提交内容清单、排期和报价。',80,464,1100,113,30,C.cyan,true);
foot(close,'合作讨论稿。团队履历与人员配置需在正式提交前补齐。');
close.speakerNotes.text='请求与FC团队活动策划、产品和开发负责人对齐试点主题、可用活动系统及奖励限制。随后才能给出具体内容清单、排期和报价。团队履历、配置和实际产能必须补充真实资料，当前原型不能代替履约证明。';

const compare=src[5], responsibilities=src[9], sources=src[19];
set(compare,'slide-title','附录：四个活动的对照');
set(compare,'lead','供需要进一步了解研究依据的读者查阅。');
set(responsibilities,'slide-title','附录：合作分工');
set(responsibilities,'lead','具体分工随首期项目范围确认。');
set(sources,'slide-title','附录：资料来源');
set(sources,'lead','官方事实与图片来源。原创提案和样本归纳在相关页面注明。');
const order=[cover,evidence,rhythm,haaland,gameplay,prototype,calendar,scope,pilot,close,compare,responsibilities,sources];
const retained=new Set(order.map(s=>s.id));
p.slides.keep(p.slides.items.map((s,i)=>retained.has(s.id)?i:-1).filter(i=>i>=0));
p.slides.reorder(order.map(s=>canonical('sl',s.id)));
for(let i=0;i<order.length;i++){const o=get(order[i],'page-number');if(o)o.text=i<10?String(i+1).padStart(2,'0'):'A'+String(i-9);}
await fs.mkdir(tmp+'/render',{recursive:true});
for(let i=0;i<order.length;i++){
 const s=order[i],stem='slide-'+String(i+1).padStart(2,'0');
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(tmp+'/render/'+stem+'.png',new Uint8Array(await png.arrayBuffer()));
 await fs.writeFile(tmp+'/render/'+stem+'.layout.json',await (await s.export({format:'layout'})).text());
 console.log('Rendered',i+1);
}
await (await PresentationFile.exportPptx(p)).save(tmp+'/candidate.pptx');
await fs.writeFile(tmp+'/font-policy.json',JSON.stringify({basis:'reference',families:[F],referencePath:source,referenceSha256:crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex')}));
await fs.writeFile(tmp+'/content.ndjson',(await p.inspect({select:'$.slides[*]',include:['id','index','title','elements.text','notes.text']})).ndjson);
console.log('Candidate: 10 main slides + 3 appendix slides');
