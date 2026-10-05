#!/usr/bin/env bash
# Invoked over SSH with an immutable, CI-tested commit. Run as the deployment user.
set -euo pipefail
umask 077
commit="${1:?Pass the tested commit SHA}"
[[ "$commit" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid commit SHA' >&2; exit 1; }
app_root="${APP_ROOT:-/srv/square-combo}"
repo_url="${REPO_URL:-https://github.com/davaico/square-combo.git}"
mkdir -p "$app_root/releases" "$app_root/shared/logs"
exec 9>"$app_root/shared/deploy.lock"
flock -n 9 || { echo 'Another deployment is running' >&2; exit 1; }
[[ -f "$app_root/shared/app.env" ]] || { echo 'Provision shared/app.env first' >&2; exit 1; }
if [[ ! -d "$app_root/repository/.git" ]]; then
    git clone --no-checkout "$repo_url" "$app_root/repository"
fi
git -C "$app_root/repository" fetch origin master
# Require the exact requested commit to be present on the master history.
git -C "$app_root/repository" merge-base --is-ancestor "$commit" origin/master
release="$app_root/releases/$commit"
[[ ! -e "$release" ]] || { echo 'Release already exists; use the documented rollback/restart procedure' >&2; exit 1; }
mkdir "$release"
git -C "$app_root/repository" archive "$commit" | tar -x -C "$release"
python3 -m venv "$release/venv"
"$release/venv/bin/python" -m pip install --require-hashes -r "$release/requirements.txt"
export SQUARE_COMBO_ENV_FILE="$app_root/shared/app.env"
export DEPLOY_SYNC_LOCK="$app_root/shared/sync.lock"
sudo systemctl stop square-combo-sync.timer
trap 'sudo systemctl start square-combo-sync.timer' ERR
exec 8>"$app_root/shared/sync.lock"
flock -w 120 8 || { sudo systemctl start square-combo-sync.timer; echo 'Sync still running' >&2; exit 1; }
(
    cd "$release"
    # Check configuration and dependency imports before changing the current release.
    "$release/venv/bin/python" -c 'import main; from utils.config import settings; assert settings.APP_URL.startswith("https://"), "Production APP_URL must use HTTPS"'
    "$release/venv/bin/python" -m tasks.sync_revenue --help >/dev/null
    # Initialization adds tables/indexes only. Back up existing SQLite before this step.
    "$release/venv/bin/python" - <<'PY'
from pathlib import Path
import os
import sqlite3
from sqlalchemy.engine import make_url
from utils.config import settings
if settings.SYNC_LOCK_PATH.resolve() != Path(os.environ['DEPLOY_SYNC_LOCK']).resolve():
    raise SystemExit('Set SYNC_LOCK_PATH to /srv/square-combo/shared/sync.lock')
url = make_url(settings.DATABASE_URL)
if url.get_backend_name() != 'sqlite' or not url.database or not Path(url.database).is_absolute():
    raise SystemExit('This deployment profile requires an absolute SQLite DATABASE_URL')
source = Path(url.database)
if source.exists():
    with sqlite3.connect(source) as db, sqlite3.connect(source.with_suffix('.pre-deploy.db')) as backup:
        db.backup(backup)
PY
    "$release/venv/bin/python" -m database
)
previous=""
if [[ -L "$app_root/current" ]]; then previous="$(readlink -f "$app_root/current")"; fi
rollback() {
    local status="$1"
    trap - ERR
    set +e
    if [[ -n "$previous" ]]; then
        ln -sfn "$previous" "$app_root/current.rollback"
        mv -Tf "$app_root/current.rollback" "$app_root/current"
        sudo systemctl restart square-combo
    else
        sudo systemctl stop square-combo
        rm -f "$app_root/current"
    fi
    sudo systemctl start square-combo-sync.timer
    exit "$status"
}
trap 'rollback "$?"' ERR
ln -sfn "$release" "$app_root/current.next"
mv -Tf "$app_root/current.next" "$app_root/current"
sudo systemctl restart square-combo
# Verify the configured public Host while connecting only to loopback.
(
    cd "$release"
    "$release/venv/bin/python" - <<'PYCODE'
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from utils.config import settings
for attempt in range(10):
    try:
        request = urllib.request.Request(f'http://127.0.0.1:8000/health', headers={'Host': urlsplit(settings.APP_URL).netloc})
        with urllib.request.urlopen(request, timeout=5) as response:
            if response.status == 200:
                break
    except (OSError, urllib.error.URLError):
        pass
    time.sleep(2)
else:
    raise SystemExit('Application health check failed')
PYCODE
)
sudo systemctl is-active --quiet square-combo
sudo systemctl start square-combo-sync.timer
trap - ERR
