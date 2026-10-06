# Testing

Install `requirements-dev.txt` with `--require-hashes`, then run `python -m pytest` from the repository root. Configuration lives in `pyproject.toml`; unknown markers/configuration and warnings fail the suite. CI requires at least 85% combined statement/branch coverage, but assertions must verify meaningful behavior rather than the coverage number alone.

The default suite uses synthetic tokens, an isolated in-memory SQLite database and mocked HTTP responses. It blocks socket connections and ignores the project's dotenv file. Tests cover account ownership, state/CSRF replay and expiry, cookie attributes, request limits, reconnection, refunds, discounts, pagination, mapping, zero/negative updates, DST, token refresh, audit failures and independent client runs.

Live provider checks are **explicitly opted in and read-only**:

```bash
export SQUARE_TEST_ACCESS_TOKEN='dedicated Square sandbox token'
export COMBO_TEST_API_KEY='dedicated Combo test-account token'
python -m pytest tests/integration --run-live --no-cov
```

The Square check uses the sandbox environment. The Combo check only lists locations. No test creates orders or posts revenue, and production credential names are not reused. Live tests are not CI gates because credentials and network access are optional.

For an operator-authorized end-to-end write, use the real `python -m tasks.sync_revenue --date YYYY-MM-DD` command in a separate deployment with dedicated test accounts and verified explicit location mappings. That operation replaces business revenue and is not part of the test suite.
