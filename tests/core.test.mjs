import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { inspect } from 'node:util';
import test from 'node:test';
import crc32 from 'crc-32';
import { createProcessor, ToolError, TOOL_INPUT_SCHEMAS } from '../server/core.mjs';

// Transport fixtures are independent of this adapter. Their existing provenance
// explicitly distinguishes constructed responses, OpenAPI examples and local
// engine results from live API results. Nothing in this suite calls an API.
const PACKAGE = fileURLToPath(new URL('../', import.meta.url));
const FIXTURES = fileURLToPath(new URL('./fixtures/', import.meta.url));
const KEY = 'fixture-key-NOT-A-REAL-RAPIDAPI-CREDENTIAL';
const PRIVATE_BODY = 'untrusted-upstream-diagnostic-must-not-be-echoed';
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
const jsonBytes = (value) => Buffer.from(JSON.stringify(value));
const readJson = async (filename) => JSON.parse(await fs.readFile(filename, 'utf8'));
const fixtures = {
  access: await readJson(path.join(FIXTURES, 'access-response.json')),
  creative: await readJson(path.join(FIXTURES, 'creative-response.json')),
  inspection: await readJson(path.join(FIXTURES, 'pattern-inspect-response.json')),
  shelf: await readJson(path.join(FIXTURES, 'shelfrelay-response.json')),
};
const samples = {
  access: await fs.readFile(path.join(PACKAGE, 'samples/sample-access.accdb')),
  creative: await fs.readFile(path.join(PACKAGE, 'samples/sample-creative.zip')),
  pattern: await fs.readFile(path.join(PACKAGE, 'samples/sample-pattern.pdf')),
  shelf: await fs.readFile(path.join(PACKAGE, 'samples/sample-onix-request.json')),
};
const collections = await readJson(path.join(FIXTURES, 'requests.json'));
const headersOf = (headers) => Object.fromEntries(
  Object.entries(headers).map(([name, value]) => [name.toLowerCase(), String(value)]),
);
const jsonResponse = (value, status = 200) => ({
  status, headers: { 'content-type': 'application/json; charset=utf-8' }, body: jsonBytes(value),
});
const pdfResponse = (body = samples.pattern) => ({
  status: 200,
  headers: {
    'content-type': 'application/pdf',
    'x-patterncopy-sha256': digest(body),
    'x-patterncopy-pages': '3',
  },
  body,
});

async function workspace(t) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'flamingo-core-test-'));
  await fs.chmod(directory, 0o700);
  t.after(() => fs.rm(directory, { recursive: true, force: true }));
  await Promise.all(Object.entries({
    'input.accdb': samples.access,
    'input.zip': samples.creative,
    'input.pdf': samples.pattern,
    'input.json': samples.shelf,
  }).map(([filename, body]) => fs.writeFile(path.join(directory, filename), body, { mode: 0o600 })));
  return fs.realpath(directory);
}

function capturedProcessor(directory, response, apiKey = KEY) {
  const calls = [];
  const transport = async (request) => {
    calls.push(request);
    return typeof response === 'function' ? response(request) : response;
  };
  return { calls, processor: createProcessor({ workspaceDir: directory, apiKey, transport }) };
}

async function expectSafeError(promise, code, status) {
  await assert.rejects(promise, (error) => {
    assert.ok(error instanceof ToolError, 'processing failures use the public safe error type');
    assert.equal(error.code, code);
    if (status !== undefined) assert.equal(error.httpStatus, status);
    const publicAndDiagnostic = `${String(error)} ${JSON.stringify(error)} ${inspect(error, { showHidden: true, depth: 5 })}`;
    assert.doesNotMatch(publicAndDiagnostic, new RegExp(KEY));
    assert.doesNotMatch(publicAndDiagnostic, new RegExp(PRIVATE_BODY));
    return true;
  });
}

async function allFiles(directory) {
  const files = [];
  for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await allFiles(full));
    else files.push(full);
  }
  return files.sort();
}

