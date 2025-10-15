import pytest


def test_intentional_failure():
    """Intentional failing test to validate CI failure handling and log export."""
    # This test intentionally fails
    assert False, "Intentional failure for CI export testing"
