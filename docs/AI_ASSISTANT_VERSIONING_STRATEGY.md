______________________________________________________________________

## nav_exclude: true

# AI Assistant Container Versioning Strategy

## Overview

The Qubinode Navigator AI Assistant implements a comprehensive semantic versioning strategy for container releases, providing automated version management, intelligent tagging, and deployment flexibility.

## Semantic Versioning

### Version Format

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
```

**Examples:**

- `1.0.0` - Stable release
- `1.0.0-alpha.1` - Prerelease version
- `1.0.0+build.20241111` - Version with build metadata
- `2.1.0-beta.2+git.abc123.build.20241111` - Full version with all components

### Version Components

- **MAJOR**: Incompatible API changes
- **MINOR**: Backward-compatible functionality additions
- **PATCH**: Backward-compatible bug fixes
- **PRERELEASE**: Pre-release versions (alpha, beta, rc)
- **BUILD**: Build metadata (git hash, timestamp)

## Version Management Tools

### Version Manager Script

The `ai-assistant/scripts/version-manager.sh` script provides comprehensive version management:

```bash
# Show current version
./scripts/version-manager.sh current

# Increment version
./scripts/version-manager.sh increment minor

# Set specific version
./scripts/version-manager.sh set 2.1.0

# Generate container tags
./scripts/version-manager.sh tags quay.io/takinosh qubinode-ai-assistant

# Full release workflow
./scripts/version-manager.sh release minor "Added new AI model support"
```

### Available Commands

| Command                    | Description                      | Example                                       |
| -------------------------- | -------------------------------- | --------------------------------------------- |
| `current`                  | Show current version             | `./version-manager.sh current`                |
| `increment <type>`         | Increment version                | `./version-manager.sh increment patch`        |
| `set <version>`            | Set specific version             | `./version-manager.sh set 1.2.0`              |
| `validate <version>`       | Validate version format          | `./version-manager.sh validate 1.0.0-alpha.1` |
| `tags [registry] [image]`  | Generate container tags          | `./version-manager.sh tags quay.io/takinosh`  |
| `build-metadata`           | Generate version with build info | `./version-manager.sh build-metadata`         |
| `changelog <changes>`      | Create changelog entry           | `./version-manager.sh changelog "Bug fixes"`  |
| `release <type> [changes]` | Full release workflow            | `./version-manager.sh release minor`          |

## Container Tagging Strategy

### Automatic Tag Generation

For version `1.2.0`, the following tags are automatically generated:

```
quay.io/takinosh/qubinode-ai-assistant:1.2.0      # Full version
quay.io/takinosh/qubinode-ai-assistant:1.2        # Major.Minor
quay.io/takinosh/qubinode-ai-assistant:1          # Major
quay.io/takinosh/qubinode-ai-assistant:latest     # Latest (stable only)
quay.io/takinosh/qubinode-ai-assistant:20241111   # Date tag
```

### Tag Strategy

- **Full Version Tag**: Exact version for pinning
- **Major.Minor Tag**: Automatic patch updates
- **Major Tag**: Automatic minor/patch updates
- **Latest Tag**: Only for stable releases (no prerelease)
- **Date Tag**: Build tracking and debugging

### Prerelease Handling

Prerelease versions (e.g., `1.2.0-alpha.1`) do not receive the `latest` tag:

```
quay.io/takinosh/qubinode-ai-assistant:1.2.0-alpha.1
quay.io/takinosh/qubinode-ai-assistant:20241111
```

## Plugin Integration

### Version Configuration

The `AIAssistantPlugin` supports flexible version configuration:

```yaml
ai_assistant:
  container_version: "1.2.0"        # Specific version
  version_strategy: "semver"        # Version strategy
  deployment_mode: "production"     # Deployment mode
```

### Version Strategies

| Strategy   | Description                         | Use Case                              |
| ---------- | ----------------------------------- | ------------------------------------- |
| `auto`     | Prefer stable, fallback to latest   | **Recommended** - Automatic selection |
| `latest`   | Always use latest tag               | Development/testing                   |
| `specific` | Use configured version              | Production pinning                    |
| `semver`   | Use latest stable from VERSION file | Controlled releases                   |

### Configuration Examples

**Auto Strategy (Recommended)**:

```yaml
ai_assistant:
  version_strategy: "auto"  # Intelligent version selection
```

**Specific Version**:

```yaml
ai_assistant:
  container_version: "1.2.0"
  version_strategy: "specific"
```

**Latest Stable**:

```yaml
ai_assistant:
  version_strategy: "semver"  # Read from VERSION file
```

## Environment Variables

### Version Override

```bash
# Override deployment mode
export QUBINODE_DEPLOYMENT_MODE=production

# Override version detection
export QUBINODE_AI_VERSION=1.2.0
```

### CI/CD Variables

```bash
# Version file location
VERSION_FILE=ai-assistant/VERSION

# Version manager script
VERSION_MANAGER=ai-assistant/scripts/version-manager.sh
```

## CI/CD Integration

### Automated Versioning

The GitHub Actions workflow automatically:

1. **Reads Version**: From `ai-assistant/VERSION` file
1. **Generates Tags**: Using version manager
1. **Builds Container**: With semantic tags
1. **Adds Labels**: OCI-compliant metadata
1. **Pushes Images**: To Quay.io registry

### Workflow Steps

```yaml
- name: Generate version and tags
  run: |
    CURRENT_VERSION=$(./scripts/version-manager.sh current | grep "Current version:" | cut -d' ' -f3)
    BUILD_VERSION=$(./scripts/version-manager.sh build-metadata)
    TAGS=$(./scripts/version-manager.sh tags quay.io/takinosh qubinode-ai-assistant)

