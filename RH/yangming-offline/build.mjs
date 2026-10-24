import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
const css=await fs.readFile(root+'/style.css','utf8'),core=await fs.readFile(root+'/core.js','utf8'),app=await fs.readFile(root+'/app.js','utf8');
let html=await fs.readFile(root+'/index.html','utf8');
const assets={};for(const [key,name]of Object.entries({hero:'festival-background.png',card:'player-card-reference.png',history:'legend-reference.png'})){assets[key]={type:'image/png',data:(await fs.readFile(root+'/assets/'+name)).toString('base64')};}
const boot=`(function(){const assets=JSON.parse(document.getElementById('assetData').textContent);for(const [key,a]of Object.entries(assets)){const bytes=Uint8Array.from(atob(a.data),c=>c.charCodeAt(0));const url=URL.createObjectURL(new Blob([bytes],{type:a.type}));document.documentElement.style.setProperty('--asset-'+key,'url("'+url+'")');}})();`;
html=html.replace('<!-- POLICY -->',`<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">`)
.replace('<link rel="stylesheet" href="style.css">','<style>'+css+'</style>')
.replace('<!-- ASSETS -->','<script type="application/json" id="assetData">'+JSON.stringify(assets)+'</script><script>'+boot+'</script>')
.replace('<script src="core.js"></script><script src="app.js"></script>','<script>'+core+'</script><script>'+app+'</script>');
await fs.writeFile(root+'/开始演示.html',html,'utf8');
console.log('Created 开始演示.html ('+Buffer.byteLength(html)+' bytes), 3 embedded images, no external dependencies.');
