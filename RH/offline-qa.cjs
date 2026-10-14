const fs=require('node:fs');const vm=require('node:vm');const assert=require('node:assert/strict');const path=require('node:path');
const root='D:/codex/RH/haaland-offline';
const source=fs.readFileSync(path.join(root,'app.js'),'utf8');
const html=fs.readFileSync(path.join(root,'开始演示.html'),'utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(x=>x[1]);
assert.equal(scripts.length,2);for(const script of scripts)new vm.Script(script);
assert(!/<(?:script|link|img)[^>]+(?:src|href)=["'](?:https?:|assets\/|style\.css|app\.js)/i.test(html));
assert(!/@import|fetch\(/.test(html));assert(html.includes("connect-src 'none'"));
assert(html.includes('img-src data: blob:'));
const encodedImage=html.match(/<script type="application\/octet-stream" id="stadiumImage">([A-Za-z0-9+/=]+)<\/script>/)?.[1];
assert(encodedImage,'Missing embedded stadium image');
const imageSource=fs.readFileSync(path.join(root,'assets/haaland-stadium.png'));
assert(Buffer.from(encodedImage,'base64').equals(imageSource),'Embedded image differs from source');
assert(!html.includes('--stadium:url(\'data:'),'Large image must not be stored in a CSS variable');
let imageBytes,cssImageValue;
const imageSetup=scripts[1].slice(scripts[1].indexOf('const imageText'),scripts[1].indexOf('const $'));
vm.runInNewContext(imageSetup,{atob,Uint8Array,document:{getElementById(){return {textContent:encodedImage};},documentElement:{style:{setProperty(name,value){assert.equal(name,'--stadium');cssImageValue=value;}}}},Blob:class{constructor(parts,options){imageBytes=Buffer.from(parts[0]);assert.equal(options.type,'image/png');}},URL:{createObjectURL(){return 'blob:offline-image-check';}}});
assert(imageBytes.equals(imageSource),'Blob decoded image differs from source');assert.equal(cssImageValue,"url('blob:offline-image-check')");assert(cssImageValue.length<200);
for(const font of ['BarlowCondensed-Bold.ttf','NotoSansSC-400.ttf','NotoSansSC-700.ttf','NotoSansSC-900.ttf']){
  const b=fs.readFileSync(path.join(root,'assets/fonts',font));assert.equal(b.readUInt32BE(0),0x00010000);
  const tables=b.readUInt16BE(4);for(let i=0;i<tables;i++){const at=12+i*16;assert(b.readUInt32BE(at+8)+b.readUInt32BE(at+12)<=b.length,`${font} has an incomplete table`);}
}
function harness(blocked=false,backing=new Map()){
  const elements=new Map();let click;
  function element(key){if(!elements.has(key))elements.set(key,{textContent:'',innerHTML:'',hidden:key==='#modalLayer',style:{},classList:{add(){},remove(){},toggle(){},contains(){return false;}},setAttribute(){},addEventListener(){},focus(){},isConnected:true});return elements.get(key);}
  const nav=['overview','training','partners','journey','final'].map(tab=>({...element('nav-'+tab),dataset:{tab}}));
  const dots=[element('dot1'),element('dot2'),element('dot3')];
  const context=vm.createContext({console,window:{},document:{body:element('body'),activeElement:element('focus'),querySelector:element,querySelectorAll:s=>s.includes('chapter-nav')?nav:s==='.shot-dot'?dots:[],addEventListener(type,handler){if(type==='click')click=handler;}},localStorage:{getItem(k){if(blocked)throw Error('Storage blocked');return backing.get(k)||null;},setItem(k,v){if(blocked)throw Error('Storage blocked');backing.set(k,v);},removeItem(k){if(blocked)throw Error('Storage blocked');backing.delete(k);}},setTimeout(fn){fn();return 1;},clearTimeout(){}});
  vm.runInContext(source,context);
  const read=()=>JSON.parse(vm.runInContext('JSON.stringify(state)',context));
  const act=(action,extra={})=>click({target:{closest(){return {dataset:{action,...extra},disabled:false};}}});
  return {read,act,context,backing};
}
for(const blocked of [false,true]){
  const h=harness(blocked);assert.equal(h.read().points,2450);
  h.act('daily');h.act('daily');assert.equal(h.read().points,2500);
  for(const id of [0,1]){h.act('drill',{id:String(id)});for(let i=0;i<3;i++)h.act('shoot');h.act('dismiss');}
  assert.equal(h.read().points,2700);assert.equal(h.read().trained.length,2);
  h.act('claimNode',{id:'1'});h.act('claimNode',{id:'1'});assert.equal(h.read().points,2900);
  h.act('route',{route:'cross'});assert.equal(h.read().route,'cross');
  for(let i=0;i<3;i++){h.act('match');h.act('finishMatch');h.act('dismiss');}
  assert.equal(h.read().points,4400);assert.equal(h.read().matches,3);assert.equal(h.read().tokens,12);
  for(const id of [0,1,2])h.act('claimTask',{id:String(id)});
  assert.equal(h.read().points,4550);h.act('claimNode',{id:'4'});assert(h.read().player);
  h.act('exchange');assert(h.read().partner);assert.equal(h.read().tokens,0);
  if(!blocked){const reloaded=harness(false,h.backing);assert(reloaded.read().player);assert.equal(reloaded.read().points,4550);}
  h.act('resetConfirm');assert.equal(h.read().points,2450);assert(!h.read().player);
}
console.log('PASS: self-contained scripts, no runtime network dependency, complete fonts, reward flow, duplicate protection, exchange, persistence and blocked-storage fallback.');
