"""Exercise the release switch and failure paths without SSH or system services."""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "deployment" / "deploy.sh"
SHA = "a" * 40


@pytest.fixture
def deploy_environment(tmp_path):
    root = tmp_path / "app"
    (root / "shared").mkdir(parents=True)
    (root / "shared" / "app.env").write_text("APP_URL=https://example.invalid\n")
    previous = root / "releases" / "previous"
    previous.mkdir(parents=True)
    (root / "current").symlink_to(previous)
    binaries = tmp_path / "bin"
    binaries.mkdir()
    scripts = {
        "git": """#!/bin/bash
set -eu
printf 'git %s\\n' "$*" >> "$EVENTS"
if [[ "$1" == clone ]]; then mkdir -p "${@: -1}/.git"; fi
if [[ "$*" == *archive* ]]; then tar -cf - --files-from /dev/null; fi
""",
        "python3": """#!/bin/bash
set -eu
mkdir -p "$3/bin"
cp "$PYTHON_STUB" "$3/bin/python"
""",
        "sudo": """#!/bin/bash
printf 'sudo %s\\n' "$*" >> "$EVENTS"
if [[ "$*" == 'systemctl restart square-combo' && "$FAIL_PHASE" == restart && ! -f "$FAIL_ONCE" ]]; then
    touch "$FAIL_ONCE"; exit 1
fi
""",
    }
    python_stub = tmp_path / "python-stub"
    python_stub.write_text("""#!/bin/bash
set -eu
printf 'python %s\\n' "$*" >> "$EVENTS"
if [[ "$*" == *pip* && "$FAIL_PHASE" == install ]]; then exit 1; fi
if [[ "$*" == - ]]; then
    input="$(cat)"
    if [[ "$input" == *urlopen* && "$FAIL_PHASE" == health ]]; then exit 1; fi
fi
""")
    python_stub.chmod(0o755)
    for name, content in scripts.items():
        target = binaries / name
        target.write_text(content)
        target.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{binaries}:{os.environ['PATH']}",
        "APP_ROOT": str(root),
        "EVENTS": str(tmp_path / "events"),
        "PYTHON_STUB": str(python_stub),
        "FAIL_ONCE": str(tmp_path / "failed"),
        "FAIL_PHASE": "",
    }
    return root, previous, env


@pytest.mark.parametrize("phase", ["", "install", "restart", "health"])
def test_exact_release_and_rollback(deploy_environment, phase):
    root, previous, env = deploy_environment
    env["FAIL_PHASE"] = phase
    result = subprocess.run(["bash", str(SCRIPT), SHA], env=env, capture_output=True, timeout=10)
    events = Path(env["EVENTS"]).read_text()
    assert (result.returncode == 0) == (phase == "")
    assert f"merge-base --is-ancestor {SHA} origin/master" in events
    assert f"archive {SHA}" in events
    assert "pip install --require-hashes" in events
    assert (root / "current").resolve() == (root / "releases" / SHA if not phase else previous)
    if phase in {"restart", "health"}:
        assert events.count("sudo systemctl restart square-combo") == 2
    if phase != "install":
        assert events.rstrip().endswith("sudo systemctl start square-combo-sync.timer")
    else:
        assert "sudo " not in events


def test_invalid_commit_never_touches_release(deploy_environment):
    root, previous, env = deploy_environment
    result = subprocess.run(
        ["bash", str(SCRIPT), "master"], env=env, capture_output=True, timeout=10
    )
    assert result.returncode != 0
    assert (root / "current").resolve() == previous
    assert not Path(env["EVENTS"]).exists()
