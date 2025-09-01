# Testing Framework

This project uses `pytest` for testing. The tests are divided into two main categories: **unit tests** and **integration tests**.

## Running Tests

Tests are executed using the `run_tests.py` script in the project root.

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the real end to end logic (Real api calls)
python -m tests.manual_sync_test

# Run all tests
python run_tests.py

# Run only unit tests (fast, mocked)
python run_tests.py --unit

# Run only integration tests (slower, real API calls)
python run_tests.py --integration
```

## Manual Sync Test (`tests/manual_sync_test.py`)

This script provides a full end-to-end test of the revenue sync process and both API integration (Square/Combo). It is designed to be run manually to verify the entire workflow with live credentials.

The script will:
1.  Connect to the Square and Combo APIs using the credentials in the `.env` file.
2.  Create several test orders in the Square sandbox.
3.  Fetch the total daily revenue from Square.
4.  Post the final revenue amount to the corresponding location in Combo.

This is the best way to confirm that the entire system is working as expected.

## Unit Tests (`tests/unit/`)

Unit tests are designed to test individual components (e.g., a single class or function) in isolation. They use mocking to simulate external dependencies, such as API calls, and do not require a network connection or valid API keys.

These tests are fast and should be run frequently during development to ensure that the core logic of the application is working correctly.

## Integration Tests (`tests/integration/`)

Integration tests are designed to test the interaction between different components of the application and with external services (like the Square and Combo APIs).

These tests make **real API calls** and require a properly configured `.env` file with valid API credentials. They are essential for verifying that the application can successfully communicate with the external services it depends on.

Due to their reliance on network calls, these tests are slower and may be less stable than the unit tests.
