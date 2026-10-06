# Security

This service handles merchant credentials and revenue. Report vulnerabilities privately using GitHub's **Report a vulnerability** link under the Security tab. Do not put credentials, merchant records or live exploit requests in public issues. If private reporting is unavailable, contact the repository owners privately before disclosing details.

The maintained `master` branch is the supported version. This small project does not promise a response SLA. Reports should include the affected commit, entry point, prerequisites, expected boundary and a synthetic reproduction where possible.

Deployment requirements:

- Serve onboarding over HTTPS, bind the application to loopback, and preserve the configured public Host at the trusted reverse proxy.
- Keep dotenv files, SQLite, logs and backups readable/writable only by the runtime account; use encrypted storage and backups. Tokens are not application-encrypted at rest.
- Disable access logs that retain OAuth query codes. Retain only necessary aggregate operational logs.
- Verify deployment SSH host keys out of band, scope sudo permissions and protect master/production deployment.
- Revoke or rotate any credential suspected of exposure. Deleting it from the current tree does not remove it from Git history or logs.

The browser setup capability expires and is consumed after successful linking. Reconnection cannot replace an existing Combo destination. Changing destinations requires restricted operator access and fresh merchant authorization.

A passing static scan or dependency audit is not a guarantee of security. Live proxy, filesystem, account permissions and provider configuration must be checked by the operator.

A history scan on 2026-10-05 detected credential-looking values in `env.example`
(commits `535c9df` and `8b51257`) and `tests/manual_sync_test.py` (commit `500e5b4`).
The current source passes the secret scan, but deleting files does not remove Git
history. Before public release, the owners must establish that these values are
synthetic or revoke the corresponding credentials and check their use. CI scans
the current source; it does not certify old credentials have been revoked.
