# Multi-stage build for AI-Enhanced Security Query Interface Appliance
FROM python:3.11-slim as base

# Set environment variables for self-contained security appliance
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AI_SERVICE_TYPE=embedded \
    MODELS_PATH=/app/models \
    VECTORSTORE_PATH=/app/data/vectorstore \
    MAX_CONCURRENT_MODELS=3 \
    EMBEDDING_MODEL=all-MiniLM-L6-v2 \
    DEFAULT_TEMPERATURE=0.7 \
    DEFAULT_MAX_TOKENS=1024 \
    CONVERSATION_MEMORY_SIZE=10

# Install system dependencies for embedded AI with CPU/GPU support
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    cmake \
    make \
    libpq-dev \
    openssh-client \
    curl \
    wget \
    build-essential \
    pkg-config \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Install CUDA support (optional - for GPU acceleration)
# Uncomment the following lines if GPU support is needed
# RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-keyring_1.0-1_all.deb && \
#     dpkg -i cuda-keyring_1.0-1_all.deb && \
#     apt-get update && \
#     apt-get install -y cuda-toolkit-12-0 && \
#     rm -rf /var/lib/apt/lists/* cuda-keyring_1.0-1_all.deb

# Create non-root user
RUN groupadd -r wazuh && useradd -r -g wazuh wazuh

# Set working directory
WORKDIR /app

# Create directories for embedded AI appliance
RUN mkdir -p /app/models /app/data/vectorstore /app/data/cache /app/models/config /app/models/local /app/models/cache

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with embedded AI support
# For CPU-only deployment (default)
RUN pip install --no-cache-dir -r requirements.txt

# For GPU support, uncomment the following line instead:
# RUN CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install --no-cache-dir llama-cpp-python==0.2.20 && \
#     pip install --no-cache-dir -r requirements.txt --ignore-installed llama-cpp-python

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov black flake8 mypy

# Copy source code
COPY . .

# Change ownership to non-root user
RUN chown -R wazuh:wazuh /app

USER wazuh

# Expose port
EXPOSE 8000

# Health check for security appliance (development)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Copy source code
COPY . .

# Remove development files
RUN rm -rf tests/ docs/ *.md .git* .env.example

# Change ownership to non-root user
RUN chown -R wazuh:wazuh /app

USER wazuh

# Expose port
EXPOSE 8000

# Health check for security appliance (production)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command with optimizations for security appliance
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--access-log"]