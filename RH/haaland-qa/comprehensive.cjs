const fs=require('node:fs');const vm=require('node:vm');const assert=require('node:assert/strict');const crypto=require('node:crypto');
const {parseHTML}=require('linkedom');const csstree=require('css-tree');
const root='D:/codex/RH/haaland-offline/';
const read=n=>fs.readFileSync(root+n,'utf8');
const html=read('开始演示.html'),sourceHtml=read('index.html'),app=read('app.js'),css=read('style.css');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(x=>x[1]);
const embeddedCss=html.match(/<style>([\s\S]*?)<\/style>/)[1];
const b64=html.match(/id="stadiumImage">([A-Za-z0-9+/=]+)<\/script>/)[1];
assert.equal(scripts.length,2);assert(scripts[1].includes(app.trim()));
assert(Buffer.from(b64,'base64').equals(fs.readFileSync(root+'assets/haaland-stadium.png')));
assert(html.includes('img-src data: blob:'));assert(html.includes("connect-src 'none'"));
assert(!/@import|fetch\(/.test(embeddedCss+scripts[1]));
assert(!/--stadium\s*:\s*url\(['"]?data:/.test(embeddedCss));
assert.equal((embeddedCss.match(/var\(--stadium\)/g)||[]).length,2);
const parseErrors=[];csstree.parse(embeddedCss,{onParseError:e=>parseErrors.push(e.message)});assert.deepEqual(parseErrors,[]);
const {document:template}=parseHTML(sourceHtml);assert(template.body.classList.contains('phone-preview'));
assert.equal(template.querySelectorAll('.studio-header,.intro,.design-notes,.studio-footer,#expandBtn').length,0);
for(const el of template.querySelectorAll('[src],[href]')){const asset=el.getAttribute('src')||el.getAttribute('href');assert(!/^https?:/.test(asset));if(asset&&!asset.startsWith('#'))assert(fs.existsSync(root+asset),asset);}
for(const name of ['BarlowCondensed-Bold.ttf','NotoSansSC-400.ttf','NotoSansSC-700.ttf','NotoSansSC-900.ttf']){const b=fs.readFileSync(root+'assets/fonts/'+name);assert(embeddedCss.includes(b.toString('base64')));assert.equal(b.readUInt32BE(0),0x00010000);for(let i=0;i<b.readUInt16BE(4);i++){const p=12+16*i;assert(b.readUInt32BE(p+8)+b.readUInt32BE(p+12)<=b.length,'Incomplete font '+name);}}
function harness({blocked=false,saved=null,width=1280,height=800}={}){
 const {window:domWindow,document}=parseHTML(html);let active=document.body;
 domWindow.HTMLElement.prototype.focus=function(){active=this;};
 Object.defineProperty(document,'activeElement',{get(){return active;}});
 const store=new Map(saved===null?[]:[['striker-lab-offline-v1',saved]]);let seq=0;const timers=new Map();let imageBytes;
 const sandbox={document,console,atob,Uint8Array,Blob:class{constructor(parts,opts){imageBytes=Buffer.from(parts[0]);assert.equal(opts.type,'image/png');}},URL:{createObjectURL(){return 'blob:qa-stadium';}},window:{innerWidth:width,innerHeight:height,addEventListener(){}},localStorage:{getItem(k){if(blocked)throw Error('blocked');return store.get(k)||null;},setItem(k,v){if(blocked)throw Error('blocked');store.set(k,v);},removeItem(k){if(blocked)throw Error('blocked');store.delete(k);}},setTimeout(fn,delay){const id=++seq;timers.set(id,{fn,delay});return id;},clearTimeout(id){timers.delete(id);},fetch(){throw Error('Unexpected network access');}};
 const ctx=vm.createContext(sandbox);vm.runInContext(scripts[0],ctx);sandbox.window.lucide=sandbox.lucide;
 const inspectable=scripts[1].replace(app.trim(),app.trim()+'\nwindow.__qaState=()=>JSON.stringify(state);window.__qaSet=saved=>{state=restoreState(saved);render();};');
 vm.runInContext(inspectable,ctx);document.dispatchEvent(new domWindow.Event('DOMContentLoaded'));
 assert(imageBytes.equals(fs.readFileSync(root+'assets/haaland-stadium.png')));assert(document.documentElement.style.getPropertyValue('--stadium').length<100);
 function click(selector){const el=document.querySelector(selector);assert(el,'Missing control: '+selector);assert(!el.disabled,'Disabled control: '+selector);el.dispatchEvent(new domWindow.Event('click',{bubbles:true}));}
 function tickShots(){for(const [id,t]of [...timers])if(t.delay===450){timers.delete(id);t.fn();}}
 const state=()=>JSON.parse(sandbox.window.__qaState());
 function verifyPage(){assert.equal(document.querySelectorAll('i[data-lucide]').length,0,'Missing icon');assert(document.querySelectorAll('svg').length>=10);assert(document.getElementById('content').innerHTML.length>300);for(const button of document.querySelectorAll('button[data-action="node"]'))assert(/^[0-4]$/.test(button.dataset.id));}
 function drill(id){click(`[data-action="drill"][data-id="${id}"]`);for(let i=0;i<3;i++){click('[data-action="shoot"]');tickShots();}assert(document.querySelector('#modalTitle').textContent.includes('漂亮'));click('[data-action="dismiss"]');}
 return {document,ctx,click,tickShots,state,verifyPage,drill,timers,store};
}
const findings=[];
for(const blocked of [false,true]){
 const h=harness({blocked});h.verifyPage();assert.equal(h.state().points,2450);
 for(const name of ['training','partners','journey','final','overview']){h.click(`.chapter-nav [data-tab="${name}"]`);h.verifyPage();assert.equal(h.document.querySelectorAll('.chapter-nav button.active').length,1);}
 h.click('#guideBtn');assert(h.document.querySelector('.game-header').inert);h.click('#closeModal');assert(!h.document.querySelector('.game-header').inert);
 h.click('#rulesBtn');assert(h.document.querySelector('#modalTitle').textContent.includes('规则'));h.click('#closeModal');
 h.click('[data-action="daily"]');h.click('[data-action="daily"]');assert.equal(h.state().points,2500);
 h.click('.chapter-nav [data-tab="training"]');h.drill(0);h.drill(1);h.drill(2);h.drill(0);assert.equal(h.state().points,2700);assert.equal(h.state().trained.length,3);assert(h.document.querySelector('#trainingDot').hidden);
 h.click('.chapter-nav [data-tab="partners"]');h.click('[data-action="route"][data-route="cross"]');h.click('[data-action="route"][data-route="through"]');assert(h.state().routeChanged);
 h.click('[data-action="partner"]');assert(h.document.querySelector('[data-action="exchange"]').disabled);h.click('#closeModal');assert.equal(h.state().tokens,6);
 h.click('.chapter-nav [data-tab="journey"]');h.click('[data-action="node"][data-id="1"]');h.click('[data-action="claimNode"][data-id="1"]');assert.equal(h.state().points,2900);
 h.click('[data-action="node"][data-id="1"]');assert(h.document.querySelector('[data-action="claimNode"]').disabled);h.click('#closeModal');
 h.click('[data-action="node"][data-id="4"]');assert(h.document.querySelector('[data-action="claimNode"]').disabled);h.click('#closeModal');
 h.click('.chapter-nav [data-tab="final"]');h.click('[data-action="match"]');h.click('#closeModal');assert.equal(h.state().matches,0);
 for(let i=0;i<3;i++){h.click('[data-action="match"]');h.click('[data-action="finishMatch"]');h.click('[data-action="dismiss"]');}
 assert.equal(h.state().matches,3);assert.equal(h.state().tokens,12);assert.equal(h.state().points,4400);
 h.click('#taskBtn');for(let i=0;i<3;i++)h.click(`[data-action="claimTask"][data-id="${i}"]`);assert.equal(h.state().points,4550);h.click('#closeModal');
 h.click('.chapter-nav [data-tab="journey"]');h.click('[data-action="node"][data-id="4"]');h.click('[data-action="claimNode"][data-id="4"]');assert(h.state().player);
 h.click('.chapter-nav [data-tab="partners"]');h.click('[data-action="partner"]');h.click('[data-action="exchange"]');assert(h.state().partner);assert.equal(h.state().tokens,0);
 if(!blocked){const reloaded=harness({saved:h.store.get('striker-lab-offline-v1')});assert(reloaded.state().player);assert(reloaded.state().partner);}
 h.click('#resetBtn');h.click('[data-action="resetConfirm"]');assert.equal(h.state().points,2450);assert(!h.state().player);assert.equal(h.document.querySelectorAll('.chapter-nav button.active[data-tab="overview"]').length,1);
 findings.push(`All chapters and reward flow passed with storage ${blocked?'blocked':'enabled'}`);
}
const cancelled=harness();cancelled.click('.chapter-nav [data-tab="training"]');cancelled.click('[data-action="drill"][data-id="0"]');cancelled.click('[data-action="shoot"]');const oldCallback=[...cancelled.timers.values()].find(t=>t.delay===450).fn;cancelled.click('#closeModal');cancelled.click('[data-action="drill"][data-id="1"]');oldCallback();assert.equal(cancelled.document.querySelector('#shotCounter').textContent,'0/3');assert.equal(cancelled.state().trained.length,0);cancelled.click('#closeModal');
const corrupt=harness({saved:'{"points":-3,"matches":99,"route":"bad","trained":[0,0,88],"tasks":"oops"}'});assert.equal(corrupt.state().points,2450);assert.equal(corrupt.state().route,'through');assert.deepEqual(corrupt.state().trained,[0]);assert.equal(corrupt.state().matches,3);
const inconsistent=harness({saved:'{"points":3000,"matches":0,"claimed":[0,4],"player":true}'});assert(!inconsistent.state().claimed.includes(4));assert(!inconsistent.state().player);
const gated=harness({saved:'{"points":4500,"matches":0}'});gated.click('.chapter-nav [data-tab="journey"]');assert(gated.document.querySelector('[data-action="node"][data-id="4"]').getAttribute('aria-label').includes('待完成冠军挑战'));assert(!gated.document.querySelector('[data-action="node"][data-id="4"]').classList.contains('unlocked'));gated.click('[data-action="node"][data-id="4"]');assert(gated.document.querySelector('[data-action="claimNode"]').disabled);
const duplicate=harness();duplicate.click('.chapter-nav [data-tab="final"]');duplicate.click('[data-action="match"]');duplicate.click('[data-action="finishMatch"]');const already=duplicate.state().points;vm.runInContext("document.querySelector('#modalContent').insertAdjacentHTML('beforeend','<button data-action=\"finishMatch\">duplicate</button>')",duplicate.ctx);duplicate.click('[data-action="finishMatch"]');assert.equal(duplicate.state().points,already);assert.equal(duplicate.state().matches,1);
for(const [width,height]of [[1920,1080],[1366,768],[900,600],[844,390],[390,844]]){const h=harness({width,height});const s=Number(h.document.documentElement.style.getPropertyValue('--preview-scale'));assert(s>0&&s<=1.15);assert(s*1200<=width-32+0.1);assert(s*546<=height-104+0.1);}
function fontHas(font,cp){const b=fs.readFileSync(root+'assets/fonts/'+font);let cmap;for(let i=0;i<b.readUInt16BE(4);i++){const p=12+16*i;if(b.toString('ascii',p,p+4)==='cmap')cmap=b.readUInt32BE(p+8);}assert(cmap);const count=b.readUInt16BE(cmap+2);for(let i=0;i<count;i++){const off=cmap+b.readUInt32BE(cmap+4+8*i+4),format=b.readUInt16BE(off);if(format===4){const n=b.readUInt16BE(off+6)/2,ends=off+14,starts=ends+2*n+2,deltas=starts+2*n,ranges=deltas+2*n;for(let j=0;j<n;j++){const start=b.readUInt16BE(starts+2*j),end=b.readUInt16BE(ends+2*j);if(cp<start||cp>end)continue;const delta=b.readInt16BE(deltas+2*j),range=b.readUInt16BE(ranges+2*j);if(range===0){if(((cp+delta)&65535)!==0)return true;}else{const address=ranges+2*j+range+2*(cp-start);if(address+2<=b.length&&b.readUInt16BE(address)!==0)return true;}}}else if(format===12){for(let j=0;j<b.readUInt32BE(off+12);j++){const p=off+16+12*j;if(cp>=b.readUInt32BE(p)&&cp<=b.readUInt32BE(p+4))return true;}}}return false;}
const chars=[...new Set((sourceHtml+app).match(/[\u3000-\u9fff\uff00-\uffef]/g))];const missing=chars.filter(c=>!fontHas('NotoSansSC-400.ttf',c.codePointAt(0)));
fs.writeFileSync('D:/codex/RH/haaland-qa/glyph-audit.json',JSON.stringify({missing,characterCount:chars.length}));
assert.equal(missing.length,0,'Missing Chinese font glyphs: '+missing.join(''));
fs.writeFileSync('D:/codex/RH/haaland-qa/check-results.json',JSON.stringify({status:'passed',findings,cancellation:'passed',corruptStorage:'passed',viewportFit:'5 sizes passed',assets:'byte comparison passed',icons:'all resolved',css:'parser passed',fonts:'all Chinese glyphs present',browserVisual:'not tested: file protocol automation blocked'},null,2));
console.log('PASS: asset parity, HTML/CSS structure, all icons, real DOM interactions, complete reward flow, cancellation, storage errors, viewport sizing and fonts.');
