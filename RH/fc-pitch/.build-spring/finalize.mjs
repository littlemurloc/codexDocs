import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const root='D:/codex/RH/fc-pitch',tmp=root+'/.build-spring';
const skill='C:/Users/littl/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations';
process.env.RUNTIME_NODE_MODULES='C:/Users/littl/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
const finalPath=root+'/output/FC mobile-羊名立万春节活动案例版.pptx';
const owners=[6,8,10,13,18,21];
const result=await finalizePresentation({
 workspaceDir:root,candidatePath:tmp+'/candidate.pptx',finalPath,
 pythonExecutable:'C:/Users/littl/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
 integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',
 layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...owners.flatMap(n=>['--require-native-table-slide',String(n)])],
 explicitTotalSlideCount:23,requiredNativeTableOwnerSlides:owners,
 fontPolicy:JSON.parse(await fs.readFile(tmp+'/font-policy.json','utf8')),
 verifyArtifactToolImport:true,receiptPath:tmp+'/validation-final.json'
});
console.log(JSON.stringify({finalPath,sha256:result.finalSha256,status:result.packageIntegrity?.status,findings:result.presentationLayout?.findingCount}));
