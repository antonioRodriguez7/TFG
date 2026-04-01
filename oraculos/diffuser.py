from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate

# LO MAS IMPORTANTE QUE DEBEMOS SABER ES QUE PODEMOS TENER CUALQUIER ESTADO COMO OBJETIVO, PERO SEA CUAL SEA HAY QUE CONVETIRLO EN 1...1
# Y ESE SIEMPRE SE MARCA CON Z PARA CAMBIARLE LA FASE, Y LUEGO YA SE DESHACE TODO.
def diffuser_circuit(nqubits:int) -> QuantumCircuit:

    circuit = QuantumCircuit(nqubits,name=f"Diffuser({nqubits})")

    for qb in range(nqubits):
        # Pasamos todo a base de superposicion
        circuit.h(qb) 
        # La X cambia 0 por 1 y 1 por 0º
        circuit.x(qb)
    
    # Por ejemplo depues de aplicar X a 000 pasamos a 111 y al aplicar Z tenemos -111
    # es una forma de marcar un estado
    multi_z = multi_control_z(nqubits)
    circuit.append(multi_z.to_gate(), range(nqubits-1,-1,-1))

    # Deshacemos todo
    for qb in range(nqubits):
        circuit.h(qb)
        circuit.x(qb)

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

nqubits = 7
diffuser = diffuser_circuit(nqubits)
print(diffuser.draw())
