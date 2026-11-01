# Flamingo File Tools

Use four focused file-processing APIs from an MCP assistant. The local bridge reads a file you select, sends one deliberate request through RapidAPI, and saves new results in your selected folder.

Version `0.1.0` is listed in the [Official MCP Registry](https://registry.modelcontextprotocol.io/?q=flamingo-file-tools) under `io.github.israeldi/flamingo-file-tools`.

| Task | API and subscription |
| --- | --- |
| Export supported MDB/ACCDB scalar tables to typed JSON or CSV ZIP | [Access File Extractor](https://rapidapi.com/IsraelDiego/api/access-file-extractor) |
| Reduce PNG/JPEG assets inside an HTML5 advertising ZIP and check a byte budget | [CreativePack](https://rapidapi.com/IsraelDiego/api/creativepack) |
| Inspect or add visible text to a supported layered PDF | [PatternCopy PDF](https://rapidapi.com/IsraelDiego/api/patterncopy-pdf) |
| Turn a supported ONIX request into an explicit book-update projection for review | [ShelfRelay ONIX](https://rapidapi.com/IsraelDiego/api/shelfrelay-onix) |

The bridge is free source code. **Processing requires your own RapidAPI application key and a separate subscription to each API you use.** Review the current free compatibility allowance, paid plans and limits on its listing. Requests, failures and deliberate retries can consume allowance. There are no automatic processing calls on startup or tool discovery, and no automatic retries.

The optional [Flamingo File Tools skill](./skills/flamingo-file-tools/SKILL.md) helps an agent select one file task, run it deliberately, and return reviewable artifacts. Skill source version `0.2.1` includes independent Python standard-library clients for macOS/Linux, so that route needs no separate MCP bridge or pip installation. A compatible agent runs the selected script unchanged temporarily. Python 3.10+, a working HTTPS trust store, a private workspace, your private application key and a separate subscription to the selected API remain necessary. An existing private `RAPIDAPI_KEY` remains supported. The optional [private-file setup](./skills/flamingo-file-tools/references/key-setup.md) uses hidden input in the user's own Terminal on the same host and OS account as the agent; remote execution needs its own private setup route. Only the processing client reads the explicitly selected key file. Never send keys or credential files in chat. Setup does not call an API, verify a subscription or replace an existing credential. The existing MCP server is still an alternative for clients already configured to use it.

The [free Agensi listing](https://www.agensi.io/skills/flamingo-file-tools-access-pdf-zip-onix) currently serves approved package `v1.1`, containing skill source `0.2.0` and the four temporary clients. The same listing's `v1.2` update (source `0.2.1`, five scripts including private key setup) was submitted on November 1, 2026 and is pending review; that update is not yet the served Agensi package. Agensi loads the selected client into a compatible agent; it does not host the processing service. Loading instructions alone makes no upload or processing request. API access and usage are separate from the free skill.

## Install

Download the `.mcpb` file from [GitHub Releases](https://github.com/israeldi/flamingo-file-tools-mcp/releases). Open it in a client that supports MCP bundles, choose a private workspace folder, and enter your application key only in the client's sensitive configuration field. MCPB support varies by client. This is a standard local stdio MCP server for clients supporting that transport; it is not a remote web connector.

For manual stdio installation, use Node.js 20 or later, clone this repository and run `npm ci --omit=dev --ignore-scripts`. Configure your client to run `node /absolute/path/to/server/index.mjs`, with `FLAMINGO_WORKSPACE_DIR` set to the selected folder and `RAPIDAPI_KEY` supplied through its private environment/credential configuration. Keep filled client configurations out of public repositories and support reports.

## Try a fictional example

Copy the original files from [samples](./samples) into your workspace. They contain invented demonstration data. Their hashes and provenance are included. Start with `capabilities`; it needs no key and sends nothing.

Ask your assistant to inspect a particular sample, name the destination service, explain the upload and allowance, and wait for your consent before processing. Each processing call requires `consent: true`. For example:

> Use Access File Extractor to export sample-access.accdb as JSON. I authorize uploading this fictional sample through RapidAPI for this one request.

Other examples:

- Optimize `sample-creative.zip` in lossless mode against a 150,000-byte budget. An `over_budget` result is valid and means further creative changes may be needed.
- Inspect `sample-pattern.pdf`; after reviewing compatibility, separately stamp it with `Licensed to Alex Example — Order 1042`. Inspection and stamping are two separate requests. Review the returned PDF visually at print scale and confirm every page has clear space for the text.
- Preview `sample-onix-request.json`, then review each record's status, diagnostics and proposed fields. HTTP 200 is not proof that all records were accepted. No WooCommerce store is changed.

The model can request tool calls; your MCP client controls its approval experience. Check the file and destination yourself. The required consent field does not replace your client's security controls or create permission to process someone else's files.

## Scope and results

Access handles supported local scalar tables, not forms, reports, macros, saved-query execution or linked-database migration. Its limits include 40 MiB input and 32 MiB serialized output. CreativePack handles up to an 8 MiB ZIP and preserves non-image members; a returned archive is not advertising-platform approval. PatternCopy supports a finite PDF profile, up to 20 MiB/100 pages; encrypted and unsupported documents are refused. Its visible text is editable and is not DRM.

ShelfRelay accepts the existing full JSON `records`/`policy` contract, including prior source XML when required. Its physical-ISBN, single-source profile is not universal ONIX validation, grouped print/ebook fulfilment or multi-supplier reconciliation. Limits include 100 records, 8 MiB JSON and 256 KiB per XML source. Unknown or absent fields must not be treated as zero or cleared values. Use the [WooCommerce connector](https://github.com/israeldi/flamingo-api-examples/tree/main/integrations/woocommerce) for separately reviewed store application.

The bridge restricts input to regular files inside the selected folder, rejects symlink traversal, preserves originals and creates a new artifact directory per operation. It never extracts or executes returned ZIP members, downloads cover URLs, or writes to a storefront. Tool results return bounded status and artifact metadata rather than putting full databases, PDFs or source XML into the conversation. Artifact contents remain untrusted data.

Use a folder you control, without untrusted people or processes modifying it concurrently. Path and symlink checks are safeguards for that workspace model, not an operating-system sandbox against a hostile local writer. On POSIX systems, the workspace and traversed subdirectories must belong to your user and must not be writable by a group or other users. On Windows, choose an appropriately restricted folder using its normal ACL controls.

Review saved results against the source before using them. Keep the workspace private and manage its retention and backups. Read [data handling](./PRIVACY.md) before connecting confidential files.

## Development and verification

`npm ci --ignore-scripts` then `npm test` exercises the MCP protocol and request/output contracts with fictional fixtures and injected transports. These checks do not establish customer adoption or a new live gateway result. Bundle installation in a particular desktop client is not inferred from protocol checks.

New bridge code is MIT licensed; dependencies retain their own licenses and notices. The samples are original fictional demonstrations; the input PDF uses standard Helvetica. See [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).
