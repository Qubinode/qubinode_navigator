---
title: AI Assistant Deployment Strategy
parent: Explanation
nav_order: 3
---

# AI Assistant Container Deployment Strategy

## Overview

The Qubinode Navigator AI Assistant now supports a sophisticated deployment strategy that automatically selects between development and production container images based on the environment and configuration.

## Deployment Modes

### 1. Development Mode (`development`)

**Purpose**: Local development and testing with rapid iteration capabilities.

**Container Image**: `localhost/qubinode-ai-assistant:latest`

**Characteristics**:

- Uses locally built container images
- Requires AI Assistant source code directory
- Supports container building via `./scripts/build.sh`
- Includes development tools and debugging capabilities
- Longer health check timeouts for build processes

**Use Cases**:

- Local development and testing
- Feature development and debugging
- Custom model experimentation
- Plugin development

### 2. Production Mode (`production`)

**Purpose**: Production deployments with stable, tested container images.

**Container Image**: `quay.io/takinosh/qubinode-ai-assistant:latest`

**Characteristics**:

- Uses published container images from Quay.io registry
- No local building required
- Optimized for performance and security
- Faster deployment times
- Production-ready configuration

**Use Cases**:

- Production deployments
- CI/CD pipelines
- Cloud deployments
- End-user installations

### 3. Auto Mode (`auto`) - **Recommended**

**Purpose**: Intelligent environment detection for seamless deployment.

**Auto-Detection Logic**:

1. **Environment Variable**: Checks `QUBINODE_DEPLOYMENT_MODE`
1. **Container Environment**: Detects if running inside a container (production)
1. **Development Files**: Checks for local AI Assistant source and Dockerfile (development)
1. **Default**: Falls back to production mode for safety

## Configuration

### Basic Configuration

```yaml
ai_assistant:
  deployment_mode: "auto"  # auto, development, production
  ai_service_url: "http://localhost:8080"
  container_name: "qubinode-ai-assistant"
  ai_assistant_path: "/opt/qubinode_navigator/ai-assistant"
  auto_start: true
  health_check_timeout: 90
  enable_diagnostics: true
  enable_rag: true
```

### Development Configuration

```yaml
ai_assistant:
  deployment_mode: "development"
  container_name: "qubinode-ai-assistant-dev"
  health_check_timeout: 120  # Longer timeout for builds
  # Other settings...
```

### Production Configuration

```yaml
ai_assistant:
  deployment_mode: "production"
  health_check_timeout: 60  # Faster timeout for pre-built images
  # Other settings...
```

### Custom Image Override

```yaml
ai_assistant:
  deployment_mode: "production"
  container_image: "custom-registry.example.com/qubinode-ai-assistant:v1.2.3"
  # Other settings...
```

## Environment Variables

### `QUBINODE_DEPLOYMENT_MODE`

Override automatic detection:

```bash
export QUBINODE_DEPLOYMENT_MODE=development
# or
export QUBINODE_DEPLOYMENT_MODE=production
```

## Deployment Workflows

### Development Workflow

1. **Setup**: Ensure AI Assistant source code is available
1. **Configuration**: Set `deployment_mode: "development"` or use auto-detection
1. **Execution**: Plugin automatically builds container if needed
1. **Testing**: Use local container for development and testing

```bash
# Example development setup
cd /opt/qubinode_navigator
export QUBINODE_DEPLOYMENT_MODE=development
python qubinode_cli.py --plugin ai_assistant --execute
```

### Production Workflow

1. **Configuration**: Set `deployment_mode: "production"` or use auto-detection
1. **Execution**: Plugin automatically pulls container from Quay.io
1. **Deployment**: Use production-ready container

```bash
# Example production setup
export QUBINODE_DEPLOYMENT_MODE=production
python qubinode_cli.py --plugin ai_assistant --execute
```

## Container Images

### Development Image (`localhost/qubinode-ai-assistant:latest`)

**Build Process**:

- Built locally using `./scripts/build.sh`
- Includes development dependencies
- May include debugging tools
- Supports rapid iteration

**Requirements**:

