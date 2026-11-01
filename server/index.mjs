import { fileURLToPath } from 'node:url';
import { realpathSync } from 'node:fs';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createProcessor, ToolError, TOOL_INPUT_SCHEMAS, TOOL_DESCRIPTIONS } from './core.mjs';

export function createMcpServer({ processor, workspaceDir = process.env.FLAMINGO_WORKSPACE_DIR, apiKey = process.env.RAPIDAPI_KEY, transport } = {}) {
  const selected = processor || createProcessor({ workspaceDir, apiKey, transport });
  const server = new McpServer({ name: 'flamingo-file-tools', version: '0.1.0' });
  for (const [name, inputSchema] of Object.entries(TOOL_INPUT_SCHEMAS)) {
    server.registerTool(name, {
      title: name.replaceAll('_', ' '), description: TOOL_DESCRIPTIONS[name], inputSchema,
      annotations: { readOnlyHint: name === 'capabilities', destructiveHint: false, idempotentHint: name === 'capabilities', openWorldHint: name !== 'capabilities' }
    }, async (args, extra) => {
      try {
        const result = await selected.run(name, args, { signal: extra.signal });
        return { content: [{ type: 'text', text: JSON.stringify(result) }], structuredContent: result };
      } catch (error) {
        // Neither raw transport exceptions nor upstream text may enter the chat.
        const safe = error instanceof ToolError ? { code: error.code, message: error.message, ...(error.httpStatus === undefined ? {} : { http_status: error.httpStatus }) } :
          { code: 'operation_failed', message: 'The operation could not complete safely. No automatic retry was made.' };
        return { isError: true, content: [{ type: 'text', text: JSON.stringify({ ok: false, error: safe }) }], structuredContent: { ok: false, error: safe } };
      }
    });
  }
  return server;
}

export async function main(argv = process.argv.slice(2)) {
  if (argv.length === 1 && ['--help', '-h'].includes(argv[0])) {
    process.stdout.write('Flamingo File Tools 0.1.0\n\nRun without arguments as a local stdio MCP server.\nEnvironment: FLAMINGO_WORKSPACE_DIR selects an existing directory; RAPIDAPI_KEY is your own subscribed application key.\nThe capabilities tool and this help need neither key nor network. Every processing call requires consent:true, sends the selected input through RapidAPI, and consumes the selected API plan allowance.\n');
    return;
  }
  if (argv.length === 1 && ['--version', '-V'].includes(argv[0])) { process.stdout.write('0.1.0\n'); return; }
  if (argv.length !== 0) { process.stderr.write('Unsupported command. Use --help or run without arguments for stdio MCP.\n'); process.exitCode = 2; return; }
  const server = createMcpServer();
  await server.connect(new StdioServerTransport());
}

function isMainModule() {
  if (!process.argv[1]) return false;
  try {
    // ESM resolves symbolic links, while argv can retain an alias such as
    // macOS /var -> /private/var. Compare actual files rather than URL spellings.
    return realpathSync(fileURLToPath(import.meta.url)) === realpathSync(process.argv[1]);
  } catch { return false; }
}

if (isMainModule()) {
  main().catch(() => { process.stderr.write('Unable to start the local MCP server. No credentials or request data were logged.\n'); process.exitCode = 1; });
}
