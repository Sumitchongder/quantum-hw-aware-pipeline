# Stage 1: Dependency builder environment
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/.local/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-dev \
    gcc \
    g++ \
    gfortran \
    liblapack-dev \
    libblas-dev \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY docker/requirements.txt .

# Install optimized wheel footprints directly to target path
RUN pip3 install --no-cache-dir --user -r requirements.txt

# Stage 2: Final minimal execution container target
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/.local/bin:$PATH"
ENV OMP_NUM_THREADS=8

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Copy installed site packages safely from builder layer
COPY --from=builder /root/.local /root/.local
COPY . /workspace

RUN chmod +x /workspace/docker/docker_entrypoint.sh

ENTRYPOINT ["/workspace/docker/docker_entrypoint.sh"]
