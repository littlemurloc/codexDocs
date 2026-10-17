import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {parseArgs} from './lib.mjs';
try {
  const a=parseArgs(process.argv.slice(2));
  if(a.help){console.log('node create-demo.mjs --theme "主题" --out <new-project-dir>');process.exit(0);}
  if(!a.theme||!a.out)throw Error('Provide --theme and --out');
  const out=path.resolve(a.out),template=fileURLToPath(new URL('../assets/frontend-template/',import.meta.url));
  try {if((await fs.readdir(out)).length)throw Error('Output directory must be empty; existing work is never overwritten');}catch(e){if(e.code!=='ENOENT')throw e;}
  await fs.mkdir(out,{recursive:true});
  for(const name of ['index.html','style.css','app.js'])await fs.copyFile(path.join(template,name),path.join(out,name),fs.constants.COPYFILE_EXCL);
  const c=JSON.parse(await fs.readFile(path.join(template,'theme.json'),'utf8'));
  c.id='season-'+crypto.createHash('sha256').update(a.theme+'\n'+out).digest('hex').slice(0,14);
  c.theme=a.theme;c.title=a.theme+' · 赛季征程';c.corePlayer=a.theme;c.heroCopy='从今日挑战开始，朝本期球员目标前进。';
  await fs.writeFile(path.join(out,'theme.json'),JSON.stringify(c,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({project:out,stage:c.stage,next:'Complete season-plan.md and adapt theme.json/UI, then build-offline.mjs'}));
} catch(e) {console.error(e.message);process.exitCode=1;}
