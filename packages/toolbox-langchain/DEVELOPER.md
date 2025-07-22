# Development

Below are the details to set up a development environment and run tests for the
`toolbox-langchain` package.

## Versioning

This library adheres to [Semantic Versioning](http://semver.org/). Releases are
automated using [Release Please](https://github.com/googleapis/release-please),
which analyzes commit messages to determine version bumps.

## Processes

### Conventional Commit Messages

This repository utilizes [Conventional
Commits](https://www.conventionalcommits.org/) for structuring commit messages.
This standard is crucial for the automated release process managed by [Release
Please](https://github.com/googleapis/release-please?tab=readme-ov-file#how-should-i-write-my-commits),
which parses your Git history to create GitHub and PyPI releases.

## Install
1. Clone the repository:
    ```bash
    git clone https://github.com/googleapis/mcp-toolbox-sdk-python
    ```
1. Navigate to the package directory:
    ```bash
    cd mcp-toolbox-sdk-python/packages/toolbox-langchain
    ```
1. Install the package in editable mode, so changes are reflected without
   reinstall:
    ```bash
    pip install -e .
    ```
1. Make code changes and contribute to the SDK's development.
> [!TIP]
> Using `-e` option allows you to make changes to the SDK code and have those
> changes reflected immediately without reinstalling the package.

## Testing

### Local Tests

To run tests locally, ensure you have the necessary dependencies and a running
Toolbox service.

1. Navigate to the package directory if needed:
    ```bash
    cd mcp-toolbox-sdk-python/packages/toolbox-langchain
    ```
1. Install the SDK and its test dependencies:
    ```bash
    pip install -e .[test]
    ```
1. Ensure your [Toolbox
   service](https://github.com/googleapis/genai-toolbox?tab=readme-ov-file#getting-started)
   is running and accessible (e.g., at `http://localhost:5000`).
1. Run tests and/or contribute to the SDK's development.

    ```bash
    pytest
    ```

> [!TIP]
> You can run specific test files or modules:
> ```bash
> pytest tests/test_client.py
> ```

#### Authentication in Local Tests
Integration tests involving authentication rely on environment variables for
`TOOLBOX_URL`, `TOOLBOX_VERSION`, and `GOOGLE_CLOUD_PROJECT`. For local runs,
you might need to mock or set up dummy authentication tokens. These tests
leverage authentication methods from `toolbox-core`. Refer to
`packages/toolbox-core/tests/conftest.py` for how authentication tokens
(`auth_token1`, `auth_token2`) are generated and used in the test environment,
and `packages/toolbox-core/src/toolbox_core/auth_methods.py` for helper
functions for obtaining Google ID tokens.

### Code Coverage

Tests are configured with `pytest-cov` to measure code coverage. Ensure your
changes maintain or improve coverage.

### Linting and Type Checking

The repository enforces code style and type adherence using `black`, `isort`,
and `mypy`. To run these checks locally:

1. Install test dependencies as described in "Local Tests" section
   [above](#local-tests).
1. Run the linters and type checker from the `packages/toolbox-langchain`
   directory:
    ```bash
    black --check .
    isort --check .
    MYPYPATH='./src' mypy --install-types --non-interactive --cache-dir=.mypy_cache/ -p toolbox_langchain
    ```

### CI and GitHub Actions

This repository uses GitHub Actions for CI. Linting, type-checking, and
integration tests are run automatically on pull requests.

* **Linting and Type Checking:** Configured in `lint-toolbox-langchain.yaml`.
* **Integration Tests:** Executed via Cloud Build, defined in
  `integration.cloudbuild.yaml`. These tests interact with a live Toolbox
  service instance.

**Triggering Tests on GitHub:** For external contributions, tests can be
triggered manually by commenting `/gcbrun` on a pull request. The `tests: run`
label can also be used to signal the CI system to run tests.

## Contribution Process

We welcome contributions to this project! Please review the following guidelines
before submitting.

### Contributor License Agreement (CLA)

Contributions to this project must be accompanied by a [Contributor License
Agreement](https://cla.developers.google.com/about) (CLA). This grants Google
permission to use and redistribute your contributions.

### Code Reviews

All submissions, including those by project members, require review. We use
[GitHub pull requests](https://help.github.com/articles/about-pull-requests/)
for this purpose.

* Ensure your pull request clearly describes the changes you are making.
* Ideally, your pull request should include code, tests, and updated
  documentation (if applicable) in a single submission.
* Code style and linting checks will run automatically. Please ensure they pass
  before requesting a review.
* A reviewer from the `@googleapis/senseai-eco` team will typically review your
  PR within 2-5 days and may request changes or approve it.

## Releases & Pipelines

This project uses `release-please` for automated releases.

* **Release Automation:** [Release
  Please](https://github.com/googleapis/mcp-toolbox-sdk-python/blob/main/.github/release-please.yml)
  is configured to manage releases based on [Conventional
  Commits](#conventional-commit-messages). It creates release pull requests and
  tags.
* **Published Packages:** The release pipeline produces Python packages,
  including:
    * [`toolbox-core`](https://pypi.org/project/toolbox-core/)
    * [`toolbox-langchain`](https://pypi.org/project/toolbox-langchain/)
    * [`toolbox-llamaindex`](https://pypi.org/project/toolbox-llamaindex/)
* **Release Trigger:** Releases are typically triggered automatically based on
  merges to the `main` branch, as configured in `release-trigger.yml`.

## Support

If you encounter issues or have questions, please check the existing [GitHub
Issues](https://github.com/googleapis/genai-toolbox/issues) for the main Toolbox
project. If your issue is specific to one of the SDKs, please look for existing
issues [here](https://github.com/googleapis/mcp-toolbox-sdk-python/issues) or
open a new issue in this repository.

### Reporting Security Issues

For security-related concerns, please report them via
[g.co/vulnz](https://g.co/vulnz).
