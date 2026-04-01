from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate

def oracle_less_than(number:int, nqubits:int, name: str | None = None) -> QuantumCircuit:

    if name:
        circuit = QuantumCircuit(nqubits, name=name)
    else:
        circuit = QuantumCircuit(nqubits, name=f"< {number}")

    num_binary = to_binary(number, nqubits)
    num_binary = num_binary.rstrip("0")  # Eliminar ceros a la izquierda

    if num_binary[0] == "1":
        circuit.x(nqubits-1)
        circuit.z(nqubits-1)
        circuit.x(nqubits-1)
    else:
        circuit.x(nqubits-1)

    # 🔵 BUCLE PRINCIPAL (comparación bit a bit)
    for position1, value in enumerate(num_binary[1:]):
        position = position1 + 1

        if value == '0':
            # Preparar (invertir bit)
            circuit.x(nqubits - position - 1)

        else:
            # 🔥 CASO IMPORTANTE: bit = 1

            # Preparar
            circuit.x(nqubits - position - 1)

            # Aplicar multi-control Z
            multi_z = multi_control_z(position + 1)
            circuit.append(
                multi_z.to_gate(),
                range(nqubits - 1, nqubits - position - 2, -1)
            )

            # Deshacer preparación
            circuit.x(nqubits - position - 1)

    # 🟢 LIMPIEZA FINAL (deshacer X iniciales)
    for position, value in enumerate(num_binary):
        if value == '0':
            circuit.x(nqubits - position - 1)

    return circuit


def multi_control_z(nqubits:int) -> QuantumCircuit:

    '''
    Function to create a multi-controlled Z gate.

    Input:
    nqubits: Integer (int) of the number of qubits in the gate (controls and target)
        This means that the gate has nqubits-1 controls and 1 target.

    Output:
    circuit: QuantumCircuit containing a multi-controlled Z gate.
        It has to be transformed with method .to_gate() to append to a QuantumCircuit larger.

    Example:

    main_circuit = QuantumCircuit(nqubits)

    gate_multi_z = multi_control_z(nqubits)

    main_circuit.append(gate_multi_z.to_gate(), range(nqubits))

    '''

    # Crea un circuito con nqubits y le asigna un nombre que indica que es una puerta MCZ con nqubits
    circuit = QuantumCircuit(nqubits, name = f"MCZ({nqubits})")

    # Aplica una puerta Hadamard al último qubit para preparar el estado de control
    circuit.h(nqubits-1)
    # Esto convertira todos los qubits en controles menos el ultimo que sera el target
    # El objetivo es que si todos los qubits de control son 1, aplicamos NOT al ultimo qubit, lo que equivale a aplicar una puerta Z al estado |1> del ultimo qubit
    circuit.append(MCXGate(nqubits - 1), range (nqubits))
    # Deshacemos cambios en el ultimo qubit para volver a su estado original
    circuit.h(nqubits-1)

    # CAMBIA LA FASE DEL ESTADO OBJETIVO

    return circuit


def to_binary(number:int, nbits: int | None = None) -> str:
    # Convertir el número a binario y eliminar el prefijo '0b'
    binary = bin(number)[2:]  

    # Sin nbits devuelve el binario "natural"
    if nbits is None:
        return binary
    
    if nbits < len(binary):
        raise ValueError(f"nbits must be >= {len(binary)} ")
    
    return binary.zfill(nbits)  # Rellenar con ceros a la izquierda para alcanzar nbits