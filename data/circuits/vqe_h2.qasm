OPENQASM 3.0;
include "stdgates.inc";

// VQE-H2: 8-qubit hydrogen molecule variational eigensolver ansatz
// Hardware-efficient ansatz with CNOT entanglement layers
// Circuit depth ~40, matching the benchmark in the paper (Table 4)
// Parametric angles set to near-optimal values from classical pre-optimisation

qubit[8] q;
bit[8] c;

// --- Layer 0: Initial Ry rotations (variational parameters theta_0..7) ---
ry(0.3491) q[0];
ry(1.0472) q[1];
ry(0.5236) q[2];
ry(1.5708) q[3];
ry(0.7854) q[4];
ry(1.2217) q[5];
ry(0.4363) q[6];
ry(0.8727) q[7];

// --- Layer 0: Rz rotations ---
rz(0.1745) q[0];
rz(0.5236) q[1];
rz(0.2618) q[2];
rz(0.7854) q[3];
rz(0.3927) q[4];
rz(0.6109) q[5];
rz(0.2182) q[6];
rz(0.4363) q[7];

// --- Entanglement block 1: linear CNOT chain ---
cx q[0], q[1];
cx q[1], q[2];
cx q[2], q[3];
cx q[3], q[4];
cx q[4], q[5];
cx q[5], q[6];
cx q[6], q[7];

// --- Layer 1: Ry rotations (variational parameters theta_8..15) ---
ry(0.6981) q[0];
ry(1.3963) q[1];
ry(0.8727) q[2];
ry(1.7453) q[3];
ry(1.0472) q[4];
ry(0.5236) q[5];
ry(0.3491) q[6];
ry(1.2217) q[7];

rz(0.3491) q[0];
rz(0.6981) q[1];
rz(0.4363) q[2];
rz(0.8727) q[3];
rz(0.5236) q[4];
rz(0.3054) q[5];
rz(0.1745) q[6];
rz(0.6109) q[7];

// --- Entanglement block 2: even-odd CNOT pairs ---
cx q[0], q[2];
cx q[1], q[3];
cx q[2], q[4];
cx q[3], q[5];
cx q[4], q[6];
cx q[5], q[7];

// --- Layer 2: Ry rotations ---
ry(1.0472) q[0];
ry(0.5236) q[1];
ry(0.7854) q[2];
ry(1.2217) q[3];
ry(0.3491) q[4];
ry(0.8727) q[5];
ry(0.6109) q[6];
ry(1.3963) q[7];

rz(0.5236) q[0];
rz(0.2618) q[1];
rz(0.3927) q[2];
rz(0.6109) q[3];
rz(0.1745) q[4];
rz(0.4363) q[5];
rz(0.3054) q[6];
rz(0.6981) q[7];

// --- Entanglement block 3: all-to-nearest CNOT chain ---
cx q[1], q[0];
cx q[3], q[2];
cx q[5], q[4];
cx q[7], q[6];
cx q[0], q[7];
cx q[2], q[5];

// --- Final rotation layer ---
ry(0.7854) q[0];
ry(1.0472) q[1];
ry(0.5236) q[2];
ry(0.8727) q[3];
ry(0.3491) q[4];
ry(1.2217) q[5];
ry(0.6109) q[6];
ry(0.4363) q[7];

// --- Measurement ---
c = measure q;
