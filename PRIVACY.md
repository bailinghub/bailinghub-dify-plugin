# Privacy

This plugin sends only the values required for the selected tool to the BailingHub
base URL configured by the Dify administrator:

- `request_id`, `route`, and `input` for job submission;
- `job_id` for job lookup and bounded polling;
- a BailingHub Client Token in the HTTP `Authorization` header.

The `input` value is provided by the Dify workflow or agent and may contain personal,
confidential, or regulated data if the deploying organization places such data in the
request. The plugin does not infer, enrich, or independently collect that data. The
configured BailingHub server also receives ordinary network metadata, such as the source
IP address and request timestamp, as part of handling the HTTPS request.

The plugin does not send data to the plugin author, ACC, the public BailingHub website,
or any analytics service. It does not contain telemetry and does not independently persist
request or response data outside Dify's normal plugin execution lifecycle.

The configured BailingHub instance and its downstream business systems are controlled
by the deploying organization, not by the plugin author. Their retention, logging, audit,
approval, deletion, and privacy policies apply to data processed after submission. Review
those policies before placing personal, confidential, or regulated data in a request. The
deploying organization is responsible for establishing an appropriate legal basis and
responding to access or deletion requests for data processed by its systems.

The plugin deliberately does not accept admin credentials, executor credentials,
business-system credentials, or acting-subject credentials. Administrators should create
a dedicated, route-scoped Client Token for each Dify application and rotate it according
to their own security policy.
