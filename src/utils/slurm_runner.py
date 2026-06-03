"""
SLURM job submission helper.

Generates SLURM batch scripts for running the benchmark harness on an HPC
cluster with NVIDIA A100 GPU nodes (§4.4 of the paper).
"""

from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path
from typing import List, Optional


class SlurmRunner:
    """Generate and optionally submit SLURM batch scripts.

    Parameters
    ----------
    partition : str
        SLURM partition name.
    n_gpus : int
        Number of GPUs per node.
    n_cpus : int
        Number of CPUs per task.
    memory_gb : int
        Memory allocation in GB.
    time_limit : str
        Wall-clock time limit in HH:MM:SS format.
    account : str
        SLURM account / project code (optional).
    """

    SCRIPT_TEMPLATE = textwrap.dedent("""
        #!/bin/bash
        #SBATCH --job-name={job_name}
        #SBATCH --partition={partition}
        #SBATCH --nodes=1
        #SBATCH --ntasks=1
        #SBATCH --cpus-per-task={n_cpus}
        #SBATCH --gres=gpu:{n_gpus}
        #SBATCH --mem={memory_gb}G
        #SBATCH --time={time_limit}
        #SBATCH --output=slurm-%j.out
        #SBATCH --error=slurm-%j.err
        {account_line}

        module purge
        module load cuda/12.2 python/3.10

        source $HOME/envs/qhw/bin/activate

        export CUDA_VISIBLE_DEVICES=0
        export CUQUANTUM_ROOT=${{CONDA_PREFIX}}

        cd {repo_root}

        {command}
    """).strip()

    def __init__(
        self,
        partition: str = "gpu",
        n_gpus: int = 1,
        n_cpus: int = 8,
        memory_gb: int = 80,
        time_limit: str = "12:00:00",
        account: Optional[str] = None,
    ) -> None:
        self.partition = partition
        self.n_gpus = n_gpus
        self.n_cpus = n_cpus
        self.memory_gb = memory_gb
        self.time_limit = time_limit
        self.account = account

    def generate_script(
        self,
        command: str,
        job_name: str = "qhw_pipeline",
        repo_root: Optional[str] = None,
    ) -> str:
        """Render a SLURM batch script string.

        Parameters
        ----------
        command : str
            Shell command to run inside the job (e.g. ``python src/main.py ...``).
        job_name : str
            SLURM job name.
        repo_root : str
            Absolute path to the repository root.

        Returns
        -------
        str
            Complete SLURM batch script as a string.
        """
        repo_root = repo_root or str(Path.cwd())
        account_line = (
            f"#SBATCH --account={self.account}" if self.account else ""
        )
        return self.SCRIPT_TEMPLATE.format(
            job_name=job_name,
            partition=self.partition,
            n_cpus=self.n_cpus,
            n_gpus=self.n_gpus,
            memory_gb=self.memory_gb,
            time_limit=self.time_limit,
            account_line=account_line,
            repo_root=repo_root,
            command=command,
        )

    def submit(
        self,
        command: str,
        job_name: str = "qhw_pipeline",
        repo_root: Optional[str] = None,
        script_path: str = "/tmp/slurm_job.sh",
    ) -> str:
        """Generate and submit a SLURM job.

        Returns
        -------
        str
            SLURM job ID string.
        """
        script = self.generate_script(command, job_name, repo_root)
        with open(script_path, "w") as fh:
            fh.write(script)
        os.chmod(script_path, 0o755)

        result = subprocess.run(
            ["sbatch", script_path],
            capture_output=True, text=True, check=True,
        )
        # Output format: "Submitted batch job 12345"
        job_id = result.stdout.strip().split()[-1]
        return job_id
