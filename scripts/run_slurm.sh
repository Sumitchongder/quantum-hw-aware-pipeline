#!/bin/bash
#SBATCH --job-name=quantum_codesign_eval
#SBATCH --output=logs/eval_%j.out
#SBATCH --error=logs/eval_%j.err
#SBATCH --partition=gpu
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=16
#SBATCH --gres=gpu:nvidia_a100_80gb:1
#SBATCH --time=12:00:00
#SBATCH --mem=64G
#SBATCH --export=ALL

set -e

# Module loading protocol for HPC clusters
module purge
module load cuda/12.2.0
module load python/3.11-anaconda

# Activate virtual environment
source activate quantum_env

# Metadata Logging for Q1 Reproducibility Audit Logs
echo "=== SYSTEM EXECUTION METADATA ==="
echo "Execution Timestamp : $(date -u)"
echo "Target QPU Simulation Platform : NVIDIA cuQuantum SDK Engine"
echo "Allocated Compute Node : $SLURMD_NODENAME"
echo "Allocated GPU Devices  : $CUDA_VISIBLE_DEVICES"
echo "================================="

# Establish environment variables for high-performance tensor simulation
export CUQUANTUM_ROOT=$CUDA_HOME
export OMP_NUM_THREADS=16
export PYTHONUNBUFFERED=1

# Execute the benchmarking pipeline across the 6-40 qubit tracking horizon
python3 -m src.pipeline.run_benchmarks \
    --config config/production_hardware_models.json \
    --output_dir results/raw_data/ \
    --enable_gpu \
    --threads 16

echo "HPC SLURM execution loop successfully terminated."
