import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire('D:/codex/RH/fc-pitch/.build-v5/run.mjs');
const {PresentationFile,FileBlob}=require('@oai/artifact-tool');
const {GlobalFonts,createCanvas,loadImage}=require('@napi-rs/canvas');
GlobalFonts.registerFromPath('C:/Windows/Fonts/msyh.ttc','Microsoft YaHei');
const root='D:/codex/RH/fc-pitch',tmp=root+'/.build-spring';
const source='C:/Users/littl/Downloads/FC mobile.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const src=[...p.slides.items];
const C={bg:'#09141E',white:'#EDF4F8',body:'#ACBDC9',cyan:'#7CE1E9',gold:'#EDC985',muted:'#74909F'};
const F='Microsoft YaHei';
const set=(id,v)=>{p.resolve(id).text=v;};
const text=(s,name,value,x,y,w,h,size=25,color=C.body,bold=false)=>{
 const o=s.shapes.add({name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 o.text=value;o.text.style={typeface:F,fontSize:size,color,bold,alignment:'left',verticalAlignment:'top',autoFit:'none',insets:0,wrap:'square'};return o;
};
const addImage=async(s,n,pos,alt,crop)=>s.images.add({blob:await fs.readFile(tmp+'/doc-assets/image'+n+'.png'),contentType:'image/png',fit:'contain',position:pos,alt,...(crop?{crop}: {})});
const doc=(await fs.readFile(tmp+'/doc-source.txt','utf8')).replace(/\r\n/g,'\n');
const noteSource='资料来源：用户提供《羊名立万_春节活动策划案.docx》。本页为该设计方案的整合，非已上线活动规则。界面来自原方案配图，奖励为占位卡。';
const section=(start,end)=>doc.slice(doc.indexOf(start),end?doc.indexOf(end):undefined);
const intro=section('一、活动定位与结构','二、开放节奏');
const calendar=section('二、开放节奏','新春见面礼\n板块作用');
const gift=section('新春见面礼\n板块作用','四、踢出开门红');
const red=section('四、踢出开门红','五、拜年有名堂');
const star=section('五、拜年有名堂','六、三羊开泰');
const legend=section('六、三羊开泰');

// Keep cover copy and the deck palette. Replace its old case artwork with the supplied theme artwork.
const coverArt=p.resolve('im/s7a1obih');
coverArt.replace({blob:await fs.readFile(tmp+'/doc-assets/image1.png'),contentType:'image/png',fit:'contain',alt:'羊名立万主题字样，裁自用户提供的活动首页'});
coverArt.frame={left:776,top:224,width:432,height:246};
coverArt.crop={left:18/1542,top:112/550,right:(1542-555)/1542,bottom:(550-395)/550};
src[0].speakerNotes.text='主题配图取自用户提供的《羊名立万_春节活动策划案.docx》活动首页。封面提案内容与合作定位沿用原稿。';

// Case opener: reuse source text geometry and replace the old Haaland artwork.
set('sh/gjutor29','羊名立万\n春节活动');
set('sh/y5o7it0r','四个板块并行，福利与比赛各有目标。');
set('sh/z6x8ryhw','新春见面礼    每日福利与日期限定礼\n踢出开门红    比赛累计与红包成长\n拜年有名堂    猜球星、领卡与升级\n三羊开泰        经典战役与球员升级');
set('sh/k769kjih','春节活动设计案例，界面与规则依据所提供策划案');
const themeArt=p.resolve('im/v2hcrydk');
themeArt.replace({blob:await fs.readFile(tmp+'/doc-assets/image1.png'),contentType:'image/png',fit:'contain',alt:'羊名立万春节主题视觉，取自方案活动首页'});
themeArt.frame={left:750,top:196,width:458,height:281};
themeArt.crop={left:18/1542,top:112/550,right:(1542-555)/1542,bottom:(550-395)/550};
src[11].speakerNotes.text=noteSource+'\n\n'+intro;

// Preserve the editable template table and relate the new proposal to the retained framework.
set('sh/t4nyh4v6','羊名立万：活动框架的应用');
set('sh/s3exozel','沿用主题、参与、推进与成长职能，四个板块分别组织玩家目标。');
const mapping=[
 ['框架模块','春节方案的选择','玩家目标'],
 ['主题与入口','四板块顶部导航，\n各自保留进度','按兴趣切换，\n不必依次完成'],
 ['日常参与与推进','每日礼、比赛红包\n与球星竞猜','当天领取福利，\n持续完成累计目标'],
 ['奖励与成长','领卡、参赛、升级\n与群像点亮','获得球员后，\n继续升级与收集'],
 ['开放节奏','日期限定、人物加开\n与战役分期','按节点回访，\n补做范围分别明确']
];
const mt=p.resolve('tb/wjedcbqd');mapping.forEach((r,i)=>r.forEach((v,j)=>mt.cells.set(i,j,v)));
set('sh/qhoryx83','同场比赛符合条件时，可同时推进红包累计与拜年任务。');
src[12].speakerNotes.text=noteSource+'\n\n此页对应前文保留的活动模块框架，说明新方案如何组合模块，不改写前面的历史研究结论。\n\n'+intro;

// The existing schedule table remains an editable native table.
set('sh/32hgjetc','春节活动的开放节奏');
set('sh/i18fa9cr','日期福利带来每日回访，人物与战役按各自节奏持续开放。');
const rhythm=[
 ['板块','开放安排','回访与补做'],
 ['新春见面礼','腊月廿四至正月十四','每天新礼，当天领取\n错过不可补领'],
 ['踢出开门红','除夕至正月十四','每日资格刷新\n累计进度与领奖记录保留'],
 ['拜年有名堂','初一开放两位，此后每两天加一位','十三全部开放\n已开任务可补做到十四'],
 ['三羊开泰','三条路线按相同阶段推进','正式起止日期\n与阶段数量待确认']
];
const rt=p.resolve('tb/knaxcfm1');rhythm.forEach((r,i)=>r.forEach((v,j)=>rt.cells.set(i,j,v)));
// The middle column needs two lines for the longer opening rule.
rt.cells.set(3,1,'初一开放两位\n此后每两天加一位');
set('sh/e50v2ls3','按策划案的农历演示日期说明。正式开放、每日刷新与结束时刻另行确认。');
src[13].speakerNotes.text=noteSource+'\n\n'+calendar;

const buildModule=(title,lead,num)=>{
 const s=p.slides.add({layoutId:src[14].layoutId});s.background.fill=C.bg;
 text(s,'slide-title',title,72,52,1136,72,44,C.white,true);
 text(s,'lead',lead,72,132,1136,68,25);
 text(s,'page-number',String(num),1170,675,40,25,16,'#537180');return s;
};
const rule=(s,i,heading,body)=>{
 const y=220+i*101;
 text(s,'rule-heading-'+i,heading,777,y,431,35,26,C.cyan,true);
 text(s,'rule-body-'+i,body,777,y+39,431,63,23,C.white);
};
const foot=(s,value)=>text(s,'source-footer',value,76,643,1100,29,18,C.muted);

// Four short case pages retain the dark canvas, cyan labels and typography of the supplied deck.
const a=buildModule('新春见面礼：每天先领一份福利','每日登录礼与日期限定礼并行，除夕用不同版面突出节日节点。',14);
await addImage(a,1,{left:72,top:219,width:650,height:232},'每日登录礼首页，以及领取前后的独立状态');
await addImage(a,2,{left:72,top:465,width:650,height:171},'除夕奖励排布、已领取、已过期和未来日期状态');
rule(a,0,'两类奖励分别领取','登录礼与日期限定礼\n分别记录，不会互相代领。');
rule(a,1,'当天资格当天使用','每日礼不累积。日期限定礼\n只在对应日期领取。');
rule(a,2,'日期与状态清楚呈现','未来奖励可预览，过去未领\n显示已过期，领取后留标记。');
rule(a,3,'除夕保留特别版面','普通日期并排展示，\n除夕奖励卡分行排列。');
a.speakerNotes.text=noteSource+'\n\n'+gift;

const b=buildModule('踢出开门红：比赛推进两类奖励','比赛攒红包，同一份累计同时用于卡牌奖励与红包成长。',15);
await addImage(b,3,{left:72,top:220,width:650,height:175},'累计奖励卡轨道与独立的每日红包领取状态');
await addImage(b,4,{left:72,top:408,width:650,height:260},'红包累计成长、红包外观及领取后的反馈');
rule(b,0,'比赛完成即可累计','进攻对战、实时对战、经理人\n模式均可参与，不要求获胜。');
rule(b,1,'各模式分别计算首场','首场不再叠加常规场次收益。\n每日资格刷新，累计保留。');
rule(b,2,'领奖不扣累计进度','卡奖励达标后逐项主动领取。\n红包成长沿用同一领奖入口。');
rule(b,3,'满级与领完分别显示','已解锁的成长奖励可一并补领。\n满级不代表所有奖励已领。');
b.speakerNotes.text=noteSource+'\n\n'+red;

const c=buildModule('拜年有名堂：从猜球星到升级收集','球衣与故事提供线索，个人任务完成后回到群像点亮人物。',16);
await addImage(c,5,{left:72,top:220,width:650,height:177},'球衣与故事猜球星、答题弹窗及揭晓后的奖励卡');
await addImage(c,6,{left:72,top:443,width:650,height:109},'群像点亮前后与个人升级兑换前后的状态');
text(c,'state-detail','群像同时承担人物入口与收集进度展示',76,587,648,52,22,C.body);
rule(c,0,'猜中后主动领卡','答错可立即重选。先领取球员，\n再完成对应参赛任务。');
rule(c,1,'参赛后兑换个人升级','不要求首发、获胜或进球。\n同场可满足多名已领球员任务。');
rule(c,2,'兑换后回总览点亮','每名人物只计入一次。\n个人升级与点亮分别记录。');
rule(c,3,'点亮累计换自选升级','从已兑换个人升级的球员中选。\n确认才消耗机会，不扣点亮数。');
c.speakerNotes.text=noteSource+'\n\n'+star;

const d=buildModule('三羊开泰：三位球星的经典战役','贝利、马拉多纳与梅西三条路线并列，用故事连接比赛挑战。',17);
await addImage(d,7,{left:72,top:220,width:650,height:193},'三位球员的获取入口，以及免费领取与FC币购买确认');
await addImage(d,8,{left:72,top:425,width:650,height:216},'贝利经典战役页，以及等待、已兑换和锁定状态');
rule(d,0,'免费与付费入口分开','贝利、马拉多纳免费领取。\n梅西以 FC 币购买，购买前确认。');
rule(d,1,'获取、获胜、兑换分开','获取球员不代替挑战。\n获胜后仍需主动兑换升级。');
rule(d,2,'三条路线同步分期','进入新阶段后，保留此前的\n挑战和兑换记录，不设共同终奖。');
rule(d,3,'正式参与条件另行确认','起止、阶段数、持卡与前阶段\n要求待定，原型顺序仅作演示。');
d.speakerNotes.text=noteSource+'\n\n'+legend;

// Remove only the former Haaland screenshot page; all research/framework pages remain.
const order=[...src.slice(0,13),a,b,c,d,src[13],...src.slice(15)];
// Update the source-index attribution that referred to the replaced case.
for(const sh of src[15].shapes.items){
 if(sh.text?.toString().includes('事实与图片来自国服官方发布'))sh.text='历史样本来自国服官方发布，春节案例与界面另据所提供策划案。';
}
src[15].speakerNotes.text=src[15].speakerNotes.text.toString().replace('哈兰德视觉为本项目AI生成概念图，网页原型为原创样板。','羊名立万案例与界面来自用户提供的春节活动策划案，奖励卡为占位示意。');
const canonical=(prefix,id)=>id.startsWith(prefix+'/')?id:prefix+'/'+id;
const retained=new Set(order.map(s=>s.id));
p.slides.keep(p.slides.items.map((s,i)=>retained.has(s.id)?i:-1).filter(i=>i>=0));
p.slides.reorder(order.map(s=>canonical('sl',s.id)));

// Align the old six-week pilot assumption with the new case without altering cooperation terms.
const pilot=src[18];
for(const sh of pilot.shapes.items){if(sh.text?.toString().includes('活动运行按6周假设'))sh.text='试点档期与春节开放日历对齐，项目工期另含准备、接入与复盘。';}
pilot.speakerNotes.text=pilot.speakerNotes.text.toString().replace(/6周/g,'春节活动档期').replace(/六周/g,'春节活动档期');
for(let i=0;i<order.length;i++){
 for(const sh of order[i].shapes.items){
  const value=sh.text?.toString().trim();
  if(/^\d{2}$/.test(value)&&sh.position.left>1150&&sh.position.top>660)sh.text=String(i+1).padStart(2,'0');
 }
}
await fs.mkdir(tmp+'/render',{recursive:true});
const unchanged=[];
for(let i=0;i<order.length;i++){
 const s=order[i],stem='slide-'+String(i+1).padStart(2,'0');
 await fs.writeFile(tmp+'/render/'+stem+'.png',new Uint8Array(await(await p.export({slide:s,format:'png',scale:1})).arrayBuffer()));
 await fs.writeFile(tmp+'/render/'+stem+'.layout.json',await(await s.export({format:'layout'})).text());
 if(i>=1&&i<=10){
  const aa=await loadImage(tmp+'/source-render/'+stem+'.png'),bb=await loadImage(tmp+'/render/'+stem+'.png');
  const cc=createCanvas(1280,720),cx=cc.getContext('2d');cx.drawImage(aa,0,0);const before=Buffer.from(cx.getImageData(0,0,1280,720).data);cx.clearRect(0,0,1280,720);cx.drawImage(bb,0,0);const after=Buffer.from(cx.getImageData(0,0,1280,720).data);
  if(!before.equals(after))throw Error('Unintended change on preserved slide '+(i+1));
  unchanged.push(i+1);
 }
 console.log('Rendered',i+1);
}
for(let base=0;base<order.length;base+=6){
 const count=Math.min(6,order.length-base),cv=createCanvas(1280,360*Math.ceil(count/2)),cx=cv.getContext('2d');
 for(let j=0;j<count;j++){cx.drawImage(await loadImage(tmp+'/render/slide-'+String(base+j+1).padStart(2,'0')+'.png'),(j%2)*640,Math.floor(j/2)*360,640,360);}
 await fs.writeFile(tmp+'/sheet-'+String(base+1).padStart(2,'0')+'.png',cv.toBuffer('image/png'));
}
await(await PresentationFile.exportPptx(p)).save(tmp+'/candidate.pptx');
await fs.writeFile(tmp+'/content.ndjson',(await p.inspect({select:'$.slides[*]',include:['id','index','title','elements.text','notes.text']})).ndjson);
await fs.writeFile(tmp+'/font-policy.json',JSON.stringify({basis:'reference',families:[F],referencePath:source,referenceSha256:crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex')}));
await fs.writeFile(tmp+'/preserved-slides.json',JSON.stringify({pixelIdenticalToSource:unchanged,slideCount:order.length},null,2));
console.log('Ready: '+order.length+' slides. Case section: slides 12–18.');
