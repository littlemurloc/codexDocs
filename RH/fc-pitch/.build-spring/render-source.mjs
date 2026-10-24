import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire('D:/codex/RH/fc-pitch/.build-v5/run.mjs');
const {PresentationFile,FileBlob}=require('@oai/artifact-tool');
const {GlobalFonts,createCanvas,loadImage}=require('@napi-rs/canvas');
GlobalFonts.registerFromPath('C:/Windows/Fonts/msyh.ttc','Microsoft YaHei');
const tmp='D:/codex/RH/fc-pitch/.build-spring';
const p=await PresentationFile.importPptx(await FileBlob.load('C:/Users/littl/Downloads/FC mobile.pptx'));
await fs.mkdir(tmp+'/source-render',{recursive:true});
await fs.writeFile(tmp+'/source-inspect.ndjson',(await p.inspect({select:'$.slides[*]',include:['id','index','title','layout','elements.id','elements.kind','elements.name','elements.text','elements.position','elements.style','notes.text']})).ndjson);
for(let i=0;i<p.slides.items.length;i++){
 const s=p.slides.items[i],stem='slide-'+String(i+1).padStart(2,'0');
 await fs.writeFile(tmp+'/source-render/'+stem+'.png',new Uint8Array(await (await p.export({slide:s,format:'png',scale:1})).arrayBuffer()));
 await fs.writeFile(tmp+'/source-render/'+stem+'.layout.json',await(await s.export({format:'layout'})).text());
 console.log('Rendered source',i+1);
}
for(let base=0;base<20;base+=5){
 const c=createCanvas(640,360*5),ctx=c.getContext('2d');
 for(let j=0;j<5;j++){const im=await loadImage(tmp+'/source-render/slide-'+String(base+j+1).padStart(2,'0')+'.png');ctx.drawImage(im,0,j*360,640,360);}
 await fs.writeFile(tmp+'/source-sheet-'+(base+1)+'.png',c.toBuffer('image/png'));
}
const ac=createCanvas(1200,Math.ceil(8/2)*350),ax=ac.getContext('2d');ax.fillStyle='#283138';ax.fillRect(0,0,1200,1400);
const assets=await fs.readdir(tmp+'/doc-assets');
for(let i=0;i<assets.length;i++){const im=await loadImage(tmp+'/doc-assets/'+assets[i]);const scale=Math.min(580/im.width,310/im.height);ax.drawImage(im,(i%2)*600,(i>>1)*350+25,im.width*scale,im.height*scale);ax.fillStyle='white';ax.font='18px Arial';ax.fillText(assets[i]+' '+im.width+'x'+im.height,(i%2)*600+5,(i>>1)*350+20);}
await fs.writeFile(tmp+'/doc-assets-sheet.png',ac.toBuffer('image/png'));
