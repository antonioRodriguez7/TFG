from qiskit import QuantumCircuit
# Sirve para obtener el estado cuantico completo del circuito en un momento dado, sin medirlo
from qiskit.quantum_info import Statevector
import numpy as np
import matplotlib.pyplot as plt

# Función para mostrar graficamente el estado cuántico en cada paso del algoritmo
def plot_state(state, title):
    # Aquí calculamos las probabilidades de cada estado base (|00>, |01>, |10>, |11>) a partir del vector de estado
    # state.data-> es un array de amplitudes complejas, cada valor es la amplitud de uno de los estados base
    # EJEMPLO: [0.5+0.j, 0.5+0.j, 0.5+0.j, 0.5+0.j]
    # np.abs(state.data)**2 -> convierte las amplitudes complejas en probabilidades reales (módulo al cuadrado, que es el **2)
    probs = np.abs(state.data)**2
    states = ['00','01','10','11']
    #Dibujamos un grafico de barras, que pone los estados 00, 01, 10, 11 en el eje x y sus probabilidades en el eje y
    plt.bar(states, probs)
    plt.title(title)
    # Eje vertical entre 0 y 1
    plt.ylim(0,1)
    plt.show()

# Creamos un circuito con 2 qubits, que es el mínimo para mostrar el algoritmo de Grover (que busca entre 4 elementos)
qc = QuantumCircuit(2)

# -------------------------
# 1. SUPERPOSICIÓN
# -------------------------
qc.h([0,1])
# Guardamos como esta el sistema justo después de la superposicion inicial
state1 = Statevector.from_instruction(qc)
# Dibujamos
plot_state(state1, "Superposición inicial")

# -------------------------
# 2. ORACLE (marca |11>)
# -------------------------
# Aplicamos una puerta CZ, que es una puerta de control que solo afecta al estado |11>, cambiando su fase (lo que hace que su amplitud se vuelva negativa)
qc.cz(0,1)

# -------------------------
# 2. ORACLE (marca |00>)
# -------------------------
# qc.x([0,1]) Antes de la 'cz' aplicamos la puerta 'x' a ambos qubits, |00>->X->|11>
# qc.cz(0,1)  Ahora marcamos el estado |11>
# qc.x([0,1]) Deshacemos con la puerta 'x' pasando de nuevo |11>->X->|00>

# -------------------------
# 2. ORACLE (marca |01>)
# -------------------------
# qc.x(0) Aplicamos la puerta 'x' al qubit 0, |01>->X->|11>
# qc.cz(0,1)  Ahora marcamos el estado |11>
# qc.x(0) Deshacemos con la puerta 'x' pasando de nuevo |11>->X->|01>

# -------------------------
# 2. ORACLE (marca |10>)
# -------------------------
# qc.x(1) Aplicamos la puerta 'x' al qubit 1, |10>->X->|11>
# qc.cz(0,1)  Ahora marcamos el estado |11>
# qc.x(1) Deshacemos con la puerta 'x' pasando de nuevo |11>->X->|10>
state2 = Statevector.from_instruction(qc)
plot_state(state2, "Después del oracle")

# -------------------------
# 3. DIFFUSION
# -------------------------
qc.h([0,1])
qc.x([0,1])
qc.cz(0,1)
qc.x([0,1])
qc.h([0,1])

state3 = Statevector.from_instruction(qc)
plot_state(state3, "Después de Grover")

print("Estado 1:", state1)
print("Estado 2:", state2)
print("Estado 3:", state3)