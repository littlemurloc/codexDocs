import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire('D:/codex/RH/fc-pitch/.build-v5/run.mjs');
const {PresentationFile,FileBlob}=require('@oai/artifact-tool');
const {GlobalFonts,createCanvas,loadImage}=require('@napi-rs/canvas');
GlobalFonts.registerFromPath('C:/Windows/Fonts/msyh.ttc','Microsoft YaHei');
const tmp='D:/codex/RH/fc-pitch/.build-spring';
const final='D:/codex/RH/fc-pitch/output/FC mobile-羊名立万春节活动案例版.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(final));
if(p.slides.items.length!==23)throw Error('Wrong slide count');
const data=await p.inspect({select:'$.slides[*]',include:['id','index','title','elements.text','notes.text']});
if(/哈兰德|haaland|金靴征程|冠军之夜|禁区猎手|六周|6周/i.test(data.ndjson))throw Error('Old case remains');
await fs.writeFile(tmp+'/final-content.ndjson',data.ndjson);
const keyRules=['首场不再叠加常规场次收益','答错可以立即重选','不要求对应球员首发、获胜或进球','本板块不另设共同终奖','自选能否重复用于同一名球员，仍待确认','当前原型在结束后默认关闭领取','已开放任务可补做到十四'];
for(const rule of keyRules){if(!data.ndjson.includes(rule))throw Error('Missing rule: '+rule);}
const sources=await fs.readFile(tmp+'/doc-source.txt','utf8');
const paras=sources.split(/\r?\n/).map(s=>s.trimEnd()).filter(s=>s.trim());
const notes=p.slides.items.map(s=>s.speakerNotes.text.toString()).join('\n');
const missing=paras.filter(s=>!notes.includes(s));
if(missing.some(s=>!['羊名立万活动策划案','FC足球世界春节活动'].includes(s)))throw Error('Source paragraphs missing from speaker notes: '+missing.join('\n'));
await fs.mkdir(tmp+'/final-render',{recursive:true});
const pixels=async file=>{const im=await loadImage(file),c=createCanvas(im.width,im.height),ctx=c.getContext('2d');ctx.drawImage(im,0,0);return Buffer.from(ctx.getImageData(0,0,im.width,im.height).data);};
const parity=[];
for(let i=0;i<23;i++){
 const stem='slide-'+String(i+1).padStart(2,'0'),dest=tmp+'/final-render/'+stem+'.png';
 await fs.writeFile(dest,new Uint8Array(await(await p.export({slide:p.slides.items[i],format:'png',scale:1})).arrayBuffer()));
 const a=await pixels(tmp+'/render/'+stem+'.png'),b=await pixels(dest);
 if(!a.equals(b))throw Error('Final render changed on slide '+(i+1));
 parity.push({slide:i+1,pixelsIdentical:true});
}
const record={slideCount:23,caseSlides:[12,13,14,15,16,17,18],sourceParagraphs:paras.length,sourceParagraphsIncludedInNotes:paras.length-missing.length,oldCaseAbsent:true,roundtripParity:parity,bytes:(await fs.stat(final)).size,sha256:crypto.createHash('sha256').update(await fs.readFile(final)).digest('hex')};
await fs.writeFile(tmp+'/final-verification.json',JSON.stringify(record,null,2));
console.log(JSON.stringify({slideCount:23,notesCoverage:(paras.length-missing.length)+'/'+paras.length,oldCaseAbsent:true,all23FinalRendersIdentical:true,bytes:record.bytes,sha256:record.sha256}));
