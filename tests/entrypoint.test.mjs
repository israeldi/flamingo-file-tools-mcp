import test from 'node:test';
import assert from 'node:assert/strict';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const execute = promisify(execFile);
const entry = fileURLToPath(new URL('../server/index.mjs', import.meta.url));

async function withAlias(run, context) {
  const temporary = await fs.mkdtemp(path.join(os.tmpdir(), 'flamingo-entrypoint-'));
  try {
    const alias = path.join(temporary, 'flamingo-aliased-entry.mjs');
    try { await fs.symlink(entry, alias, 'file'); }
    catch (error) {
      if (process.platform === 'win32' && ['EPERM', 'EACCES'].includes(error.code)) {
        context.skip('Creating a file symlink requires permission on this Windows host.');
        return;
      }
      throw error;
    }
    assert.notEqual(alias, await fs.realpath(alias));
    await run(alias);
  } finally { await fs.rm(temporary, { recursive: true, force: true }); }
}

test('CLI help executes through an actual symbolic-link entrypoint without credentials', async context => {
  await withAlias(async alias => {
    const result = await execute(process.execPath, [alias, '--help'], {
      env: { PATH: process.env.PATH || '', RAPIDAPI_KEY: '', FLAMINGO_WORKSPACE_DIR: '' }, timeout: 10_000
    });
    assert.match(result.stdout, /^Flamingo File Tools 0\.1\.0\n/);
    assert.equal(result.stderr, '');
  }, context);
});

test('an actual symbolic-link entrypoint completes SDK stdio discovery and capabilities', async context => {
  await withAlias(async alias => {
    const transport = new StdioClientTransport({ command: process.execPath, args: [alias],
      env: { PATH: process.env.PATH || '', RAPIDAPI_KEY: '', FLAMINGO_WORKSPACE_DIR: '' }, stderr: 'pipe' });
    const client = new Client({ name: 'aliased-entrypoint-regression', version: '0.1.0' });
    let stderr = '';
    transport.stderr?.on('data', chunk => { stderr += chunk.toString(); });
    try {
      await client.connect(transport);
      const tools = (await client.listTools()).tools;
      assert.equal(tools.length, 6);
      const result = await client.callTool({ name: 'capabilities', arguments: {} });
      assert.notEqual(result.isError, true);
      assert.equal(result.structuredContent.products.length, 4);
      assert.equal(stderr, '');
    } finally { await client.close(); }
  }, context);
});
