from qiskit import QuantumCircuit

# ESTE CIRCUITO ES EQUIVALENTE A MULTIPLICAR TODO POR -1
# ESTE ORACULO NO CAMBIA PROBABILIDAD4S, NO AFECTA A MEDICIONES, NO SIRVE PARA GROVER DIRECTAMENTE

def globalphase() -> QuantumCircuit:

    circuit = QuantumCircuit(1, name="Global Phase(pi)")

    circuit.z(0)
    circuit.x(0)
    circuit.z(0)
    circuit.x(0)

    return circuit