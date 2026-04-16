# Development

Below are the details to set up a development environment and run tests.

## Versioning

This library adheres to [Semantic Versioning](http://semver.org/). Releases are automated using [Release Please](https://github.com/googleapis/release-please), which analyzes commit messages to determine version bumps.

## Processes

### Conventional Commit Messages

This repository utilizes [Conventional Commits](https://www.conventionalcommits.org/) for structuring commit messages. This standard is crucial for the automated release process managed by [Release Please](https://github.com/googleapis/release-please?tab=readme-ov-file#how-should-i-write-my-commits), which parses your Git history to create GitHub and PyPI releases.

## Install

1. Clone the repository:
    ```bash
    git clone https://github.com/googleapis/mcp-toolbox-sdk-python
    ```
1. Navigate to the specific package directory you wish to work on (e.g., `toolbox-core`, `toolbox-adk`, etc.):
    ```bash
    cd mcp-toolbox-sdk-python/packages/<PACKAGE_NAME>
    ```
1. Install the package in editable mode, so changes are reflected without reinstall:
    ```bash
    pip install -e .
    ```
> [!IMPORTANT]
(For non-`toolbox-core` packages) If you are working on an orchestration package (e.g., `toolbox-adk` or `toolbox-langchain`), `pip` may download the latest released version of `toolbox-core` as a dependency. To ensure you are testing against your local changes, install `toolbox-core` in editable mode *after* installing the target package:
    ```bash
    pip install -e ../toolbox-core
    ```

> [!TIP]
> Using `-e` option allows you to make changes to the SDK code and have those changes reflected immediately without reinstalling the package.

## Testing

### Local Tests

To run tests locally for a specific package, ensure you have the necessary dependencies.

1. Navigate to the package directory:
    ```bash
    cd mcp-toolbox-sdk-python/packages/<PACKAGE_NAME>
    ```
1. Install the SDK and its test dependencies:
    ```bash
    pip install -e .[test]
    ```
> [!IMPORTANT]
>(For non-`toolbox-core` packages) If testing an orchestration package, make sure to install the local `toolbox-core` in editable mode *after* installing test dependencies to override published packages:
    ```bash
    pip install -e ../toolbox-core
    ```
1. Ensure your [Toolbox service](https://mcp-toolbox.dev/documentation/introduction/#getting-started) is running and accessible (if running integration tests).
1. Run tests:
    ```bash
    pytest
    ```

> [!TIP]
> You can run specific test files or modules:
> ```bash
> pytest tests/test_client.py
> ```

#### Authentication in Local Tests
Integration tests involving authentication rely on environment variables for `TOOLBOX_URL`, `TOOLBOX_VERSION`, and `GOOGLE_CLOUD_PROJECT`. For local runs, you might need to mock or set up dummy authentication tokens. These tests generally leverage authentication methods from `toolbox-core`. Refer to `packages/toolbox-core/tests/conftest.py` for examples.

### Code Coverage

Tests are configured with `pytest-cov` to measure code coverage. Ensure your changes maintain or improve coverage.

### Linting and Type Checking

The repository enforces code style and type adherence using `black`, `isort`, and `mypy`. To run these checks locally:

1. Install test dependencies as described in the [Local Tests](#local-tests) section.
1. Run the linters and type checker from the specific package directory:
    ```bash
    black --check .
    isort --check .
    MYPYPATH='./src' mypy --install-types --non-interactive --cache-dir=.mypy_cache/ -p <PACKAGE_MODULE_NAME>
    ```
> [!NOTE]
> Replace `<PACKAGE_MODULE_NAME>` with the Python module name, e.g., `toolbox_core`, `toolbox_adk` or `toolbox_langchain`).

### CI and GitHub Actions

This repository uses GitHub Actions for CI. Linting, type-checking, Cloud Build triggers, and integration tests are run automatically on pull requests.

* **Linting and Type Checking:** Configured in `.github/workflows/lint-*.yaml`.
* **Integration Tests:** Executed via Cloud Build, defined in `integration.cloudbuild.yaml` within each package.
**Triggering Tests:** Tests can be triggered manually by commenting `/gcbrun` on a pull request. The `tests: run` label can also be used.

## Contribution Process

For instructions regarding Contributor License Agreements (CLA), Code of Conduct, and general Code Review practices, please refer directly to [CONTRIBUTING.md](CONTRIBUTING.md).

## Releases & Pipelines

This project uses `release-please` for automated releases. The release pipeline produces several published Python packages:
* [`toolbox-core`](https://pypi.org/project/toolbox-core/)
* [`toolbox-adk`](https://pypi.org/project/toolbox-adk/)
* [`toolbox-langchain`](https://pypi.org/project/toolbox-langchain/)
* [`toolbox-llamaindex`](https://pypi.org/project/toolbox-llamaindex/)

## Support

Check the existing [GitHub Issues](https://github.com/googleapis/mcp-toolbox-sdk-python/issues) for any concerns.

### Reporting Security Issues

For security-related concerns, please report them via [g.co/vulnz](https://g.co/vulnz).