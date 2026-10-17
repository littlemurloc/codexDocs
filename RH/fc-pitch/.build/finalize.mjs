import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const root='D:/codex/RH/fc-pitch';
const skill='C:/Users/littl/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
process.env.RUNTIME_NODE_MODULES='C:/Users/littl/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
const finalPath=root+'/output/FC mobile-赛季活动合作提案-v1.pptx';
const result=await finalizePresentation({
 workspaceDir:root,
 candidatePath:root+'/.build/candidate.pptx',
 finalPath,
 pythonExecutable:'C:/Users/littl/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
 integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',
 layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','4','--require-native-table-slide','7','--require-native-table-slide','10'],
 requiredNativeTableOwnerSlides:[4,7,10],
 fontPolicy:JSON.parse(await fs.readFile(root+'/.build/font-policy.json','utf8')),
 verifyArtifactToolImport:true,
 receiptPath:root+'/.build/validation.json',
});
console.log(JSON.stringify({finalPath,result}));
