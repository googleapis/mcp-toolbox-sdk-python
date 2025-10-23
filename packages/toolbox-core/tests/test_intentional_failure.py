import pytest


def test_intentional_failure():
    """
    This test is intentionally failing to validate that CI fails
    and the export_build_logs workflow detects failing checks.
    """
    assert False, "Intentional failure to test export_build_logs workflow"
