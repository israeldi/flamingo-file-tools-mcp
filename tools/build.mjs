import * as fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';

const root = fileURLToPath(new URL('../', import.meta.url));
const pkg = JSON.parse(await fs.readFile(path.join(root, 'package.json'), 'utf8'));
const build = path.join(root, 'build');
const stage = path.join(build, 'bundle');
const dist = path.join(root, 'dist');
// Only this package's generated build directory is cleared; no user paths are accepted.
await fs.rm(build, { recursive: true, force: true });
await fs.mkdir(stage, { recursive: true });
await fs.mkdir(dist, { recursive: true });
for (const name of ['manifest.json', 'package.json', 'package-lock.json', 'LICENSE', 'README.md', 'PRIVACY.md', 'THIRD_PARTY_NOTICES.md', 'server', 'samples']) {
  await fs.cp(path.join(root, name), path.join(stage, name), { recursive: true });
}
execFileSync('npm', ['ci', '--omit=dev', '--ignore-scripts', '--no-fund', '--no-audit'], { cwd: stage, stdio: 'inherit' });
const cli = path.join(root, 'node_modules/@anthropic-ai/mcpb/dist/cli/cli.js');
execFileSync(process.execPath, [cli, 'validate', path.join(stage, 'manifest.json')], { stdio: 'inherit' });
const bundle = path.join(dist, 'flamingo-file-tools.mcpb');
execFileSync(process.execPath, [cli, 'pack', stage, bundle], { stdio: 'inherit' });
const data = await fs.readFile(bundle);
const sha = createHash('sha256').update(data).digest('hex');
const metadata = {
  $schema: 'https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json',
  name: 'io.github.israeldi/flamingo-file-tools',
  title: 'Flamingo File Tools',
  description: 'Access tables, HTML5 ad ZIPs, layered PDF stamps and ONIX previews via RapidAPI.',
  version: pkg.version,
  repository: { url: 'https://github.com/israeldi/flamingo-file-tools-mcp', source: 'github' },
  packages: [{
    registryType: 'mcpb',
    identifier: `https://github.com/israeldi/flamingo-file-tools-mcp/releases/download/v${pkg.version}/flamingo-file-tools.mcpb`,
    fileSha256: sha,
    transport: { type: 'stdio' }
  }]
};
await fs.writeFile(path.join(dist, 'server.json'), JSON.stringify(metadata, null, 2) + '\n');
await fs.writeFile(path.join(dist, 'SHA256SUMS'), `${sha}  flamingo-file-tools.mcpb\n`);
console.log(JSON.stringify({ bundle: path.basename(bundle), bytes: data.length, sha256: sha, version: pkg.version }));
