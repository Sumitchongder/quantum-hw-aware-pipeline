import pytest
import numpy as np
from qiskit import QuantumCircuit
from src.compiler.mapping_pass import NoiseWeightedILPRouter

@pytest.fixture
def sample_hardware_topology():
    # Construct a simple linear 5-qubit coupling map profile
    return {
        "nodes": [0, 1, 2, 3, 4],
        "edges": [(0, 1), (1, 2), (2, 3), (3, 4)],
        "error_rates": {(0, 1): 0.01, (1, 2): 0.015, (2, 3): 0.012, (3, 4): 0.02}
    }

@pytest.fixture
def unmapped_quantum_circuit():
    qc = QuantumCircuit(4)
    qc.h(0)
    qc.cx(0, 3) # Requires routing transformations under a linear topology model
    qc.cx(1, 2)
    return qc

def test_router_topology_satisfaction(sample_hardware_topology, unmapped_quantum_circuit):
    router = NoiseWeightedILPRouter(
        topology=sample_hardware_topology,
        ilp_window_size=10
    )
    
    # Run the physical optimization pass over target circuits
    compiled_circuit, final_layout = router.run(unmapped_quantum_circuit)
    
    assert compiled_circuit is not None
    assert len(final_layout) == 4
    
    # Verify that all physical 2-qubit operations match connection properties
    for instruction in compiled_circuit.data:
        if instruction.operation.name == "cx":
            q0 = compiled_circuit.find_bit(instruction.qubits[0]).index
            q1 = compiled_circuit.find_bit(instruction.qubits[1]).index
            assert (q0, q1) in sample_hardware_topology["edges"] or (q1, q0) in sample_hardware_topology["edges"]
