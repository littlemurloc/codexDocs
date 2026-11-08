// Read-only calls to the already-running official Y3 editor MCP.
const name = process.argv[2];
const args = process.argv[3] ? JSON.parse(process.argv[3]) : {};
const allowed = new Set(['tools/list', 'get_ui_list', 'get_map_info',
  'get_editor_log', 'screenshot_ui', 'get_object_editor_list',
  'get_editor_item_custom_data']);
if (!allowed.has(name)) throw new Error(`Read-only tool not allowed: ${name}`);
const body = name === 'tools/list'
  ? { jsonrpc: '2.0', id: 1, method: 'tools/list', params: {} }
  : { jsonrpc: '2.0', id: 1, method: 'tools/call',
      params: { name, arguments: args } };
const response = await fetch('http://127.0.0.1:8765/mcp', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json',
    Accept: 'application/json, text/event-stream' },
  body: JSON.stringify(body),
});
if (!response.ok) throw new Error(`MCP HTTP ${response.status}: ${await response.text()}`);
const raw = await response.text();
const payload = raw.split('\n').filter(line => line.startsWith('data: '))
  .map(line => JSON.parse(line.slice(6))).find(value => value.id === 1);
if (!payload) throw new Error(`Missing MCP response: ${raw.slice(0, 500)}`);
if (payload.error) throw new Error(JSON.stringify(payload.error));
if (name === 'tools/list') {
  console.log(JSON.stringify(payload.result.tools.filter(tool =>
    ['get_editor_log', 'screenshot_ui', 'get_map_info',
      'get_object_editor_list', 'get_editor_item_custom_data',
      'import_object_editor', 'import_eca'].includes(tool.name)), null, 2));
} else {
  for (const block of payload.result.content || []) {
    if (block.type === 'text') console.log(block.text);
  }
}
