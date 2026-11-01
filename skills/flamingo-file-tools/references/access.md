# Export Access tables

Use `access_extract` for a local MDB/ACCDB snapshot containing supported scalar tables. It does not migrate forms, reports, macros/VBA, saved-query execution, linked data or an Access application. Input is bounded to 40 MiB; the serialized response is bounded to 32 MiB. The bridge's manifest checks allow up to 100 tables and 250,000 total rows; reaching any boundary is a limit, not permission to truncate.

Choose `json` for typed table data and schema metadata. Choose `csv` when the downstream tool needs a ZIP containing a manifest and per-table CSVs; retain the manifest because CSV alone does not express the full type information. Do not silently coerce absent values, numbers or dates to fit an expected result.

Request shape, assuming this exact upload is already authorized:

```json
{"tool":"access_extract","arguments":{"file":"sample-access.accdb","format":"json","consent":true}}
```

For the CSV variant:

```json
{"tool":"access_extract","arguments":{"file":"sample-access.accdb","format":"csv","consent":true}}
```

These are separate alternatives, not a direction to make two calls. `format` defaults to `json` if omitted.

## Result review

The bridge saves `extracted.json` or `extracted-csv.zip` in a new result directory. Its summary contains `format`, `table_count` and `total_rows`. It checks that the manifest is complete, uses schema version `1.0`, matches the requested format and agrees with the returned table identities and row counts. JSON row widths must match the column metadata. CSV responses must have only the declared `manifest.json` and `tables/<number>.csv` members, matching headers and counts.

Those checks establish response consistency, not independent equality with every original database value. When the user's task depends on exact business totals or semantics, compare the relevant source totals/schema with the extracted data through an appropriate authorized source reader before claiming fidelity. Do not label a rejected or incomplete export as a smaller successful migration.

Preserve the original database and report the new artifact, table/row counts and any unsupported features. Do not open a returned CSV in a formula-executing application as part of extraction alone; review cell content appropriately before spreadsheet use.

For an initial demonstration, [the sample manifest](samples.json) identifies the owned `sample-access.accdb` by immutable URL, size and hash. The package does not contain a captured output for that exact sample. Run only an authorized demonstration and report its actual returned schema and counts; do not use a constructed `ExampleTable` fixture as its result.
