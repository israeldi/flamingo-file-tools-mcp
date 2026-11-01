# Access and data handling

Agensi delivers the instructions and standalone Python client source for this free companion. The agent runs only the selected script temporarily on macOS or Linux with Python 3.10+ and its standard library. These clients require POSIX file protections; Windows execution is not qualified and must stop before upload. Agensi does not host the API service or provide a RapidAPI subscription. An existing Flamingo File Tools MCP `0.1.0` connection remains an alternative; its [source and setup documentation](https://github.com/israeldi/flamingo-file-tools-mcp/tree/5e728d953d345000f6a2438dc105f9180914b49d) describes that separate route. A user asking for a file result has not thereby requested an installation or subscription.

For the Python route, pass an existing selected directory with `--workspace` and a relative selected input with `--file`. Supply only the named `RAPIDAPI_KEY` privately in that process's environment using the user's existing secure configuration. The script accepts no key or endpoint argument. Do not enumerate unrelated environment variables or copy secrets out of another client. For an existing MCP connection, the client configuration instead selects `FLAMINGO_WORKSPACE_DIR` and supplies its key privately. Do not ask the user to paste a key into chat or include one in filenames, PDF labels, source files, command arguments or shared settings.

Each processing request uploads the selected file and relevant options through a fixed HTTPS RapidAPI host to that API's NAS service:

| API | Fixed host | Selected input limit |
| --- | --- | --- |
| Access File Extractor | `access-file-extractor.p.rapidapi.com` | 40 MiB |
| CreativePack | `creativepack.p.rapidapi.com` | 8 MiB ZIP |
| PatternCopy PDF | `patterncopy-pdf.p.rapidapi.com` | 20 MiB PDF; 1–100 pages |
| ShelfRelay ONIX | `shelfrelay-onix.p.rapidapi.com` | 8 MiB JSON; 1–100 records; 256 KiB per current/prior XML record |

The user needs an active subscription to each selected API, separately from the free skill. Processing, failures and deliberate retries can consume allowance. Do not infer a subscription from possession of an application key or promise that a call is free. No request, retry or processing is made merely by discovery or startup.

Only stable regular files inside the selected workspace are supported. The clients refuse symlink traversal and outside paths, preserve originals and create new private result directories. Use a directory the user controls without untrusted concurrent writers; those checks are not an operating-system sandbox. On POSIX, the selected directory and traversed subdirectories must belong to the user and not allow group/world writes.

The clients inspect archive members in memory for integrity; they do not extract or execute returned archives, retrieve referenced book covers, write to WooCommerce or run a background queue. They use fixed verified HTTPS endpoints, refuse redirects and make no automatic retries. Saved artifacts can contain the source's confidential information. Manage their retention and sharing according to the user's task. Local file cleanup does not guarantee zero retention in RapidAPI, network intermediaries, API services or the agent's conversation.

For source-specific retention and logging questions, read the server's [privacy document](https://github.com/israeldi/flamingo-file-tools-mcp/blob/5e728d953d345000f6a2438dc105f9180914b49d/PRIVACY.md) and current policies it references before confidential processing. Do not invent a no-retention or regional-hosting guarantee.
