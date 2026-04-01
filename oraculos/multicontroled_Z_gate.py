from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate

# THE MULTICONTROLLED Z GATE

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

nqubits = 3
circuit = multi_control_z(nqubits)
print(circuit.draw())

