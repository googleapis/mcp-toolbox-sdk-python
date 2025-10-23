"""Intentional failing test to validate Cloud Build failure detection."""

import pytest


def test_intentional_failure():
    """
    This test is intentionally failing to validate that:
    1. Cloud Build checks fail as expected
    2. The export_build_logs workflow detects the failure
    3. Failed check information is correctly extracted
    
    
    """
    assert False, "Intentional failure to test export_build_logs workflow"
