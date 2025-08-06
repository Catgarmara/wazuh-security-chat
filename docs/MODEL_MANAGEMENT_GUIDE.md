# Model Management Guide - Embedded Security AI Appliance

Complete guide for managing AI models in your self-contained Security AI Appliance.

## Overview

Your embedded appliance includes a complete model management system that eliminates the need for external services like Ollama. This guide covers everything from browsing HuggingFace models to optimizing performance.

**Key Features:**
- 🌐 **HuggingFace Integration** - Browse 100,000+ models directly
- 📦 **Local Storage** - All models stored locally in `./models` directory  
- ⚡ **Hot Swapping** - Load/unload models without restart
- 👥 **User Permissions** - Control who can download/use models
- 📊 **Resource Monitoring** - Real-time CPU/Memory/GPU usage
- 🔄 **Auto-Optimization** - Intelligent model loading based on resources

## Getting Started

### First Time Setup

After deploying your appliance with `docker-compose up -d`:

1. **Access Web Interface**: http://localhost:3000
2. **Create Admin Account**: Register your admin user
3. **Explore Model Browser**: Navigate to Models → Browse HuggingFace
4. **Download Your First Model**: We recommend starting with Llama 2 7B Chat Q4_0

### Initial Model Recommendations

For security analysis workloads:

**Beginner (8-16GB RAM):**
- `llama-2-7b-chat-q4_0` (4.2GB) - Excellent general purpose
- `mistral-7b-instruct-q4_0` (4.1GB) - Good for technical analysis

**Intermediate (16-32GB RAM):**  
- `llama-2-7b-chat-q5_0` (5.1GB) - Higher quality than Q4_0
- `codellama-7b-instruct-q4_0` (4.2GB) - Specialized for code analysis

**Advanced (32GB+ RAM):**
- `llama-2-13b-chat-q4_0` (7.8GB) - Better reasoning capabilities
- Multiple concurrent models for specialized tasks

## HuggingFace Model Browser

### Accessing the Browser

1. Navigate to **Models** → **Browse HuggingFace** in your web interface
2. Use search filters to find models suitable for your needs
3. Browse by category: Text Generation, Security, Code Analysis

### Understanding Model Cards

Each model shows:
- **Parameters**: Model size (7B, 13B, etc.)
- **Quantization Options**: Q4_0, Q5_0, Q6_0, Q8_0, FP16
- **File Size**: Actual download size
- **Compatibility**: LlamaCpp support indicator
- **License**: Usage restrictions
- **Downloads**: Community adoption indicator

### Search and Filtering

**Search Tips:**
```
"llama-2 chat"          # Find Llama 2 chat models
"security bert"         # Security-specific models  
"code analysis"         # Code review models
"instruct 7b"          # Instruction-tuned 7B models
```

**Filters Available:**
- **Model Size**: Filter by parameter count
- **File Size**: Filter by download size  
- **Quantization**: Q4_0 (speed) vs Q8_0 (quality)
- **License**: Commercial vs non-commercial use
- **Category**: Security, Code, General, etc.

## Model Download Process

### Initiating Downloads

1. **Select Model**: Click on desired model card
2. **Choose Quantization**: 
   - **Q4_0**: Best speed/size balance (recommended)
   - **Q5_0**: Better quality, 25% larger
   - **Q6_0**: High quality, 50% larger  
   - **Q8_0**: Maximum quality, 100% larger
3. **Confirm Download**: Review size and estimated time
4. **Monitor Progress**: Real-time download tracking

### Download Management

**Progress Monitoring:**
```bash
# Via Web Interface
http://localhost:3000/models/downloads

# Via API
curl http://localhost:8000/api/huggingface/downloads

# Via CLI
docker-compose logs app | grep download
```

**Concurrent Downloads:**
- Maximum 3 concurrent downloads (configurable)
- Bandwidth throttling to prevent network saturation
- Resume capability for interrupted downloads

### Storage Management

**Directory Structure:**
```
./models/
├── llama-2-7b-chat-q4_0.gguf        # 4.2GB
├── mistral-7b-instruct-q4_0.gguf    # 4.1GB
├── codellama-7b-instruct-q4_0.gguf  # 4.2GB
└── .metadata/
    ├── model_info.json               # Model metadata
    └── download_history.json         # Download records
```

**Space Management:**
- Monitor available disk space in dashboard
- Set storage quotas per user/role
- Automatic cleanup of old/unused models
- Compression for rarely used models

## Model Loading and Management

### Loading Models into Memory

**Via Web Interface:**
1. Go to **Models** → **Local Models**
2. Find your model and click **Load**
3. Monitor loading progress (30-60 seconds)
4. Model status changes to "Loaded"

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/embedded-ai/models/llama-2-7b-chat-q4_0.gguf/load" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### Hot Model Swapping

Switch models without restarting the appliance:

1. **Unload Current Model**: 
   ```bash
   curl -X DELETE "http://localhost:8000/api/embedded-ai/models/current/unload"
   ```

