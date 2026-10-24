const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {parseHTML}=require('D:/codex/RH/haaland-qa/node_modules/linkedom');
const cssTree=require('D:/codex/RH/haaland-qa/node_modules/css-tree');
const root=__dirname,html=fs.readFileSync(root+'/开始演示.html','utf8'),css=fs.readFileSync(root+'/style.css','utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
assert.equal(scripts.length,3);assert(!/<(?:script|link|img)[^>]+(?:src|href)=["']https?:/i.test(html));assert(!/fetch\(|XMLHttpRequest|WebSocket|@import/.test(scripts.join('')+css));assert(html.includes("connect-src 'none'"));
const errors=[];cssTree.parse(css,{onParseError:e=>errors.push(e.message)});assert.deepEqual(errors,[]);
const assetData=JSON.parse(html.match(/<script type="application\/json" id="assetData">([\s\S]*?)<\/script>/)[1]);
for(const [key,file]of Object.entries({hero:'festival-background.png',card:'player-card-reference.png',history:'legend-reference.png'})){assert(Buffer.from(assetData[key].data,'base64').equals(fs.readFileSync(root+'/assets/'+file)));}
function harness({blocked=false,saved=null,width=1440,height=900}={}){
 const {document,window:win}=parseHTML(html);let focus=document.body;
 win.HTMLElement.prototype.focus=function(){focus=this;};Object.defineProperty(document,'activeElement',{get:()=>focus});
 const storage=new Map(saved?[['yangming-spring-offline-v1',saved]]:[]);let seq=0;const timers=new Map();
 const ctx=vm.createContext({document,console,atob,Uint8Array,Blob:class{},URL:{createObjectURL(){return'blob:embedded-'+(++seq);}},window:{innerWidth:width,innerHeight:height,addEventListener(){}},localStorage:{getItem(k){if(blocked)throw Error('blocked');return storage.get(k)||null;},setItem(k,v){if(blocked)throw Error('blocked');storage.set(k,v);}},setTimeout(fn,delay){const id=++seq;timers.set(id,{fn,delay});return id;},clearTimeout(id){timers.delete(id);},fetch(){throw Error('Unexpected network');}});
 scripts.forEach((s,i)=>vm.runInContext(i===2?s.replace('window.addEventListener(\'resize\',resize);resize();render();',"window.__QA={get:()=>JSON.parse(JSON.stringify(state)),set:s=>{state=C.restore(s);render();},ui,resize};window.addEventListener('resize',resize);resize();render();"):s,ctx));
 const get=()=>JSON.parse(JSON.stringify(ctx.window.__QA.get()));
 const click=selector=>{const el=document.querySelector(selector);assert(el,'Missing '+selector);assert(!el.disabled,'Disabled '+selector);el.dispatchEvent(new win.Event('click',{bubbles:true}));};
 const close=()=>{if(!document.querySelector('#modalShade').hidden)click('[data-action="close"]');};
 const tab=name=>{close();click('[data-action="tab"][data-tab="'+name+'"]');};
 const tick=()=>{for(const [id,t]of [...timers])if(t.delay===400){timers.delete(id);t.fn();}};
 const day=n=>{close();click('[data-action="calendar"]');click('[data-action="day"][data-day="'+n+'"]');};
 const play=({mode='attack',classic=null,stage=0,win=true,cancel=false}={})=>{
  close();if(classic){tab('legends');click('[data-action="legend"][data-id="'+classic+'"]');click('[data-action="legend-stage"][data-stage="'+stage+'"]');click('[data-action="classic"]');}else{click('.header [data-action="match"]');click('[data-action="mode"][data-mode="'+mode+'"]');}
  const dirs=win?[0,0,1]:[1,2,0];
  for(const d of dirs){click('[data-action="shoot"][data-dir="'+d+'"]');if(cancel){close();tick();return;}tick();}
  click('[data-action="settle"]');close();
 };
 const reveal=id=>{tab('stars');click('[data-action="person"][data-id="'+id+'"]');click('[data-action="guess"]');const p=ctx.SpringCore.players.find(p=>p.id===id);const wrong=p.options.find(x=>x!==p.name);click('[data-action="answer"][data-answer="'+wrong+'"]');assert(!get().players[id].revealed);click('[data-action="answer"][data-answer="'+p.name+'"]');close();click('[data-action="star-claim"]');close();};
 const upgrade=id=>{tab('stars');click('[data-action="person"][data-id="'+id+'"]');click('[data-action="star-up"]');close();assert(!get().players[id].lit);click('[data-action="person-back"]');click('[data-action="person"][data-id="'+id+'"]');assert(get().players[id].lit);};
 return{document,ctx,get,click,close,tab,day,play,reveal,upgrade,timers,tick,storage};
}
const results=[];
for(const blocked of [false,true]){
 const h=harness({blocked});assert.equal(h.get().day,7);assert(h.document.documentElement.style.getPropertyValue('--asset-hero').includes('blob:'));
 for(const tab of ['gifts','red','stars','legends']){h.tab(tab);assert(h.document.querySelector('#content').innerHTML.length>1000);assert.equal(h.document.querySelectorAll('.tabs .active').length,1);}
 h.tab('gifts');h.click('[data-action="login"]');h.close();assert.equal(h.get().login.length,1);assert(h.document.querySelector('[data-action="login"]').disabled);
 h.click('[data-action="gift-detail"][data-day="7"][data-index="0"]');h.click('[data-action="gift-claim"]');h.close();assert.deepEqual(h.get().gifts,['7:0']);
 h.click('[data-action="gift-detail"][data-day="6"][data-index="0"]');assert(h.document.querySelector('[data-action="gift-claim"]').disabled);h.close();
 h.day(6);assert.equal(h.document.querySelectorAll('[data-date-card="6"] .card-mini').length,6);h.day(7);
 h.tab('red');h.click('[data-action="red-daily"]');h.close();assert.equal(h.get().points,20);
 h.reveal('vvd');h.reveal('modric');assert(!h.get().players.vvd.played);
 h.play({cancel:true});assert.equal(h.get().matchCount,0);assert(!h.get().players.vvd.played);assert.equal(h.get().points,20);
 h.play({win:false});assert(h.get().players.vvd.played&&h.get().players.modric.played);assert.equal(h.get().points,80);
 h.play({mode:'attack'});assert.equal(h.get().points,100);h.play({mode:'realtime'});assert.equal(h.get().points,160);h.play({mode:'manager'});assert.equal(h.get().points,220);
 h.upgrade('vvd');h.upgrade('modric');h.day(9);h.reveal('kdb');h.play({mode:'manager',win:false});assert.equal(h.get().points,280);h.upgrade('kdb');
 h.click('[data-action="select"][data-goal="3"]');h.close();assert.equal(h.get().selections.length,0);
 h.click('[data-action="select"][data-goal="3"]');h.click('[data-action="select-player"][data-id="vvd"]');assert.equal(h.get().selections.length,0);h.click('[data-action="select-confirm"]');h.close();assert.deepEqual(h.get().selections,[3]);assert(h.get().players.vvd.self);
 h.day(19);for(const id of ['salah','son','griezmann','ronaldo','mbappe'])h.reveal(id);h.play({win:false});for(const id of ['salah','son','griezmann','ronaldo','mbappe'])h.upgrade(id);assert.equal(h.ctx.SpringCore.litCount(h.get()),8);
 h.click('[data-action="select"][data-goal="8"]');assert(!h.document.querySelector('[data-action="select-player"][data-id="vvd"]'));h.click('[data-action="select-player"][data-id="modric"]');h.click('[data-action="select-confirm"]');h.close();
 h.tab('legends');h.click('[data-action="legend-get"][data-id="pele"]');h.close();h.click('[data-action="legend-get"][data-id="messi"]');h.close();assert(!h.get().legends.messi.owned);h.click('[data-action="legend-get"][data-id="messi"]');h.click('[data-action="buy-confirm"]');h.close();assert(h.get().legends.messi.owned);
 h.play({classic:'pele',stage:2,win:false});assert.deepEqual(h.get().legends.pele.won,[]);h.play({classic:'pele',stage:2});assert.deepEqual(h.get().legends.pele.won,[2]);assert.deepEqual(h.get().legends.pele.redeemed,[]);h.click('[data-action="legend-up"]');h.close();assert.deepEqual(h.get().legends.pele.redeemed,[2]);
 while(h.get().points<360)h.play();h.tab('red');const total=h.get().points;for(const goal of [60,140,240,360]){h.click('[data-action="red-card"][data-goal="'+goal+'"]');h.close();}h.click('[data-action="red-growth"]');h.close();assert.equal(h.get().points,total);assert.equal(h.get().cards.length,4);assert.equal(h.get().growth.length,3);
 h.day(8);h.tab('red');h.click('[data-action="red-daily"]');h.close();const p=h.get().points;h.day(7);h.tab('red');assert(h.document.querySelector('[data-action="red-daily"]').disabled);assert.equal(h.get().points,p);
 h.day(21);h.tab('gifts');assert(h.document.querySelector('[data-action="login"]').disabled);assert(!h.ctx.SpringCore.apply(h.get(),{type:'LOGIN'}).ok);
 if(!blocked){const reload=harness({saved:h.storage.get('yangming-spring-offline-v1')});assert.deepEqual(reload.get(),h.get());}
 h.day(7);h.click('[data-action="reset"]');h.click('[data-action="reset-confirm"]');assert.equal(h.get().points,0);assert.equal(h.get().matchCount,0);assert.equal(h.get().day,7);assert.equal(h.ctx.SpringCore.litCount(h.get()),0);
 results.push('完整四板块流程、日期与领奖，存储'+(blocked?'禁用':'启用')+'：通过');
}
const q=harness(),core=q.ctx.SpringCore;let s=core.fresh();
for(const type of ['STAR_CLAIM','STAR_UP','LIGHT','LEGEND_UP'])assert(!core.apply(s,{type,id:type.startsWith('LEGEND')?'pele':'vvd',stage:0}).ok);
let r=core.apply(s,{type:'MATCH',mode:'attack',result:'loss',nonce:'same'});assert(r.ok);assert(!core.apply(r.state,{type:'MATCH',mode:'attack',result:'loss',nonce:'same'}).ok);
q.click('.header [data-action="match"]');q.click('[data-action="shoot"][data-dir="0"]');const old=[...q.timers.values()].find(t=>t.delay===400).fn;q.close();q.click('.header [data-action="match"]');old();assert.equal(q.document.querySelectorAll('.shot-score .goal').length,0);q.close();
const corrupt=harness({saved:'{"day":999,"points":-300,"players":{"vvd":{"upgraded":true,"lit":true}},"legends":{"pele":{"redeemed":[2]}}}'});assert.equal(corrupt.get().day,21);assert.equal(corrupt.get().points,0);assert(!corrupt.get().players.vvd.lit);assert.equal(corrupt.get().legends.pele.redeemed.length,0);
const broken=harness({saved:'{broken'});assert.equal(broken.get().day,7);
for(const [w,h]of [[1920,1080],[1366,768],[900,600],[844,390],[390,844]]){const x=harness({width:w,height:h}),scale=+x.document.documentElement.style.getPropertyValue('--scale');assert(scale>0);assert(scale*1280<=w-31);assert(scale*680<=h-(w<700?112:82)+1);}
fs.writeFileSync(root+'/qa-results.json',JSON.stringify({status:'passed',results,assetEmbedding:'3 images byte-identical',css:'parse passed',calendar:'21 dates plus ended state',stateSafety:'duplicate and prerequisite guards passed',cancelledMatch:'stale callbacks ignored',viewportFit:'5 sizes arithmetic checked',browserVisual:'未执行浏览器视觉验收：本地文件自动化访问受限',bytes:Buffer.byteLength(html),sha256:crypto.createHash('sha256').update(html).digest('hex')},null,2));
console.log('PASS: complete four-module DOM flow, multi-player tasks, all rewards reachable, non-winning matches, independent firsts, cancellation, date changes, storage failures, embedded assets and five viewport sizes.');
