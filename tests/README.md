# Tests

This directory contains comprehensive unit tests for the LiteLLM proxy launcher.

## Structure

```
tests/
├── README.md                 # This file
├── __init__.py               # Test package marker
└── unit/                     # Unit tests
    ├── __init__.py           # Unit test package marker
    ├── test_utils.py         # Tests for src/utils.py
    ├── test_config.py        # Tests for src/config.py
    ├── test_cli.py           # Tests for src/cli.py
    ├── test_proxy.py         # Tests for src/proxy.py
    └── test_main.py          # Tests for src/main.py
```

## Running Tests

### Prerequisites

Install the test dependencies:

```bash
pip install -e ".[test]"
# or
pip install -r requirements-test.txt
```

### Running All Tests

```bash
pytest
```

### Running Specific Test Files

```bash
pytest tests/unit/test_utils.py
pytest tests/unit/test_config.py
pytest tests/unit/test_cli.py
pytest tests/unit/test_proxy.py
pytest tests/unit/test_main.py
```

### Running with Coverage

```bash
pytest --cov=src --cov-report=term-missing
```

### Running with Verbose Output

```bash
pytest -v
```

### Running Specific Test Cases

```bash
pytest tests/unit/test_utils.py::TestEnvBool::test_env_bool_with_truthy_values
```

## Test Coverage

The test suite provides comprehensive coverage for all modules in `src/`:

### `test_utils.py`
- `env_bool()` - Boolean environment variable parsing
- `load_dotenv_files()` - .env file loading and processing
- `quote()` - JSON/YAML string escaping
- `temporary_config()` - Temporary config file context manager
- `attach_signal_handlers()` - Signal handling setup
- `validate_prereqs()` - Dependency validation

### `test_config.py`
- `render_config()` - YAML config generation
- `prepare_config()` - Config preparation and validation
- `create_temp_config_if_needed()` - Config context management

### `test_cli.py`
- `parse_args()` - Command-line argument parsing
- Environment variable integration
- CLI argument precedence over environment variables
- Boolean flag handling
- Type validation for numeric arguments

### `test_proxy.py`
- `start_proxy()` - LiteLLM proxy startup
- CLI argument transformation for proxy
- Debug flag handling
- Error propagation
- Import behavior

### `test_main.py`
- `main()` - Main entry point coordination
- Function execution order
- Context manager usage
- Exception handling
- Output message formatting

## Testing Patterns

### Mocking Strategy
- External dependencies are mocked using `unittest.mock`
- File system operations use `Path` mocks
- Environment variables are patched with `patch.dict`

### Test Organization
- Each source file has a corresponding test file
- Tests are grouped into classes by functionality
- Test methods use descriptive names following `test_<function>_<scenario>` pattern

### Fixtures and Utilities
- `capys` fixture for capturing stdout/stderr
- `tmp_path` fixture for temporary file operations
- Parameterized tests for multiple input scenarios

## Best Practices

1. **Test Isolation**: Each test is independent and doesn't rely on others
2. **Comprehensive Coverage**: Both happy path and error conditions are tested
3. **Edge Cases**: Boundary conditions and unusual inputs are included
4. **Mock Verification**: Mock calls are verified for correctness
5. **Clean Setup**: Each test sets up its own fixtures and teardown

## Adding New Tests

When adding new functionality:

1. Create corresponding test methods in the appropriate test file
2. Follow the existing naming conventions
3. Include both positive and negative test cases
4. Mock external dependencies appropriately
5. Verify all expected interactions

## CI/CD Integration

The tests are configured to run with coverage reporting and can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Run tests
  run: |
    pip install -e ".[test]"
    pytest --cov=src --cov-report=xml
```

## Troubleshooting

### Import Errors
Ensure the package is installed in development mode:
```bash
pip install -e .
```

### Module Not Found
Make sure you're running tests from the project root directory where `pyproject.toml` is located.

### Permission Errors
Some tests create temporary files - ensure you have write permissions in the test directory.