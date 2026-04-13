from qiskit import QuantumCircuit

def oracle_greater_than(number, nqubits, name=None):
    """
    Oracle que marca (fase -1) los estados mayores que 'number'
    """

    # --- Convertir a entero si viene en binario ---
    if isinstance(number, str):
        number = int(number, 2)

    # --- Crear circuito ---
    if name:
        circuit = QuantumCircuit(nqubits, name=name)
    else:
        circuit = QuantumCircuit(nqubits, name=f"> {number}")

    # --- Caso borde ---
    if number < (2**nqubits):
        number = number + 1

    # --- Oráculo auxiliar ---
    less_than = oracle_less_than(number=number, nqubits=nqubits)

    # --- Aplicar oracle_less_than ---
    circuit.append(less_than.to_gate(), list(range(nqubits)))

    # --- Global phase ---
    # En Qiskit actual se hace así:
    circuit.global_phase += np.pi

    return circuit