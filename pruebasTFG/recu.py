from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
import numpy as np
import matplotlib.pyplot as plt
from qiskit.circuit.library import MCXGate
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from qiskit.qasm2 import loads, LEGACY_CUSTOM_INSTRUCTIONS

# =========================
# ORÁCULOS REALES
# =========================

def mark_one(number, nqubits, name=None):
    if isinstance(number, str):
        binary = number.zfill(nqubits)
    else:
        binary = format(number, f"0{nqubits}b")

    circuit = QuantumCircuit(nqubits, name=name if name else f"== {number}")

    for i, bit in enumerate(reversed(binary)):
        if bit == '0':
            circuit.x(i)

    circuit.h(nqubits - 1)
    circuit.mcx(list(range(nqubits - 1)), nqubits - 1)
    circuit.h(nqubits - 1)

    for i, bit in enumerate(reversed(binary)):
        if bit == '0':
            circuit.x(i)

    return circuit


def to_binary(number: int, nbits: int | None = None) -> str:
    binary = bin(number)[2:]
    if nbits is None:
        return binary
    if nbits < len(binary):
        raise ValueError(f"nbits must be >= {len(binary)}")
    return binary.zfill(nbits)


def multi_control_z(nqubits: int) -> QuantumCircuit:
    circuit = QuantumCircuit(nqubits, name=f"MCZ({nqubits})")
    circuit.h(nqubits - 1)
    circuit.append(MCXGate(nqubits - 1), range(nqubits))
    circuit.h(nqubits - 1)
    return circuit


def oracle_less(number: int, nqubits: int, name=None):
    circuit = QuantumCircuit(nqubits, name=name if name else f"< {number}")
    num_binary = to_binary(number, nqubits)

    if num_binary[0] == "1":
        circuit.x(nqubits - 1)
        circuit.z(nqubits - 1)
        circuit.x(nqubits - 1)
    else:
        circuit.x(nqubits - 1)

    for position1, value in enumerate(num_binary[1:]):
        position = position1 + 1

        if value == '0':
            circuit.x(nqubits - position - 1)
        else:
            circuit.x(nqubits - position - 1)

            multi_z = multi_control_z(position + 1)
            circuit.append(
                multi_z.to_gate(),
                list(range(nqubits - 1, nqubits - position - 2, -1))
            )

            circuit.x(nqubits - position - 1)

    for position, value in enumerate(num_binary):
        if value == '0':
            circuit.x(nqubits - position - 1)

    return circuit


def oracle_greater(number, nqubits, name=None):
    if isinstance(number, str):
        number = int(number, 2)

    circuit = QuantumCircuit(nqubits, name=name if name else f"> {number}")

    if number < (2**nqubits):
        number = number + 1

    less_than = oracle_less(number, nqubits)
    circuit.append(less_than.to_gate(), list(range(nqubits)))
    circuit.global_phase += np.pi

    return circuit


# =========================
# DIFUSOR
# =========================

def diffuser(qc, n):
    qc.h(range(n))
    qc.x(range(n))

    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1, mode="noancilla")
    qc.h(n - 1)

    qc.x(range(n))
    qc.h(range(n))


# =========================
# ESTADO
# =========================

def get_state(qc):
    return Statevector.from_instruction(qc)


# =========================
# BASE DE GROVER
# =========================

def build_grover_basis(n, solution_indices):
    N = 2**n

    ket_t = np.zeros(N, dtype=complex)
    for index in solution_indices:
        ket_t[index] = 1.0
    if np.linalg.norm(ket_t) > 1e-12:
        ket_t /= np.linalg.norm(ket_t)

    ket_r = np.ones(N, dtype=complex)
    for index in solution_indices:
        ket_r[index] = 0.0
    if np.linalg.norm(ket_r) > 1e-12:
        ket_r /= np.linalg.norm(ket_r)

    return ket_r, ket_t


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
# SOLUCIONES
# =========================

def get_solution_indices(choice, number, n):
    N = 2**n

    if choice == "one":
        return [number]
    elif choice == "less":
        return list(range(number))
    elif choice == "greater":
        return list(range(number + 1, N))

    return []


def optimal_iterations(n, M):
    N = 2**n
    if M == 0:
        return 0
    return int(np.floor((np.pi / 4) * np.sqrt(N / M)))


# =========================
# VISUALIZACIÓN
# =========================

