import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {GlobalFonts}=require('@napi-rs/canvas');
GlobalFonts.registerFromPath('C:/Windows/Fonts/msyh.ttc','Microsoft YaHei');
const root='D:/codex/RH/fc-pitch',tmp=root+'/.build-v4';
const source=root+'/output/FC mobile-赛季活动合作提案-v3-精简版.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const src=[...p.slides.items];
const F='Microsoft YaHei',C={bg:'#09141E',white:'#EDF4F8',body:'#ACBDC9',cyan:'#7CE1E9',gold:'#EDC985',muted:'#74909F'};
const refs={
 A:'EA SPORTS，2025.01.26，《年度盛典开启！25年度最佳活动全新上线！》\nhttps://www.weibo.com/ttarticle/p/show?id=2309405127089513955762',
 B:'FC足球世界，2026.02.12，《马年春节活动即将开启！多重新春福利送不停！》\nhttps://www.taptap.cn/moment/771064711469861731',
 C:'FC足球世界，2024.06.13，《欧陆足坛风云再起，2024欧洲杯®全员上场！》\nhttps://www.taptap.cn/moment/550263876587881597',
 D:'FC足球世界，2026.04.15，《Next新世代升级，欧冠荣耀活动，巅峰序章队徽开启！首充双倍重置》\nhttps://www.taptap.cn/moment/793578209911245431'
};
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
const note=(s,value,keys)=>{s.speakerNotes.text=value+'\n\n资料来源：\n'+keys.map(k=>'['+k+'] '+refs[k]).join('\n\n');};

// Five pages retain the reasoning without restoring the report-style detail.
const samples=page('我们选了四类活动来比较','先看玩家做什么，再看进度和奖励怎样串起来。');
const sampleRows=[
 ['2024.06','欧洲杯','真实比赛竞猜，让赛程成为参与理由。'],
 ['2025.01','年度最佳','每天推进奖励路径，逐步接近目标球员。'],
 ['2026.02','春节','节日挑战与累计任务，带来福利和球员升级。'],
 ['2026.04','欧冠荣耀','重踢经典赛事，赢取球员和交换资格。']
];
sampleRows.forEach(([date,title,body],i)=>{const y=232+i*91;text(samples,'sample-date-'+i,date,76,y+3,151,41,24,C.gold);text(samples,'sample-title-'+i,title,264,y,268,48,32,C.white,true);text(samples,'sample-desc-'+i,body,580,y+4,626,59,25);});
foot(samples,'国服官方公告样本，时间为公告月份。完整对照与来源见附录。[A–D]');
note(samples,'样本覆盖年度荣誉、真实赛程、节庆和经典赛事四种切入方式，不构成全量历史活动盘点。这里先明确研究范围，后续分别拆解奖励推进与主题玩法，再归纳共性。关于参与理由的表述是设计解读，不是已验证的留存结论。',['A','B','C','D']);

const reward=page('年度最佳怎样把日常参与连到球员目标','五个章节分阶段开放，日常赛事推动路径与拼图。');
await img(reward,'toty-overview.jpg',72,216,550,250,'25年度最佳活动首页，官方原图[A]');
await img(reward,'toty-path.jpg',658,216,550,250,'球员之旅路径节点与拼图票券，官方原图[A]');
text(reward,'overview-caption','首页把五个章节放在一起',76,483,543,49,26,C.white,true);
text(reward,'path-caption','路径节点继续产出拼图票券',662,483,543,49,26,C.white,true);
text(reward,'reward-observation','完成拼图后，再解锁球员特惠交换。',76,556,1120,53,31,C.cyan,true);
foot(reward,'我们的判断：比赛、进度和交换需要一起设计。官方规则与界面：[A]');
note(reward,'官方事实：活动持续42天，共有年度盛典、提名揭秘、传奇之路、拼图挑战和终极年度最佳五个章节。首期开放其中三个。提名揭秘的登录和章节赛事提供章节代币，用来推进球员之旅。路径节点产出拼图票券，累计完成拼图可解锁球员特惠交换。设计归纳：每日行为通过资源和进度连接整期球员目标，因此应一起考虑比赛产出、进度门槛和球员获取。\n图片来源：\nhttps://wx3.sinaimg.cn/large/8764b058gy1hxutzr4qwfj212w0howj2.jpg\nhttps://wx2.sinaimg.cn/large/8764b058gy1hxutzu0bggj212w0hogpp.jpg\n保留官方图片比例和水印。',['A']);

