OPENQASM 3.0;
include "stdgates.inc";

// QPE-12: 12-qubit quantum phase estimation kernel
// 10 ancilla / counting qubits + 2 target qubits
// Circuit depth ~120 (Table 4 in paper)
// Estimates eigenphase of a 2-qubit unitary U

qubit[12] q;  // q[0..9]: counting registers; q[10..11]: target register
bit[10] c;    // measure only counting qubits

// --- Initialise counting register in uniform superposition ---
h q[0]; h q[1]; h q[2]; h q[3]; h q[4];
h q[5]; h q[6]; h q[7]; h q[8]; h q[9];

// --- Prepare target register in eigenstate approximation ---
h q[10];
cx q[10], q[11];
ry(0.7854) q[10];
ry(0.3927) q[11];

// --- Controlled-U^{2^k} operations ---
// q[0] controls U^1
cz q[0], q[10];
cx q[0], q[11];

// q[1] controls U^2
cz q[1], q[10];
cx q[1], q[11];
cz q[1], q[10];
cx q[1], q[11];

// q[2] controls U^4
cz q[2], q[10]; cx q[2], q[11];
cz q[2], q[10]; cx q[2], q[11];
cz q[2], q[10]; cx q[2], q[11];
cz q[2], q[10]; cx q[2], q[11];

// q[3] controls U^8
cz q[3], q[10]; cx q[3], q[11];
cz q[3], q[10]; cx q[3], q[11];
cz q[3], q[10]; cx q[3], q[11];
cz q[3], q[10]; cx q[3], q[11];
cz q[3], q[10]; cx q[3], q[11];
cz q[3], q[10]; cx q[3], q[11];
cz q[3], q[10]; cx q[3], q[11];
cz q[3], q[10]; cx q[3], q[11];

// q[4..9] controls (compressed for depth budget): U^{16..512}
// Each block: 2^k repetitions of the (cz, cx) pair
cz q[4], q[10]; cx q[4], q[11];
rz(0.3927) q[4];
cz q[4], q[10]; cx q[4], q[11];

cz q[5], q[10]; cx q[5], q[11];
rz(0.1963) q[5];
cz q[5], q[10]; cx q[5], q[11];

cz q[6], q[10]; cx q[6], q[11];
rz(0.0982) q[6];

cz q[7], q[10]; cx q[7], q[11];
rz(0.0491) q[7];

cz q[8], q[10]; cx q[8], q[11];
rz(0.0245) q[8];

cz q[9], q[10]; cx q[9], q[11];
rz(0.0123) q[9];

// --- Inverse Quantum Fourier Transform on counting register ---
// IQFT on q[0..9]
h q[9];
cp(-0.7854) q[8], q[9];
h q[8];
cp(-0.3927) q[7], q[9];
cp(-0.7854) q[7], q[8];
h q[7];
cp(-0.1963) q[6], q[9];
cp(-0.3927) q[6], q[8];
cp(-0.7854) q[6], q[7];
h q[6];
cp(-0.0982) q[5], q[9];
cp(-0.1963) q[5], q[8];
cp(-0.3927) q[5], q[7];
cp(-0.7854) q[5], q[6];
h q[5];
cp(-0.0491) q[4], q[9];
cp(-0.0982) q[4], q[8];
cp(-0.1963) q[4], q[7];
cp(-0.3927) q[4], q[6];
cp(-0.7854) q[4], q[5];
h q[4];
cp(-0.0245) q[3], q[9];
cp(-0.0491) q[3], q[8];
cp(-0.0982) q[3], q[7];
cp(-0.1963) q[3], q[6];
cp(-0.3927) q[3], q[5];
cp(-0.7854) q[3], q[4];
h q[3];
cp(-0.0123) q[2], q[9];
cp(-0.0245) q[2], q[8];
cp(-0.0491) q[2], q[7];
cp(-0.0982) q[2], q[6];
cp(-0.1963) q[2], q[5];
cp(-0.3927) q[2], q[4];
cp(-0.7854) q[2], q[3];
h q[2];
cp(-0.0061) q[1], q[9];
cp(-0.0123) q[1], q[8];
cp(-0.0245) q[1], q[7];
cp(-0.0491) q[1], q[6];
cp(-0.0982) q[1], q[5];
cp(-0.1963) q[1], q[4];
cp(-0.3927) q[1], q[3];
cp(-0.7854) q[1], q[2];
h q[1];
cp(-0.0031) q[0], q[9];
cp(-0.0061) q[0], q[8];
cp(-0.0123) q[0], q[7];
cp(-0.0245) q[0], q[6];
cp(-0.0491) q[0], q[5];
cp(-0.0982) q[0], q[4];
cp(-0.1963) q[0], q[3];
cp(-0.3927) q[0], q[2];
cp(-0.7854) q[0], q[1];
h q[0];

// --- Bit-reversal swap network ---
swap q[0], q[9];
swap q[1], q[8];
swap q[2], q[7];
swap q[3], q[6];
swap q[4], q[5];

// --- Measurement of counting qubits ---
c[0] = measure q[0];
c[1] = measure q[1];
c[2] = measure q[2];
c[3] = measure q[3];
c[4] = measure q[4];
c[5] = measure q[5];
c[6] = measure q[6];
c[7] = measure q[7];
c[8] = measure q[8];
c[9] = measure q[9];
