import fs from 'node:fs/promises';
const s=await fs.readFile('D:/codex/RH/standalone-phone/开始演示-手机版.html','utf8');
const a=JSON.parse(s.match(/const assetData=(\{.*?\});/s)[1]);
for(const key of ['v2/hero-title.png','v3/background-fixed.webp']){
const url=a[key];await fs.writeFile('D:/codex/RH/fc-pitch/.build-web-entry/'+key.split('/').at(-1),Buffer.from(url.split(',')[1],'base64'));
}
