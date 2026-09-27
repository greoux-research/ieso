# Releasing IES Optimiser

> **Current verification status:** The workflows have been restored for `ies-optimiser` and pass local actionlint checks. They have not yet run on GitHub for this rename; cross-platform verification and the release gate remain pending. See [Baseline Verification](baseline-verification.md).

Releases are published to PyPI by `.github/workflows/release.yml` with PyPI Trusted Publishing (OpenID Connect): no API token exists anywhere. A release is one tagged commit on `main`; one workflow run builds its wheels and sdist, tests them on every supported platform and Python, uploads **those same files** to TestPyPI, verifies installation from TestPyPI, and — for a final version, after manual approval — uploads them to PyPI and verifies installation from PyPI.

## One-time account and repository setup

These are done by a maintainer, once, in the web interfaces; the workflow cannot do them.

**Setup status (2026-09-27):** The maintainer reports that Trusted Publishing is configured on PyPI and TestPyPI for project and repository `ies-optimiser`, and that the GitHub `testpypi` and `pypi` environments have been created. The first workflow run still needs to verify the integration; environment protection rules should match the requirements below.

**PyPI** (https://pypi.org/manage/account/publishing/, "Add a new pending publisher"):

| Field | Value |
|---|---|
| PyPI project name | `ies-optimiser` |
| Owner | `greoux-research` |
| Repository name | `ies-optimiser` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

**TestPyPI** (https://test.pypi.org/manage/account/publishing/, a separate account and project): the same, with environment name `testpypi`.

A pending publisher does not reserve the name: the project is created by the first successful upload, and until then someone else can register `ies-optimiser`. Name availability must be checked on each index before configuring the pending publisher.

**GitHub** (repository Settings → Environments):
- `testpypi`: deployment branches and tags → selected tags, pattern `v*`.
- `pypi`: the same tag rule, plus **Required reviewers** (the maintainers who approve production uploads) and "Prevent self-review" if more than one maintainer exists.
- Settings → Actions → General: keep "Fork pull request workflows" requiring approval. `release.yml` runs only on tag pushes, never on pull requests.
- Optionally, a tag ruleset restricting who may create `v*` tags, and a branch ruleset requiring the `wheels / gate` check on `main`.

## Releasing a version

1. On `main`, set `project.version` in `pyproject.toml` to the new version (`2026.9.0rc1`, `2026.9.0`...), update `CHANGELOG.md`, and merge. Wait for `wheels.yml` to pass on that commit.
2. Tag that commit and push the tag: `git tag -a v2026.9.0rc1 -m "IES Optimiser 2026.9.0rc1" <commit> && git push origin v2026.9.0rc1`.
3. The `release` run checks that the tag names the version in the source and that the commit is on `main`, then builds, tests, collects (twine check, content checks, `SHA256SUMS`), uploads to TestPyPI and verifies the TestPyPI installation on every platform.
4. Prereleases (`rcN`) stop there. For a final version the `pypi` job waits for an approver in the `pypi` environment; approve only after reviewing the run's TestPyPI verification. It then uploads the same files and verifies `pip install ies-optimiser` from PyPI.
5. Record the version, commit, run URL and `SHA256SUMS` in `docs/baseline-verification.md`, and create the GitHub release for the tag.

A version is never uploaded twice, renamed or deleted to correct a release: fix the source and release a new version (`2026.9.1`, or `rc2` before a final). A final version is its own candidate with its own run; it is not a renamed release candidate.
