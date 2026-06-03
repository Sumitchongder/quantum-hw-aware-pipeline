import pytest
import numpy as np
import xgboost as xgb
from src.scheduler.ml_scheduler import DataDrivenQEDScheduler

@pytest.fixture
def dummy_scheduler_model():
    scheduler = DataDrivenQEDScheduler(max_depth=4, n_estimators=10)
    # Synthesize small data training representations
    X_dummy = np.random.uniform(1.0, 5.0, (100, 4)) # Metrics: Nodes, Connectivity, Depth, Gate Density
    y_dummy = np.random.randint(0, 2, size=(100,))
    scheduler.fit(X_dummy, y_dummy)
    return scheduler

def test_inference_latency_bounds(dummy_scheduler_model):
    import time
    
    # Test vector tracking: [qubits, graph_entropy, gate_density, baseline_latency]
    test_feature_vector = np.array([[20, 2.45, 0.65, 12.4]])
    
    start_time = time.perf_counter()
    scheduling_density_decision = dummy_scheduler_model.predict(test_feature_vector)
    end_time = time.perf_counter()
    
    total_latency_ms = (end_time - start_time) * 1000.0
    
    # Core performance assertion: real-time latency must remain strictly bounded under 6ms
    assert total_latency_ms < 6.0, f"Latency validation breached. Value recorded: {total_latency_ms:.2f} ms"
    assert scheduling_density_decision in [0, 1], "Invalid categorical target classification returned."
