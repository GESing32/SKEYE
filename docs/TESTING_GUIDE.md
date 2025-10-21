# Testing Guide for SKEYE Flight System

## Quick Start

### Using Virtual Environment (Recommended)

**Always activate the virtual environment before running tests:**

```bash
# Windows PowerShell
.venv\Scripts\activate

# Windows Command Prompt
.venv\Scripts\activate.bat

# After activation, your prompt should show (.venv)
```

**Then run tests:**

```bash
# Run all tests
pytest test/unit/

# Run with coverage
pytest test/unit/ --cov=src/flight-system/v2 --cov-report=html

# Run specific test file
pytest test/unit/pytest_test_gcs_core.py -v

# Run specific test class
pytest test/unit/pytest_test_gcs_core.py::TestErrorHandling -v
```

### Alternative: Direct Python Execution

If you don't want to activate the venv, use the Python executable directly:

```bash
# Windows
.venv\Scripts\python.exe -m pytest test/unit/

# With coverage
.venv\Scripts\python.exe -m pytest test/unit/ --cov=src/flight-system/v2 --cov-report=html
```

## Common Issues and Solutions

### Issue: "fixture 'mocker' not found"

**Cause:** pytest-mock not installed in virtual environment

**Solution:**
```bash
.venv\Scripts\python.exe -m pip install pytest-mock
```

### Issue: "ModuleNotFoundError: No module named 'pymavlink'"

**Cause:** pymavlink not installed in virtual environment

**Solution:**
```bash
.venv\Scripts\python.exe -m pip install pymavlink
```

### Issue: Tests run but use global Python instead of venv

**Symptom:** Tests pass on command line but fail in VS Code, or vice versa

**Solution:**
1. Make sure VS Code is using the venv Python interpreter:
   - Press `Ctrl+Shift+P`
   - Type "Python: Select Interpreter"
   - Choose `.venv\Scripts\python.exe`

2. Or always use the full path to venv Python:
   ```bash
   .venv\Scripts\python.exe -m pytest
   ```

## Installing All Test Dependencies

If you need to reinstall all test dependencies in the virtual environment:

```bash
# Activate venv first
.venv\Scripts\activate

# Install all test requirements
pip install -r requirements-test.txt
pip install pymavlink

# Verify installation
pytest --version
python -c "import pytest_mock; print('pytest-mock installed')"
python -c "import pymavlink; print('pymavlink installed')"
```

## Running Different Test Types

### Python Unit Tests (unittest)
```bash
python run_python_tests.py
```

### Python Unit Tests (pytest)
```bash
# All pytest tests
pytest test/unit/

# Only pytest-style tests (not unittest)
pytest test/unit/pytest_*.py

# Specific module
pytest test/unit/pytest_test_gcs_core.py
pytest test/unit/pytest_test_geometry_utils.py
pytest test/unit/pytest_test_survey_planner.py
```

### Flutter/Dart Tests
```bash
# All Flutter tests
flutter test

# With coverage
flutter test --coverage

# Specific test file
flutter test test/widget_test.dart
flutter test test/unit/telemetry_test.dart
flutter test test/integration/gcs_integration_test.dart
```

## Coverage Reports

### Generate Python Coverage
```bash
# HTML report (recommended)
pytest test/unit/ --cov=src/flight-system/v2 --cov-report=html
# Open htmlcov/index.html in browser

# Terminal report
pytest test/unit/ --cov=src/flight-system/v2 --cov-report=term

# Terminal with missing lines
pytest test/unit/ --cov=src/flight-system/v2 --cov-report=term-missing
```

### Generate Flutter Coverage
```bash
flutter test --coverage
# Coverage saved to coverage/lcov.info

# Generate HTML report (requires lcov)
genhtml coverage/lcov.info -o coverage/html
```

## Test Markers

Use pytest markers to run specific test categories:

```bash
# Run only unit tests
pytest -m unit

# Run only MAVLink tests
pytest -m mavlink

# Run only geometry tests
pytest -m geometry

# Run only survey planning tests
pytest -m survey

# Run only integration tests
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

## Useful Pytest Options

```bash
# Verbose output
pytest -v

# Very verbose (show test names and output)
pytest -vv

# Stop on first failure
pytest -x

# Run last failed tests only
pytest --lf

# Run in parallel (faster, requires pytest-xdist)
pytest -n auto

# Show local variables on failure
pytest -l

# Collect tests without running
pytest --collect-only
```

## VS Code Integration

### Run Tests in VS Code

1. Open the Testing panel (beaker icon on left sidebar)
2. Click "Configure Python Tests"
3. Select "pytest"
4. Select "test" as the root directory
5. Tests will appear in the Testing panel
6. Click the play button to run tests

### Debug Tests in VS Code

1. Set breakpoints in your test files
2. Right-click on a test in the Testing panel
3. Select "Debug Test"

## Troubleshooting

### Tests pass in terminal but fail in VS Code

**Solution:** Make sure VS Code is using the correct Python interpreter:
1. Press `Ctrl+Shift+P`
2. Type "Python: Select Interpreter"
3. Choose `.venv\Scripts\python.exe`
4. Reload the window (`Ctrl+Shift+P` → "Reload Window")

### ImportError or ModuleNotFoundError

**Solution:** Check your Python path:
```bash
# Should show venv Python
which python  # Linux/Mac
where python  # Windows

# Verify packages installed
pip list | grep pytest
pip list | grep pymavlink
```

### Tests hang or timeout

**Possible causes:**
- Infinite loop in code
- Blocking I/O operation
- Missing mock for network/serial operations

**Solution:** Add timeout to pytest:
```bash
pytest --timeout=10  # 10 second timeout per test
```

## Best Practices

1. **Always use virtual environment** for consistent dependencies
2. **Run tests before committing** to catch issues early
3. **Write tests for new features** to maintain coverage
4. **Use descriptive test names** that explain what is being tested
5. **Keep tests fast** - mock slow operations (I/O, network, serial)
6. **Use parametrized tests** for testing multiple scenarios
7. **Check coverage** regularly to find untested code

## Quick Reference Card

```bash
# Setup (one time)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-test.txt
pip install pymavlink

# Daily workflow
.venv\Scripts\activate          # Activate venv
pytest test/unit/ -v            # Run tests
pytest --cov --cov-report=html  # Check coverage
flutter test                    # Run Flutter tests
deactivate                      # Exit venv

# Before commit
pytest test/unit/               # All Python tests pass
flutter test                    # All Flutter tests pass
```

## Getting Help

- **pytest help:** `pytest --help`
- **pytest fixtures:** `pytest --fixtures`
- **pytest markers:** `pytest --markers`
- **Test documentation:** See [README.md](README.md)
- **Test results:** See [../TEST_RESULTS.md](../TEST_RESULTS.md)
