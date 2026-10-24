import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire('D:/codex/RH/fc-pitch/.build-v5/run.mjs');
const {PresentationFile,FileBlob}=require('@oai/artifact-tool');
const {GlobalFonts}=require('@napi-rs/canvas');
GlobalFonts.registerFromPath('C:/Windows/Fonts/msyh.ttc','Microsoft YaHei');
const root='D:/codex/RH/fc-pitch',tmp=root+'/.build-web-entry';
const source=root+'/output/FC mobile-羊名立万春节活动案例版.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const src=[...p.slides.items],F='Microsoft YaHei',C={bg:'#09141E',white:'#EDF4F8',body:'#ACBDC9',cyan:'#7CE1E9',gold:'#EDC985',muted:'#74909F'};
const text=(s,name,value,x,y,w,h,size=25,color=C.body,bold=false)=>{
 const o=s.shapes.add({name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 o.text=value;o.text.style={typeface:F,fontSize:size,color,bold,alignment:'left',verticalAlignment:'top',autoFit:'none',insets:0,wrap:'square'};return o;
};
const s=p.slides.add({layoutId:src[17].layoutId});s.background.fill=C.bg;
text(s,'slide-title','羊名立万 · 网页体验',72,52,1136,72,44,C.white,true);
text(s,'lead','点击体验入口，走一遍四个活动板块的领取、推进与升级。',72,132,1136,68,25);
s.images.add({blob:await fs.readFile(tmp+'/hero-title.png'),contentType:'image/png',alt:'羊名立万主题字样，来自活动网页原有素材',fit:'contain',position:{left:76,top:229,width:510,height:291}});
text(s,'preview-label','横屏手机交互原型',145,539,415,42,26,C.gold,true);
text(s,'experience-heading','四个板块，均可亲自操作',664,229,544,48,31,C.cyan,true);
text(s,'experience-chapters','新春见面礼、踢出开门红\n拜年有名堂、三羊开泰',664,294,544,86,25,C.white);
const button=s.shapes.add({name:'open-offline-demo',geometry:'rect',position:{left:664,top:406,width:500,height:84},fill:C.gold,line:{fill:C.gold,width:1},borderRadius:6});
button.text=[[{run:'点击开启网页体验',style:{typeface:F,fontSize:'31px',bold:true,color:'#30231E'},link:{uri:'demo.html',isExternal:true}}]];
button.text.style={typeface:F,fontSize:31,bold:true,color:'#30231E',alignment:'center',verticalAlignment:'middle',autoFit:'none',insets:0};
text(s,'browser-instruction','在本地浏览器打开，可离线体验',664,511,544,42,22,C.body);
text(s,'offline-package-note','解压后演示，请将 PPT 与网页保留在同一文件夹。',76,616,1125,34,21,C.body);
text(s,'prototype-note','购买、比赛和发奖均为原型演示。',76,660,1090,28,18,C.muted);
text(s,'page-number','19',1170,675,40,25,16,'#537180');
s.speakerNotes.text='放映模式下点击金色“点击开启网页体验”按钮，在系统浏览器打开同一文件夹的 demo.html。演示无需网络或登录。网页保留用户提供版本的原有素材、文案、人物与活动规则，增加横屏手机展示与日期列表。可体验四个板块，也可通过演示日期与多人比赛查看不同任务状态。购买、比赛和奖励均为本地原型模拟。\n\n配图来源：用户提供的 standalone.html 内嵌主题题字素材。';
const order=[...src.slice(0,18),s,...src.slice(18)];
p.slides.reorder(order.map(o=>o.id.startsWith('sl/')?o.id:'sl/'+o.id));
for(let i=19;i<order.length;i++){for(const sh of order[i].shapes.items){if(/^\d{2}$/.test(sh.text?.toString().trim())&&sh.position.left>1150&&sh.position.top>660)sh.text=String(i+1).padStart(2,'0');}}
await fs.mkdir(tmp+'/render',{recursive:true});
for(let i=0;i<order.length;i++){
 const slide=order[i],stem='slide-'+String(i+1).padStart(2,'0');
 await fs.writeFile(tmp+'/render/'+stem+'.png',new Uint8Array(await(await p.export({slide,format:'png',scale:1})).arrayBuffer()));
 if(i===18)await fs.writeFile(tmp+'/render/'+stem+'.layout.json',await(await slide.export({format:'layout'})).text());
}
await(await PresentationFile.exportPptx(p)).save(tmp+'/draft.pptx');
await fs.writeFile(tmp+'/font-policy.json',JSON.stringify({basis:'reference',families:[F],referencePath:source,referenceSha256:crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex')}));
await fs.writeFile(tmp+'/content.ndjson',(await p.inspect({select:'$.slides[*]',include:['id','index','title','elements.text','notes.text']})).ndjson);
console.log('Created 24 slides; new web experience entry is slide 19, relative text hyperlink demo.html.');
