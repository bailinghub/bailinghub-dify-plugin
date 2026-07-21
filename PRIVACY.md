# Privacy

This plugin sends only the values required for the selected tool to the BailingHub
base URL configured by the Dify administrator:

- `request_id`, `route`, and `input` for job submission;
- `job_id` for job lookup and bounded polling;
- a BailingHub Client Token in the HTTP `Authorization` header.

The plugin does not send data to the plugin author, ACC, the public BailingHub website,
or any analytics service. It does not contain telemetry.

The configured BailingHub instance and its downstream business systems are controlled
by the deploying organization. Their retention, audit, approval, and privacy policies
apply to data processed after submission. Review those policies before placing personal,
confidential, or regulated data in a request.

The plugin deliberately does not accept admin credentials, executor credentials,
business-system credentials, or acting-subject credentials. Administrators should create
a dedicated, route-scoped Client Token for each Dify application and rotate it according
to their own security policy.
