const fs=require('node:fs');
const csstree=require('css-tree');
const root='D:/codex/RH/haaland-offline/';
let app=fs.readFileSync(root+'app.js','utf8');
const replace=(oldText,newText)=>{if(!app.includes(oldText))throw Error('Expected source not found: '+oldText);app=app.replace(oldText,newText);};
replace("case'route':state.route=b.dataset.route;","case'route':if(!routes.some(r=>r[0]===b.dataset.route))return;if(state.route!==b.dataset.route)state.routeChanged=true;state.route=b.dataset.route;");
replace("case'finishMatch':if(state.matches>=3)return;","case'finishMatch':if(state.matches>=3||pendingMatch!==state.matches||dialogKind!=='match')return;pendingMatch=null;");
replace("case'claimNode':if(state.claimed.includes(id)","case'claimNode':if(!rewards[id])return;if(state.claimed.includes(id)");
replace("function nodeDetail(i){const r=rewards[i]","function nodeDetail(i){if(!rewards[i])return;const r=rewards[i]");
replace("${state.points>=r.at?'unlocked':''}","${state.points>=r.at&&(i!==4||state.matches>=3)?'unlocked':''}");
replace("state.points>=r.at?'可领取':'未解锁'","state.points>=r.at?(i===4&&state.matches<3?'待完成冠军挑战':'可领取'):'未解锁'");
replace("进度保存在当前浏览器，可随时重置。窄屏下可横向滑动手机画面，或旋转手机查看。","进度在浏览器允许时保存在本机，可随时重置。手机画面会随窗口缩放，横屏查看效果更好。完成两项训练、三场冠军挑战和赛季任务，即可领取核心球员。");
app=app.replace(/\nrender\(\);\s*$/,`\nfunction fitPhone(){const phone=$('#phone'),stage=$('.device-stage');if(!phone||!stage)return;const width=1200,height=phone.offsetHeight||546;const scale=Math.min(1.15,Math.max(120,window.innerWidth-32)/width,Math.max(120,window.innerHeight-104)/height);document.documentElement.style.setProperty('--preview-scale',String(scale));stage.style.width=\`\${width*scale}px\`;stage.style.height=\`\${height*scale}px\`;}\nwindow.addEventListener('resize',fitPhone);\nwindow.addEventListener('orientationchange',fitPhone);\nrender();\nfitPhone();\n`);
fs.writeFileSync(root+'app.js',app);
const ast=csstree.parse(fs.readFileSync(root+'style.css','utf8'));
const removeSelectors=/^\.(?:studio-header|studio-brand|brand-mark|brand-sub|studio-meta|divider|intro|eyebrow|view-controls|square|under-device|chapter-description|design-notes|studio-footer|expanded)(?:[\s.:>#]|$)|^h1(?:[\s.]|$)/;
ast.children.forEach((node,item,list)=>{if(node.type==='Atrule'&&node.name==='media'){const q=csstree.generate(node.prelude);if(q.includes('max-width')||q.includes('min-width'))list.remove(item);}else if(node.type==='Rule'&&removeSelectors.test(csstree.generate(node.prelude)))list.remove(item);});
const extra=`
body.phone-preview{min-height:100vh;min-height:100svh;display:flex;align-items:center;justify-content:center;overflow-x:hidden;padding:20px 16px}
.phone-preview .preview-main{padding:0;margin:0;max-width:none;width:auto}
.phone-preview .device-stage{overflow:visible;width:960px;height:437px;padding:0}
.phone-preview .phone{width:1200px;min-width:1200px;transform:scale(var(--preview-scale,.8));transform-origin:top left}
.phone-preview .game{font-size:14px}
.preview-toolbar{display:flex;align-items:center;justify-content:space-between;gap:18px;margin:16px 6px 0}
.preview-label{color:#91a8b7;font-size:12px;white-space:nowrap}
.preview-label span{font-family:'Barlow Condensed';letter-spacing:2px;color:#577381;margin-left:10px;font-size:10px}
.preview-toolbar .plain{padding:8px 0;min-height:34px}
.orientation-note{display:none;text-align:center;color:#6e8797;font-size:11px;margin:8px 0 0}
[inert]{pointer-events:none}
.node.unlocked small{color:var(--gold)}
.node.claimed small{color:var(--cyan)}
@media(max-width:600px){body.phone-preview{padding:14px 12px}.preview-toolbar{justify-content:center;flex-wrap:wrap;gap:5px;margin-top:12px}.preview-label{display:none}.prototype-tools{gap:20px}.preview-toolbar .plain{font-size:11px}.orientation-note{display:block}}
`;
fs.writeFileSync(root+'style.css',csstree.generate(ast)+'\n'+extra);
console.log('Phone-only layout and interaction fixes applied.');
