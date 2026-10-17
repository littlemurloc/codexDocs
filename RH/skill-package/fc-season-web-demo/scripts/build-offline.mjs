import fs from 'node:fs/promises';
import path from 'node:path';
import vm from 'node:vm';
import {parseArgs,validateConfig,embedJson,withinProject,writeOutput} from './lib.mjs';
try {
  const a=parseArgs(process.argv.slice(2));
  if(a.help){console.log('node build-offline.mjs --project <dir> --out <file.html> [--ready] [--force]');process.exit(0);}
  if(!a.project||!a.out)throw Error('Provide --project and --out');
  const root=path.resolve(a.project),out=path.resolve(a.out);
  if(['index.html','style.css','app.js','theme.json'].some(n=>path.resolve(root,n)===out))throw Error('Output must not overwrite project source');
  const [html,css,app,json]=await Promise.all(['index.html','style.css','app.js','theme.json'].map(n=>fs.readFile(path.join(root,n),'utf8')));
  const c=JSON.parse(json),budget=validateConfig(c,{ready:!!a.ready});new vm.Script(app,{filename:'app.js'});
  if(/@import|url\(\s*(?!["']?(?:data:|blob:|#))/i.test(css))throw Error('CSS has an unresolved URL; embed added assets before packaging');
  if(/<\/style/i.test(css))throw Error('CSS must not contain a closing style tag');
  let imageMarkup='',imageSetup='';
  if(c.heroImage) {
    const file=await withinProject(root,c.heroImage),type={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.gif':'image/gif'}[path.extname(file).toLowerCase()];
    if(!type)throw Error('Supported hero image types: PNG, JPEG, WebP, GIF');
    const bytes=await fs.readFile(file);if(!bytes.length)throw Error('Hero image is empty');
    imageMarkup=`<script id="hero-asset" type="application/octet-stream" data-mime="${type}">${bytes.toString('base64')}</script>`;
    imageSetup=`const raw=atob(document.getElementById('hero-asset').textContent.trim());const bytes=Uint8Array.from(raw,c=>c.charCodeAt(0));const url=URL.createObjectURL(new Blob([bytes],{type:${JSON.stringify(type)}}));document.documentElement.style.setProperty('--hero-image',\`url('\${url}')\`);`;
  }
  const csp="default-src 'none'; img-src data: blob:; font-src data:; media-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'";
  const safeApp=app.replace(/<\/script/gi,'<\\/script');new vm.Script(safeApp,{filename:'embedded-app.js'});
  let final=html.replace('<!--OFFLINE_CSP-->',`<meta http-equiv="Content-Security-Policy" content="${csp}">`).replace('<link rel="stylesheet" href="style.css">',()=>`<style>${css}</style>`).replace('__SEASON_CONFIG__',()=>embedJson(c)).replace('<script defer src="app.js"></script>',()=>`${imageMarkup}<script>${imageSetup}\n${safeApp}</script>`);
  if(final.includes('__SEASON_CONFIG__')||final.includes('<!--OFFLINE_CSP-->'))throw Error('Unresolved template placeholder');
  const scriptTags=[...final.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)];
  for(const [,attrs,body]of scriptTags)if(!/type=["']application\/(?:json|octet-stream)["']/i.test(attrs))new vm.Script(body);
  if(/(?:src|href)\s*=\s*["'](?:https?:|\/\/)|@import|\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b/.test(final))throw Error('Runtime network dependency found');
  await writeOutput(out,final,!!a.force);
  console.log(JSON.stringify({file:out,bytes:Buffer.byteLength(final),embeddedHero:!!c.heroImage,...budget}));
}catch(e){console.error(e.message);process.exitCode=1;}
