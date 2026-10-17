import fs from 'node:fs/promises';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {GlobalFonts,createCanvas,loadImage}=require('@napi-rs/canvas');
GlobalFonts.registerFromPath('C:/Windows/Fonts/msyh.ttc','Microsoft YaHei');
const root='D:/codex/RH/fc-pitch',tmp=root+'/.build-v5';
const finalPath=root+'/output/FC mobile-赛季活动合作提案-v5-模块框架版.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(finalPath));
const tree=p.slides.items[4];
const labels=tree.shapes.items.filter(s=>s.name?.startsWith('module-label-'));
const leaves=tree.shapes.items.filter(s=>s.name?.startsWith('module-leaf-'));
const edges=tree.shapes.items.filter(s=>s.geometry==='line');
if(labels.length!==6||leaves.length!==12||edges.length!==32||tree.images.items.length!==0)throw Error('Editable tree structure did not survive PPTX export.');
await fs.mkdir(tmp+'/final-render',{recursive:true});
const pixels=async file=>{const im=await loadImage(file),c=createCanvas(im.width,im.height),ctx=c.getContext('2d');ctx.drawImage(im,0,0);return Buffer.from(ctx.getImageData(0,0,im.width,im.height).data);};
const results=[];
for(let i=0;i<p.slides.items.length;i++){
 const stem='slide-'+String(i+1).padStart(2,'0');
 const png=await p.export({slide:p.slides.items[i],format:'png',scale:1});
 const dest=tmp+'/final-render/'+stem+'.png';await fs.writeFile(dest,new Uint8Array(await png.arrayBuffer()));
 const a=await pixels(tmp+'/render/'+stem+'.png'),b=await pixels(dest);
 const same=a.equals(b);results.push({slide:i+1,pixelsIdentical:same});
 if(!same)throw Error('Unexpected final render difference on slide '+(i+1));
 if(![1,2,3,4,5].includes(i)){
  const sourcePixels=await pixels(root+'/.build-v4/final-render/'+stem+'.png');
  if(!b.equals(sourcePixels))throw Error('Unexpected change to retained slide '+(i+1));
 }
}
await fs.writeFile(tmp+'/visual-parity.json',JSON.stringify(results,null,2));
console.log('Final PPTX: '+p.slides.items.length+' slides; all reimported renders identical to inspected previews.');