def plot_grover_step_by_step(states, labels, n, solutions):
    if len(states) < 4:
        print("No hay suficientes estados para representar.")
        return

    num_plots = (len(states) - 2) // 2
    fig, axes = plt.subplots(1, num_plots, figsize=(5 * num_plots, 5))

    if num_plots == 1:
        axes = [axes]

    plot_idx = 0

    for k in range(4, len(states) + 1, 2):
        ax = axes[plot_idx]
        plot_idx += 1

        partial_states = states[:k]
        partial_labels = labels[:k]

        points = [project_state(s, solutions, n) for s in partial_states]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        ax.axhline(0, linewidth=1.2)
        ax.axvline(0, linewidth=1.2)

        ax.quiver(0, 0, 1, 0, angles="xy", scale_units="xy", scale=1, linestyle='dashed', color="black")
        ax.text(1.05, 0, "|r⟩", fontsize=12)

        ax.quiver(0, 0, 0, 1, angles="xy", scale_units="xy", scale=1, linestyle='dashed', color="black")
        ax.text(0, 1.05, "|t⟩", fontsize=12)

        for (x, y), label in zip(points[1:], partial_labels[1:]):
            color = "black"
            if "O" in label:
                color = "red"
            elif "D" in label:
                color = "blue"
            elif label == "|s⟩":
                color = "green"

            ax.quiver(0, 0, x, y, angles="xy", scale_units="xy", scale=1, color=color, width=0.006, alpha=0.85)
            ax.text(x + 0.04, y + 0.04, label, fontsize=9)

        ax.plot(xs, ys, linestyle="--", linewidth=2, marker="o", color="gray")

        iteracion = (k // 2) - 1
        ax.set_title(f"Iter {iteracion}")
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)
        ax.set_aspect('equal')
        ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.show()


# =========================
# ANALIZAR GROVER REAL
# =========================

def analyze_grover(n, number, choice):
    qc = QuantumCircuit(n)

    states = []
    labels = []

    state = get_state(qc)
    print("\n--- Estado inicial |0...0⟩ ---")
    print(state)
    states.append(state)
    labels.append("init")

    qc.h(range(n))
    state = get_state(qc)
    print("\n--- Estado |s⟩ ---")
    print(state)
    states.append(state)
    labels.append("|s⟩")

    if choice == "one":
        oracle_circuit = mark_one(number, n)
        oracle_label = f"== {number}"
    elif choice == "less":
        oracle_circuit = oracle_less(number, n)
        oracle_label = f"< {number}"
    elif choice == "greater":
        oracle_circuit = oracle_greater(number, n)
        oracle_label = f"> {number}"
    else:
        print("Tipo de oráculo no soportado")
        return [], []

    solutions = get_solution_indices(choice, number, n)
    M = len(solutions)

    print("\nNúmero de soluciones (M):", M)

    iterations = optimal_iterations(n, M)
    print("Número de iteraciones:", iterations)

    if iterations == 0:
        print("No hay iteraciones interesantes")
        return [], []

    for i in range(iterations):
        qc.append(oracle_circuit.to_gate(), list(range(n)))
        state = get_state(qc)
        print(f"\n--- Estado tras Oráculo {i+1} ({oracle_label}) ---")
        print(state)
        states.append(state)
        labels.append(rf"$O_{{{i+1}}}$")

        diffuser(qc, n)
        state = get_state(qc)
        print(f"\n--- Estado tras Difusor {i+1} ---")
        print(state)
        states.append(state)
        labels.append(rf"$D_{{{i+1}}}$")

    return states, labels


# =========================
# UTILIDADES DE ANÁLISIS DEL QASM
# =========================

def qindex(q):
    if hasattr(q, "_index"):
        return q._index
    return q.index


def cargar_circuito(path):
    with open(path, "r") as f:
        return loads(
            f.read(),
            custom_instructions=LEGACY_CUSTOM_INSTRUCTIONS
        )


def pedir_numero_valido(n):
    root = tk.Tk()
    root.withdraw()

    max_val = 2**n - 1

    while True:
        numero = simpledialog.askinteger(
            "Entrada",
            f"Introduce la solución (0 - {max_val}):"
        )

        if numero is None:
            return None

        if 0 <= numero <= max_val:
            return numero
        else:
            messagebox.showerror("Error", f"Número fuera de rango (0 - {max_val})")


def es_capa_h_inicial(qc):
    n = qc.num_qubits
    if len(qc.data) < n:
        return False

    primeras = qc.data[:n]
    if not all(instr.operation.name == "h" for instr in primeras):
        return False

    qubits = [qindex(instr.qubits[0]) for instr in primeras]
    return sorted(qubits) == list(range(n))


