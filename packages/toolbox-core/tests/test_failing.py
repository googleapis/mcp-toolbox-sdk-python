# Copyright 2025 Google LLCdef test_intentional_failure():

#    """This test intentionally fails to verify CI failure detection."""

# Licensed under the Apache License, Version 2.0 (the "License");    assert False, "Intentional failure for testing"

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

"""Intentionally failing test to verify CI failure detection and log export workflow."""


def test_intentional_failure():
    """This test intentionally fails to verify CI failure detection."""
    assert False, "Intentional failure for testing Cloud Build log export workflow"
