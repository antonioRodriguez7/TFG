from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
import numpy as np
import matplotlib.pyplot as plt

# -------------------------
# 1. CREAR GROVER SIMPLE
# -------------------------
def create_grover_circuit():
    qc = QuantumCircuit(2)

    qc.h([0,1])
    qc.cz(0,1)

    qc.h([0,1])
    qc.x([0,1])
    qc.cz(0,1)
    qc.x([0,1])
    qc.h([0,1])

    return qc

# -------------------------
# 2. OBTENER ESTADOS
# -------------------------
def get_states():
    qc = QuantumCircuit(2)

    states = []

    qc.h([0,1])
    states.append(Statevector.from_instruction(qc))

    qc.cz(0,1)
    states.append(Statevector.from_instruction(qc))

    qc.h([0,1])
    qc.x([0,1])
    qc.cz(0,1)
    qc.x([0,1])
    qc.h([0,1])
    states.append(Statevector.from_instruction(qc))

    return states

# -------------------------
# 3. VISUALIZACIÓN BARRAS
# -------------------------
def plot_states(states):
    labels = ["Inicial", "Oracle", "Final"]
    basis = ['00','01','10','11']

    plt.figure(figsize=(12,4))

    for i, state in enumerate(states):
        probs = np.abs(state.data)**2

        plt.subplot(1,3,i+1)
        plt.bar(basis, probs)
        plt.title(labels[i])
        plt.ylim(0,1)

    plt.show()

# -------------------------
# 4. COORDENADAS 2D (MEJORADAS)
# -------------------------
def get_2d_coords(state, solution_index):
    amplitudes = state.data

    # 🔥 IMPORTANTE: usamos parte real (NO abs)
    w = np.real(amplitudes[solution_index])

    rest = np.delete(amplitudes, solution_index)
    s = np.linalg.norm(rest)

    return w, s

# -------------------------
# 5. VISUALIZACIÓN 2D (MEJORADA)
# -------------------------
def plot_2d_vectors(coords):
    plt.figure(figsize=(6,6))

    colors = ['blue', 'orange', 'green']
    labels = ['Inicial', 'Oracle', 'Final']

    for i, (x, y) in enumerate(coords):

        # Flecha
        plt.arrow(0, 0, x, y,
                  head_width=0.04,
                  length_includes_head=True,
                  color=colors[i],
                  alpha=0.8)

        # Punto
        plt.scatter(x, y, color=colors[i])

        # Texto (evita que se pisen)
        plt.text(x + 0.03, y + 0.05*i, labels[i], fontsize=11)

    plt.axhline(0)
    plt.axvline(0)

    plt.xlim(-1.1, 1.1)
    plt.ylim(0, 1.1)

    plt.xlabel("Solución (|w⟩)")
    plt.ylabel("Resto (|s⟩)")
    plt.title("Evolución de Grover en 2D (con fase)")

    plt.grid()
    plt.show()

# -------------------------
# MAIN
# -------------------------
states = get_states()

plot_states(states)

coords = [get_2d_coords(s, 3) for s in states]

for i, c in enumerate(coords):
    print(f"Estado {i}: solución={c[0]:.3f}, resto={c[1]:.3f}")

plot_2d_vectors(coords)