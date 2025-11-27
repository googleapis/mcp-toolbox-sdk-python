# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Intentional test failure to verify Cloud Build log export workflow.
This test is designed to fail to trigger the export_cloud_build_logs.yml workflow.
"""

import pytest


def test_intentional_failure_for_workflow_verification():
    """
    This test intentionally fails to verify that:
    1. Cloud Build detects the failure
    2. The export_cloud_build_logs.yml workflow triggers
    3. Logs are fetched and uploaded as artifacts
    4. A comment is posted on the PR with artifact links
    
    Remove or skip this test once workflow verification is complete.
    """
    
    assert False, "Intentional failure to test Cloud Build log export workflow in upstream"