async function assertArtifacts(result, directory, expected) {
  assert.equal(result.ok, true);
  assert.equal(result.artifacts.length, Object.keys(expected).length);
  for (const artifact of result.artifacts) {
    assert.ok(path.isAbsolute(artifact.path));
    const relative = path.relative(directory, artifact.path);
    assert.ok(relative && !relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
    assert.notEqual(path.dirname(artifact.path), directory, 'outputs have a separate private job directory');
    const name = path.basename(artifact.path);
    assert.ok(Object.hasOwn(expected, name), `unexpected artifact ${name}`);
    assert.equal(artifact.media_type, expected[name]);
    const bytes = await fs.readFile(artifact.path);
    assert.equal(artifact.bytes, bytes.length);
    assert.equal(artifact.sha256, digest(bytes));
    // POSIX permission bits do not establish Windows ACL privacy. Windows users
    // configure their own private workspace ACLs; this suite does not verify them.
    if (process.platform !== 'win32' && typeof process.getuid === 'function') {
      assert.equal((await fs.stat(artifact.path)).mode & 0o777, 0o600);
      assert.equal((await fs.stat(path.dirname(artifact.path))).mode & 0o777, 0o700);
    }
    assert.equal(bytes.includes(Buffer.from(KEY)), false, 'credential is never saved as an artifact');
  }
}

function assertRequest(request, reference) {
  assert.equal(request.url, reference.url);
  assert.equal(request.method, reference.method);
  assert.ok(Buffer.isBuffer(request.body));
  const actual = headersOf(request.headers);
  assert.equal(actual['x-rapidapi-key'], KEY);
  for (const header of reference.header) {
    if (header.key.toLowerCase() === 'x-patterncopy-options') continue;
    if (header.key.toLowerCase() === 'content-type') {
      assert.equal(actual['content-type'].split(';')[0].trim().toLowerCase(), header.value.split(';')[0].trim().toLowerCase());
    } else assert.equal(actual[header.key.toLowerCase()], header.value);
  }
  assert.ok(Number.isInteger(request.maxResponseBytes) && request.maxResponseBytes > 0 && request.maxResponseBytes <= 64 * 1024 * 1024);
  assert.ok(Number.isFinite(request.timeoutMs) && request.timeoutMs > 0);
}

// A small, independently constructed stored ZIP avoids invoking an archive
// extractor or executable during tests. Names/CRC/central records follow ZIP's
// format, while its CSV manifest follows the existing published Access client.
function storedZip(files) {
  const local = [];
  const central = [];
  let offset = 0;
  for (const [filename, contents] of Object.entries(files)) {
    const name = Buffer.from(filename);
    const body = Buffer.isBuffer(contents) ? contents : Buffer.from(contents);
    const crc = crc32.buf(body) >>> 0;
    const header = Buffer.alloc(30);
    header.writeUInt32LE(0x04034b50, 0);
    header.writeUInt16LE(20, 4);
    header.writeUInt16LE(0x21, 12);
    header.writeUInt32LE(crc, 14);
    header.writeUInt32LE(body.length, 18);
    header.writeUInt32LE(body.length, 22);
    header.writeUInt16LE(name.length, 26);
    local.push(header, name, body);
    const entry = Buffer.alloc(46);
    entry.writeUInt32LE(0x02014b50, 0);
    entry.writeUInt16LE(0x0314, 4);
    entry.writeUInt16LE(20, 6);
    entry.writeUInt16LE(0x21, 14);
    entry.writeUInt32LE(crc, 16);
    entry.writeUInt32LE(body.length, 20);
    entry.writeUInt32LE(body.length, 24);
    entry.writeUInt16LE(name.length, 28);
    entry.writeUInt32LE((0o100600 << 16) >>> 0, 38);
    entry.writeUInt32LE(offset, 42);
    central.push(entry, name);
    offset += header.length + name.length + body.length;
  }
  const directory = Buffer.concat(central);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(Object.keys(files).length, 8);
  end.writeUInt16LE(Object.keys(files).length, 10);
  end.writeUInt32LE(directory.length, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...local, directory, end]);
}

function accessCsv(csv = 'ExampleID,Label\r\n1,First synthetic row\r\n2,Second synthetic row\r\n') {
  const manifest = structuredClone(fixtures.access.manifest);
  manifest.format = 'csv';
  manifest.tables[0].csv_member = 'tables/1.csv';
  return storedZip({ 'manifest.json': jsonBytes(manifest), 'tables/1.csv': csv });
}

