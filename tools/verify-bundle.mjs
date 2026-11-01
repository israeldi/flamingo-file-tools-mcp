import * as fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const root = fileURLToPath(new URL('../', import.meta.url));
const bundle = path.join(root, 'dist/flamingo-file-tools.mcpb');
const metadata = JSON.parse(await fs.readFile(path.join(root, 'dist/server.json'), 'utf8'));
const bytes = await fs.readFile(bundle);
const sha = createHash('sha256').update(bytes).digest('hex');
assert.equal(sha, metadata.packages[0].fileSha256);
const temp = await fs.mkdtemp(path.join(os.tmpdir(), 'flamingo-bundle-'));
let client;
try {
  const target = path.join(temp, 'unpacked');
  const cli = path.join(root, 'node_modules/@anthropic-ai/mcpb/dist/cli/cli.js');
  execFileSync(process.execPath, [cli, 'unpack', bundle, target], { stdio: 'pipe' });
  for (const name of ['server/core.mjs', 'server/index.mjs', 'manifest.json']) {
    assert.deepEqual(await fs.readFile(path.join(target, name)), await fs.readFile(path.join(root, name)));
  }
  assert.ok((await fs.stat(path.join(target, 'node_modules/@modelcontextprotocol/sdk/LICENSE'))).isFile());
  await assert.rejects(fs.stat(path.join(target, 'node_modules/@anthropic-ai/mcpb')));
  const transport = new StdioClientTransport({ command: process.execPath, args: [path.join(target, 'server/index.mjs')],
    env: { PATH: process.env.PATH || '', RAPIDAPI_KEY: '', FLAMINGO_WORKSPACE_DIR: '' }, stderr: 'pipe' });
  client = new Client({ name: 'bundle-qualification', version: '0.1.0' });
  let stderr = '';
  transport.stderr?.on('data', chunk => { stderr += chunk.toString(); });
  try { await client.connect(transport); }
  catch { throw new Error(`The unpacked bundle did not complete the MCP handshake. Startup diagnostics: ${stderr}`); }
  const tools = (await client.listTools()).tools;
  assert.equal(tools.length, 6);
  const result = await client.callTool({ name: 'capabilities', arguments: {} });
  assert.notEqual(result.isError, true);
  const capabilities = result.structuredContent || JSON.parse(result.content[0].text);
  assert.equal(capabilities.products.length, 4);
  assert.equal(stderr, '');
  const receipt = { checked_at_utc: new Date().toISOString(), version: metadata.version,
    bundle: path.basename(bundle), bytes: bytes.length, sha256: sha, source_byte_parity: true,
    production_dependencies_self_contained: true, sdk_license_present: true, build_cli_not_in_runtime_bundle: true,
    actual_unpacked_stdio_handshake: true, tools: tools.map(t => t.name), capability_products: capabilities.products.length,
    processing_tools_invoked: 0, real_key_used: false, native_mcpb_client_installation_tested: false };
  await fs.mkdir(path.join(root, 'verification'), { recursive: true });
  await fs.writeFile(path.join(root, 'verification/bundle-check.json'), JSON.stringify(receipt, null, 2) + '\n');
  console.log(JSON.stringify(receipt));
} finally {
  await client?.close();
  await fs.rm(temp, { recursive: true, force: true });
}
