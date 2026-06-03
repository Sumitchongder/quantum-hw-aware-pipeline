#!/bin/bash
set -e

echo "=== INITIALIZING QUANTUM COMPILATION CONTAINER CONTEXT ==="
echo "Python Runtime Environment Version: $(python3 --version)"
echo "NVIDIA CUDA Core Integration Level: $(nvcc --version 2>/dev/null || echo 'Runtime Shared Linker Only')"

# Create required output directory paths inside the runtime volume structure
mkdir -p /workspace/results/raw_data
mkdir -p /workspace/results/plots
mkdir -p /workspace/logs

if [ "$1" == "test" ]; then
    echo "Running system test harness framework..."
    exec pytest tests/ -v
else
    echo "Executing primary numerical reproduction sequence..."
    exec /bin/bash /workspace/scripts/reproduce_key_results.sh
fi
