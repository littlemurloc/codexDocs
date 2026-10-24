(function(){
'use strict';
const C=SpringCore,K='yangming-spring-offline-v1';
let state=C.fresh(),saveOK=true;
try{const raw=localStorage.getItem(K);if(raw)state=C.restore(JSON.parse(raw));}catch{saveOK=false;}
const ui={tab:'gifts',person:null,legend:null,legendStage:0,giftFocus:state.day>20?20:state.day};
let modalType='',selected=null,selectedGoal=null,match=null,serial=0,toastTimer,lastFocus=null;
const $=s=>document.querySelector(s);
const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icons={gift:'<path d="M4 12h24v17H4zM2 7h28v6H2zM16 7v22M16 7C6 7 7 0 11 2c3 1 5 5 5 5Zm0 0c10 0 9-7 5-5-3 1-5 5-5 5Z"/>',upgrade:'<path d="m7 6-5 5 5 5v-3h17V9H7V6Zm18 20 5-5-5-5v3H8v4h17v3Z"/>',ball:'<circle cx="16" cy="16" r="13"/><path d="m16 9 7 5-3 8h-8l-3-8 7-5Zm0-6v6M3 13l6 1m3 8-5 5m13-5 5 5m-2-13 6-1"/>',check:'<path d="m6 16 7 7L27 8"/>',lock:'<path d="M7 14h18v16H7zM11 14V8a5 5 0 0 1 10 0v6"/>'};
const icon=(name)=>'<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">'+(icons[name]||icons.gift)+'</svg>';
const round=(kind='gift',claimed=false)=>'<span class="round-reward '+(claimed?'claimed':'')+'">'+icon(kind)+'</span>';
const btn=(label,action,attrs='',disabled=false,kind='')=>'<button class="button '+kind+'" data-action="'+action+'" '+attrs+(disabled?' disabled':'')+'>'+label+'</button>';
const card=(label='',size='')=>'<div class="card-art '+size+'">'+(label?'<strong>'+esc(label)+'</strong>':'')+'</div>';
function jersey(p,unknown=false){return'<div class="jersey" style="color:'+(unknown?'#241721':p.color)+'"><svg viewBox="0 0 190 225" aria-hidden="true"><defs><linearGradient id="cloth-'+p.id+'" x1="0" x2="1"><stop stop-color="currentColor"/><stop offset="1" stop-color="#17111a" stop-opacity=".3"/></linearGradient></defs><path d="M54 9 18 31 2 76 34 93 48 71 43 210Q95 226 147 210L142 71 156 93 188 76 172 31 136 9Q119 27 95 24 72 27 54 9Z" fill="currentColor" stroke="#e0c58a33" stroke-width="2"/><path d="M54 9Q95 54 136 9M48 71 52 27m90 44-4-44" stroke="#0006" fill="none" stroke-width="5"/><path d="M52 36v167m86-167v167" stroke="#fff1" stroke-width="2"/></svg><span>'+(unknown?'?':p.number)+'</span></div>';}
const intro=(title,description,extra='',big=false)=>'<aside class="intro"><p class="eyebrow">LUNAR NEW YEAR 2027</p><h1 class="'+(big?'large':'')+'">'+title+'</h1><p>'+description+'</p>'+extra+'</aside>';
const ended=()=>!C.active(state);
function save(){try{localStorage.setItem(K,JSON.stringify(state));saveOK=true;}catch{saveOK=false;}$('#saveStatus').textContent=saveOK?'进度保存在本机':'浏览器未允许保存，当前仍可体验';}
function toast(message){clearTimeout(toastTimer);$('#toast').textContent=message;$('#toast').classList.add('show');toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),3100);}
function perform(action,rewardPopup=true){const r=C.apply(state,action);if(!r.ok){toast(r.message);return r;}state=r.state;save();render();if(r.rewards.length&&rewardPopup)showRewards(r.rewards);else toast(r.message);return r;}
function giftStatus(day,index){return state.gifts.includes(day+':'+index)?'已领取':day<state.day?'已过期':day>state.day?'未开放':ended()?'已结束':'领取奖励';}
function renderGifts(){
 const days=C.dates.slice(0,21).map((d,day)=>'<article class="date-card '+(day===state.day?'today':day<state.day?'expired':'')+'" data-date-card="'+day+'"><h3>'+d+'</h3><span class="date-badge">'+(day===6?'除夕特别礼':day===state.day?'今日限定礼':'日期限定礼')+'</span><div class="gift-grid '+(day===6?'double-row':'')+'">'+Array.from({length:C.giftCount(day)},(_,index)=>'<div class="card-mini"><button data-action="gift-detail" data-day="'+day+'" data-index="'+index+'" aria-label="'+d+'奖励'+(index+1)+'，'+giftStatus(day,index)+'">'+card('', 'sm')+'</button><button class="reward-action" data-action="gift-detail" data-day="'+day+'" data-index="'+index+'">'+round('gift',state.gifts.includes(day+':'+index))+'<span class="tiny">'+giftStatus(day,index)+'</span></button></div>').join('')+'</div></article>').join('');
 return'<div class="board"><aside class="intro"><p class="eyebrow">A NEW YEAR. A NEW GLORY.</p><div class="brand-mark">羊名<span>立万</span></div><div class="brand-year">2027</div><h1>新春见面礼</h1><p>每天回来，先领一份新春好礼。<br>日期限定奖励，当天领取，错过不补。</p><div class="push">'+btn('活动规则','rules','','', 'secondary small')+'</div></aside><div class="daily soft-panel"><h2 class="panel-title">每日登录礼</h2><p>一年新起点<br>今天，也有一份心意。</p><button class="reward-action" data-action="login" '+(state.login.includes(state.day)||ended()?'disabled':'')+'>'+round('gift',state.login.includes(state.day))+'<span>'+ (state.login.includes(state.day)?'今日已领取':ended()?'活动已结束':'领取今日好礼')+'</span></button><span class="subnote">每日刷新，不累积补领</span></div><section class="date-area"><div class="section-heading"><span>日期限定礼 <small>左右浏览每日奖励</small></span><div class="arrows"><button data-action="gift-prev" aria-label="前一个日期">‹</button><button data-action="gift-today" style="width:45px;font-size:10px">今日</button><button data-action="gift-next" aria-label="后一个日期">›</button></div></div><div class="date-scroll" id="dateScroll">'+days+'</div></section></div>';
}
function renderRed(){
 const ready=C.redOpen(state),pending=C.growthGoals.filter(g=>state.points>=g&&!state.growth.includes(g)),lv=C.growthGoals.filter(g=>state.points>=g).length;
 return'<div class="board"><aside class="intro red-intro"><p class="eyebrow">A LITTLE LUCK. EVERY MATCH.</p><h1 class="large">踢出<br>开门红</h1><p>领红包，踢比赛。<br>同一份累计，推进卡奖励与红包成长。</p><div class="open-list">进攻对战 · 实时对战 · 经理人<br>各模式首场分别计算<br>完成即可，不要求获胜</div><button class="reward-action push" data-action="red-daily" '+(!ready||state.redDaily.includes(state.day)?'disabled':'')+'>'+round('gift',state.redDaily.includes(state.day))+'<span>'+ (state.redDaily.includes(state.day)?'今日红包已领':ready?'领取每日红包':'除夕起开放')+'</span></button><span class="subnote">演示领取后增加 20 累计</span></aside><section class="red-center"><div class="section-heading"><span>攒红包，领球星</span><small>累计达标后主动领取，不扣进度</small></div><div class="goal-row">'+C.cardGoals.map((g,i)=>'<div class="goal-item"><button data-action="red-detail" data-goal="'+g+'" aria-label="累计'+g+'卡奖励">'+card('累计奖励 '+(i+1))+'</button><p class="tiny">累计 '+g+'</p>'+btn(state.cards.includes(g)?'已领取':state.points>=g?'领取奖励':'尚未达成','red-card','data-goal="'+g+'"',!ready||state.points<g||state.cards.includes(g),'small')+'</div>').join('')+'</div><div class="progress-wrap"><div class="progress-track"><i style="width:'+Math.min(100,state.points/360*100)+'%"></i></div><div class="progress-value"><span>当前累计 <strong>'+state.points+'</strong></span><span>核心目标 360</span></div></div><p class="subnote">演示配置：模式首场 +60，后续有效场次 +20。首场不会同时叠加常规收益。</p><div class="push" style="margin-top:auto;display:flex;justify-content:space-between;align-items:center"><span class="tiny">今日首场 '+(state.firsts[state.day]?.length||0)+'/3　卡奖励 '+state.cards.length+'/4</span>'+btn('前往本地比赛','match','',ended(),'secondary')+'</div></section><aside class="red-growth soft-panel"><h2 class="panel-title">红包成长</h2><p class="tiny">'+(lv===3?'红包已满级':'升级红包外观，解锁成长好礼')+'</p><div class="packet lv'+lv+'"><strong>羊</strong></div><div class="growth-steps">'+['新春','鸿运','金玉','满堂'][lv]+'红包 · '+lv+'/3级</div><p class="tiny">已领取 '+state.growth.length+'/3 份成长奖励</p><button class="reward-action" style="margin-top:auto" data-action="red-growth" '+(!ready||!pending.length?'disabled':'')+'>'+round('gift',state.growth.length===3)+'<span>'+(pending.length?'领取 '+pending.length+' 份成长奖励':state.growth.length===3?'成长奖励全部已领':'暂无待领成长奖励')+'</span></button></aside></div>';
}
function renderStars(){
 if(ui.person)return renderPerson();
 const count=C.litCount(state),next=C.players.find(p=>p.day>state.day);
 return'<div class="board">'+intro('拜年<br>有名堂','从一件球衣、一段故事开始。<br>猜出球星，领卡参赛，完成升级。','<div class="open-list">初一开放两位<br>此后每两天新增一位<br>已开任务可补做到正月十四</div><p class="tiny" style="margin-top:15px">'+(next?'下一位：'+C.dates[next.day]+'开放':'人物已全部开放')+'</p><div class="push">'+btn('去比赛完成参赛任务','match','',ended(),'secondary small')+'</div>',true)+'<section class="star-center"><div class="section-heading"><span>新春球星群像</span><small>升级后，回到这里主动点亮</small></div><div class="stars-grid">'+C.players.map(p=>{const t=state.players[p.id],open=state.day>=p.day;return'<button class="person-tile '+(!open?'locked ':'')+(t.revealed?'revealed ':'')+(t.lit?'lit ':t.upgraded?'ready ':'')+'" data-action="person" data-id="'+p.id+'"><span class="badge">'+(t.lit?'已点亮':t.upgraded?'点击点亮':!open?C.dates[p.day]:'待拜年')+'</span>'+jersey(p,!t.revealed)+'<span class="name">'+(t.revealed?p.name:'神秘球星')+'</span><span class="tiny">'+(!open?'尚未开放':C.starStatus(state,p))+'</span></button>';}).join('')+'</div></section><aside class="collect-panel soft-panel"><h2 class="panel-title">一起，点亮新春</h2><div class="collection-count">'+count+' <small>/ 8 位</small></div>'+C.collectGoals.map((g,i)=>'<div class="collect-goal"><h4>'+(i?'完整群像目标':'阶段收集目标')+'</h4><p>点亮 '+g+' 位，领取一次自选升级</p>'+btn(state.selections.includes(g)?'自选已领取':count>=g?'领取自选升级':'点亮 '+count+'/'+g,'select','data-goal="'+g+'"',ended()||count<g||state.selections.includes(g),'small full')+'</div>').join('')+'<p class="subnote">自选不扣点亮进度<br>确认选择后才消耗机会</p></aside></div>';
}
function renderPerson(){
 const p=C.players.find(p=>p.id===ui.person),v=state.players[p.id],open=C.starOpen(state,p);
 return'<div class="personal"><aside class="personal-left"><button class="back-label" data-action="person-back">‹ 返回球星群像</button><div class="small-reward-panel"><h3>神秘奖励</h3><button class="reward-action" style="margin:auto" data-action="star-claim" data-id="'+p.id+'" '+(!open||!v.revealed||v.claimed?'disabled':'')+'>'+round('gift',v.claimed)+'<span>'+(v.claimed?'球员已领取':v.revealed?'领取活动球员':'答对后领取球员')+'</span></button></div><div class="small-reward-panel"><h3>个人升级</h3><button class="reward-action" style="margin:auto" data-action="star-up" data-id="'+p.id+'" '+(!open||!v.played||v.upgraded?'disabled':'')+'>'+round('upgrade',v.upgraded)+'<span>'+(v.upgraded?'个人升级已兑换':v.played?'兑换个人升级':'领卡后，参加一场比赛')+'</span></button></div></aside><div class="personal-figure">'+(v.revealed?card(p.name,'big'):jersey(p))+'<h2>'+(v.revealed?p.name:'猜猜他是谁')+'</h2><span class="pill-text">'+C.starStatus(state,p)+'</span><p class="tiny" style="margin-top:15px">球衣与故事为演示谜面，球员池待确认</p></div><article class="personal-story"><p class="eyebrow">THE STORY BEHIND THE SHIRT</p><h2>'+(state.day<p.day?'新的故事，即将揭晓':'一件球衣，一段故事')+'</h2><p>'+(state.day<p.day?C.dates[p.day]+'开放人物，敬请期待。':p.clue)+'</p><div class="step-state">'+(!v.revealed?'读完线索，打开竞猜':!v.claimed?'答对了，先到左侧主动领卡':!v.played?'已领卡，参加比赛完成个人任务':!v.upgraded?'比赛完成，到左侧兑换个人升级':!v.lit?'升级已兑换，回群像主动点亮':'已完成点亮，继续收集其他球星')+'</div>'+(v.upgraded&&!v.lit?btn('返回群像，点亮人物','person-back'):v.claimed&&!v.played?btn('去完成一场比赛','match','',ended()):btn(v.revealed?'球星已揭晓':'猜猜他是谁','guess','data-id="'+p.id+'"',!open||v.revealed))+'</article></div>';
}
function renderLegends(){
 if(ui.legend)return renderLegend();
 return'<div class="board">'+intro('三羊<br>开泰','三条路线，三位传奇。<br>先读经典故事，再赢下属于你的比赛。','<div class="open-list">贝利、马拉多纳免费领取<br>梅西模拟 FC 币购买<br>获取、获胜与升级分别记录</div><p class="subnote push">演示暂设三阶段。正式起止、阶段数和参与条件待确认。</p>',true)+'<div class="legend-grid">'+C.legends.map(l=>{const v=state.legends[l.id];return'<article class="legend-card"><h2>'+l.name+'</h2><p>'+l.tag+'</p><button class="card-button" data-action="legend" data-id="'+l.id+'" aria-label="查看'+l.name+'经典战役">'+card(l.name,'big')+'</button><span class="tiny" style="margin-bottom:12px">'+(v.owned?'已获取初始卡 · '+v.redeemed.length+'/3阶段升级':l.paid?'模拟购买 · 不扣费':'初始球员 · 免费获取')+'</span>'+btn(v.owned?'进入经典战役':l.paid?'FC 币购买':'免费领取',v.owned?'legend':'legend-get','data-id="'+l.id+'"',ended()||C.stage(state)<0,'full')+'</article>';}).join('')+'</div></div>';
}
function renderLegend(){
 const l=C.legends.find(l=>l.id===ui.legend),v=state.legends[l.id],stage=ui.legendStage,open=stage<=C.stage(state)&&!ended(),won=v.won.includes(stage),done=v.redeemed.includes(stage);
 return'<div class="legend-detail"><aside class="history-block"><button class="back-label" data-action="legend-back">‹ 返回三羊开泰</button><h2>'+l.name+' · '+l.title+'</h2>'+(l.id==='pele'?'<div class="history-photo" role="img" aria-label="原策划案中的贝利经典战役历史图片"></div>':'<div class="history-jersey">'+jersey({id:l.id,number:l.id==='messi'?10:10,color:l.id==='messi'?'#5490b8':'#96c5dc'})+'</div>')+'<p class="tiny" style="margin-top:13px">经典战役内容与正式比赛难度待确认</p><p class="tiny">'+(v.owned?'初始卡已获取':'请先获取初始球员')+'</p>'+(!v.owned?btn(l.paid?'确认模拟购买':'免费领取初始卡','legend-get','data-id="'+l.id+'"',ended()||C.stage(state)<0,'small'):'')+'</aside><article class="battle-story soft-panel"><p class="eyebrow">LEGENDARY MOMENTS</p><h3>经典战役回顾</h3><p>'+l.story+'</p><div class="stage-tabs">'+[0,1,2].map(i=>'<button class="'+(i===stage?'active':'')+'" data-action="legend-stage" data-stage="'+i+'">第'+(i+1)+'阶段<br><span class="tiny">'+C.dates[C.stageDays[i]]+(v.redeemed.includes(i)?' · 已兑换':v.won.includes(i)?' · 已获胜':'')+'</span></button>').join('')+'</div><p class="tiny">演示条件：持有初始卡且本阶段已开放。<br>挑战用三轮点球代替真实比赛，至少两球判胜。</p>'+btn(!open?'阶段尚未开放':won?'再次体验挑战':'挑战经典战役','classic','data-id="'+l.id+'" data-stage="'+stage+'"',!open||!v.owned)+'</article><aside class="legend-up soft-panel"><h2 class="panel-title">第'+(stage+1)+'阶段升级</h2><p class="tiny">'+(done?'挑战与升级均已完成':won?'已获胜，等待你主动兑换':'获胜后解锁个人升级')+'</p>'+card(l.name+' · 升级','big')+'<button class="reward-action" data-action="legend-up" data-id="'+l.id+'" data-stage="'+stage+'" '+(!open||!v.owned||!won||done?'disabled':'')+'>'+round('upgrade',done)+'<span>'+(done?'已兑换':!open||!v.owned?'锁定':!won?'等待挑战获胜':'兑换升级')+'</span></button></aside></div>';
}
function render(){
 $('#dateLabel').innerHTML='<small>演示日期</small><strong>'+C.dates[state.day]+'</strong> ▾';
 $('#ownedCount').textContent=C.players.filter(p=>state.players[p.id].claimed).length+C.legends.filter(p=>state.legends[p.id].owned).length;
 document.querySelectorAll('.tabs button').forEach(b=>{b.classList.toggle('active',b.dataset.tab===ui.tab);b.setAttribute('aria-selected',String(b.dataset.tab===ui.tab));});
 $('#content').innerHTML=ui.tab==='gifts'?renderGifts():ui.tab==='red'?renderRed():ui.tab==='stars'?renderStars():renderLegends();
 const hints={gifts:'每日登录礼与日期限定礼分别领取，未来奖励可提前查看',red:'每日资格刷新，累计保留。卡奖励、红包成长与领取分别记录',stars:'竞猜领卡后参赛，兑换个人升级后回总览点亮',legends:'领取或购买初始卡不代替挑战，获胜后主动兑换升级'};
 $('#footerText').textContent=ended()?'活动已结束 · 可切换演示日期查看开放状态':hints[ui.tab];
 $('#saveStatus').textContent=saveOK?'进度保存在本机':'浏览器未允许保存，当前仍可体验';
 const scroll=$('#dateScroll');if(scroll)scroll.scrollLeft=Math.min(20,ui.giftFocus)*280;
}
function modal(title,html,type='',wide=false){
 if(!modalType)lastFocus=document.activeElement;
 modalType=type;$('#modalTitle').textContent=title;$('#modalContent').innerHTML=html;$('.modal').classList.toggle('wide',wide);$('#modalShade').hidden=false;
 document.querySelectorAll('[data-background],.studio-strip').forEach(el=>el.inert=true);$('#closeModal').focus();
}
function close(){serial++;match=null;selected=null;selectedGoal=null;modalType='';$('#modalShade').hidden=true;$('#modalContent').innerHTML='';document.querySelectorAll('[data-background],.studio-strip').forEach(el=>el.inert=false);if(lastFocus?.isConnected)lastFocus.focus();else $('.tabs button.active').focus();}
function showRewards(list){modal('好礼已入库','<div class="reward-results">'+list.map(x=>'<div class="reward-result">'+(x.includes('球员')||x.includes('升级')?card(x.includes('升级')?'升级奖励':'活动奖励'):round('gift'))+'<p>'+esc(x)+'</p></div>').join('')+'</div><p style="text-align:center">可在「我的奖励」查看，相关进度已保存。</p><div class="actions">'+btn('开心收下','close')+'</div>','reward');}
function rules(){
 modal('活动规则与演示说明','<div class="rules-copy"><section><h3>新春见面礼</h3><p>登录礼与日期限定礼分别领取、分别记录。登录礼不累积，日期礼只在对应日期领取。未来可预览，过去未领显示过期。除夕采用六张奖励的特别排布。</p></section><section><h3>踢出开门红</h3><p>除夕至正月十四。三模式分别计算每日首场，完成即可，不要求获胜。首场不叠加常规收益。累计用于卡奖励与红包成长，领奖不扣累计，已解锁成长奖励可一并领取。每日资格刷新，进度保留。</p></section><section><h3>拜年有名堂</h3><p>答错立即重选。答对主动领卡，领卡后参加比赛，不要求首发、获胜或进球。同场可以完成多名已领取球员任务。兑换个人升级后还需回群像点亮。自选在已兑换个人升级的球员中选择，确认才消耗机会，不扣点亮数。</p></section><section><h3>三羊开泰</h3><p>贝利、马拉多纳免费领取，梅西模拟FC币购买需确认，不发生扣费。获取、挑战获胜、兑换升级分别记录。阶段间保留已完成记录，不设共同终奖。正式日期、阶段、持卡与前置条件待确认。</p></section><section><h3>日期与本地比赛</h3><p>默认初一。通过演示日期按钮切换，不使用电脑日期。回看日期不会重置已领记录。拜年初一两位，此后隔日新增一位，十三全开，可补做到十四。结束日关闭领奖与结算。比赛为三轮点球，主动结算才推进任务，取消不发奖。</p></section><section><h3>尚未确定的演示配置</h3><p>红包每日20，首场60，常规20。卡门槛60/140/240/360，成长100/220/360，自选3/8人。8人谜面为演示球员池。传奇暂设初一、初七、十三三阶段，不要求上一阶段完成。自选暂限同一人一次，正式重复规则待确认。</p></section></div><p class="rules-notice">这是依据所提供策划案制作的单机交互原型，奖励均为占位卡，比赛、发奖与购买均为本地模拟。背景为本次AI生成，卡框及贝利配图来自原策划案。不是游戏客户端或正式经济配置。</p><div class="actions">'+btn('知道了','close')+'</div>','rules',true);
}
function calendar(){modal('切换演示日期','<p>用不同日期查看开放与刷新。切换不重置已领记录，也不会清空累计。</p><div class="calendar-grid">'+C.dates.map((date,i)=>'<button data-action="day" data-day="'+i+'" class="'+(state.day===i?'active':'')+'">'+date+'<small>'+(i===6?'开门红开放':i===7?'两位球星开放':i===13?'第二阶段演示':i===19?'人物全部开放':i===21?'关闭领取':'')+'</small></button>').join('')+'</div><p class="rules-notice">正式活动的开放、每日刷新与结束时刻需另行确认。传奇阶段日期为本次演示假定。</p>','calendar',true);}
function giftDetail(day,index){const status=giftStatus(day,index);modal(C.dates[day]+' · 日期限定礼','<div class="reward-results"><div class="reward-result">'+card('日期奖励 '+(index+1),'big')+'<p>'+status+'</p></div></div><p style="text-align:center">只能在对应日期领取，不会代领每日登录礼。</p><div class="actions">'+btn(status,'gift-claim','data-day="'+day+'" data-index="'+index+'"',status!=='领取奖励')+'</div>','gift');}
function guess(id){const p=C.players.find(p=>p.id===id);if(!p||!C.starOpen(state,p)||state.players[id].revealed)return;modal('猜猜他是谁','<p>'+p.clue+'</p><div class="option-grid">'+p.options.map(x=>'<button data-action="answer" data-id="'+id+'" data-answer="'+esc(x)+'">'+x+'</button>').join('')+'</div><p class="error" id="guessHint">答错可立即重选，不扣次数。</p>','guess');}
function select(goal){
 selectedGoal=goal;selected=null;selectModal();
}
function selectModal(){
 const eligible=C.players.filter(p=>state.players[p.id].upgraded&&!state.players[p.id].self);
 modal('选择你的自选升级','<p>本次使用「点亮 '+selectedGoal+' 人」的自选机会。仅在确认后消耗，不扣点亮进度。</p><div class="select-grid">'+eligible.map(p=>'<button class="select-player '+(selected===p.id?'selected':'')+'" data-action="select-player" data-id="'+p.id+'">'+jersey(p)+'<strong>'+p.name+'</strong><span class="tiny">已兑换个人升级</span></button>').join('')+'</div>'+(eligible.length?'':'<p class="empty">当前没有符合条件的球员。</p>')+'<div class="actions">'+btn('取消','close','','','secondary')+btn('确认自选升级','select-confirm','',!selected)+'</div><p class="rules-notice">同一球员是否允许重复自选尚未确定，演示中每名球员仅接受一次。</p>','select');
}
function buyLegend(id){const l=C.legends.find(l=>l.id===id);if(!l)return;if(!l.paid){perform({type:'LEGEND_GET',id});return;}modal('梅西 · 模拟 FC 币购买','<div class="reward-results"><div>'+card('梅西','big')+'</div></div><p style="text-align:center">确认后取得梅西初始球员占位卡。<br>本次只演示购买确认，不扣费。正式价格与支付另行确认。</p><div class="actions">'+btn('取消','close','','','secondary')+btn('确认模拟购买（不扣费）','buy-confirm','data-id="messi"')+'</div>','buy');}
function inventory(){
 const entries=[];for(const p of C.players){const v=state.players[p.id];if(v.claimed)entries.push([p.name,v.self?'个人升级 + 自选升级':v.upgraded?'个人升级已兑换':v.played?'已参赛，待个人升级':'已领卡，待参赛']);}
 for(const l of C.legends){const v=state.legends[l.id];if(v.owned)entries.push([l.name,'初始卡已获取 · '+v.redeemed.length+'次阶段升级']);}
 modal('我的活动奖励','<div class="inventory-summary"><span>累计红包 <b>'+state.points+'</b></span><span>卡奖励 <b>'+state.cards.length+'</b>/4</span><span>群像点亮 <b>'+C.litCount(state)+'</b>/8</span></div><div class="inventory-grid"><div class="inventory-item"><strong>每日与日期好礼</strong><p>每日登录 '+state.login.length+' 份</p><p>日期限定 '+state.gifts.length+' 份</p></div><div class="inventory-item"><strong>红包成长奖励</strong><p>已领取 '+state.growth.length+' 份</p><p>每日红包 '+state.redDaily.length+' 份</p></div>'+entries.map(([name,status])=>'<div class="inventory-item"><strong>'+name+'</strong><p>'+status+'</p></div>').join('')+'</div><p class="rules-notice">所有奖励均为本机记录的占位内容，不发放真实游戏道具。参赛、兑换、点亮与自选分别记录。</p><div class="actions">'+btn('继续活动','close')+'</div>','inventory',true);
}
function beginMatch(options={}){
 if(ended()){toast('活动已结束，请切换至开放日期体验');return;}
 const nonce=String(Date.now())+'-'+(++serial)+'-'+Math.random().toString(36).slice(2);
 match={nonce,mode:options.mode||'attack',legend:options.legend,stage:options.stage,shots:[],goals:0,busy:false,keepers:[1,2,0]};renderMatch();
}
function renderMatch(){
 if(!match)return;const m=match,complete=m.shots.length===3,classic=m.mode==='classic',keeper=m.keepers[Math.min(2,m.shots.length)];
 modal(classic?'经典战役 · 本地点球挑战':'本地比赛 · 模拟有效结算',(!classic?'<div class="mode-options">'+C.modes.map(mode=>'<button data-action="mode" data-mode="'+mode.id+'" class="'+(m.mode===mode.id?'active':'')+'" '+(m.shots.length?'disabled':'')+'>'+mode.name+'</button>').join('')+'</div>':'<p>'+C.legends.find(l=>l.id===m.legend).name+' · 第'+(m.stage+1)+'阶段。至少两球判定挑战获胜。</p>')+'<div class="pitch"><div class="stands"></div><div class="goal-net"></div><div class="keeper" style="left:calc(50% + '+[-97,-14,69][keeper]+'px)"></div><div class="penalty-arc"></div><span class="ball" id="matchBall">⚽</span><span class="shot-label">本地简化演示 · 3轮点球</span><div class="shot-score">'+[0,1,2].map(i=>'<span class="'+(i<m.shots.length?(m.shots[i]?'goal':'miss'):'')+'">'+(i<m.shots.length?(m.shots[i]?'✓':'×'):'')+'</span>').join('')+'</div></div><div class="match-counter"><span>第 '+Math.min(3,m.shots.length+1)+' / 3 轮</span><span>进球 '+m.goals+'</span></div>'+(!complete?'<p class="match-help">观察守门员的位置，选择另一个方向射门。</p><div class="shoot-controls">'+['左路','中路','右路'].map((name,i)=>btn(name+'射门','shoot','data-dir="'+i+'"',m.busy,'secondary')).join('')+'</div>':'<p class="match-summary">'+(m.goals>=2?'漂亮，赢下本场挑战！':m.goals===1?'本场战平，仍是一场有效比赛。':'本场落败，下次继续！')+'</p><div class="actions">'+btn('完成比赛并结算','settle')+'</div>')+'<p class="rules-notice">'+(classic?'经典战役需获胜才推进，结束后仍要回活动页主动兑换升级。':'红包比赛不要求获胜。符合条件的已领活动球员会同时完成参赛任务。')+'取消或关闭不结算。</p>','match');
}
function shoot(dir){
 if(!match||match.busy||match.shots.length>=3||![0,1,2].includes(dir))return;
 const session=match;session.busy=true;document.querySelectorAll('[data-action="shoot"]').forEach(b=>b.disabled=true);
 const goal=dir!==session.keepers[session.shots.length];const ball=$('#matchBall');if(ball)ball.style.transform='translate('+[-105,0,105][dir]+'px,-140px) scale(.45)';
 setTimeout(()=>{if(match!==session||modalType!=='match')return;session.shots.push(goal);if(goal)session.goals++;session.busy=false;renderMatch();},400);
}
function settle(){
 if(!match||match.busy||match.shots.length!==3)return;const m=match;match=null;
 const r=perform({type:'MATCH',nonce:m.nonce,mode:m.mode,legend:m.legend,stage:m.stage,result:m.goals>=2?'win':m.goals===1?'draw':'loss'},false);
 if(r.ok)modal('比赛已结算','<p class="match-summary">'+esc(r.message)+'</p><p style="text-align:center">'+(m.mode==='classic'?'回到战役页，满足条件后主动兑换升级。':'继续领取卡奖励、红包成长奖励，或回个人页兑换升级。')+'</p><div class="actions">'+btn('返回活动','close')+'</div>','match-result');else close();
}
function resize(){const width=window.innerWidth,height=window.innerHeight,extra=width<700?112:82;const scale=Math.max(.1,Math.min(1.15,(width-32)/1280,(height-extra)/680));document.documentElement.style.setProperty('--scale',String(scale));}
document.addEventListener('click',e=>{
 if(e.target===$('#modalShade')){close();return;}
 const b=e.target.closest?.('[data-action]');if(!b||b.disabled)return;if(modalType&&!b.closest('.modal')&&b.dataset.action!=='close')return;
 const a=b.dataset.action,id=b.dataset.id;
 switch(a){
 case'home':ui.tab='gifts';ui.person=null;ui.legend=null;render();break;
 case'tab':ui.tab=b.dataset.tab;ui.person=null;ui.legend=null;render();break;
 case'close':close();break;
 case'rules':rules();break;
 case'calendar':calendar();break;
 case'day':{const day=+b.dataset.day;close();ui.giftFocus=Math.min(day,20);perform({type:'DAY',day},false);break;}
 case'inventory':inventory();break;
 case'login':perform({type:'LOGIN'});break;
 case'gift-detail':giftDetail(+b.dataset.day,+b.dataset.index);break;
 case'gift-claim':perform({type:'GIFT',day:+b.dataset.day,index:+b.dataset.index});break;
 case'gift-prev':ui.giftFocus=Math.max(0,ui.giftFocus-1);if($('#dateScroll'))$('#dateScroll').scrollLeft=ui.giftFocus*280;break;
 case'gift-next':ui.giftFocus=Math.min(20,ui.giftFocus+1);if($('#dateScroll'))$('#dateScroll').scrollLeft=ui.giftFocus*280;break;
 case'gift-today':ui.giftFocus=Math.min(20,state.day);if($('#dateScroll'))$('#dateScroll').scrollLeft=ui.giftFocus*280;break;
 case'red-daily':perform({type:'RED_DAILY'});break;
 case'red-card':perform({type:'RED_CARD',goal:+b.dataset.goal});break;
 case'red-growth':perform({type:'RED_GROWTH'});break;
 case'red-detail':{const goal=+b.dataset.goal;modal('累计 '+goal+' · 球员奖励','<div class="reward-results"><div>'+card('累计球员奖励','big')+'</div></div><p style="text-align:center">当前累计 '+state.points+'，领取不扣累计。</p><div class="actions">'+btn(state.cards.includes(goal)?'已领取':state.points>=goal?'领取奖励':'尚未达成','red-card','data-goal="'+goal+'"',!C.redOpen(state)||state.points<goal||state.cards.includes(goal))+'</div>','red-detail');break;}
 case'person':{const p=C.players.find(p=>p.id===id);if(!p)return;if(state.players[id].upgraded&&!state.players[id].lit&&C.starOpen(state,p)){perform({type:'LIGHT',id},false);}else{ui.person=id;render();}break;}
 case'person-back':ui.person=null;render();break;
 case'guess':guess(id);break;
 case'answer':{const r=C.apply(state,{type:'GUESS',id,answer:b.dataset.answer});if(!r.ok){b.classList.add('wrong');$('#guessHint').textContent=r.message;return;}state=r.state;save();render();b.classList.add('correct');modal('答对了！','<div class="reward-results"><div>'+card(C.players.find(p=>p.id===id).name,'big')+'</div></div><p style="text-align:center">球员已揭晓。回到个人页，主动领取神秘奖励中的球员。</p><div class="actions">'+btn('返回个人页领卡','close')+'</div>','guessed');break;}
 case'star-claim':perform({type:'STAR_CLAIM',id});break;
 case'star-up':perform({type:'STAR_UP',id});break;
 case'select':select(+b.dataset.goal);break;
 case'select-player':selected=id;selectModal();break;
 case'select-confirm':{const chosen=selected,goal=selectedGoal;selected=null;selectedGoal=null;perform({type:'SELECT',id:chosen,goal});break;}
 case'legend':ui.legend=id;ui.legendStage=Math.max(0,C.stage(state));render();break;
 case'legend-back':ui.legend=null;render();break;
 case'legend-stage':ui.legendStage=+b.dataset.stage;render();break;
 case'legend-get':buyLegend(id);break;
 case'buy-confirm':perform({type:'LEGEND_GET',id,confirm:true});break;
 case'legend-up':perform({type:'LEGEND_UP',id,stage:+b.dataset.stage});break;
 case'classic':beginMatch({mode:'classic',legend:id,stage:+b.dataset.stage});break;
 case'match':beginMatch();break;
 case'mode':if(match&&!match.shots.length){match.mode=b.dataset.mode;renderMatch();}break;
 case'shoot':shoot(+b.dataset.dir);break;
 case'settle':settle();break;
 case'reset':modal('重新开始体验','<p>清空本机的本次活动进度，并回到正月初一。此操作只影响这个演示。</p><div class="actions">'+btn('取消','close','','','secondary')+btn('确认重新开始','reset-confirm')+'</div>','reset');break;
 case'reset-confirm':close();ui.tab='gifts';ui.person=null;ui.legend=null;ui.giftFocus=7;perform({type:'RESET'},false);break;
 }
});
document.addEventListener('keydown',e=>{if(!modalType)return;if(e.key==='Escape'){e.preventDefault();close();}if(e.key==='Tab'){const all=[...$('.modal').querySelectorAll('button:not(:disabled),[tabindex="0"]')];if(!all.length)return;const first=all[0],last=all.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}});
window.addEventListener('resize',resize);resize();render();
})();
