import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


# =========================
# CARGAR ORÁCULO DESDE QASM
# =========================
def load_oracle(path):
    return QuantumCircuit.from_qasm_file(path)


# =========================
# DETECTAR SOLUCIONES
# =========================
def detect_solutions(oracle_circuit, n):

    solutions = []

    for i in range(2**n):

        state = Statevector.from_int(i, dims=2**n)
        final_state = state.evolve(oracle_circuit)

        amp_in = state.data[i]
        amp_out = final_state.data[i]

        if np.isclose(amp_out, -amp_in):
            solutions.append(i)

    return solutions


# =========================
# VALIDAR ORÁCULO
# =========================
def is_valid_oracle(oracle_circuit, n):

    for i in range(2**n):

        state = Statevector.from_int(i, dims=2**n)
        final_state = state.evolve(oracle_circuit)

        non_zero = np.nonzero(final_state.data)[0]

        # Debe haber solo un estado activo (no mezcla)
        if len(non_zero) != 1:
            return False

    return True


# =========================
# DIFUSOR
# =========================
def diffuser(qc, n):

    qc.h(range(n))
    qc.x(range(n))

    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)

    qc.x(range(n))
    qc.h(range(n))


# =========================
# BASE DE GROVER
# =========================
def build_grover_basis(n, solution_indices):

    N = 2**n

    ket_t = np.zeros(N, dtype=complex)
    for i in solution_indices:
        ket_t[i] = 1

    if np.linalg.norm(ket_t) > 0:
        ket_t /= np.linalg.norm(ket_t)

    ket_r = np.ones(N, dtype=complex)
    for i in solution_indices:
        ket_r[i] = 0

    if np.linalg.norm(ket_r) > 0:
        ket_r /= np.linalg.norm(ket_r)

    return ket_r, ket_t


# =========================
# PROYECCIÓN
# =========================
def project_state(statevector, solution_indices, n):

    amps = statevector.data
    ket_r, ket_t = build_grover_basis(n, solution_indices)

    c_r = np.vdot(ket_r, amps)
    c_t = np.vdot(ket_t, amps)

    if abs(c_r) > 1e-12:
        phase = np.exp(-1j * np.angle(c_r))
        c_r *= phase
        c_t *= phase

    return c_r.real, c_t.real


# =========================
# ITERACIONES ÓPTIMAS
# =========================
def optimal_iterations(n, M):

    N = 2**n

    if M == 0:
        return 0

    return int(np.floor((np.pi / 4) * np.sqrt(N / M)))


# =========================
# ANALIZAR GROVER
# =========================
def analyze_grover(n, oracle_circuit, solution_indices):

    qc = QuantumCircuit(n)

    states = []
    labels = []

    states.append(Statevector.from_instruction(qc))
    labels.append("init")

    qc.h(range(n))
    states.append(Statevector.from_instruction(qc))
    labels.append("|s⟩")

    M = len(solution_indices)
    iterations = optimal_iterations(n, M)

    print("Soluciones detectadas:", solution_indices)
    print("M =", M)
    print("Iteraciones =", iterations)

    for i in range(iterations):

        qc.append(oracle_circuit.to_gate(), range(n))
        states.append(Statevector.from_instruction(qc))
        labels.append(f"O{i+1}")

        diffuser(qc, n)
        states.append(Statevector.from_instruction(qc))
        labels.append(f"D{i+1}")

    return states, labels


# =========================
# PLOT
# =========================
def plot_grover(states, labels, n, solution_indices):

    points = [project_state(s, solution_indices, n) for s in states]

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    plt.figure(figsize=(8, 6))

    plt.axhline(0)
    plt.axvline(0)

    plt.quiver(0, 0, 1, 0, scale=1, scale_units="xy")
    plt.text(1.05, 0, "|r⟩")

    plt.quiver(0, 0, 0, 1, scale=1, scale_units="xy")
    plt.text(0, 1.05, "|t⟩")

    for (x, y), label in zip(points[1:], labels[1:]):

        color = "black"
        if "O" in label:
            color = "red"
        elif "D" in label:
            color = "blue"
        elif label == "|s⟩":
            color = "green"

        plt.quiver(0, 0, x, y, color=color)
        plt.text(x + 0.03, y + 0.03, label)

    plt.plot(xs, ys, "--o")

    plt.title("Grover con oráculo externo")
    plt.axis("equal")
    plt.grid()
    plt.show()


# =========================
# MAIN
# =========================
def main():

    path = "oracle.qasm"

    oracle = load_oracle(path)
    n = oracle.num_qubits

    print("Qubits:", n)

    if not is_valid_oracle(oracle, n):
        print("❌ El circuito NO es un oráculo válido")
        return

    print("✅ Oráculo válido")

    solutions = detect_solutions(oracle, n)

    states, labels = analyze_grover(n, oracle, solutions)

    plot_grover(states, labels, n, solutions)


if __name__ == "__main__":
    main()