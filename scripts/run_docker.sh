#!/bin/bash
set -e

IMAGE_NAME="quantum-codesign-pipeline:v1.0.0"
CONTAINER_NAME="quantum_compiler_runtime"

# Ensure runtime reporting paths exist locally
mkdir -p "$(pwd)/results"
mkdir -p "$(pwd)/logs"

echo "Initializing isolated Docker container environment..."

# Check for native GPU runtime capabilities
if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA Container Toolkit detected. Initializing GPU-accelerated runtime..."
    GPU_FLAG="--gpus all"
else
    echo "WARNING: NVIDIA Container Toolkit not found. Falling back to classical CPU execution..."
    GPU_FLAG=""
fi

# Execute container containerization runtime layer
docker run --rm -it \
    $GPU_FLAG \
    --name "$CONTAINER_NAME" \
    -v "$(pwd)/results:/workspace/results" \
    -v "$(pwd)/logs:/workspace/logs" \
    -e PYTHONUNBUFFERED=1 \
    -e CUQUANTUM_ENABLE=1 \
    "$IMAGE_NAME"

echo "Container runtime environment terminated successfully."
