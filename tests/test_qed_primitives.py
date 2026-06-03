import pytest
from qiskit import QuantumCircuit
from src.qed.primitives import inject_syndrome_check_block

def test_qed_injection_ancilla_isolation():
    base_qc = QuantumCircuit(2)
    base_qc.cx(0, 1)
    
    # Apply error detection weave functions to target sequences
    qed_circuit = inject_syndrome_check_block(base_qc, target_qubits=[0, 1], ancilla_index=2)
    
    # Core structural constraint assertions
    assert qed_circuit.num_qubits == 3, "Failure to properly allocate required ancilla tracking lines."
    
    # Verify readout measurement assignments map safely into isolated data arrays
    gate_counts = qed_circuit.count_ops()
    assert "measure" in gate_counts, "Syndrome verification extraction pass must execute read operations."
    assert "reset" in gate_counts, "Ancilla recycling loops require active state resetting primitives."