2. **Load New Model**:
   ```bash
   curl -X POST "http://localhost:8000/api/embedded-ai/models/mistral-7b-instruct-q4_0.gguf/load"
   ```

3. **Verify Model Active**:
   ```bash
   curl http://localhost:8000/api/embedded-ai/health
   ```

### Memory Management

**Model Memory Usage:**
- **7B Q4_0**: ~4-6GB RAM
- **7B Q5_0**: ~5-7GB RAM  
- **13B Q4_0**: ~8-12GB RAM
- **System Overhead**: ~2-4GB

**Optimization Strategies:**
- Load models on-demand
- Unload unused models automatically
- Use smaller quantizations for multiple concurrent models
- Monitor swap usage to prevent system slowdown

## User Permissions and Access Control

### Permission Levels

**Administrator:**
- Download any models from HuggingFace
- Delete models from local storage
- Load/unload any models
- Manage user permissions
- Access system monitoring

**Security Analyst:**
- Use pre-approved models
- Cannot download new models
- Cannot delete existing models
- Limited to specific model categories

**Viewer:**
- Read-only access to chat interface
- Cannot manage models
- Limited query quotas
- Restricted to designated models

### Configuring Permissions

**Via Web Interface:**
1. Go to **Admin** → **User Management**
2. Select user to modify
3. Configure model permissions:
   - **Can Download Models**: Yes/No
   - **Allowed Models**: Specific list or wildcard
   - **Can Delete Models**: Yes/No
   - **Max Concurrent Sessions**: Number limit

**Via API:**
```bash
curl -X PUT "http://localhost:8000/api/users/2" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "permissions": {
      "can_download_models": false,
      "can_use_models": ["llama-2-7b-chat-q4_0.gguf", "mistral-7b-instruct-q4_0.gguf"],
      "can_delete_models": false,
      "max_concurrent_sessions": 2
    }
  }'
```

## Performance Optimization

### Resource Monitoring

**Real-Time Dashboard:**
- CPU usage per model
- Memory consumption breakdown
- GPU utilization (if available)
- Disk I/O for model loading
- Network usage for downloads

**Performance Metrics:**
```bash
# System resource check
curl http://localhost:8000/api/system/status

# AI-specific metrics  
curl http://localhost:8000/api/system/metrics

# Model performance stats
curl http://localhost:8000/api/embedded-ai/health
```

### Optimization Techniques

**Memory Optimization:**
```yaml
# Optimal configurations
Small System (8-16GB):
  max_concurrent_models: 1
  preferred_quantization: Q4_0
  auto_unload_timeout: 10min

Medium System (16-32GB):
  max_concurrent_models: 2  
  preferred_quantization: Q5_0
  auto_unload_timeout: 30min

Large System (32GB+):
  max_concurrent_models: 3
  preferred_quantization: Q6_0
  auto_unload_timeout: 60min
```

**Performance Tuning:**
- **CPU Affinity**: Pin model processes to specific cores
- **Memory Pinning**: Lock model memory to prevent swapping
- **Quantization Selection**: Balance quality vs speed
- **Batch Processing**: Group queries for efficiency

### GPU Acceleration (Optional)

**NVIDIA GPU Support:**
```bash
# Enable GPU support during deployment
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

# Verify GPU detection
curl http://localhost:8000/api/system/status | jq '.system.gpu'

# GPU memory usage
curl http://localhost:8000/api/embedded-ai/health | jq '.system_resources.gpu_usage'
```

**GPU Performance Gains:**
- **Inference Speed**: 3-10x faster
- **Memory Efficiency**: Better memory utilization
- **Concurrent Models**: Support more simultaneous models
- **Larger Models**: Enable 13B+ models on limited RAM

## Security Best Practices

### Model Security

**Validation Process:**
- Verify model checksums after download
- Scan for malicious content using built-in tools
- Quarantine suspicious models
- Regular security updates for model parser

**Access Control:**
```bash
# Restrict model downloads to admin only
export ALLOW_MODEL_DOWNLOADS=admin

# Set model size limits
export MODEL_SIZE_LIMIT=50GB

# Enable model scanning
export ENABLE_MODEL_SCANNING=true
```

### Network Security

**Firewall Configuration:**
```bash
# Allow only necessary traffic
sudo ufw allow 22      # SSH
sudo ufw allow 3000    # Web interface  
sudo ufw allow 8000    # API (internal only)
sudo ufw deny outbound 11434  # Block Ollama port
```

**Proxy Configuration:**
```yaml
# For restricted environments
environment:
  - HTTP_PROXY=http://corporate-proxy:8080
  - HTTPS_PROXY=http://corporate-proxy:8080
  - NO_PROXY=localhost,127.0.0.1,postgres,redis
```

## Troubleshooting

### Common Issues

