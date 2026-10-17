import fs from 'node:fs/promises';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';
const root='D:/codex/RH/fc-pitch';
const p=await PresentationFile.importPptx(await FileBlob.load(root+'/output/FC mobile-赛季活动合作提案-v1.pptx'));
await fs.mkdir(root+'/.build/final-render',{recursive:true});
for(let i=0;i<p.slides.items.length;i++){
 const png=await p.export({slide:p.slides.items[i],format:'png',scale:1});
 await fs.writeFile(root+'/.build/final-render/slide-'+String(i+1).padStart(2,'0')+'.png',new Uint8Array(await png.arrayBuffer()));
}
console.log('Final exported PPTX rendered:',p.slides.items.length,'slides');
