(function(){
'use strict';
const app=document.getElementById('phonePreviewApp'),screen=document.getElementById('phoneScreen'),select=document.getElementById('phoneCalendarSelect'),dialog=document.getElementById('reward-dialog');
const api=window.PhonePresentation;
function refresh(){
 if(!api)return;const s=api.getCalendar();select.value=s.phase==='ended'?'ended':String(s.day);
 document.querySelector('[data-phone-next]').disabled=s.phase==='ended';
 document.getElementById('phoneCurrentChapter').textContent=api.getChapterName();
}
function fit(){
 const narrow=window.innerWidth<580,short=window.innerHeight<500&&window.innerWidth>window.innerHeight;
 const padding=short?10:narrow?20:32;
 const extras=short?51:narrow?145:window.innerWidth<1050?128:104;
 const scale=Math.max(.08,Math.min(1.13,(window.innerWidth-padding)/1280,(window.innerHeight-extras)/664));
 document.documentElement.style.setProperty('--phone-scale',String(scale));api?.resize();
 const r=screen.getBoundingClientRect();
 for(const [key,value]of Object.entries({'--phone-cx':r.left+r.width/2,'--phone-cy':r.top+r.height/2,'--phone-width':r.width,'--phone-height':r.height,'--phone-bottom':r.bottom}))document.documentElement.style.setProperty(key,value+'px');
}
function updateDialog(){screen.classList.toggle('has-dialog',!!dialog.open);fit();}
select.addEventListener('change',()=>{api?.setCalendar(select.value);refresh();});
document.querySelector('.phone-tools').addEventListener('click',event=>{
 const b=event.target.closest('button');if(!b||b.disabled)return;
 if(b.hasAttribute('data-phone-prev'))api?.browse(-1);
 if(b.hasAttribute('data-phone-forward'))api?.browse(1);
 if(b.hasAttribute('data-phone-next'))api?.nextDay();
 if(b.hasAttribute('data-phone-match'))api?.match();
 if(b.hasAttribute('data-phone-reset'))api?.confirmReset();
 if(b.hasAttribute('data-phone-fullscreen')){
  if(document.fullscreenElement){document.exitFullscreen?.().catch(()=>{});}
  else if(app.requestFullscreen){app.requestFullscreen().catch(()=>{document.getElementById('phoneStatus').textContent='浏览器未允许全屏，可使用浏览器全屏功能。';});}
  else document.getElementById('phoneStatus').textContent='可使用浏览器全屏功能查看。';
 }
 refresh();
});
document.addEventListener('phone:state',refresh);
window.addEventListener('resize',fit);document.addEventListener('fullscreenchange',fit);
new MutationObserver(updateDialog).observe(dialog,{attributes:true,attributeFilter:['open']});
dialog.addEventListener('close',updateDialog);refresh();fit();
})();
