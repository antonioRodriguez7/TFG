from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
import numpy as np
import matplotlib.pyplot as plt

# Pasamos 4 parametros:
# state: el vector de estado cuántico que queremos graficar
# title: el título que queremos ponerle a la gráfica
# pos: la posición de la gráfica dentro de la figura (1, 2, 3, etc.)
# total: el número total de gráficas que vamos a mostrar (para organizar el layout)
def plot_state(state, title, pos, total):
    probs = np.abs(state.data)**2
    states = ['000', '001', '010', '011', '100', '101', '110', '111']
    
    plt.subplot(1, total, pos)
    plt.bar(states, probs)
    plt.title(title)
    plt.ylim(0, 1)
    plt.xticks(rotation=45)

qc = QuantumCircuit(3)

# -------------------------
# 1. SUPERPOSICIÓN
# -------------------------
qc.h([0, 1, 2])
state1 = Statevector.from_instruction(qc)

# -------------------------
# ITERACIÓN 1
# -------------------------

# ORACLE (marca |101>)
# ESTO ACTUA COMO UNA CCZ
# qc.h(2)           
# qc.ccx(0, 1, 2)  
# qc.h(2)
qc.x(1)          # Antes de la 'ccx' aplicamos la puerta 'x' al qubit 1, |101>->X->|111>
qc.h(2)          # Aplicamos la puerta 'h' al qubit 2 para preparar el estado de control para la 'ccx'
qc.ccx(0, 1, 2)  # "si qubit 0 es 1 y qubit 1 es 1, entonces aplica una 'x' al qubit 2", lo que marca el estado |111>
qc.h(2)          # Deshacemos la preparación del estado de control con otra 'h'
qc.x(1)          # Deshacemos la puerta 'x' al qubit 1 pasando de nuevo |111>->X->|101>

state2 = Statevector.from_instruction(qc)

# DIFUSOR
qc.h([0, 1, 2])
qc.x([0, 1, 2])

qc.h(2)
qc.ccx(0, 1, 2)
qc.h(2)

qc.x([0, 1, 2])
qc.h([0, 1, 2])

state3 = Statevector.from_instruction(qc)

# -------------------------
# ITERACIÓN 2
# -------------------------

# ORACLE otra vez
qc.x(1)
qc.h(2)
qc.ccx(0, 1, 2)
qc.h(2)
qc.x(1)

state4 = Statevector.from_instruction(qc)

# DIFUSOR otra vez
qc.h([0, 1, 2])
qc.x([0, 1, 2])

qc.h(2)
qc.ccx(0, 1, 2)
qc.h(2)

qc.x([0, 1, 2])
qc.h([0, 1, 2])

state5 = Statevector.from_instruction(qc)

# -------------------------
# PRINTS (amplitudes)
# -------------------------
print("Estado 1 (Inicial):")
print(np.round(state1.data, 3))

print("\nEstado 2 (Después del oracle 1):")
print(np.round(state2.data, 3))

print("\nEstado 3 (Después iteración 1):")
print(np.round(state3.data, 3))

print("\nEstado 4 (Después del oracle 2):")
print(np.round(state4.data, 3))

print("\nEstado 5 (Después iteración 2):")
print(np.round(state5.data, 3))

# -------------------------
# GRÁFICAS
# -------------------------
plt.figure(figsize=(20, 4))

plot_state(state1, "Inicial", 1, 5)
plot_state(state2, "Oracle 1", 2, 5)
plot_state(state3, "Iteración 1", 3, 5)
plot_state(state4, "Oracle 2", 4, 5)
plot_state(state5, "Iteración 2", 5, 5)

plt.tight_layout()
plt.show()