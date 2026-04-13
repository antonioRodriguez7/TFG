from qiskit import QuantumCircuit
import numpy as np

from oraculos.greater_than import oracle_greater_than

def oracle_range_of(lower, upper, nqubits, name=None):
    """
    Oracle que marca (fase -1) los estados:
    lower < x < upper
    """

    # --- Crear circuito ---
    if name:
        circuit = QuantumCircuit(nqubits, name=name)
    else:
        circuit = QuantumCircuit(nqubits, name="range_of")

    # --- Construir oráculos auxiliares ---
    less = oracle_less_than(number=upper, nqubits=nqubits)
    greater = oracle_greater_than(number=lower, nqubits=nqubits)

    # --- Aplicar primero greater_than ---
    circuit.append(greater.to_gate(), list(range(nqubits)))

    # --- Aplicar después less_than ---
    circuit.append(less.to_gate(), list(range(nqubits)))

    # --- Fase global ---
    circuit.global_phase += np.pi

    return circuit