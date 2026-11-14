const fs=require('fs'),path=require('path'),crypto=require('crypto');
const root=path.resolve(__dirname,'..');
const img=(file,title)=>`<figure><a href="${file}" target="_blank"><img src="${file}" alt="${title}" loading="lazy"></a><figcaption>${title}</figcaption></figure>`;
const comparisons=[['comparison/01_reference.png','1 · 原始 2D 参考图'],['comparison/02_previous.png','2 · 上一次场景图（原样保留）'],['comparison/03_rebuild.png','3 · 本次从空场景重建']];
const steps=[['renders/01_blockout.png','白模与镜头校准'],['renders/02_assets.png','新建资产与原纸画内容'],['renders/03_lighting_v1.png','第一轮灯光'],['renders/04_review_v3.png','发现过暗与侧光遮挡问题'],['renders/04_review_v5.png','主镜头纠偏'],['renders/07_reopen_check.png','独立进程重开验证']];
const views=['hero','left','right','reverse','overhead','bear','stool','wall'];
const html=`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>熊娃娃房间 · 三图对照</title><style>*{box-sizing:border-box}body{margin:0;background:#101820;color:#dee7ed;font:16px/1.65 system-ui,'Microsoft YaHei',sans-serif}main{max-width:1800px;margin:auto;padding:32px}h1{font-size:28px}h2{margin-top:48px}p{color:#b5c5d0;max-width:1000px}a{color:#b3ddf5}figure{margin:0;background:#192630;border:1px solid #344551;border-radius:6px;overflow:hidden}img{display:block;width:100%;aspect-ratio:3/2;object-fit:contain;background:#080d12}figcaption{padding:12px 16px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.views{grid-template-columns:repeat(4,minmax(0,1fr))}@media(max-width:1000px){.grid{grid-template-columns:1fr 1fr}.views{grid-template-columns:1fr 1fr}}@media(max-width:650px){main{padding:18px}.grid,.views{grid-template-columns:1fr}}</style><main><h1>熊娃娃房间 · 原图 / 上一版 / 从空场景重建</h1><p>2026-11-10。三个画面保持全图 3:2，不裁切，不对旧版补画。新版用新脚本从空场景构建；未加载或追加上一版 3D 工程。点击每张图查看原尺寸。</p><div class="grid">${comparisons.map(x=>img(...x)).join('')}</div><p>新版相机按原图的桌面、主熊、吊灯和地毯锚点匹配；单图不足以唯一恢复真实相机。纸画来自原图对应区域，其他主体为实际三维模型。角色、磨损和部分散物仍有差异。</p><p><a href="scene_cycles.blend">Cycles 工程</a> · <a href="scene_realtime.blend">EEVEE 浏览工程</a> · <a href="README.md">制作说明</a> · <a href="visual_review.md">逐物件评审</a> · <a href="camera_alignment.json">镜头记录</a></p><h2>工序检查点</h2><div class="grid">${steps.map(x=>img(...x)).join('')}</div><h2>同一工程中的诊断视角</h2><p>反向/俯视/凳子/墙面图临时移除顶棚、雾与侧光遮挡片，并加检查灯；非原照明成片。反向可见开放拍摄面，本例不是完整关卡。</p><div class="grid views">${views.map(x=>img('renders/view_'+x+'.png',x)).join('')}</div></main></html>`;
fs.writeFileSync(path.join(root,'index.html'),html,'utf8');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const oldRoot='D:/codex/blender/scenes/TeddyRoom_Study';
const mig=JSON.parse(fs.readFileSync('D:/codex/blender/docs/migration_manifest.json','utf8').replace(/^\uFEFF/,''));
const baseline=[];
for(const file of ['scene.blend','scene_realtime.blend','reference.png','renders/05_final.png']){
 const full=path.join(oldRoot,file),record=mig.records.find(x=>path.resolve(x.destination).toLowerCase()===path.resolve(full).toLowerCase());
 const hash=sha(full);if(record&&hash.toLowerCase()!==record.final_sha256.toLowerCase())throw Error('Baseline changed: '+file);
 baseline.push({file:full,sha256:hash,unchanged_from_migrated_baseline:!!record});
}
if(sha(path.join(root,'comparison/01_reference.png'))!==sha(path.join(oldRoot,'reference.png')))throw Error('Reference copy mismatch');
if(sha(path.join(root,'comparison/02_previous.png'))!==sha(path.join(oldRoot,'renders/05_final.png')))throw Error('Old comparison mismatch');
if(sha(path.join(root,'comparison/03_rebuild.png'))!==sha(path.join(root,'renders/05_final.png')))throw Error('New comparison mismatch');
const dims=comparisons.map(([file,title])=>{const b=fs.readFileSync(path.join(root,file));return{file,title,width:b.readUInt32BE(16),height:b.readUInt32BE(20),sha256:sha(path.join(root,file))}});
fs.writeFileSync(path.join(root,'provenance.json'),JSON.stringify({created_at:new Date().toISOString(),construction:'factory-startup; new source; no previous blend loaded/linked/appended',baseline,comparison_images:dims,scene_pixels_used:'Only individual paper faces/table paper use source image UV regions; no full-scene backdrop or composited source'},null,2));
const validation=JSON.parse(fs.readFileSync(path.join(root,'validation.json'),'utf8'));
const rt=JSON.parse(fs.readFileSync(path.join(root,'realtime_validation.json'),'utf8'));
if(!validation.reopened_and_rendered||!rt.passed||validation.missing_external_images.length)throw Error('Scene validation failed');
const src=fs.readFileSync(path.join(root,'source/rebuild.py'),'utf8');
if(/open_mainfile|libraries\.load|wm\.append/.test(src))throw Error('Unexpected external scene load in builder');
const refs=[...html.matchAll(/(?:src|href)="([^"]+)"/g)].map(x=>x[1]);
for(const ref of refs){if(!fs.existsSync(path.join(root,ref)))throw Error('Missing HTML reference: '+ref)}
fs.writeFileSync(path.join(root,'delivery_check.json'),JSON.stringify({checked_at:new Date().toISOString(),passed:true,comparison_binary_copies_verified:true,previous_scene_untouched:true,html_links_checked:refs.length,view_count:views.length,cycles_reopened:true,realtime_reopened:true},null,2));
console.log(JSON.stringify({passed:true,comparison:dims.map(({file,width,height})=>({file,width,height})),objects:validation.objects,links:refs.length}));
