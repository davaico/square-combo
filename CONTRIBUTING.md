# Contributing

Keep changes focused on reliable daily revenue synchronization. Document financial or mapping policy changes with examples and regression tests. Never include real merchant data, tokens, provider responses or deployment addresses in fixtures/issues.

Use Python 3.12–3.14 on Linux and install `requirements-dev.txt` with `python -m pip install --require-hashes -r requirements-dev.txt`. Before opening a PR, run:

```bash
ruff format .
ruff check .
python -m pytest
pip-audit --strict --no-deps --disable-pip -r requirements.txt
pip-audit --strict --no-deps --disable-pip -r requirements-dev.txt
bash -n deployment/deploy.sh
```

CI runs those checks and command/import smoke checks. Repository maintainers should require `test (3.12)`, `test (3.13)`, `test (3.14)`, `audit`, `secrets` and `workflows` before merging and enable private vulnerability reporting. Deployment is manual. Workflow configuration alone does not enforce branch protection.

Runtime and development dependencies are separate, fully pinned and hashed. Edit the `.in` files, then regenerate both locks in a clean Python 3.12 environment:

```bash
pip-compile --generate-hashes --no-emit-index-url --no-emit-trusted-host -o requirements.txt requirements.in
pip-compile --allow-unsafe --generate-hashes --no-emit-index-url --no-emit-trusted-host -o requirements-dev.txt requirements-dev.in
```

Review upstream advisories and compatibility notes, rerun tests/audits and validate the full matrix. Dependabot opens weekly dependency/action updates; regenerate both locks when an update changes resolution. GitHub Actions and the secret scanner are pinned to immutable commits/checksums.

Contributions are accepted under this repository's LGPL-3.0-only license. Preserve attribution and both license texts. Third-party assets require explicit redistribution permission; the application uses text branding rather than bundled provider logos.
