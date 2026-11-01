# Fictional inputs and honest demonstrations

Read [samples.json](samples.json) for the immutable source URL, expected length and SHA-256 of each owned fictional input. No binary input, response fixture or processing output is included in this skill.

When the user requests a demonstration, download only the requested input into the selected private workspace and verify both its byte length and SHA-256 before processing. A mismatch is a failed provenance check; do not replace the expected digest or silently use a newer file.

Sample downloads from GitHub are separate from API processing. Fetching an input does not authorize uploading it through RapidAPI. Once the requested processing is authorized, choose one applicable operation and use its actual result. Keep a demonstration record of input hash, operation/options, execution date, returned output hash and observed checks. Never include the user's key.

The JSON examples in this skill are request shapes. They are not executed transcripts. Existing constructed transport fixtures in the MCP project's tests are not captured responses to these inputs and must not be used as such. An older successful extraction of a different, larger synthetic MDB also does not establish this ACCDB's result.

For the small Access demonstration, report the actual schema and counts returned by an authorized run. For CreativePack, report the actual byte budget status even when it remains over budget. For PatternCopy, distinguish inspection from a new stamp and identify any visual/layer checks performed. For ShelfRelay, distinguish a preview from applying a store update.
