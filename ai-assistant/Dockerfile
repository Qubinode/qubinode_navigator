# Multi-stage build for Qubinode AI Assistant
# Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture

# Stage 1: Build llama.cpp
FROM registry.redhat.io/ubi9/ubi:latest AS builder

# Install build dependencies
RUN dnf update -y && \
    dnf install -y --allowerasing gcc-c++ cmake make git wget curl libcurl-devel && \
    dnf clean all

# Clone and build llama.cpp with CPU optimizations (static build)
WORKDIR /build
RUN git clone https://github.com/ggerganov/llama.cpp.git && \
    cd llama.cpp && \
    cmake -B build -DGGML_NATIVE=ON -DGGML_AVX2=ON -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF && \
    cmake --build build --config Release -j$(nproc)

# Stage 2: Runtime environment
FROM registry.redhat.io/ubi9/python-312:latest

# Switch to root for package installation
USER root

# Install runtime dependencies including libraries needed for llama.cpp
RUN dnf update -y && \
    dnf install -y --allowerasing curl wget libgomp libstdc++ && \
    dnf clean all

# Python 3.12 image already has 'default' user with UID 1001

# Copy llama.cpp binaries from builder stage
COPY --from=builder /build/llama.cpp/build/bin/llama-server /usr/local/bin/
COPY --from=builder /build/llama.cpp/build/bin/llama-cli /usr/local/bin/

# Create compatibility symlinks for backward compatibility
RUN mkdir -p /app/llama.cpp && \
    ln -s /usr/local/bin/llama-server /app/llama.cpp/server && \
    ln -s /usr/local/bin/llama-cli /app/llama.cpp/cli

# Install uv for fast dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Set up Python virtual environment (best practice)
WORKDIR /app
RUN uv venv /app/venv

# Install Python dependencies in virtual environment
COPY requirements.txt .
RUN uv pip install --python /app/venv/bin/python --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create directories for models and data
RUN mkdir -p /app/models /app/data /app/logs && \
    chown -R 1001:0 /app

# Switch to non-root user (default user with UID 1001)
USER 1001

# Expose API port
EXPOSE 8080

# Health check - increased start-period for model download (can take 2-5 minutes)
# Uses /health endpoint which returns 503 during startup, 200 when ready
HEALTHCHECK --interval=30s --timeout=30s --start-period=300s --retries=5 \
    CMD curl -sf --max-time 30 http://localhost:8080/health || exit 1

# Default command using virtual environment
CMD ["/app/venv/bin/python", "src/main.py"]