test('capabilities are available without a credential or an existing workspace', async (t) => {
  const absent = path.join(os.tmpdir(), `flamingo-absent-${process.pid}-${Date.now()}`);
  let calls = 0;
  const processor = createProcessor({ workspaceDir: absent, transport: async () => { calls++; throw new Error('must not run'); } });
  const value = processor.capabilities();
  assert.ok(value && typeof value === 'object');
  assert.equal(calls, 0);
  await assert.rejects(fs.stat(absent), { code: 'ENOENT' });
  assert.equal(createProcessor({}).capabilities() instanceof Promise, false);
});

test('strict tool schemas require explicit consent and reject unexpected arguments', () => {
  const inputs = {
    access_extract: { file: 'input.accdb', consent: true },
    creativepack_optimize: { file: 'input.zip', budget_bytes: 150000, consent: true },
    patterncopy_inspect: { file: 'input.pdf', consent: true },
    patterncopy_stamp: { file: 'input.pdf', text: 'Licensed to Alex Example - Order 1042', consent: true },
    shelfrelay_preview: { file: 'input.json', consent: true },
  };
  for (const [tool, input] of Object.entries(inputs)) {
    assert.equal(TOOL_INPUT_SCHEMAS[tool].safeParse(input).success, true, tool);
    assert.equal(TOOL_INPUT_SCHEMAS[tool].safeParse({ ...input, api_key: KEY }).success, false, tool);
    assert.equal(TOOL_INPUT_SCHEMAS[tool].safeParse({ ...input, consent: false }).success, false, tool);
    const { consent, ...withoutConsent } = input;
    assert.equal(TOOL_INPUT_SCHEMAS[tool].safeParse(withoutConsent).success, false, tool);
  }
});

test('every processing tool enforces consent and strict arguments at the invocation boundary', async (t) => {
  const directory = await workspace(t);
  const { processor, calls } = capturedProcessor(directory, jsonResponse(fixtures.access));
  const inputs = {
    access_extract: { file: 'input.accdb' },
    creativepack_optimize: { file: 'input.zip', budget_bytes: 150000 },
    patterncopy_inspect: { file: 'input.pdf' },
    patterncopy_stamp: { file: 'input.pdf', text: 'Fictional order 1042' },
    shelfrelay_preview: { file: 'input.json' },
  };
  for (const [tool, input] of Object.entries(inputs)) {
    await expectSafeError(processor.run(tool, input), 'consent_required');
    await expectSafeError(processor.run(tool, { ...input, consent: false }), 'consent_required');
    await expectSafeError(processor.run(tool, { ...input, consent: true, retries: 3 }), 'invalid_arguments');
  }
  assert.equal(calls.length, 0, 'no product can consume allowance before deliberate consent');
});

