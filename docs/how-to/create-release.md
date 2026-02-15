---
title: Creating a Release
parent: How to
nav_order: 2
---

# Creating a Release

This guide explains how to create a new release of Qubinode Navigator using the automated GitHub Actions release pipeline.

## Prerequisites

- Maintainer access to the repository
- All changes merged to `main` branch
- Tests passing in CI/CD

## Release Methods

### Method 1: Tag-Based Release (Recommended)

Create and push a version tag to automatically trigger the release:

```bash
# Make sure you're on main and up to date
git checkout main
git pull origin main

# Create a version tag (format: vX.Y.Z)
git tag -a v0.1.0 -m "Release version 0.1.0"

# Push the tag to GitHub
git push origin v0.1.0
```

The release workflow will automatically:

1. Validate the version format
1. Run all tests
1. Build container images
1. Create a GitHub release with auto-generated changelog
1. Create a release announcement issue

### Method 2: Manual Workflow Dispatch

Trigger a release manually from the GitHub Actions UI:

1. Go to **Actions** tab in GitHub
1. Select **Release Pipeline** workflow
1. Click **Run workflow**
1. Enter the version number (e.g., `0.1.0`)
1. Optionally mark as pre-release
1. Click **Run workflow**

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **Major version (X.0.0)**: Breaking changes
- **Minor version (0.X.0)**: New features, backward compatible
- **Patch version (0.0.X)**: Bug fixes, backward compatible
- **Pre-release (0.1.0-beta.1)**: Pre-release versions

Examples:

- `v0.1.0` - Initial release
- `v0.2.0` - New features added
- `v0.2.1` - Bug fixes
- `v1.0.0` - First stable release
- `v1.1.0-rc.1` - Release candidate

## What Happens During a Release

### 1. Validation

- Checks version format (X.Y.Z)
- Validates tag doesn't already exist
- Verifies changelog requirements

### 2. Testing

- Runs unit tests (`tests/unit/`)
- Runs integration tests (`tests/integration/`)
- Must pass before proceeding

### 3. Container Build

- Builds Jekyll documentation container
- Pushes to GitHub Container Registry (ghcr.io)
- Tags: `vX.Y.Z` and `latest`

### 4. Release Creation

- Generates changelog from commit history
- Creates GitHub release
- Attaches release notes
- Creates announcement issue

## Changelog Generation

The workflow automatically generates changelogs by analyzing commit messages:

- **Features**: Commits starting with `feat:`
- **Bug Fixes**: Commits starting with `fix:`
- **Documentation**: Commits starting with `docs:`

### Commit Message Examples

```bash
feat: add support for RHEL 10
fix: resolve ansible vault integration issue
docs: update installation guide for MCP servers
```

## After Release

### Update Documentation

The documentation site will automatically rebuild with the new release tag.

### Verify Release

1. Check the [Releases page](https://github.com/Qubinode/qubinode_navigator/releases)
1. Verify container images: `ghcr.io/qubinode/qubinode-docs:X.Y.Z`
1. Test installation from the release tag:

```bash
git clone https://github.com/Qubinode/qubinode_navigator.git
cd qubinode_navigator
git checkout vX.Y.Z
./deploy-qubinode-with-airflow.sh
```

### Announce Release

The workflow automatically creates an announcement issue, but you may also want to:

- Update README badges
- Post on social media
- Notify users/contributors
- Update external documentation

## Troubleshooting

### Release Workflow Fails

1. Check the Actions tab for error details
1. Common issues:
   - **Tests failing**: Fix tests before releasing
   - **Tag already exists**: Use a new version number
   - **Invalid version format**: Must be `X.Y.Z` or `X.Y.Z-suffix`

### Container Build Fails

1. Check Dockerfile.jekyll for errors
1. Verify GitHub Container Registry permissions
1. Check build logs in Actions

### Need to Delete a Release

```bash
# Delete the tag locally
git tag -d vX.Y.Z

# Delete the tag on GitHub
git push origin :refs/tags/vX.Y.Z

# Delete the release from GitHub UI
# Go to Releases → Click on the release → Delete
```

## Current Version

The current version is defined in:

- `Makefile`: `TAG := 0.1.0`

Update this version number after each release.

## Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG reviewed (if manual)
- [ ] Version number decided
- [ ] Tag created and pushed
- [ ] Release workflow completed
- [ ] Container images published
- [ ] Release announcement created
- [ ] Installation verified

## Support

For questions about the release process:

- Open an issue with the `release` label
- Check existing release workflow runs in Actions
- Review this documentation
