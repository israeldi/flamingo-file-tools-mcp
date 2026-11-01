import test from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const exec = promisify(execFile);
const server = fileURLToPath(new URL('../server/index.mjs', import.meta.url));
const names = ['capabilities', 'access_extract', 'creativepack_optimize', 'patterncopy_inspect', 'patterncopy_stamp', 'shelfrelay_preview'];

test('real stdio handshake and capability discovery work with no key or workspace', { timeout: 15000 }, async () => {
  const temp = await fs.mkdtemp(path.join(os.tmpdir(), 'flamingo-protocol-'));
  const absent = path.join(temp, 'not-created');
  const transport = new StdioClientTransport({ command: process.execPath, args: [server], env: {
    PATH: process.env.PATH || '', RAPIDAPI_KEY: '', FLAMINGO_WORKSPACE_DIR: absent
  }, stderr: 'pipe' });
  const client = new Client({ name: 'flamingo-qualification', version: '0.1.0' });
  let errors = '';
  transport.stderr?.on('data', chunk => { errors += chunk.toString(); });
  try {
    await client.connect(transport);
    const tools = (await client.listTools()).tools;
    assert.deepEqual(tools.map(x => x.name).sort(), [...names].sort());
    for (const tool of tools) {
      assert.equal(tool.annotations.readOnlyHint, tool.name === 'capabilities');
      assert.equal(tool.annotations.openWorldHint, tool.name !== 'capabilities');
      assert.equal(tool.annotations.destructiveHint, false);
      assert.equal(tool.inputSchema.additionalProperties, false);
      if (tool.name !== 'capabilities') assert.ok(tool.inputSchema.required.includes('consent'));
    }
    const capabilities = await client.callTool({ name: 'capabilities', arguments: {} });
    assert.notEqual(capabilities.isError, true);
    const content = capabilities.structuredContent || JSON.parse(capabilities.content[0].text);
    assert.equal(content.products.length, 4);
    assert.deepEqual((await fs.readdir(temp)), []);
    const missing = await client.callTool({ name: 'access_extract', arguments: { file: 'fictional.accdb', consent: true } });
    assert.equal(missing.isError, true);
    assert.match(missing.content[0].text, /key_missing/);
    assert.deepEqual((await fs.readdir(temp)), []);
    const unknown = await client.callTool({ name: 'capabilities', arguments: { extra: 'refuse' } });
    assert.equal(unknown.isError, true);
    assert.equal(errors, '');
  } finally {
    await client.close();
    await fs.rm(temp, { recursive: true, force: true });
  }
});

test('CLI help starts without a key and discloses upload and allowance', { timeout: 10000 }, async () => {
  const { stdout, stderr } = await exec(process.execPath, [server, '--help'], { env: { PATH: process.env.PATH || '' } });
  assert.match(stdout, /consent:true/);
  assert.match(stdout, /RapidAPI/);
  assert.match(stdout, /allowance/);
  assert.equal(stderr, '');
});