- name: Build and push production image
  uses: docker/build-push-action@v5
  with:
    tags: ${{ steps.version.outputs.container-tags }}
    labels: |
      version=${{ steps.version.outputs.current-version }}
      build-version=${{ steps.version.outputs.build-version }}
```

### Container Labels

All containers include OCI-compliant labels:

```dockerfile
LABEL version="1.2.0"
LABEL build-version="1.2.0+git.abc123.build.20241111"
LABEL org.opencontainers.image.version="1.2.0"
LABEL org.opencontainers.image.revision="abc123"
```

## Release Workflow

### 1. Development Phase

```bash
# Work on features
git checkout -b feature/new-ai-model

# Test locally with development builds
./scripts/build.sh
```

### 2. Release Preparation

```bash
# Increment version
./scripts/version-manager.sh release minor "Added new AI model support"

# Review changes
git diff VERSION CHANGELOG.md
```

### 3. Release Execution

```bash
# Commit version changes
git add VERSION CHANGELOG.md
git commit -m "Release 1.2.0"

# Create git tag
git tag -a v1.2.0 -m "Release 1.2.0"

# Push to trigger CI/CD
git push origin main --tags
```

### 4. Deployment

The CI/CD pipeline automatically:

- Builds container with semantic tags
- Pushes to Quay.io registry
- Updates deployment configurations

## Version File Management

### VERSION File

Located at `ai-assistant/VERSION`, contains the current version:

```
1.2.0
```

### CHANGELOG.md

Automatically maintained changelog:

```markdown
# Changelog

## [1.2.0] - 2024-11-11

### Added
- Added new AI model support
- Enhanced deployment strategy

### Changed
- Updated container version to 1.2.0

### Fixed
- Various bug fixes and improvements
```

## Best Practices

### Version Increment Guidelines

- **MAJOR**: Breaking changes to API or configuration
- **MINOR**: New features, model updates, enhancements
- **PATCH**: Bug fixes, security patches, documentation

### Release Timing

- **Patch**: As needed for critical fixes
- **Minor**: Monthly or feature-driven
- **Major**: Quarterly or for significant changes

### Testing Strategy

1. **Development**: Use local builds with current version
1. **Staging**: Use specific version tags
1. **Production**: Use stable semantic versions

### Rollback Strategy

```bash
# Rollback to previous version
./scripts/version-manager.sh set 1.1.0

# Update deployment
kubectl set image deployment/ai-assistant container=quay.io/takinosh/qubinode-ai-assistant:1.1.0
```

## Troubleshooting

### Common Issues

**Version File Not Found**:

```bash
# Create VERSION file
echo "1.0.0" > ai-assistant/VERSION
```

**Invalid Version Format**:

```bash
# Validate version
./scripts/version-manager.sh validate 1.2.0-alpha.1
```

**Tag Generation Issues**:

```bash
# Debug tag generation
./scripts/version-manager.sh tags localhost qubinode-ai-assistant
```

### Debug Commands

```bash
# Check current configuration
python -c "
from plugins.services.ai_assistant_plugin import AIAssistantPlugin
plugin = AIAssistantPlugin({'version_strategy': 'auto'})
print(f'Version: {plugin.container_version}')
print(f'Strategy: {plugin.version_strategy}')
print(f'Image: {plugin.container_image}')
"

# Verify version manager
./scripts/version-manager.sh --help
```

## Migration Guide

### From Hardcoded Versions

**Before**:

```yaml
ai_assistant:
  container_image: "quay.io/takinosh/qubinode-ai-assistant:latest"
```

**After**:

```yaml
ai_assistant:
  version_strategy: "auto"  # Intelligent version selection
```

### From Manual Tagging

**Before**: Manual container tagging and pushing

**After**: Automated semantic versioning with CI/CD

## Security Considerations

### Version Pinning

For production environments, consider version pinning:

```yaml
ai_assistant:
  container_version: "1.2.0"  # Pin to specific version
  version_strategy: "specific"
```

### Vulnerability Management

- **Patch Releases**: Automated security updates
- **Version Tracking**: Full traceability via git tags
- **Rollback Capability**: Quick rollback to known-good versions

## Future Enhancements

### Planned Features

1. **Multi-Architecture Support**: ARM64 and AMD64 builds
1. **Registry Mirroring**: Support for multiple registries
1. **Automated Testing**: Version-specific test suites
1. **Release Notes**: Automated release note generation
1. **Dependency Tracking**: Track AI model and dependency versions

### Integration Roadmap

1. **Kubernetes Operators**: Version-aware deployment operators
1. **Helm Charts**: Semantic versioning for Helm releases
1. **ArgoCD Integration**: GitOps-driven version management
1. **Monitoring**: Version-aware monitoring and alerting

## Related Documentation

- [AI Assistant Deployment Strategy](explanation/ai-assistant-deployment-strategy.md)
- [Container Build Process](../ai-assistant/scripts/build.sh)
- [CI/CD Pipeline](../.github/workflows/ai-assistant-ci.yml)
- [Plugin Configuration](../config/ai_assistant_deployment.yml)
