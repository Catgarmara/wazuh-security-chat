# Embedded AI Security Appliance Configuration

This document describes the configuration options available for the embedded AI security appliance.

## Core Settings

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `MODELS_PATH` | `./models` | Path where AI models are stored |
| `VECTORSTORE_PATH` | `./data/vectorstore` | Path for vector database storage |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Default embedding model name |
| `MAX_CONCURRENT_MODELS` | `3` | Maximum number of models loaded simultaneously |
| `CONVERSATION_MEMORY_SIZE` | `10` | Number of conversation turns to remember |
| `DEFAULT_TEMPERATURE` | `0.7` | Default temperature for AI responses |
| `DEFAULT_MAX_TOKENS` | `1024` | Default maximum tokens per response |

## Security Appliance Specific Settings

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `ENABLE_MODEL_AUTO_DOWNLOAD` | `true` | Automatically download missing models |
| `DEFAULT_SECURITY_MODEL` | `mistral-7b-instruct-v0.1.Q4_K_M.gguf` | Default model for security analysis |
| `MODEL_CACHE_SIZE_GB` | `8` | Maximum disk space for model cache (GB) |
| `ENABLE_GPU_ACCELERATION` | `true` | Enable GPU acceleration if available |
| `MAX_MEMORY_USAGE_GB` | `8` | Maximum memory usage for AI processing (GB) |
| `MODEL_LOAD_TIMEOUT_SECONDS` | `300` | Timeout for model loading operations |
| `ENABLE_MODEL_QUANTIZATION` | `true` | Enable model quantization for efficiency |

## Resource Management

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `RESOURCE_MONITORING_INTERVAL` | `30` | Resource monitoring interval (seconds) |
| `AUTO_UNLOAD_INACTIVE_MODELS` | `true` | Automatically unload unused models |
| `MODEL_INACTIVITY_TIMEOUT_MINUTES` | `30` | Minutes before unloading inactive models |
| `ENABLE_HEALTH_CHECKS` | `true` | Enable health monitoring |
| `HEALTH_CHECK_INTERVAL_SECONDS` | `60` | Health check interval (seconds) |

## LlamaCpp Engine Settings

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `N_GPU_LAYERS` | `-1` | Number of layers to offload to GPU (-1 = auto) |
| `N_BATCH` | `512` | Batch size for processing |
| `N_CTX` | `4096` | Context window size |
| `USE_MMAP` | `true` | Use memory mapping for models |
| `USE_MLOCK` | `false` | Lock model in memory |
| `TOP_P` | `0.9` | Top-p sampling parameter |
| `TOP_K` | `40` | Top-k sampling parameter |
| `REPEAT_PENALTY` | `1.1` | Repetition penalty |

## Security and Compliance

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `ENABLE_AUDIT_LOGGING` | `true` | Enable audit logging for compliance |
| `LOG_MODEL_INTERACTIONS` | `true` | Log all model interactions |
| `ENABLE_CONVERSATION_ENCRYPTION` | `false` | Encrypt conversation data at rest |
| `MAX_CONVERSATION_HISTORY_DAYS` | `30` | Days to retain conversation history |

## Validation Rules

The configuration system includes comprehensive validation:

- Memory constraints: Minimum 2GB allocation required
- Model cache cannot exceed max memory usage
- Concurrent models must fit within memory limits
- Context size must be reasonable (512-32768)
- All timeouts have sensible ranges
- Security settings are enforced in production

## Example Configuration

```bash
# Basic security appliance setup
MODELS_PATH=/opt/security-appliance/models
MAX_MEMORY_USAGE_GB=16
MAX_CONCURRENT_MODELS=5
ENABLE_GPU_ACCELERATION=true
N_GPU_LAYERS=-1

# Security settings
ENABLE_AUDIT_LOGGING=true
LOG_MODEL_INTERACTIONS=true
MAX_CONVERSATION_HISTORY_DAYS=90

# Performance tuning
N_CTX=8192
N_BATCH=1024
RESOURCE_MONITORING_INTERVAL=15
```

## Deployment Validation

The system automatically validates configuration on startup in production mode:
- Ensures minimum memory requirements
- Validates model cache vs memory constraints
- Checks security settings compliance
- Verifies database and Redis connectivity