test('all processing requests use the current published hosts, encodings and options', async (t) => {
  const cases = [
    { tool: 'access_extract', file: 'input.accdb', source: samples.access, response: jsonResponse(fixtures.access), reference: collections.access.item[0].request, artifacts: { 'extracted.json': 'application/json' } },
    { tool: 'creativepack_optimize', file: 'input.zip', source: samples.creative, options: { budget_bytes: 150000, mode: 'lossless' }, response: jsonResponse(fixtures.creative), reference: collections.creative.item[0].request, artifacts: { 'optimized.zip': 'application/zip', 'report.json': 'application/json' } },
    { tool: 'patterncopy_inspect', file: 'input.pdf', source: samples.pattern, response: jsonResponse(fixtures.inspection), reference: collections.pattern.item[0].request, artifacts: { 'inspection.json': 'application/json' } },
    { tool: 'patterncopy_stamp', file: 'input.pdf', source: samples.pattern, options: { text: 'Licensed to Alex Example - Order 1042', font_size: 6, margin: 12, position: 'bottom-left' }, response: pdfResponse(), reference: collections.pattern.item[1].request, artifacts: { 'stamped.pdf': 'application/pdf' } },
    { tool: 'shelfrelay_preview', file: 'input.json', source: samples.shelf, response: jsonResponse(fixtures.shelf), reference: collections.shelf.item[0].request, artifacts: { 'preview.json': 'application/json' } },
  ];
  for (const item of cases) {
    await t.test(item.tool, async (t) => {
      const directory = await workspace(t);
      const { processor, calls } = capturedProcessor(directory, item.response);
      const result = await processor.run(item.tool, { file: item.file, consent: true, ...item.options });
      assert.equal(result.tool, item.tool);
      assert.equal(calls.length, 1);
      assertRequest(calls[0], item.reference);
      if (item.tool === 'creativepack_optimize') {
        const payload = JSON.parse(calls[0].body);
        assert.deepEqual(Object.keys(payload).sort(), ['archive_base64', 'budget_bytes', 'mode']);
        assert.deepEqual(Buffer.from(payload.archive_base64, 'base64'), item.source);
        assert.equal(payload.budget_bytes, 150000);
        assert.equal(payload.mode, 'lossless');
        assert.equal(result.summary.status, 'over_budget', 'valid processing must not be represented as meeting the budget');
        assert.equal(result.summary.output_bytes, samples.creative.length);
      } else if (item.tool === 'shelfrelay_preview') {
        assert.deepEqual(JSON.parse(calls[0].body), JSON.parse(item.source));
        assert.deepEqual(result.summary, { total: 1, ok: 1, rejected: 0 });
      } else {
        assert.deepEqual(calls[0].body, item.source);
      }
      if (item.tool === 'patterncopy_stamp') {
        const actual = headersOf(calls[0].headers)['x-patterncopy-options'];
        const documented = item.reference.header.find((h) => h.key === 'X-PatternCopy-Options').value;
        assert.deepEqual(JSON.parse(Buffer.from(actual, 'base64')), JSON.parse(Buffer.from(documented, 'base64')));
      }
      await assertArtifacts(result, directory, item.artifacts);
      assert.deepEqual(await fs.readFile(path.join(directory, item.file)), item.source);
      assert.equal(JSON.stringify(result.summary).includes(KEY), false);
    });
  }
});

test('Access CSV mode checks its manifest, header, row count and artifact digest', async (t) => {
  const directory = await workspace(t);
  const body = accessCsv();
  const { processor, calls } = capturedProcessor(directory, { status: 200, headers: { 'content-type': 'application/zip' }, body });
  const result = await processor.run('access_extract', { file: 'input.accdb', format: 'csv', consent: true });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'https://access-file-extractor.p.rapidapi.com/v1/extract?format=csv');
  assert.equal(headersOf(calls[0].headers).accept, 'application/zip');
  assert.deepEqual(calls[0].body, samples.access);
  assert.deepEqual(result.summary, { format: 'csv', table_count: 1, total_rows: 2 });
  await assertArtifacts(result, directory, { 'extracted-csv.zip': 'application/zip' });
});

test('CreativePack balanced mode is sent explicitly and keeps valid over-budget semantics', async (t) => {
  const directory = await workspace(t);
  const response = structuredClone(fixtures.creative);
  response.report.requested_mode = 'balanced';
  const { processor, calls } = capturedProcessor(directory, jsonResponse(response));
  const result = await processor.run('creativepack_optimize', { file: 'input.zip', budget_bytes: 150000, mode: 'balanced', consent: true });
  assert.equal(calls.length, 1);
  assert.equal(JSON.parse(calls[0].body).mode, 'balanced');
  assert.equal(result.summary.status, 'over_budget');
  await assertArtifacts(result, directory, { 'optimized.zip': 'application/zip', 'report.json': 'application/json' });
});

test('ShelfRelay retains selected previous state and the complete supported policy envelope', async (t) => {
  const directory = await workspace(t);
  const request = JSON.parse(samples.shelf);
  request.records[0].previous_xml = request.records[0].xml;
  request.policy.as_of = '2026-10-31';
  request.policy.supplier_id = { type: '01', value: 'Example supplier' };
  request.policy.merchant_owned_fields = ['description'];
  await fs.writeFile(path.join(directory, 'with-state.json'), jsonBytes(request), { mode: 0o600 });
  const { processor, calls } = capturedProcessor(directory, jsonResponse(fixtures.shelf));
  await processor.run('shelfrelay_preview', { file: 'with-state.json', consent: true });
  assert.equal(calls.length, 1);
  assert.deepEqual(JSON.parse(calls[0].body), request, 'the adapter must not discard client-owned state or policy');
});

