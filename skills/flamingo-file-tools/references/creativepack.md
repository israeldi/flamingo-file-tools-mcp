# Optimize an HTML5 advertising ZIP

Use `creativepack_optimize` when eligible PNG/JPEG assets inside a finished HTML5 advertising ZIP need recompression and a complete-ZIP byte-budget report. The input limit is 8 MiB compressed, 32 MiB expanded and 256 members. This is not HTML/JavaScript generation, clickTag repair, rich-media validation or advertising-platform certification.

Obtain the real byte budget for the destination. The tool accepts an integer `budget_bytes` from 1,024 to 8,388,608. Do not substitute a generic 150 KB assumption for an unspecified publisher limit. `lossless` is the default mode. `balanced` can change image pixels and belongs only in a task that allows that tradeoff.

Request shape for an explicitly requested fictional demonstration:

```json
{"tool":"creativepack_optimize","arguments":{"file":"sample-creative.zip","budget_bytes":150000,"mode":"lossless","consent":true}}
```

The example's 150,000-byte budget is a demonstration option, not an ad-network rule.

## Result review

The bridge saves `optimized.zip` and `report.json`. Its summary includes `status`, `input_bytes`, `output_bytes` and `saved_bytes`. A valid result may be `over_budget`; that means processing completed without meeting the specified budget and still consumes allowance. Do not describe it as upload-ready or retry in another mode without authorization.

The bridge compares archive member paths, member hashes and selected report invariants. Non-image member bytes must remain unchanged, dimensions must be reported unchanged, the output archive must not grow, and its digest must agree with the report. It does not execute HTML/JavaScript or independently certify every rendered image.

Review the processed images visually when appearance matters, especially with `balanced`. Use a suitable isolated preview for an explicitly requested functional banner test; extraction/optimization alone does not authorize running an untrusted archive. The relevant ad platform still needs its own checks for click handling, animation, dimensions and delivery requirements.

Deliver both files, actual compressed sizes and the budget status. If it remains too large, explain that code, fonts, animation or creative changes may be needed outside this image-only operation. Keep the source ZIP unchanged.

Use the immutable, hashed [fictional archive](samples.json) only when the user requests a sample run. No optimizer output is bundled with this skill.
