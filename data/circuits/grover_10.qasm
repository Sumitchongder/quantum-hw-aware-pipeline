// Grover's algorithm – 10-qubit search circuit
// Target: |1111111111> (all-ones bitstring)
// Two oracle + diffusion iterations for depth-56 benchmark (§5)
// Compatible with Qiskit QuantumCircuit.from_qasm_str()

OPENQASM 2.0;
include "qelib1.inc";

qreg q[10];
creg c[10];

// ── Hadamard initialisation ──────────────────────────────────────────────────
h q[0]; h q[1]; h q[2]; h q[3]; h q[4];
h q[5]; h q[6]; h q[7]; h q[8]; h q[9];

// ── Iteration 1: Oracle ──────────────────────────────────────────────────────
// Phase flip on |1111111111> via multi-controlled-Z decomposed into CX+H chain
h q[9];
cx q[0],q[9];  cx q[1],q[9];  cx q[2],q[9];  cx q[3],q[9];
cx q[4],q[9];  cx q[5],q[9];  cx q[6],q[9];  cx q[7],q[9];
cx q[8],q[9];
h q[9];

// ── Iteration 1: Diffusion operator ─────────────────────────────────────────
h q[0]; h q[1]; h q[2]; h q[3]; h q[4];
h q[5]; h q[6]; h q[7]; h q[8]; h q[9];

x q[0]; x q[1]; x q[2]; x q[3]; x q[4];
x q[5]; x q[6]; x q[7]; x q[8]; x q[9];

h q[9];
cx q[0],q[9];  cx q[1],q[9];  cx q[2],q[9];  cx q[3],q[9];
cx q[4],q[9];  cx q[5],q[9];  cx q[6],q[9];  cx q[7],q[9];
cx q[8],q[9];
h q[9];

x q[0]; x q[1]; x q[2]; x q[3]; x q[4];
x q[5]; x q[6]; x q[7]; x q[8]; x q[9];

h q[0]; h q[1]; h q[2]; h q[3]; h q[4];
h q[5]; h q[6]; h q[7]; h q[8]; h q[9];

// ── Iteration 2: Oracle ──────────────────────────────────────────────────────
h q[9];
cx q[0],q[9];  cx q[1],q[9];  cx q[2],q[9];  cx q[3],q[9];
cx q[4],q[9];  cx q[5],q[9];  cx q[6],q[9];  cx q[7],q[9];
cx q[8],q[9];
h q[9];

// ── Iteration 2: Diffusion operator ─────────────────────────────────────────
h q[0]; h q[1]; h q[2]; h q[3]; h q[4];
h q[5]; h q[6]; h q[7]; h q[8]; h q[9];

x q[0]; x q[1]; x q[2]; x q[3]; x q[4];
x q[5]; x q[6]; x q[7]; x q[8]; x q[9];

h q[9];
cx q[0],q[9];  cx q[1],q[9];  cx q[2],q[9];  cx q[3],q[9];
cx q[4],q[9];  cx q[5],q[9];  cx q[6],q[9];  cx q[7],q[9];
cx q[8],q[9];
h q[9];

x q[0]; x q[1]; x q[2]; x q[3]; x q[4];
x q[5]; x q[6]; x q[7]; x q[8]; x q[9];

h q[0]; h q[1]; h q[2]; h q[3]; h q[4];
h q[5]; h q[6]; h q[7]; h q[8]; h q[9];

// ── Measurement ──────────────────────────────────────────────────────────────
measure q[0] -> c[0]; measure q[1] -> c[1]; measure q[2] -> c[2];
measure q[3] -> c[3]; measure q[4] -> c[4]; measure q[5] -> c[5];
measure q[6] -> c[6]; measure q[7] -> c[7]; measure q[8] -> c[8];
measure q[9] -> c[9];