test('Access refuses a complete-looking CSV ZIP whose rows disagree with the manifest', async (t) => {
  const directory = await workspace(t);
  const before = await allFiles(directory);
  const { processor } = capturedProcessor(directory, { status: 200, headers: { 'content-type': 'application/zip' }, body: accessCsv('ExampleID,Label\r\n1,Only one row\r\n') });
  await expectSafeError(processor.run('access_extract', { file: 'input.accdb', format: 'csv', consent: true }), 'response_invalid');
  assert.deepEqual(await allFiles(directory), before);
});

test('a processed ShelfRelay batch with rejected records is not counted as accepted', async (t) => {
  const directory = await workspace(t);
  const request = { records: [{ xml: '<bad/>' }], policy: { market_country: 'US', currency: 'USD', price_type: '01' } };
  await fs.writeFile(path.join(directory, 'rejected.json'), jsonBytes(request), { mode: 0o600 });
  // Exact shape produced locally by the released ShelfRelay engine for <bad/>;
  // no HTTP call or successful book interpretation is claimed.
  const response = {
    profile: 'shelfrelay-onix3-physical-v1', ok: true,
    results: [{ index: 0, status: 'rejected', operation: null, identity: null, next_xml: null, source_hash: null,
      projection: { fields: {}, field_states: {}, apply_fields: {}, merchant_owned_fields: [] },
      diagnostics: [{ code: 'onix_version_unsupported', severity: 'error', message: 'An explicit ONIX 3.0 or 3.1 release/namespace is required.' }] }],
    summary: { total: 1, ok: 0, rejected: 1 },
  };
  const { processor, calls } = capturedProcessor(directory, jsonResponse(response));
  const result = await processor.run('shelfrelay_preview', { file: 'rejected.json', consent: true });
  assert.equal(calls.length, 1);
  assert.equal(result.ok, true, 'the batch was processed, with the record failure reported separately');
  assert.deepEqual(result.summary, { total: 1, ok: 0, rejected: 1 });
  await assertArtifacts(result, directory, { 'preview.json': 'application/json' });
});

test('local preflight failures never invoke the transport', async (t) => {
  const directory = await workspace(t);
  const { processor, calls } = capturedProcessor(directory, jsonResponse(fixtures.access));
  const outsideDirectory = await fs.mkdtemp(path.join(os.tmpdir(), 'flamingo-outside-test-'));
  t.after(() => fs.rm(outsideDirectory, { recursive: true, force: true }));
  await fs.writeFile(path.join(outsideDirectory, 'outside.accdb'), samples.access);
  await fs.symlink(path.join(directory, 'input.accdb'), path.join(directory, 'linked.accdb'));
  await fs.symlink(directory, path.join(directory, 'alias'));
  await fs.mkdir(path.join(directory, 'folder.accdb'));
  const large = await fs.open(path.join(directory, 'large.accdb'), 'wx', 0o600);
  await large.truncate(40 * 1024 * 1024 + 1);
  await large.close();
  const checks = [
    [{ file: 'input.accdb' }, 'consent_required'],
    [{ file: 'input.accdb', consent: false }, 'consent_required'],
    [{ file: 'input.accdb', consent: true, url: 'https://example.invalid/steal' }, 'invalid_arguments'],
    [{ file: 'input.accdb', consent: true, output_dir: outsideDirectory }, 'invalid_arguments'],
    [{ file: path.join(outsideDirectory, 'outside.accdb'), consent: true }, 'file_invalid'],
    [{ file: path.relative(directory, path.join(outsideDirectory, 'outside.accdb')), consent: true }, 'file_invalid'],
    [{ file: 'linked.accdb', consent: true }, 'file_invalid'],
    [{ file: 'alias/input.accdb', consent: true }, 'file_invalid'],
    [{ file: 'folder.accdb', consent: true }, 'file_invalid'],
    [{ file: 'missing.accdb', consent: true }, 'file_invalid'],
    [{ file: 'large.accdb', consent: true }, 'file_too_large'],
  ];
  for (const [args, code] of checks) await expectSafeError(processor.run('access_extract', args), code);
  await expectSafeError(processor.run('unknown_tool', { file: 'input.accdb', consent: true }), 'invalid_arguments');
  assert.equal(calls.length, 0);
});

