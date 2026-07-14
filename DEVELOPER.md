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

### CI and Validation Pipelines

This repository splits CI responsibilities between GitHub Actions and Google Cloud Build.

* **GitHub Actions:** These are linting and type checks that run when a pull request is opened or synchronized.
* **Cloud Build:** These are live integration tests, that run upon PR creation, and interact with live GCP instances.

### Triggering Validations
Different triggers must be applied depending on the target pipeline:
* **Cloud Build (Integration Tests):** To authorize external test builds against GCP environments, a repository maintainer must add a comment containing `/gcbrun` directly on the pull request thread.
* **GitHub Actions (Linting/Types):** While these run natively for trusted contributors, testing them against external fork contexts specifically requires a repository maintainer to apply the `tests: run` metadata label on the pull request.

## Contribution Process

For instructions regarding Contributor License Agreements (CLA), Code of Conduct, and general Code Review practices, please refer directly to [CONTRIBUTING.md](CONTRIBUTING.md).

## Releases & Pipelines

This project uses `release-please` for automated releases. The release pipeline produces several published Python packages:
* [`toolbox-core`](https://pypi.org/project/toolbox-core/)
* [`toolbox-adk`](https://pypi.org/project/toolbox-adk/)
* [`toolbox-langchain`](https://pypi.org/project/toolbox-langchain/)
* [`toolbox-llamaindex`](https://pypi.org/project/toolbox-llamaindex/)

## API Reference Documentation

The API reference is published to [py.mcp-toolbox.dev](https://py.mcp-toolbox.dev).

It is generated with
[pydoc-markdown](https://niklasrosenstein.github.io/pydoc-markdown/) and rendered
by [Hugo](https://gohugo.io/) + [Docsy](https://www.docsy.dev/) from the
`docs-site/` directory.

Docs are built **per package, per version** and served at
`/<package>/<version>/` (e.g. `/core/v1.0.0/`), with a `/<package>/latest/`
redirect to the newest release. `<package>` is the URL slug: `core`, `adk`,
`langchain`, or `llamaindex`.

pydoc-markdown parses the SDK source statically — it never imports the packages —
so no build or install of the SDK is needed before generating docs.

### What gets documented

Each package's public API is a **curated module list** in
[`scripts/generate-api-docs.sh`](./scripts/generate-api-docs.sh). The `case` block
there is the single source of truth for both the valid package slugs and the
modules rendered for each; internal modules (e.g. `utils`, the transport layer)
are deliberately left out. To document a new module, add it to that package's
`MODULES`.

#### Adding a new package

The package must already live under `packages/toolbox-<slug>/`. Then:

1. Add a `case` arm (slug → `TITLE` + `MODULES`) in
   [`scripts/generate-api-docs.sh`](./scripts/generate-api-docs.sh).
2. In [`.github/workflows/api-docs.yml`](./.github/workflows/api-docs.yml), add a
   `refs/tags/toolbox-<slug>-v*` arm to the tag router **and** append the slug to
   the default `packages=` list (the `dev` build of all packages).
3. Add a `[[params.versions.<slug>]]` block in
   [`docs-site/hugo.toml`](./docs-site/hugo.toml) so the version picker lists it
   (see [Adding a version to the picker](#adding-a-version-to-the-picker)).

### Workflows

The [`api-docs.yml`](.github/workflows/api-docs.yml) workflow deploys to the
`gh-pages` branch. It runs only on the upstream repository and uses the
`api-docs-deploy` concurrency group, so it never races another deploy.

The automatic flow is as follows:

* Push to `main` (or manual dispatch) → builds all four packages as `dev`.
* Push of a per-package tag → builds that one version **and** rebuilds the root
  landing page. Tags are hyphenated: `toolbox-core-vX.Y.Z` builds `core`,
  `toolbox-adk-vX.Y.Z` builds `adk`, and likewise for `langchain` and
  `llamaindex`.
* Other tags (e.g. `release-please-*`) are skipped.

### Adding a version to the picker

The version dropdown and the `/<package>/latest/` redirect are driven entirely by
the hand-edited `[params.versions.<pkg>]` list in `docs-site/hugo.toml` — not by
the build's version. Before each **new release**, add a `[[params.versions.<pkg>]]`
block for the version (newest first; the first non-`dev` entry becomes `latest`).

Add it in the **same commit you tag from**: the deploy reads `hugo.toml` from the
tagged ref and regenerates the dropdown/`latest` files in that run. Only list a
version whose `/<pkg>/<version>/` pages already exist (or will after this run), or
the dropdown link 404s.

### Backfilling old docs

Use the [`api-docs-backfill.yml`](.github/workflows/api-docs-backfill.yml)
(API Reference Backfill) workflow to publish docs for a version whose pages are
missing — typically a tag whose on-push deploy failed or never ran. It builds
**one version per run**.

Unlike `api-docs.yml`, this workflow does **not** deploy to production directly.
Each run opens a **pull request into the `gh-pages` branch**, so the docs are
reviewed before they go live. The page is published only when you merge that PR.

The run builds **entirely from the release tag** (`toolbox-<pkg>-<version>`): the
tag carries both that version's source and the docs tooling (`docs-site/`,
`scripts/`), so nothing is overlaid from `main` and no per-package or
dependency-build step is needed. It builds `/<package>/<version>/` (plus the
package's `releases`/`latest` files), overlays the result onto a clone of the
live `gh-pages` tree — existing versions, `CNAME`, and `.nojekyll` are preserved
— and opens a PR from branch `backfill/<pkg>-<ver>` with `gh-pages` as the base.
Only tags that already carry the docs tooling can be backfilled; tags cut before
it landed will fail.

Steps to backfill:

1.  Trigger the workflow from the Actions tab, or with:

    ```bash
    gh workflow run api-docs-backfill.yml -f package=core -f version=v1.0.0
    ```

    To catch up several versions, dispatch it once per `package`/`version`. The
    concurrency group is scoped per package/version, so the runs are independent
    and none are cancelled — each opens its own PR.
2.  Review the resulting `backfill/<pkg>-<ver>` PR (the diff should be just that
    version's directory) and **merge it into `gh-pages`** to publish. Re-running
    the workflow for the same version updates the existing PR's branch.
3.  **Add the version to the picker** if it isn't already listed — add a
    `[[params.versions.<pkg>]]` block in `docs-site/hugo.toml` on `main` (see
    [Adding a version to the picker](#adding-a-version-to-the-picker)), otherwise
    the dropdown won't link to it.

#### Previewing a backfill PR

GitHub won't render the built HTML in the PR diff. Because the PR branch *is* the
rendered `gh-pages` tree, check it out and serve it statically — exactly what
Pages will serve after merge:

```bash
git fetch origin backfill/<pkg>-<ver>
# Check the branch out somewhere disposable (a detached worktree keeps your
# current branch untouched).
git worktree add --detach /tmp/preview-docs origin/backfill/<pkg>-<ver>
python3 -m http.server 8099 --directory /tmp/preview-docs
# → http://localhost:8099/<pkg>/<ver>/   e.g. http://localhost:8099/core/v0.6.0/
```

The version dropdown fetches the package's version list at runtime, so links to
versions not present in this branch (other backfills) will 404 locally — that's
expected.

When done, clean up:

```bash
git worktree remove /tmp/preview-docs
```

### Building locally

```bash
# Build a single package/version (base URL must end in a slash).
./scripts/generate-api-docs.sh core dev http://localhost:8080/

# Serve the output.
(cd docs-site/public && python3 -m http.server 8080)
# → http://localhost:8080/core/dev/
```

## Support

Check the existing [GitHub Issues](https://github.com/googleapis/mcp-toolbox-sdk-python/issues) for any concerns.

### Reporting Security Issues

For security-related concerns, please report them via [g.co/vulnz](https://g.co/vulnz).