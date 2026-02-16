---
nav_exclude: true
---

# AI Assistant Model Configuration Guide

## Quick Start

The AI Assistant supports multiple AI models via PydanticAI's multi-provider support. Configure models using environment variables in your `.env` file.

## Configuration File Location

Place your `.env` file in the **repository root** (same location as `.env.example`):

```bash
cd /path/to/qubinode_navigator
cp .env.example .env
# Edit .env with your preferred models and API keys
```

## Model Configuration Variables

### Core Model Variables

```bash
# Manager Model (orchestration & planning)
MANAGER_MODEL=google-gla:gemini-2.0-flash

# Developer Model (code generation & execution)
DEVELOPER_MODEL=google-gla:gemini-2.0-flash

# Deployment Model (infrastructure provisioning)
PYDANTICAI_MODEL=google-gla:gemini-2.0-flash
```

### Model Format

PydanticAI uses `provider:model` format (note the **colon**, not slash):

```bash
# ✅ Correct
MANAGER_MODEL=google-gla:gemini-2.0-flash
MANAGER_MODEL=openrouter:anthropic/claude-3.5-sonnet
MANAGER_MODEL=openai:gpt-4o

# ❌ Incorrect
MANAGER_MODEL=google-gla/gemini-2.0-flash  # Wrong separator
MANAGER_MODEL=gemini/gemini-2.0-flash      # LiteLLM format, not PydanticAI
```

## Supported Providers

### 1. Google Gemini (Recommended - Fast & Cheap)

```bash
MANAGER_MODEL=google-gla:gemini-2.0-flash
GEMINI_API_KEY=your-api-key
```

Get API key: https://makersuite.google.com/app/apikey

**Available Models:**

- `google-gla:gemini-2.0-flash` - Fast, recommended for most tasks
- `google-gla:gemini-2.5-flash` - Latest version
- `google-gla:gemini-1.5-pro` - More capable, higher latency

### 2. OpenRouter (100+ Models via Single API)

```bash
MANAGER_MODEL=openrouter:anthropic/claude-3.5-sonnet
DEVELOPER_MODEL=openrouter:google/gemini-2.0-flash-exp
PYDANTICAI_MODEL=openrouter:openai/gpt-4o
OPENROUTER_API_KEY=sk-or-your-api-key
```

Get API key: https://openrouter.ai/keys

**Popular Models:**

- `openrouter:anthropic/claude-3.5-sonnet` - Claude via OpenRouter
- `openrouter:google/gemini-2.0-flash-exp` - Gemini via OpenRouter
- `openrouter:openai/gpt-4o` - GPT-4o via OpenRouter
- `openrouter:meta-llama/llama-3.3-70b-instruct` - Llama 3.3 70B
- `openrouter:deepseek/deepseek-chat` - DeepSeek Chat

### 3. Anthropic Claude

```bash
MANAGER_MODEL=anthropic:claude-3-5-sonnet-latest
ANTHROPIC_API_KEY=sk-ant-your-api-key
```

Get API key: https://console.anthropic.com/

**Available Models:**

- `anthropic:claude-3-5-sonnet-latest` - Claude 3.5 Sonnet
- `anthropic:claude-3-haiku-20240307` - Fast & cheap
- `anthropic:claude-3-opus-latest` - Most capable

### 4. OpenAI

```bash
MANAGER_MODEL=openai:gpt-4o
OPENAI_API_KEY=sk-your-api-key
```

**Available Models:**

- `openai:gpt-4o` - GPT-4o
- `openai:gpt-4-turbo` - GPT-4 Turbo

### 5. Local Models (Ollama)

```bash
MANAGER_MODEL=ollama:granite3.3:8b
OLLAMA_BASE_URL=http://localhost:11434
```

Setup: https://ollama.com/download

**Popular Models:**

- `ollama:llama3.2:latest` - Meta Llama 3.2
- `ollama:granite3.3:8b` - IBM Granite 3.3 8B
- `ollama:mistral:7b` - Mistral 7B

### 6. Groq (Fast Inference)

```bash
MANAGER_MODEL=groq:llama-3.3-70b-versatile
GROQ_API_KEY=gsk-your-api-key
```

## Configuration Examples

### Example 1: Google Gemini (Default - Fast & Free)

```bash
# .env
MANAGER_MODEL=google-gla:gemini-2.0-flash
DEVELOPER_MODEL=google-gla:gemini-2.0-flash
PYDANTICAI_MODEL=google-gla:gemini-2.0-flash
GEMINI_API_KEY=your-gemini-api-key
```

