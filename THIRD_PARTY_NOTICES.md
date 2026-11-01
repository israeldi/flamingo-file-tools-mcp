# Third-party components

The release bundle includes the exact production dependencies recorded in `package-lock.json`, with their original license and notice files retained inside `node_modules`. The bridge's MIT license does not replace those licenses.

The pinned Model Context Protocol TypeScript SDK 1.32.2 includes the MIT License, which is retained in the bundle. Zod, yauzl, crc-32 and csv-parse retain their own included licenses. Transitive dependencies retain theirs as well. The repository's later licensing transition must not be substituted for the actual pinned package license.

The MCPB CLI is a build-time dependency and is not part of the runtime bundle. Its license remains applicable to the CLI itself.

The original fictional input PDF uses standard Helvetica and does not bundle DejaVu font material. The separately hosted PDF service's implementation and licensing are outside this local bridge package.
