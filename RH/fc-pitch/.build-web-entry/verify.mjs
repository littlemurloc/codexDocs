import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire('D:/codex/RH/fc-pitch/.build-v5/run.mjs');
const {PresentationFile,FileBlob}=require('@oai/artifact-tool');
const {GlobalFonts,createCanvas,loadImage}=require('@napi-rs/canvas');
GlobalFonts.registerFromPath('C:/Windows/Fonts/msyh.ttc','Microsoft YaHei');
const root='D:/codex/RH/fc-pitch',tmp=root+'/.build-web-entry';
const p=await PresentationFile.importPptx(await FileBlob.load(root+'/output/羊名立万-提案与网页体验/FC mobile-羊名立万-含网页体验.pptx'));
if(p.slides.items.length!==24)throw Error('Wrong count');
await fs.mkdir(tmp+'/final-render',{recursive:true});
const pixels=async file=>{const im=await loadImage(file),c=createCanvas(im.width,im.height),ctx=c.getContext('2d');ctx.drawImage(im,0,0);return Buffer.from(ctx.getImageData(0,0,im.width,im.height).data);};
for(let i=0;i<24;i++){
 const stem='slide-'+String(i+1).padStart(2,'0'),dest=tmp+'/final-render/'+stem+'.png';
 await fs.writeFile(dest,new Uint8Array(await(await p.export({slide:p.slides.items[i],format:'png',scale:1})).arrayBuffer()));
 const a=await pixels(dest),b=await pixels(tmp+'/render/'+stem+'.png');
 if(!a.equals(b))throw Error('Roundtrip render changed on '+(i+1));
 if(i!==18){
  const old=await pixels(root+'/.build-spring/final-render/slide-'+String(i<18?i+1:i).padStart(2,'0')+'.png');
  for(let y=0;y<720;y++)for(let x=0;x<1280;x++){if(x>=1150&&y>=660)continue;const n=(y*1280+x)*4;if(a[n]!==old[n]||a[n+1]!==old[n+1]||a[n+2]!==old[n+2]||a[n+3]!==old[n+3])throw Error('Unexpected retained page change '+(i+1));}
 }
}
await fs.writeFile(tmp+'/final-inspect.ndjson',(await p.inspect({select:'$.slides[*]',include:['id','index','title','elements.text','notes.text']})).ndjson);
console.log('PASS: 24 final renders match previews; all 23 retained pages unchanged except page numbers.');