### Example 2: OpenRouter with Mixed Models

```bash
# .env
MANAGER_MODEL=openrouter:anthropic/claude-3.5-sonnet
DEVELOPER_MODEL=openrouter:google/gemini-2.0-flash-exp
PYDANTICAI_MODEL=openrouter:openai/gpt-4o
OPENROUTER_API_KEY=sk-or-your-api-key
```

### Example 3: Anthropic Claude for All Tasks

```bash
# .env
MANAGER_MODEL=anthropic:claude-3-5-sonnet-latest
DEVELOPER_MODEL=anthropic:claude-3-haiku-20240307
PYDANTICAI_MODEL=anthropic:claude-3-5-sonnet-latest
ANTHROPIC_API_KEY=sk-ant-your-api-key
```

### Example 4: Local Ollama (No API Key Required)

```bash
# .env
MANAGER_MODEL=ollama:granite3.3:8b
DEVELOPER_MODEL=ollama:llama3.2
PYDANTICAI_MODEL=ollama:granite3.3:8b
OLLAMA_BASE_URL=http://localhost:11434
```

## Deployment

After configuring your `.env` file, deploy with:

```bash
./scripts/development/deploy-qubinode.sh
```

The script will:

1. Load your `.env` file from the repository root
1. Validate model configuration
1. Log the models being used
1. Start the AI Assistant container with your configuration

### Verification

Check that your models are loaded correctly:

```bash
# During deployment, look for:
[INFO] AI Model Configuration:
[INFO]   Manager Model: openrouter:anthropic/claude-3.5-sonnet
[INFO]   Developer Model: openrouter:google/gemini-2.0-flash-exp
[INFO]   Deployment Model: openrouter:openai/gpt-4o
[INFO]   OpenRouter API Key: [SET]

# After deployment, verify via API:
curl http://localhost:8080/orchestrator/status
```

Expected response:

```json
{
  "status": "ready",
  "models": {
    "manager": "openrouter:anthropic/claude-3.5-sonnet",
    "developer": "openrouter:google/gemini-2.0-flash-exp",
    "deployment": "openrouter:openai/gpt-4o"
  },
  "api_keys": {
    "openrouter": true
  }
}
```

## Troubleshooting

### Issue: Container uses default models instead of .env configuration

**Solution:** Ensure `.env` file is in the repository root:

```bash
# Check .env location
ls -la /path/to/qubinode_navigator/.env

# If missing, copy from example
cp .env.example .env
```

### Issue: Model format error

**Error:** `Invalid model format: google-gla/gemini-2.0-flash`

**Solution:** Use colon separator (PydanticAI format), not slash:

```bash
# ✅ Correct
MANAGER_MODEL=google-gla:gemini-2.0-flash

# ❌ Wrong
MANAGER_MODEL=google-gla/gemini-2.0-flash
```

### Issue: API key not being used

**Solution:** Verify API key is exported:

```bash
# Check if API key is loaded
./scripts/development/deploy-qubinode.sh 2>&1 | grep "API Key"

# Should see:
#   OpenRouter API Key: [SET]
```

### Issue: Container fails to start

**Solution:** Check container logs:

```bash
podman logs qubinode-ai-assistant
```

Common issues:

- Invalid API key format
- Network connectivity issues
- Missing required environment variables

## Advanced Configuration

### Using Different Models for Different Agents

```bash
# Smart manager, fast worker
MANAGER_MODEL=anthropic:claude-3-5-sonnet-latest  # Planning
DEVELOPER_MODEL=google-gla:gemini-2.0-flash       # Execution
PYDANTICAI_MODEL=openrouter:meta-llama/llama-3.3-70b-instruct
```

### PYDANTICAI_MODEL Default Behavior

If `PYDANTICAI_MODEL` is not set, it defaults to `MANAGER_MODEL`:

```bash
# Only set MANAGER_MODEL
MANAGER_MODEL=anthropic:claude-3-5-sonnet-latest

# PYDANTICAI_MODEL automatically becomes:
# anthropic:claude-3-5-sonnet-latest
```

## Reference

- `.env.example` - Full configuration template with all options
- PydanticAI Docs: https://ai.pydantic.dev/models/
- OpenRouter Models: https://openrouter.ai/models
- ADR-0049: PydanticAI Integration
- ADR-0063: Multi-Agent Architecture
