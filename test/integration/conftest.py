"""
pytest configuration for integration tests.

Registers custom markers and command line options for integration testing.
"""

import pytest


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--sitl",
        action="store_true",
        default=False,
        help="Run SITL integration tests (requires ArduPilot SITL)"
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "sitl: mark test as requiring SITL"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "stress: mark test as stress/load test"
    )