- AI Assistant source code directory
- Container runtime (podman/docker)
- Build dependencies

### Production Image (`quay.io/takinosh/qubinode-ai-assistant:latest`)

**Features**:

- **Size**: Optimized 681MB container
- **Base Image**: Python 3.12 with llama.cpp integration
- **AI Model**: IBM Granite-4.0-Micro (2.0GB Q4_K_M quantization)
- **Components**: RAG system (5,199 documents), 6 diagnostic tools
- **API**: REST API on port 8080
- **Security**: Non-root user, health checks

**Usage**:

```bash
podman pull quay.io/takinosh/qubinode-ai-assistant:latest
podman run -d --name qubinode-ai-assistant -p 8080:8080 quay.io/takinosh/qubinode-ai-assistant:latest
curl http://localhost:8080/health
```

## Plugin Integration

### Automatic Image Selection

The `AIAssistantPlugin` automatically:

1. Detects the deployment mode
1. Selects the appropriate container image
1. Builds or pulls the container as needed
1. Starts and monitors the container

### Health Status

The plugin provides deployment mode information in health status:

```python
health_status = plugin.get_health_status()
print(f"Deployment Mode: {health_status['deployment_mode']}")
print(f"Container Image: {health_status['container_image']}")
```

## Troubleshooting

### Common Issues

1. **Build Failures in Development Mode**

   - Ensure AI Assistant source directory exists
   - Check build script permissions
   - Verify container runtime availability

1. **Pull Failures in Production Mode**

   - Check network connectivity
   - Verify registry access
   - Ensure container runtime is available

1. **Auto-Detection Issues**

   - Use explicit deployment mode configuration
   - Set `QUBINODE_DEPLOYMENT_MODE` environment variable
   - Check file system permissions

### Debug Commands

```bash
# Check deployment mode detection
python -c "
from plugins.services.ai_assistant_plugin import AIAssistantPlugin
plugin = AIAssistantPlugin({'deployment_mode': 'auto'})
print(f'Detected mode: {plugin.deployment_mode}')
print(f'Container image: {plugin.container_image}')
"

# Test container availability
podman images | grep qubinode-ai-assistant
podman pull quay.io/takinosh/qubinode-ai-assistant:latest
```

## Migration Guide

### From Hardcoded Images

**Before**:

```yaml
ai_assistant:
  container_image: "localhost/qubinode-ai-assistant:latest"
```

**After**:

```yaml
ai_assistant:
  deployment_mode: "auto"  # Automatically selects appropriate image
```

### From Manual Container Management

**Before**: Manual container building and pulling

**After**: Automatic container management based on deployment mode

## Security Considerations

### Development Mode

- Uses local images that may include development tools
- Suitable for trusted development environments
- May have longer startup times due to building

### Production Mode

- Uses verified images from trusted registry
- Optimized for security and performance
- Faster deployment with pre-built images

## Performance Impact

### Development Mode

- **Build Time**: 2-5 minutes for initial build
- **Startup Time**: 30-60 seconds after build
- **Resource Usage**: Higher during build process

### Production Mode

- **Pull Time**: 30-120 seconds (depending on network)
- **Startup Time**: 15-30 seconds
- **Resource Usage**: Optimized for runtime efficiency

## Future Enhancements

1. **Versioned Releases**: Support for specific version tags
1. **Multi-Architecture**: Support for ARM64 and other architectures
1. **Registry Configuration**: Support for custom registries
1. **Caching**: Improved caching for faster deployments
1. **Health Monitoring**: Enhanced health checks and monitoring

## Related Documentation

- [AI Assistant Configuration](https://github.com/Qubinode/qubinode_navigator/blob/main/ai-assistant/config/ai_config.yaml)
- [Container Build Process](https://github.com/Qubinode/qubinode_navigator/blob/main/ai-assistant/scripts/build.sh)
- [Plugin Framework](./adrs/adr-0028-modular-plugin-framework-for-extensibility.md)
- [Container Architecture](./adrs/adr-0027-cpu-based-ai-deployment-assistant-architecture.md)
