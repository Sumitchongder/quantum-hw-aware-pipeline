"""[[n,n-2,2]] quantum error detection primitives."""
from .primitives import QEDBlock
from .circuit_builder import QEDCircuitBuilder

__all__ = ["QEDBlock", "QEDCircuitBuilder"]
