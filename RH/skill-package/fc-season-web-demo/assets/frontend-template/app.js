(() => {
  'use strict';
  const c=JSON.parse(document.getElementById('season-config').textContent);
  const $=id=>document.getElementById(id),esc=value=>String(value).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const key='fc-season-demo:'+c.id,routeIds=c.routes.map(r=>r.id),drillIds=c.drills.map(d=>d.id);
  const initial=()=>({points:c.initialPoints,tokens:c.initialTokens,trained:[],claimed:[],daily:false,matches:0,route:routeIds[0],partner:false,partnerRoute:null});
  const storage={get(){try{return localStorage.getItem(key);}catch{return null;}},set(v){try{localStorage.setItem(key,v);return true;}catch{return false;}},clear(){try{localStorage.removeItem(key);}catch{}}};
  const normalize=s=>{
    const n=initial();if(!s||typeof s!=='object'||Array.isArray(s))return n;
    for(const k of ['points','tokens','matches'])if(Number.isSafeInteger(s[k])&&s[k]>=0)n[k]=Math.min(s[k],k==='matches'?c.matchesRequired:1000000);
    if(Array.isArray(s.trained))n.trained=[...new Set(s.trained.filter(id=>drillIds.includes(id)))];
    if(Array.isArray(s.claimed))n.claimed=[...new Set(s.claimed.filter(i=>Number.isInteger(i)&&i>=0&&i<c.milestones.length))];
    n.daily=s.daily===true;if(routeIds.includes(s.route))n.route=s.route;
    if(s.partner===true&&routeIds.includes(s.partnerRoute)){n.partner=true;n.partnerRoute=s.partnerRoute;}
    if(n.points<c.coreThreshold||n.matches<c.matchesRequired)n.claimed=n.claimed.filter(i=>i!==c.milestones.length-1);
    return n;
  };
  let state;try{state=normalize(JSON.parse(storage.get()));}catch{state=initial();}
  let active='overview',kind=null,live=null,pendingMatch=null,generation=0,raf=0,shotTimer=0,toastTimer=0;
  const persist=()=>{if(!storage.set(JSON.stringify(state)))$('status-line').textContent='存储不可用，本轮仍可继续体验';};
  const route=()=>c.routes.find(r=>r.id===state.route),coreReady=()=>state.points>=c.coreThreshold&&state.matches>=c.matchesRequired;
  const coreClaimed=()=>state.claimed.includes(c.milestones.length-1),percent=()=>Math.min(100,Math.floor(state.points/c.coreThreshold*100));
  const button=(label,action,style='primary',attrs='')=>`<button class="${style}" data-action="${action}" ${attrs}>${esc(label)}</button>`;
  const note=()=>'<p class="note">本地交互样板，奖励和比赛均为模拟。每轮补给限领一次，可重置体验。</p>';
  const toast=t=>{$('toast').textContent=t;$('toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('visible'),2100);};
  const stop=()=>{generation++;cancelAnimationFrame(raf);clearTimeout(shotTimer);raf=0;shotTimer=0;live=null;pendingMatch=null;kind=null;};
  const close=()=>{stop();if(typeof $('dialog').close==='function')$('dialog').close();else $('dialog').removeAttribute('open');};
  const modal=(title,body,type='summary')=>{stop();kind=type;$('dialog-body').innerHTML=`<span class="modal-eyebrow">SEASON DEMO</span><h2 id="dialog-title">${esc(title)}</h2>${body}`;if(!$('dialog').hasAttribute('open')){if(typeof $('dialog').showModal==='function')$('dialog').showModal();else $('dialog').setAttribute('open','');}};
  const navItems=[['overview','赛季大厅'],['training','主题训练'],['partners','最佳搭档'],['journey','赛季征程'],['final','冠军之夜']];
  function render(){
    $('topstats').innerHTML=`<span>${esc(c.pointLabel)}<b>${state.points.toLocaleString()}</b></span><span>${esc(c.tokenLabel)}<b>${state.tokens}</b></span>`;
    $('navigation').innerHTML=navItems.map(([id,label])=>`<button data-tab="${id}" class="${active===id?'active':''}" aria-current="${active===id?'page':'false'}">${label}</button>`).join('');
    let h='';
    if(active==='overview')h=`<div class="hero"><p class="eyebrow">${esc(c.durationDays)} DAY CONCEPT / ${esc(c.subtitle)}</p><h1>${esc(c.title)}</h1><p class="intro">${esc(c.heroCopy)}</p><div class="actions">${button('开始今日训练','go-training')}${button(state.daily?'本轮补给已领取':'领取本轮补给','daily','secondary',state.daily?'disabled':'')}</div><div class="daily-list"><span class="${state.daily?'done':''}">${state.daily?'✓':'○'} 领取补给</span><span class="${state.trained.length>=2?'done':''}">${state.trained.length>=2?'✓':'○'} 完成两项训练</span><span class="${state.matches===c.matchesRequired?'done':''}">${state.matches===c.matchesRequired?'✓':'○'} 完成冠军挑战</span></div><div class="core-card"><span class="small">${esc(c.rewardLabel)} / CONCEPT</span><h2>${esc(c.corePlayer)}</h2><p>累计达到 ${c.coreThreshold} ${esc(c.pointLabel)}<br>并完成 ${c.matchesRequired} 场冠军挑战</p><div class="progress"><span style="width:${percent()}%"></span></div><div class="progress-caption"><span>${state.points} / ${c.coreThreshold}</span><b>${percent()}%</b></div>${button(coreClaimed()?'球员已领取':'查看奖励征程','go-journey','secondary')}</div></div>`;
    if(active==='training')h=`<div class="inner"><div class="page-heading"><div><h1>主题训练</h1><p>每项完成三次射门，首次完成获得奖励。再次练习不重复发放。</p></div><span class="eyebrow">${state.trained.length} / ${c.drills.length} COMPLETED</span></div><div class="drills">${c.drills.map((d,i)=>`<article class="panel"><span class="number">0${i+1}</span><h2>${esc(d.name)}</h2><p>${esc(d.description)}</p><div class="reward">${state.trained.includes(d.id)?'首次奖励已领取':`首次完成 +${d.points} ${esc(c.pointLabel)}`}</div>${button(state.trained.includes(d.id)?'再次练习':'开始训练','drill','primary',`data-id="${d.id}"`)}</article>`).join('')}</div></div>`;
    if(active==='partners')h=`<div class="inner"><div class="page-heading"><div><h1>最佳搭档</h1><p>选择进攻路线，查看对应任务与搭档类型。</p></div>${button(state.partner?'搭档已兑换':`兑换搭档 · ${c.partnerCost} ${c.tokenLabel}`,'partner','secondary',state.partner?'disabled':'')}</div><div class="routes">${c.routes.map((r,i)=>`<article class="panel ${state.route===r.id?'selected':''}">${state.route===r.id?'<span class="selected-text">当前路线</span>':''}<span class="number">0${i+1}</span><h2>${esc(r.name)}</h2><p>${esc(r.description)}</p><div class="route-task">${esc(r.task)}</div>${button(state.route===r.id?'已选择':'选择路线','route',state.route===r.id?'secondary':'primary',`data-id="${r.id}"`)}</article>`).join('')}</div>${note()}</div>`;
    if(active==='journey')h=`<div class="inner"><div class="journey-head"><div><h1>赛季征程</h1><p>累计领奖不扣除${esc(c.pointLabel)}，末节点还需要完成冠军挑战。</p></div><b>${state.points} / ${c.coreThreshold}</b></div><div class="progress"><span style="width:${percent()}%"></span></div><div class="journey-track">${c.milestones.map((m,i)=>{const claimed=state.claimed.includes(i),last=i===c.milestones.length-1,ready=state.points>=m.at&&(!last||coreReady());return `<article class="node ${claimed?'claimed':''}"><div class="node-symbol">${claimed?'✓':String(i+1).padStart(2,'0')}</div><h2>${esc(last?c.corePlayer:m.name)}</h2><p>${m.at} ${esc(c.pointLabel)}${last?`<br>${c.matchesRequired} 场冠军挑战`:''}</p>${button(claimed?'已领取':ready?'领取奖励':'查看条件','node',ready?'primary':'secondary',`data-index="${i}" ${claimed?'disabled':''}`)}</article>`;}).join('')}</div>${note()}</div>`;
    if(active==='final')h=`<div class="inner"><div class="page-heading"><div><h1>冠军之夜</h1><p>先完成至少一项训练，然后挑战 ${c.matchesRequired} 场比赛。比赛用简化结算演示。</p></div></div><div class="final-layout"><div class="final-art"><span class="eyebrow">FINAL CHALLENGE</span><div class="big">${String(state.matches).padStart(2,'0')} / ${String(c.matchesRequired).padStart(2,'0')}</div><h2>${esc(route().name)}</h2><p>${esc(route().task)}</p><div class="final-steps">${Array.from({length:c.matchesRequired},(_,i)=>`<span class="final-step ${i<state.matches?'won':''}">${i<state.matches?'✓':i+1}</span>`).join('')}</div></div><div class="final-right"><h2>每场胜利奖励</h2><p>+${c.matchPoints} ${esc(c.pointLabel)}<br>+${c.matchTokens} ${esc(c.tokenLabel)}</p>${button(state.matches===c.matchesRequired?'前往领取球员':'开始下一场',state.matches===c.matchesRequired?'go-journey':'match')}<p class="note">当前路线决定本场任务说明。此样板不包含真实足球比赛引擎。</p></div></div></div>`;
    $('content').innerHTML=h;
  }
  const navigate=id=>{if(!navItems.some(([key])=>key===id))return;close();active=id;render();$('content').scrollTop=0;};
  function drill(id){
    const d=c.drills.find(d=>d.id===id);if(!d)return;
    modal(d.name,`<p>${esc(d.description)}</p><div class="pitch" id="pitch"><div class="goal"></div><div class="ball"></div></div><div class="meter"><span class="target" style="left:${d.targetStart}%;width:${d.targetEnd-d.targetStart}%"></span><span class="cursor" id="cursor"></span></div><div class="training-info"><span id="shots">射门 0 / 3</span><span id="goals">命中 0</span></div><div class="feedback" id="feedback">观察亮起的目标区间，点击射门。</div>${button('射门','shoot','primary','id="shoot-button"')}`,'training');
    const token=generation;live={id,shots:0,goals:0,locked:false,start:Date.now(),token};
    const frame=()=>{if(!live||kind!=='training'||token!==generation)return;const pos=((Date.now()-live.start)%1600)/16;$('cursor').style.left=pos+'%';raf=requestAnimationFrame(frame);};raf=requestAnimationFrame(frame);
  }
  function shoot(){
    if(!live||kind!=='training'||live.locked)return;
    const d=c.drills.find(d=>d.id===live.id),pos=((Date.now()-live.start)%1600)/16,hit=pos>=d.targetStart&&pos<=d.targetEnd;
    live.locked=true;live.shots++;if(hit)live.goals++;$('shots').textContent=`射门 ${live.shots} / 3`;$('goals').textContent=`命中 ${live.goals}`;$('feedback').textContent=hit?'漂亮的终结！':'再观察一下出脚时机。';$('shoot-button').disabled=true;$('pitch').classList.add('kick');
    const token=generation;
    shotTimer=setTimeout(()=>{
      if(!live||kind!=='training'||token!==generation)return;
      if(live.shots===3){const goals=live.goals,first=!state.trained.includes(d.id);if(first){state.trained.push(d.id);state.points+=d.points;persist();}render();modal('训练完成',`<p>完成三次射门，命中 ${goals} 次。</p><div class="reward-total">${first?`+${d.points} ${esc(c.pointLabel)}`:'本项首次奖励已领取'}</div><p>再次练习可以继续体验，不会重复发放首次奖励。</p>${button('返回活动','close')}`);}
      else{live.locked=false;$('shoot-button').disabled=false;$('pitch').classList.remove('kick');}
    },180);
  }
  function match(){
    if(state.matches>=c.matchesRequired)return;
    if(!state.trained.length){toast('先完成一项训练，再进入冠军挑战');return;}
    modal(`冠军挑战 · 第 ${state.matches+1} 场`,`<p>当前路线：${esc(route().name)}</p><p>本场目标：${esc(route().task)}</p><p>本地样板用结果结算代替真实比赛。确认完成后领取本场奖励。</p><div class="reward-total">+${c.matchPoints} ${esc(c.pointLabel)}　+${c.matchTokens} ${esc(c.tokenLabel)}</div>${button('完成比赛并结算','finish-match')}`,'match');pendingMatch=state.matches;
  }
  function finishMatch(){
    if(kind!=='match'||pendingMatch!==state.matches||state.matches>=c.matchesRequired)return;
    state.matches++;state.points+=c.matchPoints;state.tokens+=c.matchTokens;persist();render();modal(state.matches===c.matchesRequired?'冠军挑战全部完成':'比赛胜利',`<div class="reward-total">+${c.matchPoints} ${esc(c.pointLabel)}</div><p>冠军挑战进度：${state.matches} / ${c.matchesRequired}</p>${button('领取并继续','close')}`);
  }
  function node(index){
    const m=c.milestones[index];if(!m||state.claimed.includes(index))return;
    const last=index===c.milestones.length-1;
    if(state.points<m.at||(last&&!coreReady())){modal('奖励获取条件',`<p>累计达到 ${m.at} ${esc(c.pointLabel)}${last?`，并完成 ${c.matchesRequired} 场冠军挑战`:''}。</p><p>当前为 ${state.points} 点、${state.matches} 场。累计领奖不会扣点。</p>${button('继续挑战','close')}`);return;}
    state.claimed.push(index);persist();render();modal(last?'核心球员已领取':'阶段奖励已领取',`<div class="reward-total">${esc(last?c.corePlayer:m.name)}</div><p>奖励已记录在本地演示进度中。该节点不会重复发奖。</p>${button('继续征程','close')}`);
  }
  function rules(){modal('活动规则与演示范围',`<p>主题：${esc(c.theme)}。周期 ${c.durationDays} 天为设计假设，模板不模拟真实服务器日历。</p><p>加速体验从 ${c.initialPoints} ${esc(c.pointLabel)}、${c.initialTokens} ${esc(c.tokenLabel)} 开始。本轮补给 +${c.dailyReward} 点，三项训练各发首次奖励，冠军挑战每场 +${c.matchPoints} 点及 ${c.matchTokens} 枚徽记。</p><p>累计 ${c.coreThreshold} 点并完成 ${c.matchesRequired} 场冠军挑战，可领取${esc(c.corePlayer)}。征程领奖不扣点，兑换搭档消耗 ${c.partnerCost} 枚徽记。</p><p>每日补给在每轮演示中限领一次，可重置后重新体验。比赛采用简化结算，不代表完整足球引擎。图像来源：${esc(c.visualNote)}。</p><p>${c.stage==='starter'?'当前是通用起步模板，尚未完成独立主题设计。':'当前为原创活动概念，数值与内容不代表官方已上线活动。'}</p>${button('开始体验','close')}`);}
  document.addEventListener('click',e=>{
    const b=e.target.closest('button');if(!b||b.disabled)return;
    if(b.dataset.tab){navigate(b.dataset.tab);return;}
    switch(b.dataset.action){
      case 'go-training':navigate('training');break;case 'go-journey':navigate('journey');break;
      case 'daily':if(!state.daily){state.daily=true;state.points+=c.dailyReward;persist();render();toast('本轮补给已领取');}break;
      case 'drill':drill(b.dataset.id);break;case 'shoot':shoot();break;
      case 'route':if(routeIds.includes(b.dataset.id)){state.route=b.dataset.id;persist();render();toast('已选择 '+route().name);}break;
      case 'partner':if(!state.partner)modal('兑换进攻搭档',`<p>当前路线：${esc(route().name)}</p><div class="reward-total">${esc(route().partner)}</div><p>消耗 ${c.partnerCost} ${esc(c.tokenLabel)}，当前持有 ${state.tokens}。</p>${button(state.tokens<c.partnerCost?'徽记不足':'确认兑换','exchange','primary',state.tokens<c.partnerCost?'disabled':'')}`,'exchange');break;
      case 'exchange':if(kind==='exchange'&&!state.partner&&state.tokens>=c.partnerCost){state.tokens-=c.partnerCost;state.partner=true;state.partnerRoute=state.route;persist();close();render();toast('搭档已加入球队');}break;
      case 'node':node(Number(b.dataset.index));break;case 'match':match();break;case 'finish-match':finishMatch();break;
      case 'close':close();break;case 'rules':rules();break;
      case 'reset':modal('重置本轮体验',`<p>清除这套活动的本地演示进度，重新领取奖励。</p>${button('确认重置','reset-confirm')}`,'reset');break;
      case 'reset-confirm':if(kind==='reset'){storage.clear();state=initial();close();active='overview';render();toast('体验已重置');}break;
    }
  });
  $('dialog').addEventListener('cancel',e=>{e.preventDefault();close();});
  const fit=()=>{const scale=Math.min((window.innerWidth-24)/1200,(window.innerHeight-62)/660,1);$('phone').style.transform=`scale(${Math.max(.1,scale)})`;$('phone-wrap').style.width=1200*Math.max(.1,scale)+'px';$('phone-wrap').style.height=660*Math.max(.1,scale)+'px';};
  document.documentElement.style.setProperty('--accent',c.accent);document.documentElement.style.setProperty('--gold',c.gold);
  $('season-title').textContent=c.title;$('season-subtitle').textContent=c.subtitle;$('demo-label').textContent=c.theme+' · 手机预览';document.title=c.title+' · 离线演示';
  window.addEventListener('resize',fit);window.addEventListener('pagehide',()=>{stop();clearTimeout(toastTimer);});
  window.SeasonDemo={snapshot:()=>JSON.parse(JSON.stringify(state)),navigate,dispose:()=>{stop();clearTimeout(toastTimer);window.removeEventListener('resize',fit);}};
  render();fit();
})();
