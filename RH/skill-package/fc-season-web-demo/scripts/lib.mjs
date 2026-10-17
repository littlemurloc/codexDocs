import fs from 'node:fs/promises';
import path from 'node:path';

export function parseArgs(argv) {
  const result={_:[]};
  for(let i=0;i<argv.length;i++) {
    const key=argv[i];
    if(!key.startsWith('--')) {result._.push(key);continue;}
    if(['--force','--ready','--help'].includes(key)) result[key.slice(2)]=true;
    else {if(!argv[i+1]||argv[i+1].startsWith('--'))throw Error(`Missing value for ${key}`);result[key.slice(2)]=argv[++i];}
  }
  return result;
}
export function validateConfig(c,{ready=false}={}) {
  if(!c||typeof c!=='object'||Array.isArray(c))throw Error('theme.json must be an object');
  for(const key of ['id','theme','title','subtitle','heroCopy','corePlayer','rewardLabel','pointLabel','tokenLabel','visualNote'])if(typeof c[key]!=='string'||!c[key].trim())throw Error(`Invalid text: ${key}`);
  if(!['starter','concept'].includes(c.stage))throw Error('stage must be starter or concept');
  if(ready&&c.stage!=='concept')throw Error('Starter template is not a finished theme. Complete the design and set stage=concept.');
  for(const key of ['accent','gold'])if(!/^#[0-9a-f]{6}$/i.test(c[key]))throw Error(`Invalid color: ${key}`);
  if(typeof c.heroImage!=='string')throw Error('heroImage must be a project-relative path or empty');
  for(const key of ['initialPoints','initialTokens','dailyReward','matchPoints','matchTokens','coreThreshold','matchesRequired','partnerCost','durationDays'])if(!Number.isSafeInteger(c[key])||c[key]<0)throw Error(`Invalid non-negative integer: ${key}`);
  if(c.coreThreshold<1||c.matchesRequired<1||c.matchesRequired>30||c.partnerCost<1||c.durationDays<1)throw Error('Core threshold, match count, cost, or duration outside supported range');
  if(!Array.isArray(c.drills)||c.drills.length!==3)throw Error('Template requires three drills; edit the template if changing the structure');
  if(!Array.isArray(c.routes)||c.routes.length!==3)throw Error('Template requires three routes');
  for(const [key,items] of [['drills',c.drills],['routes',c.routes]]) {
    const ids=new Set();
    for(const item of items) {
      for(const field of ['id','name','description'])if(typeof item[field]!=='string'||!item[field].trim())throw Error(`Invalid ${key}.${field}`);
      if(!/^[a-z0-9-]+$/.test(item.id)||ids.has(item.id))throw Error(`Duplicate or unsupported ${key} id`);ids.add(item.id);
    }
  }
  for(const d of c.drills)if(!Number.isFinite(d.targetStart)||!Number.isFinite(d.targetEnd)||d.targetStart<0||d.targetEnd>100||d.targetStart>=d.targetEnd||!Number.isSafeInteger(d.points)||d.points<0)throw Error('Invalid drill target or reward');
  for(const r of c.routes)for(const k of ['task','partner'])if(typeof r[k]!=='string'||!r[k].trim())throw Error(`Invalid route ${k}`);
  if(!Array.isArray(c.milestones)||c.milestones.length!==5)throw Error('Template requires five milestones');
  let previous=-1;
  for(const m of c.milestones) {if(!Number.isSafeInteger(m.at)||m.at<0||m.at<=previous||typeof m.name!=='string'||!m.name.trim())throw Error('Milestones must have increasing thresholds and names');previous=m.at;}
  if(previous!==c.coreThreshold)throw Error('Final milestone must match coreThreshold');
  const available=c.initialPoints+c.dailyReward+c.drills.reduce((sum,d)=>sum+d.points,0)+c.matchesRequired*c.matchPoints;
  if(available<c.coreThreshold)throw Error(`Core reward unreachable: ${available} < ${c.coreThreshold}`);
  if(c.initialTokens+c.matchesRequired*c.matchTokens<c.partnerCost)throw Error('Partner exchange unreachable');
  return {availablePoints:available,requiredPoints:c.coreThreshold,stage:c.stage};
}
export function embedJson(c) {return JSON.stringify(c).replace(/</g,'\\u003c').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');}
export async function withinProject(root,relative) {
  if(path.isAbsolute(relative)||/^[a-z]+:/i.test(relative))throw Error('Image path must be relative to the project');
  const full=path.resolve(root,relative),realRoot=await fs.realpath(root),realFile=await fs.realpath(full);
  const rel=path.relative(realRoot,realFile);
  if(rel.startsWith('..'+path.sep)||rel==='..'||path.isAbsolute(rel))throw Error('Image must stay within the project (including symlink targets)');
  return realFile;
}
export async function writeOutput(file,data,force=false) {
  await fs.mkdir(path.dirname(file),{recursive:true});
  await fs.writeFile(file,data,{encoding:'utf8',flag:force?'w':'wx'});
}
