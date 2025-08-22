# Testing Framework

This directory contains the test suite for the square-combo application using pytest.

## Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── unit/                      # Unit tests with mocked dependencies
│   └── adapters/
│       └── test_combo_client.py
├── integration/               # Integration tests with real API calls
│   └── test_combo_integration.py
└── fixtures/                  # Test data and mock responses
```

## Setup

1. Install test dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables for integration tests:
```bash
cp env.example .env
# Edit .env with your actual Combo API credentials
```

## Running Tests

### All Tests
```bash
pytest tests/ -v
# or
python run_tests.py
```

### Unit Tests Only (with mocks)
```bash
pytest tests/unit/ -v
# or  
python run_tests.py --unit
```

### Integration Tests Only (real API calls)
```bash
pytest tests/integration/ -v
# or
python run_tests.py --integration
```

## Test Types

### Unit Tests (`tests/unit/`)
- Fast execution
- Use mocked HTTP responses
- Test error handling and edge cases
- No external dependencies required

### Integration Tests (`tests/integration/`)
- Make real API calls to Combo API
- Require valid `COMBO_API_KEY` environment variable
- Test actual API integration
- Slower execution

## Environment Variables

For integration tests, ensure these are set in your `.env` file:
- `COMBO_API_KEY`: Your Combo API key
- `COMBO_BASE_URL`: Combo API base URL (default: https://partner.combohr.com)

## Test Fixtures

Common test data is defined in `conftest.py`:
- `combo_client`: Configured ComboClient instance
- `mock_locations_response`: Sample locations with teams
- `mock_empty_locations_response`: Empty locations list
- `test_settings`: Test-specific configuration

## Adding New Tests

1. For unit tests: Add to `tests/unit/adapters/test_combo_client.py`
2. For integration tests: Add to `tests/integration/test_combo_integration.py`
3. Use existing fixtures or create new ones in `conftest.py`
4. Follow the naming convention: `test_method_name_scenario`
