import fs from 'node:fs/promises';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {GlobalFonts}=require('@napi-rs/canvas');
GlobalFonts.registerFromPath('C:/Windows/Fonts/msyh.ttc','Microsoft YaHei');
const root='D:/codex/RH/fc-pitch', tmp=root+'/.build-v2';
const p=await PresentationFile.importPptx(await FileBlob.load(root+'/output/FC mobile-赛季活动合作提案-v1.pptx'));
const original=[...p.slides.items];
const F='Microsoft YaHei';
const C={bg:'#09141E',white:'#EDF4F8',body:'#ACBDC9',cyan:'#7CE1E9',gold:'#EDC985',table:'#102331',header:'#193645',muted:'#74909F'};
const refs={
 A:'EA SPORTS，2025-01-26，《年度盛典开启！25年度最佳活动全新上线！》\nhttps://www.weibo.com/ttarticle/p/show?id=2309405127089513955762',
 B:'FC足球世界官方，2026-02-12，《马年春节活动即将开启！多重新春福利送不停！》\nhttps://www.taptap.cn/moment/771064711469861731',
 C:'FC足球世界官方，2024-06-13，《欧陆足坛风云再起，2024欧洲杯®全员上场！》\nhttps://www.taptap.cn/moment/550263876587881597',
 D:'FC足球世界官方，2026-04-15，《Next新世代升级，欧冠荣耀活动，巅峰序章队徽开启！首充双倍重置》\nhttps://www.taptap.cn/moment/793578209911245431'
};
const text=(s,name,value,x,y,w,h,size=26,color=C.body,bold=false)=>{
 const o=s.shapes.add({name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 o.text=value;o.text.style={typeface:F,fontSize:size,color,bold,alignment:'left',verticalAlignment:'top',autoFit:'none',insets:0,wrap:'square'};return o;
};
const page=(title,lead='')=>{
 const s=p.slides.add({layoutId:original[1].layoutId});s.background.fill=C.bg;
 text(s,'slide-title',title,72,52,1136,72,44,C.white,true);
 if(lead)text(s,'lead',lead,72,132,1136,68,25);
 text(s,'page-number','00',1170,675,40,25,16,'#537180');return s;
};
const foot=(s,t)=>text(s,'source-footer',t,76,638,1100,30,18,C.muted);
const notes=(s,t,keys=[])=>{s.speakerNotes.text=t+'\n\n公开资料来源（核对于2026-10-15）：\n'+keys.map(k=>'['+k+'] '+refs[k]).join('\n\n');};
const img=async(s,f,x,y,w,h,alt)=>s.images.add({blob:await fs.readFile(tmp+'/assets/'+f),contentType:'image/jpeg',position:{left:x,top:y,width:w,height:h},fit:'contain',alt});
const table=(s,values,widths,top=214,height=390,size=22.8)=>{
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:72,top,width:1136,height,columnWidths:widths,values});
 t.styleOptions={headerRow:false,bandedRows:false};t.borders.assign({fill:'#294250',width:.7,style:'solid'});
 t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({fill:C.table,textStyle:{typeface:F,fontSize:size,color:C.white},margins:{top:10,bottom:10,left:15,right:15},anchor:'middle'});
 for(let r=0;r<values.length;r++){t.rows[r].height=height/values.length;for(let c=0;c<values[0].length;c++){const cell=t.getCell(r,c);cell.text.style={typeface:F,fontSize:r===0?23:size,color:r===0?C.cyan:C.white,bold:r===0,alignment:'left',verticalAlignment:'middle',insets:{top:9,bottom:9,left:15,right:15}};if(r===0)cell.fill=C.header;}}
 return t;
};
const newIntro=[];
// The research scope precedes any generalization.
{
 const s=page('公开活动研究样本','选取四种主题与机制组合，比较参与、推进、奖励和开放节奏。');
 const rows=[['2024.06','欧洲杯','真实赛事联动','锦标赛、竞猜与主题球员'],['2025.01','年度最佳','年度荣誉','章节、奖励路径与拼图'],['2026.02','马上过足瘾','春节庆典','福气累积、年兽挑战与球员升级'],['2026.04','欧冠荣耀','赛事回顾','问答、决赛重现与票券兑换']];
 rows.forEach(([date,title,type,desc],i)=>{const y=230+i*91;text(s,'date-'+i,date,76,y+3,145,37,23,C.gold);text(s,'sample-'+i,title,248,y,285,43,30,C.white,true);text(s,'type-'+i,type,558,y+1,210,37,25,C.cyan);text(s,'desc-'+i,desc,785,y+3,410,64,23,C.body);});
 foot(s,'研究范围：国服《FC足球世界》官方公告与配图，非全量历史活动盘点。[A–D]');
 notes(s,'四个样本按差异化机制选择，覆盖2024至2026年。时间为公告发布时间，不等同于整期活动起止。只使用国服《FC足球世界》资料，不把国际服FC Mobile或主机版FC的机制混入。公开资料可以确认规则和呈现方式，不能证明留存、收入或制作成本表现。',['A','B','C','D']);newIntro.push(s);
}
{
 const s=page('年度最佳：章节之间存在资源衔接','42天活动分阶段开放，奖励路径产生的票券继续用于拼图。');
 await img(s,'toty-overview.jpg',72,220,550,250,'[A] 25年度最佳官方活动首页，包含五个章节');
 await img(s,'toty-path.jpg',658,220,550,250,'[A] 提名揭秘球员之旅节点与拼图票券奖励');
 text(s,'left-caption','入口组织五个章节，首期开放其中三个',76,489,545,42,23,C.white,true);
 text(s,'right-caption','登录和赛事产出代币，用于推进球员之旅',662,489,550,42,23,C.white,true);
 text(s,'mechanism','路径节点产出票券，拼图累计完成后解锁特惠交换。',76,560,1120,42,27,C.cyan,true);
 foot(s,'官方规则与界面：[A] EA SPORTS，2025.01.26');
 notes(s,'事实：活动持续42天，五章节中三个先开放。提名揭秘的登录和章节赛事提供章节代币，代币用于球员之旅。路径节点提供拼图票券，拼图完成可解锁特惠球员交换。设计解读：资源在章节之间衔接，设计时需要同时检查产出、推进和解锁门槛。不能仅以界面数量估计活动内容量。\n图片原址：\nhttps://wx3.sinaimg.cn/large/8764b058gy1hxutzr4qwfj212w0howj2.jpg\nhttps://wx2.sinaimg.cn/large/8764b058gy1hxutzu0bggj212w0hogpp.jpg\n图为官方文章原图，保留原比例及水印。',['A']);newIntro.push(s);
}
{
 const s=page('春节：累计进度与球员升级并行','节庆主题落实到挑战形式、开放日历和奖励成长。');
 await img(s,'spring-challenge.jpg',76,207,225,412,'[B] 福气临门与年兽挑战官方机制说明图');
 const rows=[['每日参与','首场多人对战与每日挑战积累福气值。'],['阶段目标','升级福袋、领取里程碑，完成年兽挑战。'],['持续成长','鸿运叠彩累计14日任务，交换升级球员。']];
 rows.forEach(([a,b],i)=>{const y=230+i*123;text(s,'spring-label-'+i,a,356,y,830,44,30,C.cyan,true);text(s,'spring-body-'+i,b,356,y+53,830,55,25,C.white);});
 foot(s,'官方规则及机制说明图：[B] 2026.02.12；部分章节于2月16日开放。');
 notes(s,'事实：春节登录福利先上线，福气临门、年兽挑战和鸿运叠彩后续开放。福气累积、年兽挑战与叠彩升级存在关联和并行关系，不是所有玩家必须依次通过的单一路径。鸿运升级球员加入骐骥图鉴并保留原养成等级。设计解读：节庆活动可以用每日累积支撑阶段目标，同时让球员自身成长。左侧是官方机制说明配图，不是游戏实机截图。\n图源：https://img2-tc.tapimg.com/moment/etag/33b06e2300097dcd53b8ce0fcad778e1.png/_tap_ugc.jpg',['B']);newIntro.push(s);
}
{
 const s=page('赛事主题：现实进程与经典比赛两种组织方式','欧洲杯连接当下赛况，欧冠荣耀重现比赛内容。');
 text(s,'euro-title','2024 欧洲杯',76,225,440,52,32,C.cyan,true);
 text(s,'euro-facts','24支参赛队的锦标赛\n点数参与真实比赛竞猜\n球员卡面随登场情况更新',78,300,450,168,25,C.white);
 text(s,'euro-reading','解读：赛事进程可以成为\n回访理由和内容更新依据。',78,521,465,83,24,C.gold);
 await img(s,'ucl-finals.jpg',560,228,648,291,'[D] 欧冠荣耀冠军巡礼官方实机界面');
 text(s,'ucl-caption','2026 欧冠荣耀：完成决赛赛事，获得奖励\n并解锁球员特价交换。',562,538,646,70,25,C.white);
 foot(s,'官方规则：[C] 2024.06.13、[D] 2026.04.15；右图为[D]官方界面。');
 notes(s,'欧洲杯事实：公告包含使用24支参赛队的锦标赛、活动点数参与比赛竞猜，以及甄选球员卡面随实际登场逐步更新。不可由此推断所有欧洲杯活动均采用同一玩法。欧冠荣耀事实：荣耀时刻、冠军巡礼、精彩时刻三章节分别包含对战与问答、决赛赛事、精彩瞬间赛事。冠军巡礼直接奖励球员并解锁特价交换，构成可观察的机制差异。解读：题材可以改变内容生成依据，而不只是改变背景。\n右图源：https://img2-tc.tapimg.com/moment/etag/b73d126035e15df9b26d710f11a3220e.jpg/_tap_ugc.jpg',['C','D']);newIntro.push(s);
}
{
 const s=page('四个样本的机制对照','相同的参与与奖励职能，可以由不同的规则承担。');
 table(s,[['比较维度','年度最佳 [A]','春节 [B]','欧洲杯 [C]','欧冠荣耀 [D]'],['参与行为','登录、赛事\n每周任务','对战、挑战\n节日登录','锦标赛\n比赛竞猜','对战、问答\n主题赛事'],['推进机制','代币路径\n票券拼图','福气里程碑\n累计升级','赛程联动\n赛事推进','问答里程碑\n赛事与任务'],['奖励衔接','球员奖励\n交换资格','福利、球员\n升级交换','球员与\n竞猜奖励','球员、票券\n特价交换'],['节奏依据','分阶段开放\n日常与每周','节日节点\n14日累计','真实赛程\n赛况更新','日常问答\n分章节挑战']],[164,243,243,243,243],214,408,22.8);
 foot(s,'按公告可确认机制摘录。“未列出”不代表活动中不存在。来源：[A–D]');
 notes(s,'对照表是公开公告的选择性摘录，不是完整玩法清单，也不是活动效果比较。欧洲杯的赛事推进来自锦标赛及真实赛况联动，不据此补写代币路径或拼图。春节的球员升级与累计目标可以并行。不同年份的图鉴、徽章或队徽规则也不能视为完全相同。',['A','B','C','D']);newIntro.push(s);
}
{
 const s=page('活动框架：共同职能与可变模块','以下是对样本的归纳，各模块可以并行，并非每期固定的线性流程。');
 const line=(name,x,y,w,h)=>s.shapes.add({name,geometry:'line',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'#45636F',width:2}});
 text(s,'tree-root','赛季活动',76,386,190,56,34,C.white,true);
 line('root-to-trunk',244,409,58,0);line('tree-trunk',302,245,0,328);
 const rows=[['主题与入口','荣誉、赛事或节庆，组织章节导览'],['每日参与','登录、对战、问答与任务，形成资源产出'],['推进与目标','路径、拼图、累计或挑战，支持不同进度'],['奖励与交换','直接奖励、代币兑换或解锁交换资格'],['成长与收集','球员入队，衔接图鉴、徽章或队徽']];
 rows.forEach(([a,b],i)=>{const y=226+i*82;line('branch-'+i,302,y+19,35,0);text(s,'tree-label-'+i,a,355,y,225,44,28,C.cyan,true);text(s,'tree-desc-'+i,b,610,y+3,594,50,24,C.white);});
 foot(s,'归纳自[A–D]。开放节奏贯穿各模块，收集与成长规则随版本变化。');
 notes(s,'本图是我们的设计归纳，不是官方架构图或唯一玩家路径。可观察职能包括主题入口、参与、推进、奖励与成长，但具体机制、顺序和分支不同。部分赛事直接奖励球员，不要求先兑换。图鉴和队徽亦可作为平行目标。新增赛季设计应先选择适合的模块，再明确连接关系与规则边界。',['A','B','C','D']);newIntro.push(s);
}
{
 const s=page('研究对新赛季设计的启示','将观察转化为可评审的设计选择，效果在试点中验证。');
 table(s,[['样本观察','我们的设计判断','对应交付'],['路径、拼图和里程碑\n承担不同推进职能','选择适合主题的推进方式，\n明确每个资源的用途','章节关系、资源流向\n与门槛测算'],['主题能改变比赛内容\n或现实赛事联动方式','让球星特征进入挑战规则，\n形成具体参与体验','关卡目标、比赛条件\n与交互原型'],['分阶段开放与日常累计\n共同组织活动节奏','分别设计每日目标、\n阶段目标与补领安排','内容日历、目标清单\n与异常状态']],[364,410,362],224,370,24);
 foot(s,'本页为基于样本的设计提议，不据公开公告推断留存、收入或成本。');
 notes(s,'左列为跨样本的结构观察，中列和右列是我们的设计判断与拟议交付，不是官方自述或已验证结果。资源衔接见[A]，节庆累计及分期见[B]，主题参与方式见[C][D]。所有设计选择都要经过FC团队的系统能力、奖励经济和制作排期评审。',['A','B','C','D']);newIntro.push(s);
}
const mapping=page('哈兰德方案的设计依据','沿用已识别的活动职能，将变化集中在中锋的参与体验。');
table(mapping,[['研究依据','哈兰德方案选择','评审与验证'],['主题影响挑战内容 [C][D]','训练终结技巧，设计禁区挑战\n与搭档配合任务','球星特色是否落实为\n不同的挑战条件'],['资源衔接推进 [A]','训练与比赛积累赛季资源，\n金靴征程承接阶段奖励','产出、消耗和核心球员\n获取时间是否合理'],['累计与阶段开放 [A][B]','按周开放内容，冠军之夜\n承接整期目标','各阶段内容量、难度\n与回访理由是否明确'],['奖励连接持续成长 [A][B][D]','球员、养成与收藏目标\n采用FC团队认可的规则','经济投放与版本能力\n是否支持设计']],[330,464,342],218,400,23);
foot(mapping,'原创设计假设。禁区猎手、完整周内容和成长配置仍需制作。');
notes(mapping,'此页把研究发现回扣到原创方案，避免将官方活动和哈兰德概念混为一谈。引用仅支持设计依据，不意味着官方采用或认可该方案。训练、最佳搭档和金靴征程在网页中为简化样板，禁区猎手没有独立实现。玩家资源与时间需要正式数值表复核。FC团队最终决定球员投放、图鉴或队徽等成长方式。',['A','B','C','D']);
const appendix=page('附录：公开资料索引','事实与图片来自国服官方发布，归纳与原创设计在相关页面分别标明。');
const sourceRows=[
 ['[A] 年度最佳','EA SPORTS，2025.01.26','https://www.weibo.com/ttarticle/p/show?id=2309405127089513955762'],
 ['[B] 马上过足瘾','FC足球世界，2026.02.12','https://www.taptap.cn/moment/771064711469861731'],
 ['[C] 欧洲杯','FC足球世界，2024.06.13','https://www.taptap.cn/moment/550263876587881597'],
 ['[D] 欧冠荣耀','FC足球世界，2026.04.15','https://www.taptap.cn/moment/793578209911245431']
];
sourceRows.forEach(([a,b,url],i)=>{const y=218+i*99;text(appendix,'ref-label-'+i,a,76,y,355,40,28,C.cyan,true);text(appendix,'ref-date-'+i,b,470,y+4,700,35,22,C.white);text(appendix,'ref-url-'+i,url,78,y+46,1125,34,19,C.body);});
foot(appendix,'资料核对：2026.10.15。详细出处与图片来源亦记录在相关页面备注中。');
notes(appendix,'此索引仅覆盖本次引用样本。页面中的官方截图和机制图均保留原比例，不以AI图替代。哈兰德视觉为本项目AI生成概念图，网页原型为原创样板。公开资料不包含内部运营数据，也不构成全量历史活动审计。',['A','B','C','D']);
// Delete only the old conclusion-first slide, then explicitly order every slide.
p.slides.keep(p.slides.items.map((_,i)=>i).filter(i=>i!==1));
const order=[original[0],...newIntro,...original.slice(2,6),mapping,...original.slice(6),appendix];
p.slides.reorder(order.map(s=>s.id.startsWith('sl/')?s.id:'sl/'+s.id));
for(let i=0;i<p.slides.items.length;i++){
 const s=p.slides.items[i];
 const number=s.shapes.items.find(o=>o.name==='page-number');if(number)number.text=String(i+1).padStart(2,'0');
}
// Make the transition from the evidence section explicit.
const goalLead=original[2].shapes.items.find(o=>o.name==='lead');
if(goalLead)goalLead.text='基于上述研究，拟将活动设计落实为可排期、可制作、可验收的持续交付。';
await fs.mkdir(tmp+'/render',{recursive:true});
console.log('Slide count',p.slides.items.length);
for(let i=0;i<p.slides.items.length;i++){
 const s=p.slides.items[i], stem='slide-'+String(i+1).padStart(2,'0');
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(tmp+'/render/'+stem+'.png',new Uint8Array(await png.arrayBuffer()));
 await fs.writeFile(tmp+'/render/'+stem+'.layout.json',await (await s.export({format:'layout'})).text());
 console.log('Rendered',i+1);
}
await (await PresentationFile.exportPptx(p)).save(tmp+'/candidate.pptx');
await fs.writeFile(tmp+'/font-policy.json',JSON.stringify({basis:'reference',families:[F],referencePath:root+'/output/FC mobile-赛季活动合作提案-v1.pptx',referenceSha256:'ee881a95907af5f8b0d1bc80386d632d117ba6d00b757276820548e66f2486f0'}));
await fs.writeFile(tmp+'/content.ndjson',(await p.inspect({select:'$.slides[*]',include:['id','index','title','elements.text','notes.text']})).ndjson);
console.log('Candidate ready');
