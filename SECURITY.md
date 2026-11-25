# Security policy

## Scope

This policy covers the local Flamingo File Tools MCP bridge and its distributed bundle. The bridge calls separately hosted file-processing APIs through RapidAPI; the services and MCP clients have their own security and privacy boundaries. See [data handling](PRIVACY.md) and the supported input profiles in [the README](README.md).

## Reporting a suspected vulnerability

For a suspected vulnerability, use a private provider message through the relevant [RapidAPI listing](README.md#flamingo-file-tools) if that option is available. Begin with the affected component and a short, non-sensitive summary; do not send credentials or actual customer files. If a private contact option is unavailable, open a [repository issue](https://github.com/israeldi/flamingo-file-tools-mcp/issues) requesting a private reporting channel, without disclosing the vulnerability details in public. Ordinary non-security bugs may be reported in the issue tracker using fictional or redacted examples.

Useful details for a private report include the affected release, client and OS, the tool or operation, expected versus observed behavior, and minimal reproduction steps using synthetic data. Do not include API keys, authorization headers, private paths, customer documents, or other personal or confidential information. Do not test against other people's accounts or files or perform destructive testing on a live service.

## Releases and limitations

Report the exact bundle or source revision you used; see [releases](https://github.com/israeldi/flamingo-file-tools-mcp/releases). No fixed support period, response time, security certification, or reward is promised. This policy is not authorization to access systems or data without permission.
