import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.dirname(fileURLToPath(import.meta.url));
const input='C:/Users/littl/Downloads/standalone.html';
let html=await fs.readFile(input,'utf8');const hash=crypto.createHash('sha256').update(html).digest('hex');
const originalScript=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const originalCss=html.match(/<style>([\s\S]*?)<\/style>/)[1];
const add=(before,after)=>{if(!html.includes(before))throw Error('Missing exact source anchor: '+before.slice(0,100));html=html.replace(before,after);};
const css=await fs.readFile(root+'/phone.css','utf8'),js=await fs.readFile(root+'/phone.js','utf8');
add('<title>羊名立万 · 春节活动</title>','<title>羊名立万 · 手机预览版</title><meta name="theme-color" content="#100b10"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data: blob:; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; font-src data:; connect-src \'none\'; object-src \'none\'; base-uri \'none\'; form-action \'none\'">');
add('</style>','</style><style id="phonePresentationStyle">'+css+'</style>');
add('<div id="yangnian-login-inline">','<main class="phone-preview-app" id="phonePreviewApp"><div class="phone-fit"><div class="phone-device"><div class="phone-earpiece" aria-hidden="true"></div><div class="phone-screen" id="phoneScreen"><div id="yangnian-login-inline">');
const names=['腊月廿四','腊月廿五','腊月廿六','腊月廿七','腊月廿八','腊月廿九','除夕','正月初一','正月初二','正月初三','正月初四','正月初五','正月初六','正月初七','正月初八','正月初九','正月初十','正月十一','正月十二','正月十三','正月十四'];
const toolbar='<div class="phone-tools" aria-label="演示操作"><div class="phone-calendar-group"><label for="phoneCalendarSelect"><span>演示日期</span><select id="phoneCalendarSelect" aria-label="选择农历演示日期">'+names.map((n,i)=>'<option value="'+(i+1)+'">'+n+'</option>').join('')+'<option value="ended">活动结束</option></select></label></div><div class="phone-browse-group"><button type="button" data-phone-prev aria-label="向左浏览">‹</button><span id="phoneCurrentChapter">新春见面礼</span><button type="button" data-phone-forward aria-label="向右浏览">›</button></div><div class="phone-controls-group"><button type="button" data-phone-next>下一天</button><button type="button" data-phone-match>打一场多人</button><button type="button" data-phone-reset>全部重置</button><button type="button" data-phone-fullscreen>全屏查看</button></div></div><p class="phone-footnote" id="phoneStatus">单文件离线版 <strong>·</strong> 左右滑动浏览活动内容 <strong>·</strong> 原版素材、数值与玩法保留</p>';
add('</div>\n<script>','</div></div><div class="phone-home-indicator" aria-hidden="true"></div></div></div>'+toolbar+'</main>\n<script>window.__H5_EXPORT_ID__="phone-'+hash.slice(0,16)+'";</script><script>');
add("const resolveAsset=(name)=>assetData[name]||'';",`const resolvedAssetCache=Object.create(null);
  const resolveAsset=(name)=>{
    if(resolvedAssetCache[name])return resolvedAssetCache[name];
    const value=assetData[name]||'';
    if(!value.startsWith('data:image/')||!value.includes(';base64,'))return value;
    const split=value.indexOf(','),type=value.slice(5,value.indexOf(';'));
    const bytes=Uint8Array.from(atob(value.slice(split+1)),c=>c.charCodeAt(0));
    return resolvedAssetCache[name]=URL.createObjectURL(new Blob([bytes],{type}));
  };`);
add("function sizeCanvas(){scale=stage.getBoundingClientRect().width/2160;stage.style.setProperty('--design-scale',String(scale));}","function sizeCanvas(){scale=stage.getBoundingClientRect().width/2160;stage.style.setProperty('--design-scale',String(stage.clientWidth/2160));}");
// Publish presentation state changes without changing the original snapshot or reward models.
add('    if(gmBatch)return;\n    bridgeRevision+=1;','    if(gmBatch)return;\n    document.dispatchEvent(new Event(\'phone:state\'));\n    bridgeRevision+=1;');
add("    if(button.hasAttribute('data-gm-toggle'))", "    if(button.hasAttribute('data-phone-reset-confirm')){gmReset();return;}\n    if(button.hasAttribute('data-gm-toggle'))");
const api=`
  window.PhonePresentation={
    resize:sizeCanvas,
    getCalendar:()=>({day:loginState.day,phase:loginState.phase}),
    getChapterName:()=>chapterNames[activeChapter],
    nextDay:gmNextDay,
    match:gmMatch,
    browse(direction){if(dialog.open)return;const e=currentViewport();e.scrollBy({left:direction*2160*.82,behavior:behavior()});},
    confirmReset(){gmMenu(false);openDialog('重新开始演示','<p class="dialog-copy">清空此手机版的活动进度，回到腊月廿四。原始文件不受影响。</p><div class="dialog-actions"><button class="dialog-action secondary" data-close>取消</button><button class="dialog-action" data-phone-reset-confirm>确认全部重置</button></div>');},
    setCalendar(value){
      const phase=value==='ended'?'ended':'active';
      const day=value==='ended'?Login.ACTIVITY_DAYS:Number(value);
      if(!Number.isInteger(day)||day<1||day>Login.ACTIVITY_DAYS)return;
      gmMenu(false);closeDialog();
      if(day===loginState.day&&phase===loginState.phase)return;
      scrollPositions[activeChapter]=currentViewport().scrollLeft;
      loginState=Login.normalize({...loginState,day,phase});
      syncActivityCalendar();renderActivities();save();
      notify(phase==='ended'?'活动已结束':GM.calendarLabel(day));
    }
  };
`;
add('  makePanels();renderLoginDaily();renderOpening();renderChapter();setupScroll(viewport,0);',api+'\n  makePanels();renderLoginDaily();renderOpening();renderChapter();setupScroll(viewport,0);');
add('</body></html>','<script>'+js+'</script></body></html>');
await fs.mkdir(root+'/.build',{recursive:true});
await fs.writeFile(root+'/开始演示-手机版.html',html,'utf8');
await fs.writeFile(root+'/.build/source-script.js',originalScript,'utf8');
await fs.writeFile(root+'/.build/source-style.css',originalCss,'utf8');
await fs.writeFile(root+'/.build/source-manifest.json',JSON.stringify({input,sourceSha256:hash,outputBytes:Buffer.byteLength(html),assetsRetained:true,changes:['手机外框及比例缩放','原生日期选择列表','原版演示控制移至手机外侧','修正双重缩放对画布和拖动的影响','弹窗与提示限定于手机画面','嵌入图片以本地Blob引用'],scope:'不使用前一个新建原型的业务规则或素材'},null,2));
console.log('Built 开始演示-手机版.html, '+Buffer.byteLength(html)+' bytes; original business code and embedded images retained.');
