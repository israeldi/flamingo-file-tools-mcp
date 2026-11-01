# Inspect or label a supported layered PDF

Use PatternCopy for its finite supported unencrypted PDF profile, up to 20 MiB and 100 pages. A visible label is editable and is not DRM. Do not promise universal layer/form preservation, legal copy protection or support for every script/font.

Inspection and stamping are different network operations and can each consume allowance. For an unfamiliar document, inspection can help qualify the profile, but do not silently add it to a stamp-only request. Use an existing relevant inspection when available or obtain authorization for an additional preflight if needed.

Inspection request shape:

```json
{"tool":"patterncopy_inspect","arguments":{"file":"sample-pattern.pdf","consent":true}}
```

The resulting `inspection.json` reports the supported-profile inspection. Its summary includes page count, input size, layer count, form-widget/annotation counts and flags for layers, forms and outlines. It is not a visual certification.

## Stamp the intended line

Confirm the text and placement in the user's request. The text must be one line with 1–160 Unicode code points, no control characters or line separators, and fit the service's supported unshaped left-to-right text profile. Supported corners are `bottom-left`, `bottom-right`, `top-left` and `top-right`. `font_size` is 6–14 pt (default 9); `margin` is 6–72 pt (default 12).

A clear corner must exist on **every page**. Retaining page geometry does not guarantee that a label avoids pattern lines, scale squares, annotations or artwork. A short fictional label and explicit placement can be requested as follows:

```json
{"tool":"patterncopy_stamp","arguments":{"file":"sample-pattern.pdf","text":"Licensed to Alex Example - Order 1042","position":"bottom-left","font_size":9,"margin":12,"consent":true}}
```

This shape does not authorize either operation by itself. Run only the operation(s) covered by the task.

## Result review

Stamping saves `stamped.pdf` in a new result directory. The bridge checks PDF signature, bounded byte length, the response SHA-256 and page-count headers. Its summary reports input/output bytes and pages. These integrity checks cannot establish visual fidelity or meaningful layer behavior.

For a production label, review original and output in a viewer supporting optional-content layer controls. Check size-layer selection/default visibility, page dimensions/rotation and label clearance at the intended print scale. Report which checks were actually performed and any unverified behavior. Do not infer all-document correctness from one successful save or a single rendered page.

Preserve the original. Deliver the stamped PDF and its identity metadata. If the profile or glyphs are unsupported, report that limit rather than flattening or rasterizing the document to force a result.

The [fictional PDF](samples.json) is an input demonstration only. No stamped output or captured inspection is bundled here.