test('group/world-writable POSIX workspaces are rejected without changing their permissions', {
  skip: process.platform === 'win32' || typeof process.getuid !== 'function',
}, async (t) => {
  for (const mode of [0o770, 0o707]) {
    await t.test(mode.toString(8), async (t) => {
      const directory = await workspace(t);
      await fs.chmod(directory, mode);
      const { processor, calls } = capturedProcessor(directory, jsonResponse(fixtures.access));
      await expectSafeError(processor.run('access_extract', { file: 'input.accdb', consent: true }), 'workspace_invalid');
      assert.equal(calls.length, 0);
      assert.equal((await fs.stat(directory)).mode & 0o777, mode, 'the adapter must not silently change an existing folder');
    });
  }
});

test('group/world-writable POSIX ancestors inside the selected workspace are rejected before upload', {
  skip: process.platform === 'win32' || typeof process.getuid !== 'function',
}, async (t) => {
  for (const mode of [0o770, 0o707]) {
    await t.test(mode.toString(8), async (t) => {
      const directory = await workspace(t);
      const ancestor = path.join(directory, 'shared');
      await fs.mkdir(ancestor, { mode: 0o700 });
      await fs.writeFile(path.join(ancestor, 'input.accdb'), samples.access, { mode: 0o600 });
      await fs.chmod(ancestor, mode);
      const { processor, calls } = capturedProcessor(directory, jsonResponse(fixtures.access));
      await expectSafeError(processor.run('access_extract', { file: 'shared/input.accdb', consent: true }), 'file_invalid');
      assert.equal(calls.length, 0);
      assert.equal((await fs.stat(ancestor)).mode & 0o777, mode);
    });
  }
});

test('processing requires the explicitly supplied key rather than a global environment key', async (t) => {
  const directory = await workspace(t);
  const prior = process.env.RAPIDAPI_KEY;
  process.env.RAPIDAPI_KEY = KEY;
  t.after(() => { if (prior === undefined) delete process.env.RAPIDAPI_KEY; else process.env.RAPIDAPI_KEY = prior; });
  const calls = [];
  const explicit = createProcessor({ workspaceDir: directory, apiKey: undefined, transport: async (request) => { calls.push(request); return jsonResponse(fixtures.access); } });
  await expectSafeError(explicit.run('access_extract', { file: 'input.accdb', consent: true }), 'key_missing');
  assert.equal(calls.length, 0);
});

test('authentication, subscription, quota and service failures remain distinct and do not retry or echo bodies', async (t) => {
  for (const [status, code] of [[401, 'authentication_failed'], [403, 'subscription_required'], [429, 'quota_exceeded'], [413, 'service_rejected'], [422, 'service_rejected'], [500, 'service_unavailable'], [503, 'service_unavailable']]) {
    await t.test(String(status), async (t) => {
      const directory = await workspace(t);
      const before = await allFiles(directory);
      const { processor, calls } = capturedProcessor(directory, { status, headers: { 'content-type': 'application/json' }, body: jsonBytes({ message: `${KEY} ${PRIVATE_BODY}` }) });
      await expectSafeError(processor.run('access_extract', { file: 'input.accdb', consent: true }), code, status);
      assert.equal(calls.length, 1);
      assert.deepEqual(await allFiles(directory), before);
    });
  }
});

test('redirects are refused without a second request or successful artifacts', async (t) => {
  for (const status of [301, 302, 307, 308]) {
    await t.test(String(status), async (t) => {
      const directory = await workspace(t);
      const before = await allFiles(directory);
      const { processor, calls } = capturedProcessor(directory, { status, headers: { location: 'https://example.invalid/credential-sink' }, body: Buffer.alloc(0) });
      await expectSafeError(processor.run('access_extract', { file: 'input.accdb', consent: true }), 'redirect_refused', status);
      assert.equal(calls.length, 1);
      assert.deepEqual(await allFiles(directory), before);
    });
  }
});

