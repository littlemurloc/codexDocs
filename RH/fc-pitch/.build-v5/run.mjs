try{await import('./update.mjs');}catch(e){console.error(e.message);console.error(e.stack?.split('\n').slice(1,5).join('\n'));process.exitCode=1;}
