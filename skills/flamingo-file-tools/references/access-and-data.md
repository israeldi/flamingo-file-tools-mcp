# Access and data handling

This skill targets Flamingo File Tools MCP `0.1.0`, a local stdio server. Agensi supplies these instructions, not the server runtime. The server's [source and setup documentation](https://github.com/israeldi/flamingo-file-tools-mcp/tree/5e728d953d345000f6a2438dc105f9180914b49d) describe client-specific connection steps. A user asking only for a file result has not thereby requested a new installation or subscription.

The client configuration selects `FLAMINGO_WORKSPACE_DIR` and supplies `RAPIDAPI_KEY` privately. The key is not a tool argument. Do not ask the user to paste it into chat or include it in filenames, PDF labels, source files or shared client settings.

Each processing request uploads the selected file and relevant options through a fixed HTTPS RapidAPI host to that API's NAS service:

| API | Fixed host | Selected input limit |
| --- | --- | --- |
| Access File Extractor | `access-file-extractor.p.rapidapi.com` | 40 MiB |
| CreativePack | `creativepack.p.rapidapi.com` | 8 MiB ZIP |
| PatternCopy PDF | `patterncopy-pdf.p.rapidapi.com` | 20 MiB PDF; 1–100 pages |
| ShelfRelay ONIX | `shelfrelay-onix.p.rapidapi.com` | 8 MiB JSON; 1–100 records; 256 KiB per current/prior XML record |

The user needs an active subscription to each selected API, separately from the free skill. Processing, failures and deliberate retries can consume allowance. Do not infer a subscription from possession of an application key or promise that a call is free. No request, retry or processing is made merely by discovery or startup.

Only stable regular files inside the selected workspace are supported. The bridge refuses symlink traversal and outside paths, preserves originals and creates new result directories. Use a directory the user controls without untrusted concurrent writers; those checks are not an operating-system sandbox. On POSIX, the selected directory and traversed subdirectories must belong to the user and not allow group/world writes.

The bridge does not execute or extract returned archives, retrieve referenced book covers, write to WooCommerce or run a background queue. Saved artifacts can contain the source's confidential information. Manage their retention and sharing according to the user's task. Local file cleanup does not guarantee zero retention in RapidAPI, network intermediaries, API services or the agent's conversation.

For source-specific retention and logging questions, read the server's [privacy document](https://github.com/israeldi/flamingo-file-tools-mcp/blob/5e728d953d345000f6a2438dc105f9180914b49d/PRIVACY.md) and current policies it references before confidential processing. Do not invent a no-retention or regional-hosting guarantee.
