import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {GlobalFonts}=require('@napi-rs/canvas');
GlobalFonts.registerFromPath('C:/Windows/Fonts/msyh.ttc','Microsoft YaHei');
const root='D:/codex/RH/fc-pitch',tmp=root+'/.build-v5';
const source=root+'/output/FC mobile-赛季活动合作提案-v4-五页分析版.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const src=[...p.slides.items],F='Microsoft YaHei';
const C={bg:'#09141E',white:'#EDF4F8',body:'#ACBDC9',cyan:'#7CE1E9',gold:'#EDC985',muted:'#74909F'};
const text=(s,name,value,x,y,w,h,size=26,color=C.body,bold=false)=>{
 const o=s.shapes.add({name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 o.text=value;o.text.style={typeface:F,fontSize:size,color,bold,alignment:'left',verticalAlignment:'top',autoFit:'none',insets:0,wrap:'square'};return o;
};
const page=(title,lead)=>{
 const s=p.slides.add({layoutId:src[4].layoutId});s.background.fill=C.bg;
 text(s,'slide-title',title,72,52,1136,72,44,C.white,true);
 text(s,'lead',lead,72,132,1136,68,25);
 text(s,'page-number','00',1170,675,40,25,16,'#537180');return s;
};
const get=(s,n)=>s.shapes.items.find(o=>o.name===n);
const set=(s,n,v)=>{const o=get(s,n);if(o)o.text=v;};
const foot=(s,v)=>text(s,'source-footer',v,76,638,1100,30,18,C.muted);
const canonical=(prefix,id)=>id.startsWith(prefix+'/')?id:prefix+'/'+id;
const line=(s,name,x,y,w,h)=>s.shapes.add({name,geometry:'line',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'#45636F',width:1.7}});

// The evidence pages now lead to a module taxonomy rather than a player funnel.
set(src[1],'lead','比较各期用了哪些模块，以及这些模块怎样连接。');
set(src[2],'reward-observation','日常参与产出代币，推动进度，再解锁奖励。');
set(src[2],'source-footer','对应模块：主题入口、日常产出、推进机制、奖励获取。官方规则与界面：[A]');
set(src[3],'source-footer','可见的模块变化：主题挑战、累计推进、球员升级。官方规则与配图：[B][D]');

const tree=page('赛季活动设计：模块提纲','主题决定模块的取舍与组合，部分模块可以缺席，也可以并行。');
text(tree,'tree-root','赛季活动\n设计框架',76,372,174,94,32,C.white,true);
line(tree,'root-branch',246,412,36,0);
line(tree,'main-trunk',282,237,0,350);
const modules=[
 ['主题与入口','赛季题材、球星与视觉包装','活动总览与章节入口'],
 ['日常参与与产出','登录、任务、训练与比赛','活动代币、票券与任务进度'],
 ['推进机制','路径、拼图、累计与里程碑','章节目标、挑战与解锁条件'],
 ['奖励获取','直接领奖、代币兑换','条件交换与球员升级'],
 ['成长与收藏','阵容补强与球员养成','图鉴、徽章或队徽'],
 ['开放节奏','每日刷新、每周更新与分期开放','结束时间与兑换安排']
];
modules.forEach(([label,a,b],i)=>{
 const cy=237+i*70;
 line(tree,'module-branch-'+i,282,cy,34,0);
 text(tree,'module-label-'+i,label,334,cy-20,250,43,28,C.cyan,true);
 line(tree,'leaf-link-'+i,590,cy,77,0);
 line(tree,'leaf-trunk-'+i,667,cy-12,0,30);
 line(tree,'leaf-top-'+i,667,cy-12,30,0);
 line(tree,'leaf-bottom-'+i,667,cy+18,30,0);
 text(tree,'module-leaf-'+i+'-a',a,711,cy-27,497,34,23,C.white);
 text(tree,'module-leaf-'+i+'-b',b,711,cy+3,497,34,23,C.body);
});
foot(tree,'按公开样本归纳的常见设计范围。每期按需选配，开放节奏贯穿其他模块。');
tree.speakerNotes.text='这是本提案的主要分析结论：将不同主题活动归纳为可组合的设计模块，而非固定的玩家线性流程。六个主模块下列出常见实现方式，表示设计范围及可选做法，不要求每期齐备。路径、拼图、里程碑可以择一或组合，直接领奖、兑换与条件交换亦可并行。图鉴、徽章、队徽依版本和投放规则选用。开放节奏是贯穿各模块的设计维度。框架来自公开样本归纳，不声称穷尽未来所有创新机制。\n\n'+src[4].speakerNotes.text;

const selection=page('哈兰德方案的模块选择','沿用这套提纲，把本期变化放进中锋主题的任务、比赛和奖励。');
const choices=[
 ['主题与入口','哈兰德锋线征程，球星视觉与章节大厅'],
 ['日常参与与产出','终结训练与主题比赛，获得训练点和搭档徽记'],
 ['推进机制','金靴奖励路径，搭配阶段挑战目标'],
 ['奖励获取','赛季版哈兰德、搭档兑换与阶段奖励'],
 ['成长与收藏','球员入队与养成，收藏内容按版本能力选配'],
 ['开放节奏','六周分阶段开放，第六周完成剩余目标']
];
choices.forEach(([a,b],i)=>{const y=222+i*66;text(selection,'choice-module-'+i,a,76,y,305,45,28,C.cyan,true);text(selection,'choice-detail-'+i,b,443,y+3,765,59,25,C.white);});
foot(selection,'原创方案。具体关卡、奖励数值与成长配置需与FC团队确认。');
selection.speakerNotes.text='用与上一页完全一致的六个模块逐项说明原创方案怎样从框架中选择内容。本页是对框架的应用，并非新增一套机制。训练点、搭档徽记与简化奖励流程已用于网页原型，完整六周关卡、正式经济测算、成长配置和客户端接入仍需制作。\n\n'+src[5].speakerNotes.text;

const order=[...src.slice(0,4),tree,selection,...src.slice(6)];
const retained=new Set(order.map(s=>s.id));
p.slides.keep(p.slides.items.map((s,i)=>retained.has(s.id)?i:-1).filter(i=>i>=0));
p.slides.reorder(order.map(s=>canonical('sl',s.id)));
for(let i=0;i<order.length;i++){const n=get(order[i],'page-number');if(n)n.text=i<13?String(i+1).padStart(2,'0'):'A'+String(i-12);}
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
console.log('16 slides. Editable module tree on slide 5; matching Haaland choices on slide 6.');