test('transport failures are safe, single attempt failures', async (t) => {
  const directory = await workspace(t);
  const before = await allFiles(directory);
  const { processor, calls } = capturedProcessor(directory, async () => { throw new Error(`${KEY} ${PRIVATE_BODY}`); });
  await expectSafeError(processor.run('access_extract', { file: 'input.accdb', consent: true }), 'transport_failed');
  assert.equal(calls.length, 1);
  assert.deepEqual(await allFiles(directory), before);
});

test('successful HTTP responses still require the expected type and complete service semantics', async (t) => {
  const invalidAccess = structuredClone(fixtures.access);
  invalidAccess.manifest.complete = false;
  const wrongRows = structuredClone(fixtures.access);
  wrongRows.manifest.total_rows = 3;
  const wrongBudget = structuredClone(fixtures.creative);
  wrongBudget.report.status = 'within_budget';
  const wrongShelf = structuredClone(fixtures.shelf);
  wrongShelf.summary.ok = 0;
  wrongShelf.summary.rejected = 1;
  const badPdf = pdfResponse();
  badPdf.headers['x-patterncopy-sha256'] = '0'.repeat(64);
  const cases = [
    ['access_extract', { file: 'input.accdb' }, { status: 200, headers: { 'content-type': 'text/html' }, body: Buffer.from(`<html>${PRIVATE_BODY}</html>`) }],
    ['access_extract', { file: 'input.accdb' }, jsonResponse(invalidAccess)],
    ['access_extract', { file: 'input.accdb' }, jsonResponse(wrongRows)],
    ['creativepack_optimize', { file: 'input.zip', budget_bytes: 150000 }, jsonResponse(wrongBudget)],
    ['patterncopy_stamp', { file: 'input.pdf', text: 'Fictional order 1042' }, badPdf],
    ['shelfrelay_preview', { file: 'input.json' }, jsonResponse(wrongShelf)],
  ];
  for (const [tool, input, response] of cases) {
    await t.test(`${tool} rejects invalid semantic output`, async (t) => {
      const directory = await workspace(t);
      const before = await allFiles(directory);
      const { processor, calls } = capturedProcessor(directory, response);
      await expectSafeError(processor.run(tool, { ...input, consent: true }), 'response_invalid');
      assert.equal(calls.length, 1);
      assert.deepEqual(await allFiles(directory), before);
    });
  }
});

test('an injected oversized response cannot bypass the advertised byte ceiling', async (t) => {
  const directory = await workspace(t);
  const before = await allFiles(directory);
  const { processor, calls } = capturedProcessor(directory, async (request) => {
    assert.ok(request.maxResponseBytes <= 64 * 1024 * 1024);
    return { status: 200, headers: { 'content-type': 'application/json' }, body: Buffer.alloc(request.maxResponseBytes + 1, 0x20) };
  });
  await expectSafeError(processor.run('access_extract', { file: 'input.accdb', consent: true }), 'response_too_large');
  assert.equal(calls.length, 1);
  assert.deepEqual(await allFiles(directory), before);
});

test('repeat deliberate calls produce separate artifacts and preserve an identically named source', async (t) => {
  const directory = await workspace(t);
  await fs.writeFile(path.join(directory, 'stamped.pdf'), samples.pattern, { mode: 0o600 });
  const { processor, calls } = capturedProcessor(directory, pdfResponse());
  const args = { file: 'stamped.pdf', text: 'Fictional order 1042', consent: true };
  const first = await processor.run('patterncopy_stamp', args);
  const second = await processor.run('patterncopy_stamp', args);
  assert.equal(calls.length, 2, 'only the two deliberate invocations consume requests');
  assert.notEqual(first.artifacts[0].path, second.artifacts[0].path);
  await assertArtifacts(first, directory, { 'stamped.pdf': 'application/pdf' });
  await assertArtifacts(second, directory, { 'stamped.pdf': 'application/pdf' });
  assert.deepEqual(await fs.readFile(path.join(directory, 'stamped.pdf')), samples.pattern);
});
