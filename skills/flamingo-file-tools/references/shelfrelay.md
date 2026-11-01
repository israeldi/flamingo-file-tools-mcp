# Preview supported ONIX book updates

Use `shelfrelay_preview` for a **prepared UTF-8 JSON records/policy request**, not a raw XML feed. The profile handles supported ONIX 3.0/3.1 physical-book ISBN records from one source authority. It is not universal ONIX validation, arbitrary supplier mapping, multi-supplier reconciliation, grouped print/ebook fulfilment or a storefront synchronization job.

The envelope has 1–100 `records`, each with `xml` and optional `previous_xml`. Its `policy` requires two-letter `market_country`, three-letter `currency` and `price_type` (`01` excludes tax; `02` includes tax). Optional policy includes `as_of`, a selected supplier identifier and supported `merchant_owned_fields`. Preserve a valid previous source state when the request needs it; do not invent or omit one merely to force a desired update.

The request file is at most 8 MiB. Each current/prior XML record is at most 256 KiB. A large catalogue must not be silently truncated into a purportedly complete preview. If the user only has a raw feed, explain that this tool needs the full envelope and use an authorized existing preparation/connector workflow; do not send raw XML to the JSON tool or drop header context.

The fictional sample contains the complete request shape:

```json
{"tool":"shelfrelay_preview","arguments":{"file":"sample-onix-request.json","consent":true}}
```

Before processing real catalogue data, confirm the applicable market/currency/price convention and which fields the merchant controls. The bridge sends the prepared request as selected; it does not perform the WooCommerce connector's header sanitization. Do not include unnecessary credentials, customer/order records or private contact details in the catalogue envelope.

## Result review

The bridge saves `preview.json`. A successful top-level tool return and HTTP 200 do not mean every book was accepted. Its summary is `total`, `ok` and `rejected`; inspect every result's index, `status`, diagnostics and proposed `projection` before describing it as usable.

Review ISBN identity, source authority, price/tax convention, availability and merchant-owned fields. Preserve distinctions among absent, unknown, explicit clears and concrete values: missing price/stock is not zero, and omitted delta records are not deletions. A withdrawn record needs its explicit supported operation rather than a guessed clear.

`next_xml` is proposed retained source state for a later successful downstream write. The preview tool does not write products or commit a store checkpoint. Do not mark it applied or replace a merchant's stored source history merely because a preview returned. Refer an explicitly requested store integration to its existing separately reviewed connector workflow.

The bridge does not fetch the returned cover URL or download a catalogue. An image URL in a result is metadata, not proof the image was retrieved or permitted. Date-dependent decisions may require a new authorized preview for the intended decision date; do not claim a stale preview is current.

The [sample request](samples.json) contains invented catalogue data. It is not a live response or evidence of customer adoption.
