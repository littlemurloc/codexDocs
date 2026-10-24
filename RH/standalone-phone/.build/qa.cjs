const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {parseHTML}=require('D:/codex/RH/haaland-qa/node_modules/linkedom');
const cssTree=require('D:/codex/RH/haaland-qa/node_modules/css-tree');
const dir='D:/codex/RH/standalone-phone',html=fs.readFileSync(dir+'/开始演示-手机版.html','utf8'),source=fs.readFileSync('C:/Users/littl/Downloads/standalone.html','utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
const sourceAssets=JSON.parse(source.match(/const assetData=(\{.*?\});/s)[1]),outputAssets=JSON.parse(html.match(/const assetData=(\{.*?\});/s)[1]);
assert.deepEqual(outputAssets,sourceAssets);assert.equal(Object.keys(sourceAssets).length,34);
assert.equal(html.match(/<style>([\s\S]*?)<\/style>/)[1],source.match(/<style>([\s\S]*?)<\/style>/)[1]);
const originalScript=source.match(/<script>([\s\S]*?)<\/script>/)[1],mainAnchor="(() => {\n  'use strict';\n  const root=document.getElementById('yangnian-login-inline');";
assert.equal(scripts[1].split(mainAnchor)[0],originalScript.split(mainAnchor)[0]);
const errors=[];cssTree.parse(fs.readFileSync(dir+'/phone.css','utf8'),{onParseError:e=>errors.push(e.message)});assert.deepEqual(errors,[]);
assert(!/fetch\(|XMLHttpRequest|WebSocket|@import/.test(scripts.join('')+fs.readFileSync(dir+'/phone.css','utf8')));
function harness({width=1440,height=900,blocked=false,saved=null}={}){
 const {document,window:domWindow}=parseHTML(html);let focused=document.body,phoneScale=1;
 Object.defineProperty(domWindow.HTMLSelectElement.prototype,'value',{configurable:true,get(){return this.querySelector('option[selected]')?.getAttribute('value')||this.querySelector('option')?.getAttribute('value')||'';},set(v){for(const o of this.querySelectorAll('option')){if(o.getAttribute('value')===String(v))o.setAttribute('selected','');else o.removeAttribute('selected');}}});
 const proto=domWindow.HTMLElement.prototype;
 proto.focus=function(){focused=this;};proto.getBoundingClientRect=function(){
  const scale=Number(document.documentElement.style.getPropertyValue('--phone-scale'))||1;
  if(this.id==='login-preview'||this.id==='phoneScreen')return{x:0,y:0,left:0,top:0,width:1248*scale,height:624*scale,right:1248*scale,bottom:624*scale};
  return{x:0,y:0,left:0,top:0,width:100,height:100,right:100,bottom:100};
 };
 Object.defineProperty(proto,'clientWidth',{configurable:true,get(){return ['login-preview','phoneScreen'].includes(this.id)?1248:2160;}});
 Object.defineProperty(proto,'clientHeight',{configurable:true,get(){return this.id==='login-preview'?624:1080;}});
 Object.defineProperty(proto,'offsetLeft',{configurable:true,get(){return Number(this.dataset.greetingIndex||this.dataset.kingsIndex||0)*2160;}});
 proto.scrollTo=function(o){this.scrollLeft=o.left||0;};proto.scrollBy=function(o){this.scrollLeft=(this.scrollLeft||0)+(o.left||0);};
 proto.showModal=function(){this.open=true;this.setAttribute('open','');};proto.close=function(){this.open=false;this.removeAttribute('open');this.dispatchEvent(new domWindow.Event('close'));};
 proto.getClientRects=function(){return[this.getBoundingClientRect()];};
 Object.defineProperty(document,'activeElement',{get(){return focused;}});
 const store=new Map(saved?Object.entries(saved):[]),timers=new Map();let timer=0,blob=0;
 const no=()=>{};
 const sandbox={document,console,Uint8Array,atob,Blob:class{constructor(parts,options){this.parts=parts;this.type=options.type;}},URL:{createObjectURL(){return 'blob:offline-'+(++blob);}},URLSearchParams,location:{search:''},crypto:{randomUUID:()=> 'qa-'+(++timer)},Event:domWindow.Event,CustomEvent:domWindow.CustomEvent,
 innerWidth:width,innerHeight:height,matchMedia:()=>({matches:true,addEventListener:no}),getComputedStyle(el){return new Proxy({getPropertyValue:p=>el.style.getPropertyValue(p),fontSize:'27px',fontFamily:'Microsoft YaHei',fontWeight:'400',lineHeight:'1.5',visibility:'visible',display:'block',translate:'none',scale:'none',transform:'none',overflowX:'visible',overflowY:'visible'},{get(t,k){return t[k]??'none';}});},
 ResizeObserver:class{observe(){}},MutationObserver:class{observe(){}},addEventListener:no,
 localStorage:{getItem(k){if(blocked)throw Error('blocked');return store.get(k)||null;},setItem(k,v){if(blocked)throw Error('blocked');store.set(k,v);},removeItem(k){if(blocked)throw Error('blocked');store.delete(k);}},
 setTimeout(fn,delay){const i=++timer;timers.set(i,{fn,delay});return i;},clearTimeout(i){timers.delete(i);},requestAnimationFrame(fn){fn();return 1;},fetch(){throw Error('Unexpected network');},performance:{now:()=>0}};
 sandbox.window=sandbox;sandbox.parent=sandbox;
 const ctx=vm.createContext(sandbox);scripts.forEach(s=>vm.runInContext(s,ctx));
 const state=()=>JSON.parse(ctx.render_game_to_text());
 const click=selector=>{const b=document.querySelector(selector);assert(b,'Missing '+selector);assert(!b.disabled,'Disabled '+selector);b.dispatchEvent(new domWindow.Event('click',{bubbles:true}));};
 const close=()=>{if(document.querySelector('#reward-dialog').open)click('#reward-dialog [data-close]');};
 const day=n=>{close();const select=document.querySelector('#phoneCalendarSelect');select.value=String(n);select.dispatchEvent(new domWindow.Event('change',{bubbles:true}));};
 const chapter=n=>{close();click('[data-chapter="'+n+'"]');};
 return{ctx,document,state,click,close,day,chapter,store};
}
const h=harness();assert.equal(h.state().login.day,1);assert.equal(h.document.querySelectorAll('#phoneCalendarSelect option').length,22);
assert.equal(h.document.querySelector('#login-preview').style.getPropertyValue('--design-scale'),String(1248/2160));
h.click('[data-login-daily]');h.close();assert.equal(h.state().login.dailyClaims.length,1);
h.day(7);assert.equal(h.state().login.day,7);assert.equal(h.state().openingRed.phase,'active');assert.equal(h.state().openingRed.day,1);assert.equal(h.state().greeting.phase,'before');assert.equal(h.document.querySelectorAll('.date-panel.is-eve .date-reward-item').length,6);
h.chapter(1);h.click('[data-opening-daily]');h.close();assert.equal(h.state().openingRed.total,100);h.click('[data-phone-match]');assert.equal(h.state().openingRed.total,200);h.click('[data-phone-match]');assert.equal(h.state().openingRed.total,225);
h.day(8);assert.equal(h.state().openingRed.day,2);assert.equal(h.state().openingRed.total,225);assert.equal(h.state().greeting.phase,'active');assert.equal(h.state().greeting.day,1);
h.chapter(2);h.click('[data-greeting-quiz="0"]');h.click('[data-greeting-answer="0,0"]');assert(!h.state().greeting.players[0].solved);h.click('[data-greeting-answer="0,1"]');assert(h.state().greeting.players[0].solved);h.click('[data-greeting-claim="0"]');h.close();h.click('[data-phone-match]');assert(h.state().greeting.players[0].played);h.click('[data-greeting-upgrade="0"]');h.close();h.click('[data-greeting-light="0"]');assert(h.state().greeting.players[0].lit);
h.chapter(3);h.click('[data-kings-acquire="2"]');h.close();assert(!h.state().kings.owned[2]);h.click('[data-kings-acquire="2"]');h.click('[data-kings-buy]');h.close();assert(h.state().kings.owned[2]);h.click('[data-kings-challenge="2"]');h.click('[data-kings-result="2,1,win"]');h.close();h.click('[data-kings-exchange="2"]');h.close();assert(h.state().kings.exchanged[2][0]);
h.day('ended');assert.equal(h.state().login.phase,'ended');assert.equal(h.state().openingRed.phase,'ended');assert.equal(h.state().greeting.phase,'ended');h.day(8);assert.equal(h.state().login.phase,'active');assert(h.state().greeting.players[0].lit);
for(const n of [0,1,2,3]){h.chapter(n);assert.equal(h.document.querySelectorAll('[data-chapter][aria-current="page"]').length,1);h.click('[data-phone-forward]');h.click('[data-phone-prev]');}
const oldState=h.state();const reloaded=harness({saved:Object.fromEntries(h.store)});assert.equal(reloaded.state().openingRed.total,oldState.openingRed.total);assert(reloaded.state().greeting.players[0].lit);assert(reloaded.state().kings.owned[2]);
h.click('[data-phone-reset]');h.close();assert(h.state().kings.owned[2]);h.click('[data-phone-reset]');h.click('[data-phone-reset-confirm]');assert.equal(h.state().login.day,1);assert.equal(h.state().openingRed.total,0);assert(!h.state().kings.owned[2]);
const blocked=harness({blocked:true});blocked.day(8);blocked.click('[data-login-daily]');assert.equal(blocked.state().login.dailyClaims.length,1);blocked.close();
for(const [width,height]of [[1920,1080],[1366,768],[900,600],[844,390],[390,844]]){const x=harness({width,height}),scale=+x.document.documentElement.style.getPropertyValue('--phone-scale');assert(scale>0);assert(scale*1280<=width-9);assert(scale*664<height-40);assert.equal(+x.document.querySelector('#login-preview').style.getPropertyValue('--design-scale'),1248/2160);}
const result={status:'passed',assets:'34 embedded resources retained byte-for-byte',originalStyles:'unchanged',originalModels:'unchanged',calendar:'22 list options, 3 original chapter calendars synchronize',interactions:'login, packet daily/first/repeat, quiz wrong/right, claim/play/upgrade/light, Messi cancel/buy/win/exchange, reset cancel/confirm',persistence:'reload and denied storage passed',scaling:'5 viewport sizes, no double scaling',browserVisual:'not performed: local-file browser automation unavailable',sha256:crypto.createHash('sha256').update(html).digest('hex')};
fs.writeFileSync(dir+'/.build/qa-results.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
