from qiskit import QuantumCircuit

def oracle_equal_to(number, nqubits, name=None):
    """
    Oracle que marca (fase -1) el estado |x⟩ tal que x == number
    """

    # --- Convertir a entero si viene en binario ---
    if isinstance(number, str):
        number_int = int(number, 2)
        binary = number.zfill(nqubits)
    else:
        number_int = number
        binary = format(number, f"0{nqubits}b")

    # --- Crear circuito ---
    if name:
        circuit = QuantumCircuit(nqubits, name=name)
    else:
        circuit = QuantumCircuit(nqubits, name=f"== {number_int}")

    # --- Paso 1: convertir el estado objetivo en |111...⟩ ---
    for i, bit in enumerate(reversed(binary)):
        if bit == '0':
            circuit.x(i)

    # --- Paso 2: aplicar cambio de fase ---
    circuit.h(nqubits - 1)
    circuit.mcx(list(range(nqubits - 1)), nqubits - 1)
    circuit.h(nqubits - 1)

    # --- Paso 3: deshacer transformación ---
    for i, bit in enumerate(reversed(binary)):
        if bit == '0':
            circuit.x(i)

    return circuit