const theme=page('题材也改变了玩家参与的方式','春节加入节日挑战，欧冠让玩家重踢经典比赛。');
await img(theme,'spring-challenge.jpg',76,218,200,367,'福气临门与年兽挑战官方机制说明配图[B]');
text(theme,'spring-title','春节',308,235,310,53,32,C.cyan,true);
text(theme,'spring-facts','累积福气、挑战年兽，\n完成连续任务升级球员。',308,313,310,127,25,C.white);
text(theme,'spring-reading','参与跟着节日节点展开。',308,482,310,93,25,C.gold);
await img(theme,'ucl-finals.jpg',665,219,543,244,'欧冠荣耀冠军巡礼官方实机界面[D]');
text(theme,'ucl-title','欧冠荣耀',669,487,530,49,29,C.cyan,true);
text(theme,'ucl-facts','重踢经典决赛，赢球后\n获得奖励并解锁特价交换。',669,543,530,74,25,C.white);
foot(theme,'官方规则与配图：[B] 2026.02.12、[D] 2026.04.15。左图为机制说明。');
note(theme,'春节事实：每日首次多人对战和每日挑战积累福气值，用于福袋升级及里程碑。年兽挑战包含节庆主题比赛，鸿运叠彩累计14日任务升级球员。部分章节于2月16日开放。欧冠事实：冠军巡礼让玩家参与多个欧冠决赛赛事，获得球员奖励并解锁特价交换。设计解读：主题不仅决定画面，还可以决定比赛内容和开放节点。本页未声称两类设计具备已验证的运营提升。\n左图是官方机制说明图，并非实机截图。\n左图源：https://img2-tc.tapimg.com/moment/etag/33b06e2300097dcd53b8ce0fcad778e1.png/_tap_ugc.jpg\n右图源：https://img2-tc.tapimg.com/moment/etag/b73d126035e15df9b26d710f11a3220e.jpg/_tap_ugc.jpg',['B','D']);

const framework=src[2];
set(framework,'slide-title','这些活动的共同线索');
set(framework,'lead','参与方式各有不同，日常行为都在逐步接近球员与球队目标。');
set(framework,'design-position','日常参与能看见进度，阶段目标最终连接球员获取。');
framework.speakerNotes.text='在具体案例之后，归纳主题入口、每日参与、可见进度、球员获取和球队成长这几项常见职能。这是样本归纳，各模块可以并行，也存在直接奖励球员等分支，不是每期固定的线性流程。下一页再说明它怎样影响原创设计。\n\n'+src[2].speakerNotes.text;

const bridge=page('这些观察怎样影响哈兰德方案','保留清楚的参与和领奖进度，把新意放进比赛内容。');
text(bridge,'observation-label','从案例里看到',76,224,530,44,25,C.body);
text(bridge,'proposal-label','在哈兰德方案里',665,224,530,44,25,C.body);
text(bridge,'observation-one','年度最佳',76,301,530,49,32,C.white,true);
text(bridge,'observation-one-body','日常赛事连接路径、拼图\n和球员交换。',78,366,525,92,26);
text(bridge,'proposal-one','金靴征程',665,301,530,49,32,C.cyan,true);
text(bridge,'proposal-one-body','每次参与都能看见\n距离球员目标的进度。',667,366,525,92,26,C.white);
text(bridge,'observation-two','春节与欧冠',76,485,530,49,32,C.white,true);
text(bridge,'observation-two-body','题材直接决定挑战内容。',78,551,525,53,26);
text(bridge,'proposal-two','训练、搭档与冠军挑战',665,485,540,49,32,C.cyan,true);
text(bridge,'proposal-two-body','围绕创造机会和完成进球设计任务。',667,551,540,75,26,C.white);
foot(bridge,'右侧为原创设计选择，具体关卡与奖励数值需与FC团队确认。');
note(bridge,'本页完成从资料到设计的推导。左侧是对官方机制的简要归纳，右侧为原创方案选择。以年度最佳的进度关系为参考，用金靴征程展示球员目标。以春节与欧冠的主题比赛为参考，把哈兰德的终结与配合写进训练、路线和冠军挑战。并不意味着官方已采用或认可方案，规则和数值还需正式测算，完整关卡也未实现。',['A','B','D']);

const order=[src[0],samples,reward,theme,framework,bridge,...src.slice(3)];
const retained=new Set(order.map(s=>s.id));
p.slides.keep(p.slides.items.map((s,i)=>retained.has(s.id)?i:-1).filter(i=>i>=0));
p.slides.reorder(order.map(s=>canonical('sl',s.id)));
for(let i=0;i<order.length;i++){
 const number=get(order[i],'page-number');if(number)number.text=i<13?String(i+1).padStart(2,'0'):'A'+String(i-12);
}
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
console.log('Candidate: 13 main slides including 5 analysis slides + 3 appendix slides');
