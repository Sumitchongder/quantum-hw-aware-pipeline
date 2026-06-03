OPENQASM 3.0;
include "stdgates.inc";

// VQE-LiH: 12-qubit lithium hydride molecule variational eigensolver ansatz
// Hardware-efficient ansatz, depth ~68 (Table 4 in paper)
// Parametric angles near-optimal from classical pre-optimisation

qubit[12] q;
bit[12] c;

// --- Layer 0: Ry + Rz initialisation ---
ry(0.3054) q[0];  ry(0.6109) q[1];  ry(1.0472) q[2];  ry(0.7854) q[3];
ry(1.2217) q[4];  ry(0.5236) q[5];  ry(0.4363) q[6];  ry(0.8727) q[7];
ry(1.3963) q[8];  ry(0.2618) q[9];  ry(0.6981) q[10]; ry(1.1345) q[11];

rz(0.1745) q[0];  rz(0.3491) q[1];  rz(0.5236) q[2];  rz(0.3927) q[3];
rz(0.6109) q[4];  rz(0.2618) q[5];  rz(0.2182) q[6];  rz(0.4363) q[7];
rz(0.6981) q[8];  rz(0.1309) q[9];  rz(0.3491) q[10]; rz(0.5672) q[11];

// --- Entanglement block 1: linear chain ---
cx q[0], q[1];   cx q[1], q[2];   cx q[2], q[3];   cx q[3], q[4];
cx q[4], q[5];   cx q[5], q[6];   cx q[6], q[7];   cx q[7], q[8];
cx q[8], q[9];   cx q[9], q[10];  cx q[10], q[11];

// --- Layer 1: variational rotations ---
ry(0.6981) q[0];  ry(1.3963) q[1];  ry(0.8727) q[2];  ry(1.7453) q[3];
ry(0.5236) q[4];  ry(0.3491) q[5];  ry(1.2217) q[6];  ry(0.6109) q[7];
ry(1.0472) q[8];  ry(0.4363) q[9];  ry(0.7854) q[10]; ry(0.2618) q[11];

rz(0.3491) q[0];  rz(0.6981) q[1];  rz(0.4363) q[2];  rz(0.8727) q[3];
rz(0.2618) q[4];  rz(0.1745) q[5];  rz(0.6109) q[6];  rz(0.3054) q[7];
rz(0.5236) q[8];  rz(0.2182) q[9];  rz(0.3927) q[10]; rz(0.1309) q[11];

// --- Entanglement block 2: skip-one pairs ---
cx q[0], q[2];   cx q[1], q[3];   cx q[2], q[4];   cx q[3], q[5];
cx q[4], q[6];   cx q[5], q[7];   cx q[6], q[8];   cx q[7], q[9];
cx q[8], q[10];  cx q[9], q[11];

// --- Layer 2 ---
ry(1.0472) q[0];  ry(0.5236) q[1];  ry(0.7854) q[2];  ry(1.2217) q[3];
ry(0.3491) q[4];  ry(0.8727) q[5];  ry(0.6109) q[6];  ry(1.3963) q[7];
ry(0.4363) q[8];  ry(0.6981) q[9];  ry(1.1345) q[10]; ry(0.3054) q[11];

rz(0.5236) q[0];  rz(0.2618) q[1];  rz(0.3927) q[2];  rz(0.6109) q[3];
rz(0.1745) q[4];  rz(0.4363) q[5];  rz(0.3054) q[6];  rz(0.6981) q[7];
rz(0.2182) q[8];  rz(0.3491) q[9];  rz(0.5672) q[10]; rz(0.1527) q[11];

// --- Entanglement block 3: long-range pairs ---
cx q[0], q[6];   cx q[1], q[7];   cx q[2], q[8];   cx q[3], q[9];
cx q[4], q[10];  cx q[5], q[11];

// --- Layer 3 ---
ry(0.7854) q[0];  ry(1.0472) q[1];  ry(0.5236) q[2];  ry(0.8727) q[3];
ry(0.3491) q[4];  ry(1.2217) q[5];  ry(0.6109) q[6];  ry(0.4363) q[7];
ry(1.3963) q[8];  ry(0.2618) q[9];  ry(0.6981) q[10]; ry(1.1345) q[11];

rz(0.3927) q[0];  rz(0.7854) q[1];  rz(0.2618) q[2];  rz(0.4363) q[3];
rz(0.1745) q[4];  rz(0.6109) q[5];  rz(0.3054) q[6];  rz(0.2182) q[7];
rz(0.6981) q[8];  rz(0.1309) q[9];  rz(0.3491) q[10]; rz(0.5672) q[11];

// --- Entanglement block 4: reverse chain ---
cx q[11], q[10]; cx q[10], q[9];  cx q[9], q[8];   cx q[8], q[7];
cx q[7], q[6];   cx q[6], q[5];   cx q[5], q[4];   cx q[4], q[3];
cx q[3], q[2];   cx q[2], q[1];   cx q[1], q[0];

// --- Final rotation layer ---
ry(0.6109) q[0];  ry(0.8727) q[1];  ry(1.2217) q[2];  ry(0.5236) q[3];
ry(0.3491) q[4];  ry(1.0472) q[5];  ry(0.7854) q[6];  ry(0.4363) q[7];
ry(0.6981) q[8];  ry(1.3963) q[9];  ry(0.2618) q[10]; ry(0.5672) q[11];

// --- Measurement ---
c = measure q;
