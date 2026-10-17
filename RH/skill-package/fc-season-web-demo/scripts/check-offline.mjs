import fs from 'node:fs/promises';
import path from 'node:path';
import vm from 'node:vm';
import {parseArgs,validateConfig} from './lib.mjs';
try {
  const a=parseArgs(process.argv.slice(2));
  if(a.help){console.log('node check-offline.mjs <file.html> [--ready]');process.exit(0);}
  if(!a._[0])throw Error('Provide an HTML file');
  const file=path.resolve(a._[0]),html=await fs.readFile(file,'utf8');
  if(!/^<!doctype html>/i.test(html.trim()))throw Error('Missing HTML doctype');
  const configTag=html.match(/<script\b[^>]*id=["']season-config["'][^>]*>([\s\S]*?)<\/script>/i);
  if(!configTag)throw Error('Missing embedded season-config');
  const config=JSON.parse(configTag[1]),budget=validateConfig(config,{ready:!!a.ready});
  const scripts=[...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)];let executable=0;
  for(const [,attrs,body]of scripts)if(!/type=["']application\/(?:json|octet-stream)["']/i.test(attrs)){new vm.Script(body);executable++;}
  if(!executable)throw Error('No executable interaction code');
  if(/<(?:script|link|img|iframe|audio|video|source)\b[^>]*(?:src|href)\s*=/i.test(html))throw Error('External or unresolved element asset reference');
  if(/@import|\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b|\bEventSource\b|import\s*\(/.test(html))throw Error('Network or module loader found');
  const styles=[...html.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style\s*>/gi)].map(m=>m[1]).join('\n');
  if(/url\(\s*(?!["']?(?:data:|blob:|#))/i.test(styles))throw Error('Unresolved CSS image or font URL');
  if(!/http-equiv=["']Content-Security-Policy["']/i.test(html)||!html.includes("connect-src 'none'"))throw Error('Missing offline CSP');
  if(config.heroImage&&!/<script\b[^>]*id=["']hero-asset["'][^>]*>[A-Za-z0-9+/=\s]+<\/script>/.test(html))throw Error('Configured hero image was not embedded');
  console.log(JSON.stringify({file,status:'pass',bytes:Buffer.byteLength(html),embeddedScripts:executable,...budget,limits:'Static/package checks only; no browser rendering or live network capture.'}));
}catch(e){console.error(e.message);process.exitCode=1;}
