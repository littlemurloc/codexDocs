import fs from 'node:fs/promises';
import path from 'node:path';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {GlobalFonts}=require('@napi-rs/canvas');
GlobalFonts.registerFromPath('C:/Windows/Fonts/msyh.ttc','Microsoft YaHei');
const root='D:/codex/RH/fc-pitch';
const fontPolicy={basis:'design',families:['Microsoft YaHei']};
const F='Microsoft YaHei';
const C={bg:'#09141E',white:'#EDF4F8',body:'#ACBDC9',cyan:'#7CE1E9',gold:'#EDC985',table:'#102331',header:'#193645'};
// The provided file has no slides. Its canvas was read from presentation.xml.
const p=Presentation.create({slideSize:{width:1280,height:720}});
const layout=p.layouts.add('FC season proposal');
if(p.masters.items.length)layout.setParentLayoutId(p.masters.items[0].id);
await fs.mkdir(root+'/.build/render',{recursive:true});
const text=(slide,name,value,x,y,w,h,size=26,color=C.body,bold=false)=>{
 const s=slide.shapes.add({name,geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 s.text=value;s.text.style={typeface:F,fontSize:size,color,bold,alignment:'left',verticalAlignment:'top',autoFit:'none',insets:0,wrap:'square'};return s;
};
const note=(slide,value)=>{slide.speakerNotes.text=value;};
const page=(title,n,lead='')=>{
 const s=p.slides.add({layoutId:layout.id});s.background.fill=C.bg;
 text(s,'slide-title',title,72,52,1136,72,44,C.white,true);
 if(lead)text(s,'lead',lead,72,132,1136,68,25,C.body);
 text(s,'page-number',String(n).padStart(2,'0'),1170,675,40,25,16,'#537180');return s;
};
const image=async(slide,file,x,y,w,h,alt,crop)=>{const b=await fs.readFile(file);return slide.images.add({blob:b,contentType:file.endsWith('.png')?'image/png':'image/jpeg',position:{left:x,top:y,width:w,height:h},fit:'cover',alt,...(crop?{crop}:{})});};
const table=(slide,values,widths,top=210,height=390)=>{
 const t=slide.tables.add({rows:values.length,columns:values[0].length,left:72,top,width:1136,height,columnWidths:widths,values});
 t.styleOptions={headerRow:false,bandedRows:false};
 t.borders.assign({fill:'#294250',width:.7,style:'solid'});
 t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({fill:C.table,textStyle:{typeface:F,fontSize:23,color:C.white},margins:{top:12,bottom:10,left:18,right:18},anchor:'middle'});
 for(let r=0;r<values.length;r++){t.rows[r].height=height/values.length;for(let c=0;c<values[0].length;c++){const cell=t.getCell(r,c);cell.text.style={typeface:F,fontSize:r===0?23:22.8,color:r===0?C.cyan:C.white,bold:r===0,alignment:'left',verticalAlignment:'middle',insets:{top:9,bottom:9,left:16,right:16}};if(r===0)cell.fill=C.header;}}
 return t;
};
const hero='D:/codex/RH/haaland-offline/assets/haaland-stadium.png';

// 01
{
 const s=p.slides.add({layoutId:layout.id});s.background.fill=C.bg;
 await image(s,hero,0,0,1280,720,'哈兰德主题AI生成球场背景');
 text(s,'client-title','FC 足球世界',72,74,620,56,32,C.cyan,true);
 text(s,'cover-title','赛季活动设计\n合作提案',72,202,690,202,72,C.white,true);
 text(s,'cover-subtitle','通过一期试点，建立持续的活动内容交付合作',76,444,670,92,27,C.body);
 text(s,'discussion-label','合作讨论稿',76,626,350,32,19,C.gold);
 note(s,'开场：建议从一期试点开始，评估我们承担赛季主题、章节玩法、任务奖励和活动体验设计的方式。团队履历、人员配置和报价需在对外提交前补充。\n视觉素材：D:/codex/RH/haaland-offline/assets/haaland-stadium.png，为本项目AI生成概念素材，不是官方宣传图。\n用户提供的空白文件画布为12192000×6858000 EMU，沿用16:9尺寸。');
}
// 02
{
 const s=page('现有活动的组织方式',2,'根据公开活动样本归纳：主题提供表达，球员获取和球队成长串联体验。');
 const rows=[['主题','年度荣誉、真实赛事、传奇球星与节日庆典'],['参与','登录、训练、比赛、任务与主题互动'],['推进','代币、路径、拼图、里程碑与阶段开放'],['奖励','球员、交换资格、养成资源与展示内容'],['节奏','每日参与、每周更新、整期目标']];
 rows.forEach(([a,b],i)=>{const y=228+i*75;text(s,'framework-'+i,a,76,y,140,45,30,C.cyan,true);text(s,'framework-desc-'+i,b,250,y+3,935,45,26,C.white);});
 text(s,'sample-caveat','公开样本的设计归纳，具体机制随活动变化',76,636,1080,30,18,'#74909F');
 note(s,'这不是对内部运营效果的判断，而是对公开活动结构的归纳。2025年度最佳包含多章节、代币路径、拼图和球员交换；春节活动包含登录、累计进度和主题挑战。\n来源：EA SPORTS，2025年度最佳活动介绍，https://www.weibo.com/ttarticle/p/show?id=2309405127089513955762\n来源：FC足球世界，马年春节活动公告，https://www.taptap.cn/moment/771064711469861731');
}
// 03
{
 const s=page('合作目标',3,'每期主题形成明确的参与体验，交付内容能够排期、制作和验收。');
 const items=[['主题表达','将主题落实到章节目标与玩家选择，\n让球星特色影响参与方式。'],['制作明确','同步交付规则、字段、界面状态与素材需求，\n提前识别制作依赖。'],['持续更新','将整期目标拆到每周内容与每日循环，\n保持奖励路径清晰。'],['结果复盘','通过参与、完成和交付记录，\n提出下一期的具体调整。']];
 items.forEach(([a,b],i)=>{const x=i%2?665:76,y=i<2?252:445;text(s,'goal-title-'+i,a,x,y,510,52,33,C.cyan,true);text(s,'goal-body-'+i,b,x,y+65,520,100,24,C.body);});
 note(s,'这里列的是合作希望实现的目标，不是已有业绩，也没有承诺具体留存或收入增幅。需要在试点前与FC团队确认优先目标，并在复盘时验证。');
}
// 04
{
 const s=page('合作范围与决策分工',4,'首期以活动内容设计为主，配置制作与上线执行按工具、权限和人员逐步扩大。');
 table(s,[['工作','我们拟承担','FC团队确认或决策'],['主题与玩法','概念、章节及内容清单','方向、档期与系统限制'],['任务与奖励','规则、配置建议及测算','经济、评级与投放审批'],['活动 UI/UX','流程、原型及素材需求','设计规范与制作标准'],['制作与验收','配置映射、修订与内容验收','客户端、服务端及版本接入'],['上线与复盘','观察结果、分析及调整建议','发布审批与线上变更权限']],[200,464,472],218,397);
 note(s,'我们提出的是设计与制作配合的责任范围。FC团队继续掌握产品方向、球员经济和版本发布的最终决策。进入配置制作或上线执行前，需要确认可用工具、权限、负责人和验收机制。');
}
// 05
{
 const s=page('每期的交付清单',5);
 text(s,'delivery-headline','一套可以进入\n制作评审的设计包',76,220,465,155,44,C.white,true);
 text(s,'delivery-context','交付颗粒度与对方模板对齐。\n新增系统能力单独提出需求。',78,420,465,110,25,C.body);
 const rows=[['赛季总案','主题、目标玩家、章节关系和日历'],['完整内容','关卡、任务、奖励节点与获取方式'],['规则与数值','产出、消耗、门槛与异常状态'],['UI/UX材料','流程、线框、交互原型和文案'],['制作材料','素材清单、字段映射和开发需求'],['运营材料','验收、埋点需求和复盘报告']];
 rows.forEach(([a,b],i)=>{const y=210+i*72;text(s,'delivery-title-'+i,a,620,y,550,32,25,C.cyan,true);text(s,'delivery-body-'+i,b,620,y+35,580,35,22.8,C.body);});
 note(s,'交付物按FC团队实际配置结构和评审习惯映射。此页是拟议交付目录，不表示这些材料已经全部制作完毕。试点前应准备一份完整配置样表，让制作方验证字段和状态是否足够。');
}
// 06
{
 const s=p.slides.add({layoutId:layout.id});s.background.fill=C.bg;await image(s,hero,0,0,1280,720,'哈兰德主题案例AI生成背景');
 text(s,'case-label','设计案例',72,55,500,44,26,C.gold,true);
 text(s,'case-title','哈兰德的\n锋线征程',72,132,650,152,64,C.white,true);
 text(s,'case-promise','围绕中锋创造机会，完成高效终结。',76,320,690,50,28,C.cyan,true);
 text(s,'case-chapters','射手训练场   技巧与终结\n禁区猎手       应对不同防线\n最佳搭档       选择配合路线\n金靴征程       推进球员奖励\n冠军之夜       完成终章挑战',78,396,650,226,26,C.white);
 text(s,'case-caveat','原创概念，按6周活动假设设计。AI生成主题视觉。',78,660,1080,28,17,C.body);
 note(s,'这份主题方案把哈兰德作为设计线索：训练、创造机会、搭档配合和终章挑战共同构成成长过程。禁区猎手是活动设计的一部分，尚未单独实现到网页原型。网页已有大厅、训练、搭档、征程和冠军五个页面，不能将页面数量等同于完整五个玩法章节。\n视觉素材为本项目AI生成，非官方宣传图片。');
}
// 07
{
 const s=page('六周赛季的内容节奏',7,'开放顺序同时考虑学习、阶段目标和核心奖励的达成时间。');
 table(s,[['阶段','内容重点','玩家目标'],['第1至2周','基础训练、主题比赛','熟悉终结方式'],['第3至4周','搭档路线、进阶挑战','形成自己的进攻组合'],['第5周','冠军之夜','冲击核心球员'],['第6周','补领与剩余目标','完成征程与收藏']],[220,466,450],225,360);
 text(s,'calendar-caveat','开放时间与内容数量为初步设计，需结合现有系统、投放和制作产能确认。',76,622,1120,52,21,C.body);
 note(s,'整期设计需要独立内容清单，包括训练关卡、周赛场次、路线任务链、奖励节点和日常任务配置。重复日常的次数不等同于新增内容数量。6周指活动运行长度，项目工期另含设计准备、制作接入与复盘。');
}
// 08
{
 const s=page('关键交互已经有可操作的样板',8,'训练、路线选择、奖励领取和冠军结算，能够在同一条体验流程中演示。');
 await image(s,'D:/codex/RH/haaland-season/preview-overview.jpg',72,200,1136,415,'哈兰德活动早期网页原型的手机画面截取',{left:.036,top:.201,right:.026,bottom:.287});
 text(s,'prototype-caveat','当前为交互样板，完整关卡、赛季配置与游戏客户端接入仍需制作。',76,634,1110,40,21,C.body);
 note(s,'截图来自本项目早期网页原型，仅截取手机活动画面用于展示。当前还提供独立的单文件离线版。演示中的训练和比赛采用简化交互，不代表完整足球引擎或游戏客户端实现。禁区猎手未单独接入，完整六周内容也尚未制作。\n截图：D:/codex/RH/haaland-season/preview-overview.jpg\n离线演示：D:/codex/RH/haaland-offline/开始演示-手机预览版.html\n在线参考：https://haaland-season-lab-oct14.apt-toast-4281.chatgpt.site ，当前有访问权限限制，不作为对外提交的唯一入口。');
}
// 09
{
 const s=page('持续内容交付流程',9,'每个阶段保留确认人和验收项，新增系统能力单独评估排期。');
 const steps=[['01','需求对齐','档期、主题和目标\n球员池与奖励边界\n现有活动系统能力'],['02','设计锁定','章节和核心玩法\n任务、规则与奖励\n原型和制作依赖'],['03','制作联调','字段与配置交付\n客户端和美术接入\n完整路径与异常验收'],['04','上线复盘','内容开放跟进\n参与与达成数据\n后续调整和下一期建议']];
 steps.forEach(([n,a,b],i)=>{const x=76+i*296;text(s,'process-index-'+i,n,x,245,230,64,48,C.gold,true);text(s,'process-title-'+i,a,x,329,245,49,30,C.white,true);text(s,'process-body-'+i,b,x,408,250,161,24,C.body);});
 note(s,'顺序覆盖活动简报、概念评审、内容锁定、配置交付、联调验收和上线复盘。交付日程应以现有系统和资源可用性为前提，避免把需要新增开发的机制混入常规配置工作。');
}
// 10
{
 const s=page('效果评估与交付验收',10,'玩家结果与交付质量分开记录，目标值在试点前基于历史数据共同确定。');
 table(s,[['方向','观察内容','解释与比较口径'],['活动参与','入口、章节参与与回访','与历史同类活动比较'],['奖励体验','达成率、耗时与资源积累','按玩家类型分层观察'],['商业表现','付费参与与奖励经济影响','结合球员强度和投放解释'],['交付质量','按期完成、返工与上线问题','按双方约定的标准记录']],[220,458,458],225,360);
 text(s,'measurement-caveat','当前没有真实运营数据，不预先承诺留存或收入提升幅度。',76,622,1120,45,22,C.body);
 note(s,'试点需要先确认埋点和历史基线。若没有实验或合适的比较对象，不能将指标变化全部归因于设计合作。球员强度、同期投放、渠道流量和版本变化均可能影响结果。本提案没有虚构项目业绩或提升百分比。');
}
// 11
{
 const s=page('先完成一期试点，再扩大持续合作',11,'选择双方认可的主题，在现有活动能力支持的范围内完成设计与接入验证。');
 text(s,'pilot-design','制作前：设计验收',76,250,530,60,33,C.cyan,true);
 text(s,'pilot-design-body','主题与玩法符合活动简报\n规则、配置和界面状态完整\n制作依赖与排期明确',78,339,530,195,26,C.white);
 text(s,'pilot-live','上线后：运行验证',665,250,530,60,33,C.cyan,true);
 text(s,'pilot-live-body','关键流程与奖励发放正常\n内容按约定节奏开放\n数据口径与复盘建议可交付',667,339,530,195,26,C.white);
 text(s,'pilot-duration','活动运行按6周假设，项目总工期另含准备、接入与复盘。',78,605,1120,54,23,C.body);
 note(s,'试点可按系统能力缩小范围，不必一次引入全部新机制。设计验收与线上效果验收分别约定。商业目标和最终范围需双方确认，当前不提供未经人员与产能核实的交付承诺。');
}
// 12
{
 const s=page('下一步：确定一期试点',12);
 text(s,'next-statement','一次需求对齐，\n确认合作的起点。',76,200,1050,150,60,C.white,true);
 text(s,'next-topics','试点主题     可用活动系统\n奖励边界     验收口径与负责人',80,409,1080,112,32,C.cyan,true);
 text(s,'next-commercial','试点范围、排期与费用在需求确认后约定。',80,567,1100,45,25,C.body);
 text(s,'next-readiness','提交前补充：团队履历、岗位配置与实际产能样表。',80,632,1100,35,20,C.gold);
 note(s,'结束时提出具体请求：与活动策划、产品及开发负责人对齐一次，确认试点主题、系统能力和验收标准。对外发送前需要补充真实的团队履历、岗位配置、产能样表和商务信息，不以当前设计原型替代履约能力证据。');
}

console.log('Rendering',p.slides.items.length,'slides');
for(let i=0;i<p.slides.items.length;i++){
 const slide=p.slides.items[i];
 const png=await p.export({slide,format:'png',scale:1});
 await fs.writeFile(root+'/.build/render/slide-'+String(i+1).padStart(2,'0')+'.png',new Uint8Array(await png.arrayBuffer()));
 const data=await slide.export({format:'layout'});
 await fs.writeFile(root+'/.build/render/slide-'+String(i+1).padStart(2,'0')+'.layout.json',await data.text());
 console.log('Rendered',i+1);
}
const candidate=root+'/.build/candidate.pptx';
await (await PresentationFile.exportPptx(p)).save(candidate);
await fs.writeFile(root+'/.build/font-policy.json',JSON.stringify(fontPolicy));
await fs.writeFile(root+'/.build/content.ndjson',(await p.inspect({select:'$.slides[*]',include:['id','index','title','elements.text','notes.text']})).ndjson);
console.log('Candidate:',candidate);
