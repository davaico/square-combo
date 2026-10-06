# Linux deployment

The supplied profile uses Python 3.12+, SQLite, Nginx/TLS, a restricted `squarecombo` runtime/deployment account and `/srv/square-combo`. Change paths consistently if your installation differs. The web application never installs its own scheduler.

## Provisioning

Install Git, Python with venv support, Nginx, certbot and util-linux (`flock`). Create the system account and shared directories:

```bash
sudo useradd --system --create-home --home-dir /srv/square-combo --shell /bin/bash squarecombo
sudo install -d -m 700 -o squarecombo -g squarecombo /srv/square-combo/shared /srv/square-combo/shared/logs /srv/square-combo/releases
sudo install -m 600 -o squarecombo -g squarecombo env.example /srv/square-combo/shared/app.env
```

Edit `shared/app.env`: configure production Square credentials, `APP_URL=https://your-domain.example`, `SQUARE_ENVIRONMENT=production`, and these absolute shared paths:

```dotenv
DATABASE_URL=sqlite:////srv/square-combo/shared/square_combo.db
LOG_DIR=/srv/square-combo/shared/logs
SYNC_LOCK_PATH=/srv/square-combo/shared/sync.lock
```

The deployment account needs an SSH key accepted by the VM and read access to the GitHub repository (public HTTPS after publication, or a read-only deploy key while private). Give it sudo permission **only** for stopping/restarting/checking `square-combo.service` and stopping/starting `square-combo-sync.timer`; do not grant general root shell access.

While the repository is private, initialize its checkout with a read-only SSH deploy key before the first deployment:

```bash
sudo -u squarecombo git clone --no-checkout git@github.com:davaico/square-combo.git /srv/square-combo/repository
```

Install the units under `/etc/systemd/system/` and reload systemd:

```bash
sudo install -m 644 deployment/square-combo.service deployment/square-combo-sync.service deployment/square-combo-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable square-combo.service square-combo-sync.timer
```

Install `deployment/nginx.conf` in your Nginx HTTP context, replace the domain, verify with `sudo nginx -t`, and obtain a TLS certificate with certbot. The sample limits body size, throttles onboarding requests and suppresses query-bearing access logs. Test HTTPS before onboarding. Do not trust incoming forwarded headers from arbitrary peers.

Deploy a tested master commit, initially over the provisioned account's SSH connection:

```bash
ssh squarecombo@YOUR_VM bash -s -- TESTED_40_CHARACTER_COMMIT < deployment/deploy.sh
```

The script serializes deployments, fetches master history, requires the requested SHA to belong to it, creates an immutable release with its own venv, checks configuration, stops the timer and locks out sync, backs up the SQLite database, applies additive schema initialization, switches `current`, restarts and verifies health. An installation, migration or restart failure fails deployment. Startup failure restores the previous release. On first-install failure there is no previous release to restore; correct the provisioning error and retry after removing the failed release directory.

## Manual deployment

GitHub Actions validates the code; deployment is a manual operator action. No VM SSH credentials are required by CI. Use the exact master commit whose CI checks passed when invoking the deployment command above. Verify the VM's SSH host key out of band and retain normal strict host-key checking.

Protect master with the required CI checks and review requirements. Repository workflow files cannot establish branch protection.

## Existing-installation migration

Before merging/deploying this release:

1. Stop the old cron entry, back up the existing database and capture the previous service configuration. Move the database into the protected shared directory without discarding merchant rows.
2. Remove obsolete dotenv keys (`SQUARE_BASE_URL`, `COMBO_API_KEY`, `SYNC_TIME`, `SQUARE_ACCESS_TOKEN`, `SQUARE_APPLICATION_ID`), then use the supported configuration above. OAuth environment now controls both authorization and API reads.
3. Check for duplicate `clients.square_merchant_id` rows. Resolve duplicates under operator control before initialization; creating the unique index intentionally fails rather than choosing one credential set. Empty Combo keys should be cleared to SQL NULL before fresh onboarding.
4. Review stored expiry timestamps. Previous Square RFC3339 imports normally represent UTC; normalize any manually entered host-local values to UTC before the new UTC comparisons.
5. Initialize with `SQUARE_COMBO_ENV_FILE=/srv/square-combo/shared/app.env python -m database` using the release venv. This adds setup sessions, explicit mappings and run records; existing client/sync-log columns remain compatible. Restrict database/backups to mode 600.
6. Verify each location mapping. Old singleton name mismatches now require an explicit ID mapping or the explicit singleton policy. Disable inactive clients and rerun selected dates to correct old financial totals.
7. Replace old service/cron configuration with the supplied units; verify `systemctl list-timers`, a test-account run and monitoring. Review access-log retention and restrict or retire old raw-order logs according to your retention policy.

## Backups and rollback

The script makes a consistent SQLite `.pre-deploy.db` backup before schema initialization. Protect/encrypt that backup; it contains tokens. Arrange retained, off-host backups separately—this single local copy is not a backup policy.

For a code rollback, stop the timer, wait for/acquire `shared/sync.lock`, repoint `current` to a known working release, restart the web service, check health and restart the timer. Do not restore a stale database while a task is running. Schema changes here are additive; a credential/schema data rollback requires a deliberate restore from a verified backup and reconciliation of any provider writes after the backup.

Use `journalctl -u square-combo -u square-combo-sync` for process failures. The job's nonzero exit status and aggregate metrics distinguish failed synchronization from healthy HTTP liveness. Actual TLS, filesystem permissions, secret rotation and provider production access require operator verification; CI does not contact the production VM or accounts.