def detectar_inicio_difusor(qc):
    ops = qc.data
    n = qc.num_qubits
    total = len(ops)

    for i in range(n, total):
        if i + 2*n + 3 > total:
            break

        bloque_h = ops[i:i+n]
        bloque_x = ops[i+n:i+2*n]

        if not all(instr.operation.name == "h" for instr in bloque_h):
            continue
        if not all(instr.operation.name == "x" for instr in bloque_x):
            continue

        qubits_h = sorted(qindex(instr.qubits[0]) for instr in bloque_h)
        qubits_x = sorted(qindex(instr.qubits[0]) for instr in bloque_x)

        if qubits_h != list(range(n)) or qubits_x != list(range(n)):
            continue

        return i

    return None


def extraer_bloque_oraculo(qc):
    if not es_capa_h_inicial(qc):
        return None

    inicio_difusor = detectar_inicio_difusor(qc)
    if inicio_difusor is None:
        return None

    n = qc.num_qubits
    oracle_ops = qc.data[n:inicio_difusor]

    oracle_qc = QuantumCircuit(n)
    for instr in oracle_ops:
        qargs = [qindex(q) for q in instr.qubits]
        cargs = []
        oracle_qc.append(instr.operation, qargs, cargs)

    return oracle_qc


def es_patron_equal(oracle_qc):
    ops = oracle_qc.data
    if len(ops) != 3:
        return False

    n1 = ops[0].operation.name
    n2 = ops[1].operation.name
    n3 = ops[2].operation.name

    if n1 != "h" or n3 != "h":
        return False

    if n2 not in ("ccx", "mcx"):
        return False

    t1 = qindex(ops[0].qubits[0])
    t3 = qindex(ops[2].qubits[0])

    if t1 != t3:
        return False

    return True


def es_patron_less(oracle_qc):
    ops = oracle_qc.data
    if len(ops) != 3:
        return False

    n1 = ops[0].operation.name
    n2 = ops[1].operation.name
    n3 = ops[2].operation.name

    if n1 != "x" or n3 != "x":
        return False

    if n2 not in ("ccx", "mcx"):
        return False

    t1 = qindex(ops[0].qubits[0])
    t3 = qindex(ops[2].qubits[0])

    if t1 != t3:
        return False

    return True


def detectar_tipo_oraculo_desde_qasm(qc):
    oracle_qc = extraer_bloque_oraculo(qc)
    if oracle_qc is None:
        return None

    ops = oracle_qc.data

    if len(ops) != 3:
        return None

    n1 = ops[0].operation.name
    n2 = ops[1].operation.name
    n3 = ops[2].operation.name

    if n2 not in ("ccx", "mcx"):
        return None

    if n1 == "h" and n3 == "h":
        return "one"

    if n1 == "x" and n3 == "x":
        return "less"

    if n1 == "z" and n3 == "z":
        return "greater"

    return None

def obtener_parametros_desde_qasm():
    root = tk.Tk()
    root.withdraw()
    root.update()

    path = filedialog.askopenfilename(
        title="Selecciona un circuito Grover (.qasm)",
        filetypes=[("Archivos QASM", "*.qasm")]
    )

    root.destroy()

    if not path:
        print("No se seleccionó archivo")
        return None

    qc = cargar_circuito(path)
    n = qc.num_qubits

    if not es_capa_h_inicial(qc):
        print("El circuito no empieza con una superposición uniforme de Grover")
        return None

    if detectar_inicio_difusor(qc) is None:
        print("No se ha detectado un difusor con estructura de Grover")
        return None

    number = pedir_numero_valido(n)
    if number is None:
        print("Entrada cancelada")
        return None

    choice = detectar_tipo_oraculo_desde_qasm(qc)
    if choice is None:
        print("No se pudo detectar el tipo de oráculo")
        print("Ahora mismo solo detecto patrones estructurales diferenciables")
        return None

    print("Número de qubits:", n)
    print("Tipo detectado:", choice)
    print("Número introducido:", number)

    return n, number, choice


# =========================
# MAIN
# =========================

def main():
    params = obtener_parametros_desde_qasm()

    if params is None:
        return

    n, number, choice = params

    states, labels = analyze_grover(n, number, choice)

    if not states:
        print("No hay estados para graficar.")
        return

    solutions = get_solution_indices(choice, number, n)
    plot_grover_step_by_step(states, labels, n, solutions)


if __name__ == "__main__":
    main()