**Model Download Failures:**
```bash
# Check network connectivity
curl -I https://huggingface.co

# Verify disk space
df -h ./models

# Check download logs
docker-compose logs app | grep download

# Retry failed download
curl -X POST "http://localhost:8000/api/huggingface/download" \
  -H "Content-Type: application/json" \
  -d '{"model_id":"meta-llama/llama-2-7b-chat-hf","quantization":"Q4_0"}'
```

**Model Loading Issues:**
```bash
# Check available memory
free -h

# Verify model file integrity
ls -la ./models/
file ./models/llama-2-7b-chat-q4_0.gguf

# Check model metadata
curl http://localhost:8000/api/embedded-ai/models | jq '.models[0]'

# Force reload model
curl -X DELETE "http://localhost:8000/api/embedded-ai/models/current/unload"
curl -X POST "http://localhost:8000/api/embedded-ai/models/llama-2-7b-chat-q4_0.gguf/load"
```

**Performance Issues:**
```bash
# Monitor resource usage
docker stats --no-stream

# Check system load
uptime

# Analyze slow queries
curl http://localhost:8000/api/system/metrics | jq '.ai_metrics'

# Optimize model selection
curl http://localhost:8000/api/embedded-ai/models | jq '.models[] | select(.status=="loaded")'
```

### Recovery Procedures

**Corrupted Model Files:**
```bash
# Remove corrupted model
rm ./models/corrupted-model.gguf

# Re-download from HuggingFace
curl -X POST "http://localhost:8000/api/huggingface/download" \
  -H "Content-Type: application/json" \
  -d '{"model_id":"original-model-id","quantization":"Q4_0"}'
```

**Storage Full:**
```bash
# Clean up old downloads
docker-compose exec app python -c "
import os
for f in os.listdir('./models'):
    if f.endswith('.tmp') or f.endswith('.partial'):
        os.remove(f'./models/{f}')
"

# Remove unused models
curl -X DELETE "http://localhost:8000/api/embedded-ai/models/unused"
```

**Memory Issues:**
```bash
# Restart AI service
docker-compose restart app

# Reduce concurrent models
curl -X PUT "http://localhost:8000/api/system/config" \
  -H "Content-Type: application/json" \
  -d '{"max_concurrent_models": 1}'

# Clear model cache
docker-compose exec app python -c "
import gc
gc.collect()
"
```

## Advanced Configuration

### Custom Model Integration

**Adding Custom GGUF Models:**
```bash
# Copy model to models directory
cp /path/to/custom-model.gguf ./models/

# Refresh model list
curl -X POST "http://localhost:8000/api/embedded-ai/refresh-models"

# Verify model detected
curl http://localhost:8000/api/embedded-ai/models | jq '.models[] | select(.filename=="custom-model.gguf")'
```

### Batch Operations

**Bulk Model Management:**
```python
import requests

base_url = "http://localhost:8000"
headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}

# Download multiple models
models_to_download = [
    {"model_id": "meta-llama/llama-2-7b-chat-hf", "quantization": "Q4_0"},
    {"model_id": "mistralai/mistral-7b-instruct-v0.1", "quantization": "Q4_0"},
    {"model_id": "codellama/codellama-7b-instruct-hf", "quantization": "Q4_0"}
]

for model in models_to_download:
    response = requests.post(f"{base_url}/api/huggingface/download", 
                           json=model, headers=headers)
    print(f"Download started: {response.json()}")
```

### Integration with External Systems

**SIEM Integration:**
```bash
# Configure log forwarding to external SIEM
docker-compose exec app python -c "
from services.siem_service import SIEMService
siem = SIEMService()
siem.configure_forwarding('siem-server:514')
"
```

**API Integration:**
```python
# Python SDK example
from wazuh_ai_client import EmbeddedAIClient

client = EmbeddedAIClient("http://localhost:8000", api_key="your_jwt_token")

# Load model and query
client.load_model("llama-2-7b-chat-q4_0.gguf")
response = client.analyze_log("SSH brute force attempt detected...")
print(response.analysis)
```

---

## Best Practices Summary

### Model Selection
- **Start Small**: Begin with Q4_0 quantized 7B models
- **Test Performance**: Benchmark response times with your data
- **Scale Gradually**: Add larger models as needs grow
- **Specialize**: Use different models for different security tasks

### Resource Management  
- **Monitor Usage**: Keep CPU <80%, Memory <90%
- **Plan Capacity**: Reserve 20% headroom for peak usage
- **Optimize Loading**: Pre-load frequently used models
- **Clean Regularly**: Remove unused models monthly

### Security
- **Control Access**: Restrict downloads to authorized users
- **Validate Models**: Always verify model integrity
- **Monitor Activity**: Log all model operations
- **Network Isolation**: Run in isolated network segments

### Operations
- **Backup Configurations**: Regular backup of model metadata
- **Document Changes**: Track model updates and performance
- **Test Thoroughly**: Validate all models before production use
- **Plan Maintenance**: Schedule regular system maintenance

Your embedded Security AI Appliance provides enterprise-grade model management without any external dependencies. This complete self-contained approach ensures maximum security, reliability, and control for your security operations.