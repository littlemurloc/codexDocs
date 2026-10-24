(function(root){
'use strict';
const dates=['腊月廿四','腊月廿五','腊月廿六','腊月廿七','腊月廿八','腊月廿九','除夕','正月初一','正月初二','正月初三','正月初四','正月初五','正月初六','正月初七','正月初八','正月初九','正月初十','正月十一','正月十二','正月十三','正月十四','活动结束'];
const modes=[{id:'attack',name:'进攻对战'},{id:'realtime',name:'实时对战'},{id:'manager',name:'经理人模式'}];
const players=[
{id:'vvd',name:'范戴克',day:7,number:4,color:'#bd2929',clue:'一件红色的4号球衣。后防线上的高塔，也是禁区里最可靠的守护者。',options:['范戴克','莫德里奇','孙兴慜']},
{id:'modric',name:'莫德里奇',day:7,number:10,color:'#ece7da',clue:'中场的节奏，总在他的脚下慢下来。一件10号球衣，写着细腻与从容。',options:['萨拉赫','莫德里奇','姆巴佩']},
{id:'kdb',name:'德布劳内',day:9,number:17,color:'#79b8d9',clue:'一件天蓝色的17号球衣。请跟随那脚穿过防线的传球，找到这位中场创造者。',options:['德布劳内','范戴克','格列兹曼']},
{id:'salah',name:'萨拉赫',day:11,number:11,color:'#c42d2d',clue:'红色的11号球衣，在右路划出弧线。速度、内切、射门，都是他的语言。',options:['孙兴慜','萨拉赫','莫德里奇']},
{id:'son',name:'孙兴慜',day:13,number:7,color:'#efefef',clue:'白色的7号球衣，带着熟悉的笑容。双脚都能完成终结，冲刺时总是格外坚决。',options:['姆巴佩','德布劳内','孙兴慜']},
{id:'griezmann',name:'格列兹曼',day:15,number:7,color:'#8a262d',clue:'一件7号球衣，一位游走在锋线与中场之间的创造者。捕捉空间，是他的拿手好戏。',options:['格列兹曼','范戴克','萨拉赫']},
{id:'ronaldo',name:'C罗',day:17,number:7,color:'#c83037',clue:'7号背影再次站上禁区。起跳、滞空、终结，信念藏在每一次跑动里。',options:['莫德里奇','C罗','孙兴慜']},
{id:'mbappe',name:'姆巴佩',day:19,number:10,color:'#263a78',clue:'深蓝色的10号球衣，像一道掠过边线的闪电。防线还没转身，他已跑向下一片空间。',options:['萨拉赫','格列兹曼','姆巴佩']}
];
const legends=[{id:'pele',name:'贝利',tag:'三次捧杯，传奇加冕。',paid:false,title:'三冠加冕',story:'从故事走进球场，重温贝利的经典决赛舞台。先完成本地挑战，再回到这里兑换本阶段升级。'},{id:'maradona',name:'马拉多纳',tag:'一场比赛，两个传奇瞬间。',paid:false,title:'蓝白传奇',story:'以突破和创造力为线索，走进马拉多纳的经典战役。正式比赛选题与条件待确认，本页演示挑战和升级的先后关系。'},{id:'messi',name:'梅西',tag:'终章捧杯，梦想成真。',paid:true,title:'梦想加冕',story:'以冠军之夜为背景，走进梅西的经典战役。正式对阵与难度待确认，本页用本地点球演示获胜和升级兑换。'}];
const cardGoals=[60,140,240,360],growthGoals=[100,220,360],collectGoals=[3,8],stageDays=[7,13,19];
const own=()=>({revealed:false,claimed:false,played:false,upgraded:false,lit:false,self:false});
const fresh=()=>({version:1,day:7,login:[],gifts:[],redDaily:[],points:0,firsts:{},cards:[],growth:[],players:Object.fromEntries(players.map(p=>[p.id,own()])),legends:Object.fromEntries(legends.map(p=>[p.id,{owned:false,won:[],redeemed:[]} ])),selections:[],matches:[],matchCount:0});
const num=(v,min,max,fallback=0)=>Number.isFinite(v)?Math.max(min,Math.min(max,Math.floor(v))):fallback;
const unique=(v,test)=>Array.isArray(v)?[...new Set(v.filter(test))]:[];
function restore(input){
 const s=fresh();if(!input||typeof input!=='object')return s;
 s.day=num(input.day,0,21,7);s.points=num(input.points,0,100000);s.matchCount=num(input.matchCount,0,100000);
 s.login=unique(input.login,n=>Number.isInteger(n)&&n>=0&&n<=20);s.redDaily=unique(input.redDaily,n=>Number.isInteger(n)&&n>=6&&n<=20);
 s.gifts=unique(input.gifts,v=>typeof v==='string'&&/^\d{1,2}:\d$/.test(v)&&+v.split(':')[0]<=20&&+v.split(':')[1]<giftCount(+v.split(':')[0]));
 s.cards=unique(input.cards,n=>cardGoals.includes(n)&&s.points>=n);s.growth=unique(input.growth,n=>growthGoals.includes(n)&&s.points>=n);
 for(let day=6;day<=20;day++){const f=input.firsts?.[day];if(Array.isArray(f))s.firsts[day]=unique(f,id=>modes.some(m=>m.id===id));}
 for(const p of players){const a=input.players?.[p.id];if(a&&typeof a==='object'){const t=s.players[p.id];t.revealed=a.revealed===true;t.claimed=t.revealed&&a.claimed===true;t.played=t.claimed&&a.played===true;t.upgraded=t.played&&a.upgraded===true;t.lit=t.upgraded&&a.lit===true;t.self=t.upgraded&&a.self===true;}}
 for(const l of legends){const a=input.legends?.[l.id];if(a&&typeof a==='object'){const t=s.legends[l.id];t.owned=a.owned===true;t.won=t.owned?unique(a.won,n=>[0,1,2].includes(n)):[];t.redeemed=t.owned?unique(a.redeemed,n=>t.won.includes(n)):[];}}
 s.selections=unique(input.selections,n=>collectGoals.includes(n)&&litCount(s)>=n);s.matches=unique(input.matches,id=>typeof id==='string'&&id.length<100).slice(-2000);return s;
}
function giftCount(day){return day===6?6:2;}
function active(s){return s.day<=20;}
function redOpen(s){return s.day>=6&&active(s);}
function starOpen(s,p){return s.day>=p.day&&active(s);}
function litCount(s){return players.filter(p=>s.players[p.id].lit).length;}
function stage(s){return s.day>=19?2:s.day>=13?1:s.day>=7?0:-1;}
function starStatus(s,p){const a=s.players[p.id];if(a.lit)return'已点亮';if(a.upgraded)return'已兑换待点亮';if(a.played)return'可兑换升级';if(a.claimed)return'已领卡待参赛';return a.revealed?'已揭晓待领卡':'未揭晓';}
function apply(current,a){
 const s=restore(current);let message='',rewards=[];
 const fail=message=>({state:current,ok:false,message,rewards:[]});
 if(!a||typeof a.type!=='string')return fail('操作无效');
 if(a.type==='DAY'){s.day=num(a.day,0,21,s.day);return{state:s,ok:true,message:'已切换至'+dates[s.day],rewards:[]};}
 if(a.type==='RESET')return{state:fresh(),ok:true,message:'已重新开始演示',rewards:[]};
 if(!active(s))return fail('活动已结束，当前演示关闭领取与任务结算');
 const p=players.find(p=>p.id===a.id),v=p?s.players[p.id]:null;
 const l=legends.find(l=>l.id===a.id),lv=l?s.legends[l.id]:null;
 switch(a.type){
 case'LOGIN':if(s.login.includes(s.day))return fail('今天的登录礼已领取');s.login.push(s.day);rewards=['每日登录奖励 ×1'];break;
 case'GIFT':{const day=+a.day,index=+a.index,key=day+':'+index;if(day!==s.day||index<0||!Number.isInteger(index)||index>=giftCount(day))return fail(day<s.day?'这份日期礼已过期':'请在对应日期领取');if(s.gifts.includes(key))return fail('这份奖励已领取');s.gifts.push(key);rewards=['日期限定奖励 ×1'];break;}
 case'RED_DAILY':if(!redOpen(s))return fail('除夕起开放');if(s.redDaily.includes(s.day))return fail('今日红包已领取');s.redDaily.push(s.day);s.points+=20;rewards=['每日红包 +20累计'];break;
 case'RED_CARD':if(!redOpen(s)||!cardGoals.includes(a.goal)||s.points<a.goal)return fail('还未达到累计目标');if(s.cards.includes(a.goal))return fail('该卡奖励已领取');s.cards.push(a.goal);rewards=['累计球员奖励 ×1'];break;
 case'RED_GROWTH':{if(!redOpen(s))return fail('当前不可领取');const can=growthGoals.filter(g=>s.points>=g&&!s.growth.includes(g));if(!can.length)return fail('暂无待领的成长奖励');s.growth.push(...can);rewards=can.map((_,i)=>'红包成长奖励 ×1');break;}
 case'GUESS':if(!p||!starOpen(s,p))return fail('人物尚未开放');if(v.revealed)return fail('人物已经揭晓');if(a.answer!==p.name)return fail('再想一想，可以立即重新选择');v.revealed=true;message='答对了！回到个人页主动领取球员';break;
 case'STAR_CLAIM':if(!p||!starOpen(s,p)||!v.revealed)return fail('先答对竞猜，再来领卡');if(v.claimed)return fail('球员已领取');v.claimed=true;rewards=[p.name+' · 活动球员占位卡'];break;
 case'STAR_UP':if(!p||!starOpen(s,p)||!v.played)return fail('领取球员后参加一场有效比赛');if(v.upgraded)return fail('个人升级已兑换');v.upgraded=true;rewards=[p.name+' · 个人升级'];break;
 case'LIGHT':if(!p||!starOpen(s,p)||!v.upgraded)return fail('兑换个人升级后，再回总览点亮');if(v.lit)return fail('该人物已经点亮');v.lit=true;message=p.name+'已点亮，当前 '+litCount(s)+'/8';break;
 case'SELECT':if(!p||!v.upgraded||v.self)return fail('请选择已兑换个人升级、且尚未使用自选的球员');if(!collectGoals.includes(a.goal)||litCount(s)<a.goal||s.selections.includes(a.goal))return fail('该自选机会尚不可用');s.selections.push(a.goal);v.self=true;rewards=[p.name+' · 自选升级'];break;
 case'LEGEND_GET':if(!l||stage(s)<0)return fail('三羊开泰尚未开放');if(lv.owned)return fail('已获取该球员');if(l.paid&&a.confirm!==true)return fail('请先确认模拟购买');lv.owned=true;rewards=[l.name+' · 初始球员占位卡'];break;
 case'LEGEND_UP':if(!l||!Number.isInteger(a.stage)||a.stage<0||a.stage>stage(s)||!lv.owned||!lv.won.includes(a.stage))return fail('先获取球员，并赢下对应阶段挑战');if(lv.redeemed.includes(a.stage))return fail('本阶段升级已兑换');lv.redeemed.push(a.stage);rewards=[l.name+' · 第'+(a.stage+1)+'阶段升级'];break;
 case'MATCH':{
 if(typeof a.nonce!=='string'||!a.nonce||a.nonce.length>=100||s.matches.includes(a.nonce))return fail('该比赛已经结算或无效');
 if(!['win','draw','loss'].includes(a.result))return fail('比赛结果无效');
 if(a.mode==='classic'){
  const target=legends.find(l=>l.id===a.legend),t=target?s.legends[target.id]:null;
  if(!t?.owned||!Number.isInteger(a.stage)||a.stage<0||a.stage>stage(s))return fail('挑战尚未开放或未获取初始球员');
  if(a.result==='win'&&!t.won.includes(a.stage))t.won.push(a.stage);
  message=a.result==='win'?'挑战获胜！返回战役页主动兑换升级':'本场未获胜，可再次挑战';
 }else{
  if(!modes.some(m=>m.id===a.mode))return fail('比赛模式无效');
  let gain=0;if(redOpen(s)){const list=s.firsts[s.day]??=[];const first=!list.includes(a.mode);gain=first?60:20;if(first)list.push(a.mode);s.points+=gain;}
  let advanced=0;for(const p of players){const t=s.players[p.id];if(starOpen(s,p)&&t.claimed&&!t.played){t.played=true;advanced++;}}
  message='比赛已结算'+(gain?'，红包累计 +'+gain:'')+(advanced?'，'+advanced+'名球员参赛任务完成':'');
 }
 s.matches.push(a.nonce);s.matches=s.matches.slice(-2000);s.matchCount++;break;
 }
 default:return fail('未知操作');
 }
 return{state:s,ok:true,message:message||(rewards.length?'奖励已领取':'操作完成'),rewards};
}
root.SpringCore={dates,modes,players,legends,cardGoals,growthGoals,collectGoals,stageDays,fresh,restore,apply,giftCount,active,redOpen,starOpen,litCount,stage,starStatus};
})(globalThis);
