# Data handling

Flamingo File Tools runs locally. It has no advertising, analytics, remote telemetry, automatic directory scanning or automatic processing on startup. Listing capabilities and tools does not contact a processing service.

When you authorize a processing tool, the chosen file and relevant options are uploaded to that API's fixed `*.p.rapidapi.com` HTTPS hostname. RapidAPI authenticates and forwards the request to the corresponding Access File Extractor, CreativePack, PatternCopy or ShelfRelay service. Your subscription allowance may be consumed even if a request fails. The bridge makes no automatic retry and does not follow redirects.

The RapidAPI application key comes from local sensitive client configuration or the `RAPIDAPI_KEY` environment variable. It is sent only to the selected fixed RapidAPI host. It is not a tool argument, returned in tool results, embedded in the bundle or recorded in bridge analytics. Do not paste it into conversations, public issues or shared configuration files. Your client, operating system and environment management have their own handling and retention.

The bridge creates result files in new directories within your selected workspace and leaves the input intact. It requests owner-only permissions where supported; operating-system ACLs, client permissions, backups and workspace sharing remain under your control. Results can contain confidential source data, archive member names, buyer text, book metadata or processing diagnostics. Delete or retain them according to your needs. Tool summaries are bounded and do not return entire documents or raw error bodies, but your assistant/client may retain the conversation and file names you supply.

Select an owner-controlled folder with no untrusted concurrent writers. The path safeguards do not provide an operating-system sandbox against another local process able to rename or replace workspace directories. POSIX ownership/write-permission checks provide an additional guard; Windows ACL configuration remains your responsibility. The bundle itself does not install an OS sandbox or change your workspace permissions.

ShelfRelay receives your selected JSON request, including supported current and prior XML records and policy. This bridge does not perform the WooCommerce connector's header sanitization for you. Submit only an authorized, prepared request; omit credentials, unnecessary contact details and customer/order data from catalogue records. The bridge neither retrieves referenced cover images nor applies changes to a store.

RapidAPI, API services and network intermediaries have separate processing and logging. Local cleanup is not a guarantee of immediate physical erasure or zero retention by those systems. Review their current policies before uploading:

- [RapidAPI privacy notice](https://rapidapi.com/page/privacy)
- [Access File Extractor: files and marketplace records](https://rapidapi.com/IsraelDiego/api/access-file-extractor)
- [CreativePack: data handling and support](https://rapidapi.com/IsraelDiego/api/creativepack)
- [PatternCopy PDF](https://flamingoapis.synology.me:8443/privacy)
- [ShelfRelay ONIX](https://shelfrelay.flamingoapis.synology.me:8443/privacy)

For bridge issues, use this repository's issue tracker with fictional or redacted examples. For service/account questions, use the relevant RapidAPI listing. Never submit a real key or confidential input in a public support request.
