# Square → Combo

A small integration that sends daily revenue from a Square merchant account to Combo. Merchants connect their accounts through a web page; a separately scheduled command reconciles closed business days. It supports multiple merchants and locations.

## Revenue contract

For each active Square location and configured business date, the amount is:

**completed orders' `total_money` − completed payment refunds' `amount_money`**

The order total already includes discounts; they are not subtracted again. This is the total collected-order amount, including the taxes, tips and service charges represented in Square's total, before payment-processing fees. It is not Square Dashboard's tax-exclusive “net sales” metric. Refunds are assigned to their **creation date**, included only once they are completed, and deduplicated by refund ID. Cumulative returns on updated orders are never subtracted again.

The default business day runs from **06:00 Europe/Paris to the next 06:00**, with daylight-saving time applied. Amounts are calculated in integer minor units and converted to decimal units only when sent. Configure one supported two-decimal currency (EUR, USD, GBP, CHF, CAD or AUD); a different provider currency fails the sync instead of silently converting it. Zero and negative refund-only days are sent too.

The default run reconciles the last three closed business dates. This catches delayed refunds and late provider data within that window. Square can delay offline orders; refunds can remain pending longer. Increase `SYNC_LOOKBACK_DAYS` or rerun affected dates when data arrives later. This is eventual reconciliation, not an exactly-once event stream.

See [Square Orders](https://developer.squareup.com/reference/square/objects/order) and [dated payment refunds](https://developer.squareup.com/reference/square/refunds-api/list-payment-refunds). Combo's Partner API `POST /api/v1/revenues` creates or replaces revenue for the given location/date; reruns intentionally update that amount. Confirm Partner API access with Combo before deployment.

## Local setup

Python **3.12–3.14** on Linux is supported and tested in CI. The command lock and deployment samples use Linux facilities. The default unit suite requires no provider credentials.

```bash
git clone https://github.com/davaico/square-combo.git
cd square-combo
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements.txt
cp env.example .env
# Set Square OAuth application credentials and your intended origin.
python -m database
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open `http://localhost:8000`. In the Square developer dashboard, register the exact callback URL `http://localhost:8000/square-auth/callback` (use an HTTPS development origin if your Square application requires it). Set `SQUARE_ENVIRONMENT=sandbox` for sandbox credentials. OAuth and revenue reads always use the same environment. The application requests only payments, orders and merchant-profile read permissions.

Onboarding uses normal redirects, an expiring server-side setup session, one-use OAuth state and a CSRF-protected Combo form. Reconnecting Square refreshes its credentials and preserves the existing Combo destination and activation policy. Changing an already connected Combo destination is an operator operation: deactivate the client, clear the stored Combo key through your restricted database administration process, then have the merchant reconnect Square and authorize the new destination. No public administrative API is provided.

## Locations and daily synchronization

By default, all active Square locations must have unique case-insensitive name matches in Combo. Unmapped locations, ambiguous name matches or two sources resolving to one destination **fail before any revenue is posted**. Extra unused Combo locations are allowed. A differently named singleton pair is not automatically accepted; `ALLOW_SINGLE_LOCATION_MAPPING=true` explicitly enables that policy.

Explicit ID mappings take precedence and are checked against the available provider locations each run. Use local operator access to configure them:

```bash
python -m tasks.manage clients
python -m tasks.manage map --client-id 1 --square SQUARE_LOCATION_ID --combo COMBO_LOCATION_ID
python -m tasks.manage active --client-id 1 --value false
python -m tasks.sync_revenue             # configured lookback, serialized by a file lock
python -m tasks.sync_revenue --date 2026-09-01  # rerun one closed business date
```

The command returns **0 only when every required location/client succeeds**, otherwise 1. Each client has its own database session; failures do not stop other clients. Transient provider reads and Combo's idempotent updates have bounded retries. OAuth code exchange and token refresh are not replayed automatically. Location results are written to `sync_logs`; business-date run outcomes are written to `sync_runs`. An audit-write failure makes that sync fail even if Combo accepted the update; rerun after fixing persistence.

Scheduling is explicit. Application startup does not install cron. The supplied [systemd timer](deployment/square-combo-sync.timer) runs at 06:15 Europe/Paris; change its timezone/time if you change the business cutoff. [Deployment instructions](docs/VM_SETUP.md) cover setup, backups and rollback.

## Configuration

`env.example` contains supported settings. Configuration reads `.env` from the repository root, independent of the process working directory. Process environment overrides dotenv values; `SQUARE_COMBO_ENV_FILE` selects another dotenv file. Unknown dotenv keys are rejected to catch obsolete configuration.

Production must use an HTTPS `APP_URL`, loopback-only application binding behind TLS, and absolute paths to a protected shared database/log/lock directory. Cookie security follows the configured origin, not untrusted forwarded headers. Provider endpoints require HTTPS outside loopback.

`SYNC_DAYS_BACK` selects how far back the latest reconciled closed day is; its default is 1. `SYNC_LOOKBACK_DAYS` includes additional older dates. Token expiry is stored as naive **UTC** for compatibility with existing database columns, and compared using UTC.

SQLite credentials are stored in ordinary columns. Restrict the runtime account, database, dotenv and backups; use encrypted storage/backups. There is no claim of application-level encryption at rest. Initialization creates additive tables and a unique merchant index; see the migration checklist before upgrading an existing installation.

## Health and logs

- `GET /health`: process/database liveness, HTTP 503 if the database connection fails. This does not claim the scheduled sync is healthy.
- `GET /metrics`: aggregate latest-run outcome, last successful completion timestamp and failed business-date runs in the past 24 hours. Restrict access at the reverse proxy.
- `/`: merchant onboarding; `/auth/square`, `/square-auth/callback`, `POST /combo`: setup flow.

Logs contain IDs, counts and sanitized error classes/statuses, not raw orders, credentials or provider responses. Files rotate at 10 MB, with five general and ten sync backups. Disable proxy/ASGI access logs containing callback query strings, as shown in the deployment examples. [Monitoring guidance](docs/GRAFANA_SETUP.md) explains alerts and retention.

## Development and tests

```bash
python -m pip install --require-hashes -r requirements-dev.txt
python -m pytest
ruff check .
ruff format --check .
pip-audit --strict --no-deps --disable-pip -r requirements.txt
```

The default suite blocks network connections and tests real HTTP setup routes, SQLite state transitions and mocked provider contracts. Opt-in provider checks are read-only and use dedicated test credentials; see [tests/README.md](tests/README.md). See [CONTRIBUTING.md](CONTRIBUTING.md) for dependency updates and the required CI checks.

## License and security

Copyright © 2026 Davai. Licensed under **GNU LGPLv3 only** (`LGPL-3.0-only`), with the [LGPL terms](LICENSE) and incorporated [GPLv3 terms](COPYING). Preserve the [notice](NOTICE) when redistributing. Commercial use and resale are permitted under the license's conditions. Square and Combo trademarks belong to their owners; provider logos and proprietary documentation are not distributed here.

Report vulnerabilities privately through [GitHub's security reporting](https://github.com/davaico/square-combo/security/advisories/new), following [SECURITY.md](SECURITY.md).
