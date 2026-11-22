// Import this package via Y3 and capture its assigned texture IDs.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const project = "D:/littl/testTempFile/ProjectMonster02";
const packageName = process.argv[2] || "safezone-jade-insignia-v01";
if (!["safezone-jade-insignia-v01", "safezone-draw-reveal-v01"].includes(packageName)) {
    throw new Error("Unknown safety-zone icon package");
}
const assets = path.resolve("assets/art/packages", packageName);
const manifest = JSON.parse(fs.readFileSync(path.join(assets, "manifest.json"), "utf8"));
const cases = path.join(project, "editor_table/editoricon");
const receipt = path.join(assets, "y3-icons.json");
const records = fs.existsSync(receipt) ? JSON.parse(fs.readFileSync(receipt, "utf8")) : {};
const hash = data => crypto.createHash("sha256").update(data).digest("hex");
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

async function rpc(method, params = {}) {
    const response = await fetch("http://127.0.0.1:8765/mcp", {
        method: "POST",
        headers: {"Content-Type": "application/json", Accept: "application/json, text/event-stream"},
        body: JSON.stringify({jsonrpc: "2.0", id: 1, method, params}),
        signal: AbortSignal.timeout(25000),
    });
    if (!response.ok) throw new Error(`${method} HTTP ${response.status}`);
    const body = await response.text();
    const msg = body.startsWith("{") ? JSON.parse(body) : body.split("\n")
        .filter(line => line.startsWith("data: ")).map(line => JSON.parse(line.slice(6)))
        .find(message => message.id === 1);
    if (!msg?.result || msg.result.isError) throw new Error(body.slice(0, 1000));
    return msg.result;
}

async function call(name, args = {}) {
    const result = await rpc("tools/call", {name, arguments: args});
    const text = (result.content || []).map(block => block.text).filter(Boolean).join("\n");
    if (/^\s*(?:Error:|错误)/i.test(text)) throw new Error(text);
    return text;
}

async function main() {
    const map = await call("get_map_info");
    if (!map.includes("ProjectMonster02") || !map.includes("map3")) {
        throw new Error(`Unexpected project or map: ${map}`);
    }
    const {tools} = await rpc("tools/list");
    const tool = tools.find(entry => entry.name === "import_editor_icon");
    if (!tool) throw new Error("Y3 import_editor_icon is unavailable");
    const properties = tool.inputSchema.properties;
    const fileField = Object.keys(properties).find(key => /path/i.test(key) &&
        !/folder|output|target|directory/i.test(key));
    if (!fileField || properties[fileField].type !== "string") {
        throw new Error(JSON.stringify(tool.inputSchema));
    }
    const unsupported = (tool.inputSchema.required || []).filter(key => key !== fileField &&
        !["name", "icon_name", "resource_name"].includes(key));
    if (unsupported.length) throw new Error(JSON.stringify(tool.inputSchema));
    console.log("Y3 icon import schema:", JSON.stringify(tool.inputSchema));
    const prepared = [];
    for (const [key, asset] of Object.entries(manifest)) {
        const image = path.join(assets, asset.file);
        if (hash(fs.readFileSync(image)) !== asset.sha256) throw new Error(`Texture changed: ${key}`);
        const native = path.join(project, "custom/OriginalRes/icon", key + ".package");
        const metaFile = path.join(native, "meta.json");
        if (!fs.existsSync(metaFile)) {
            const args = {[fileField]: image};
            for (const field of ["name", "icon_name", "resource_name"]) {
                if (properties[field]?.type === "string") args[field] = "安全区青玉_" + key;
            }
            console.log(`${key}: ${await call(tool.name, args)}`);
            for (let tries = 0; tries < 18 && !fs.existsSync(metaFile); tries++) await pause(350);
            if (!fs.existsSync(metaFile)) {
                await call("save_editor");
                for (let tries = 0; tries < 24 && !fs.existsSync(metaFile); tries++) await pause(350);
            }
        }
        const meta = JSON.parse(fs.readFileSync(metaFile, "utf8"));
        if (meta.source_path !== path.basename(image) ||
            hash(fs.readFileSync(path.join(native, meta.source_path))) !== asset.sha256) {
            throw new Error(`Existing Y3 icon has different pixels: ${key}`);
        }
        if (records[key] && records[key].id !== meta.id) throw new Error(`Import ID changed for ${key}`);
        prepared.push({key, id: meta.id, sha256: asset.sha256, basename: meta.source_path});
    }
    console.log(await call("save_editor"));
    for (const {key, id, sha256, basename} of prepared) {
        const iconFile = path.join(cases, id + ".json");
        for (let tries = 0; tries < 24 && !fs.existsSync(iconFile); tries++) await pause(350);
        const icon = JSON.parse(fs.readFileSync(iconFile, "utf8"));
        if (icon.key !== id || icon.res_name !== basename) throw new Error(`Incorrect resource entry for ${key}`);
        records[key] = {id, sha256};
        fs.writeFileSync(receipt, JSON.stringify(records, null, 2) + "\n");
        console.log(`${key} → ${id}`);
    }
}

main().catch(error => {
    console.error(error.message);
    process.exitCode = 1;
});
