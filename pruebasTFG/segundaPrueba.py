from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.circuit.library import MCXGate
from qiskit.qasm2 import loads, LEGACY_CUSTOM_INSTRUCTIONS

import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox

import math
import json
import os
import sys
import subprocess

# #########################
# CONFIGURACION
# #########################

GENERAR_GRAFICAS = True
GENERAR_VIDEO_MANIM = True

MANIM_QUALITY = "-pql"   # -pql, -pqm, -pqh
MANIM_DATA_FILE = "grover_manim_data.json"

try:
    from manim import *
    MANIM_AVAILABLE = True
except ImportError:
    MANIM_AVAILABLE = False


# #########################
# ESCENA MANIM
# #########################

if MANIM_AVAILABLE:
    class GroverScene(Scene):
        def construct(self):
            if not os.path.exists(MANIM_DATA_FILE):
                raise FileNotFoundError(f"No existe {MANIM_DATA_FILE}")

            with open(MANIM_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            points = data["points"]
            labels = data["labels"]
            title_text = data["title"]
            iterations = data["iterations"]

            plane = NumberPlane(
                x_range=[-1.2, 1.2, 0.5],
                y_range=[-1.2, 1.2, 0.5],
                x_length=8,
                y_length=8,
                background_line_style={"stroke_opacity": 0.25}
            )

            origin = plane.c2p(0, 0)

            title = Text(title_text, font_size=28).to_edge(UP)
            self.play(Write(title))
            self.play(Create(plane))

            eje_r = Arrow(origin, plane.c2p(1, 0), buff=0, color=WHITE)
            eje_t = Arrow(origin, plane.c2p(0, 1), buff=0, color=WHITE)

            label_r = Text("|r>", font_size=24).next_to(plane.c2p(1, 0), RIGHT, buff=0.12)
            label_t = Text("|t>", font_size=24).next_to(plane.c2p(0, 1), UP, buff=0.12)

            self.play(Create(eje_r), Create(eje_t), Write(label_r), Write(label_t))

            legend_1 = Text("Verde: estado de partida", font_size=20).to_corner(UL).shift(DOWN * 0.8)
            legend_2 = Text("Rojo: oraculo", font_size=20).next_to(legend_1, DOWN, aligned_edge=LEFT)
            legend_3 = Text("Azul: difusor", font_size=20).next_to(legend_2, DOWN, aligned_edge=LEFT)

            self.play(Write(legend_1), Write(legend_2), Write(legend_3))

            current_group = None
            current_iter_text = None

            for i in range(1, iterations + 1):
                start_idx = 1 if i == 1 else 2 * i - 1
                oracle_idx = 2 * i
                diffuser_idx = 2 * i + 1

                start_x, start_y = points[start_idx]
                oracle_x, oracle_y = points[oracle_idx]
                diff_x, diff_y = points[diffuser_idx]

                start_label = labels[start_idx]
                oracle_label = labels[oracle_idx]
                diff_label = labels[diffuser_idx]

                start_p = plane.c2p(start_x, start_y)
                oracle_p = plane.c2p(oracle_x, oracle_y)
                diff_p = plane.c2p(diff_x, diff_y)

                start_arrow = Arrow(origin, start_p, buff=0, color=GREEN, stroke_width=6)
                oracle_arrow = Arrow(origin, oracle_p, buff=0, color=RED, stroke_width=6)
                diff_arrow = Arrow(origin, diff_p, buff=0, color=BLUE, stroke_width=6)

                start_dot = Dot(start_p, color=GREEN, radius=0.05)
                oracle_dot = Dot(oracle_p, color=RED, radius=0.05)
                diff_dot = Dot(diff_p, color=BLUE, radius=0.05)

                start_text = Text(start_label, font_size=20).next_to(start_p, UR, buff=0.08)
                oracle_text = Text(oracle_label, font_size=20).next_to(oracle_p, UR, buff=0.08)
                diff_text = Text(diff_label, font_size=20).next_to(diff_p, UR, buff=0.08)

                seg_oracle = DashedLine(start_p, oracle_p, color=RED)
                seg_diff = DashedLine(oracle_p, diff_p, color=BLUE)

                iter_text = Text(f"Iteracion {i}", font_size=24).to_edge(DOWN)

                group = VGroup(
                    start_arrow, start_dot, start_text,
                    oracle_arrow, oracle_dot, oracle_text,
                    diff_arrow, diff_dot, diff_text,
                    seg_oracle, seg_diff
                )

                if current_group is not None:
                    self.play(FadeOut(current_group), FadeOut(current_iter_text), run_time=0.5)

                self.play(FadeIn(iter_text), run_time=0.3)
                self.play(Create(start_arrow), FadeIn(start_dot), Write(start_text), run_time=0.8)
                self.wait(0.35)
                self.play(Create(oracle_arrow), FadeIn(oracle_dot), Write(oracle_text), Create(seg_oracle), run_time=0.8)
                self.wait(0.35)
                self.play(Create(diff_arrow), FadeIn(diff_dot), Write(diff_text), Create(seg_diff), run_time=0.8)
                self.wait(1.0)

                current_group = group
                current_iter_text = iter_text

            self.wait(2)


# #########################
# ORACULOS REALES
# #########################

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
    circuit.append(MCXGate(nqubits - 1), list(range(nqubits)))
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


# #########################
# DIFUSOR
# #########################

def diffuser(qc, n):
    qc.h(range(n))
    qc.x(range(n))

    qc.h(n - 1)
    qc.append(MCXGate(n - 1), list(range(n)))
    qc.h(n - 1)

    qc.x(range(n))
    qc.h(range(n))


# #########################
# ESTADO
# #########################
def get_state(qc):
    return Statevector.from_instruction(qc)


# #########################
# BASE DE GROVER
# #########################
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


# #########################
# SOLUCIONES
# #########################
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


# #########################
# GRAFICAS ESTATICAS
# #########################


def draw_iteration_subplot(ax, points, labels, iteration_number):
    start_idx = 1 if iteration_number == 1 else 2 * iteration_number - 1
    oracle_idx = 2 * iteration_number
    diffuser_idx = 2 * iteration_number + 1

    x_start, y_start = points[start_idx]
    x_oracle, y_oracle = points[oracle_idx]
    x_diff, y_diff = points[diffuser_idx]

    label_start = labels[start_idx]
    label_oracle = labels[oracle_idx]
    label_diff = labels[diffuser_idx]

    ax.axhline(0, linewidth=1.2, color="black")
    ax.axvline(0, linewidth=1.2, color="black")

    ax.quiver(0, 0, 1, 0, angles="xy", scale_units="xy", scale=1,
              linestyle='dashed', color="black")
    ax.text(1.05, 0, "|r>", fontsize=11)

    ax.quiver(0, 0, 0, 1, angles="xy", scale_units="xy", scale=1,
              linestyle='dashed', color="black")
    ax.text(0, 1.05, "|t>", fontsize=11)

    # Flecha de partida
    ax.quiver(0, 0, x_start, y_start, angles="xy", scale_units="xy", scale=1,
              color="green", width=0.006, alpha=0.9)
    ax.scatter([x_start], [y_start], color="green", s=35)
    ax.text(x_start + 0.03, y_start + 0.03, label_start, fontsize=9, color="green")

    # Flecha oraculo
    ax.quiver(0, 0, x_oracle, y_oracle, angles="xy", scale_units="xy", scale=1,
              color="red", width=0.006, alpha=0.9)
    ax.scatter([x_oracle], [y_oracle], color="red", s=35)
    ax.text(x_oracle + 0.03, y_oracle + 0.03, label_oracle, fontsize=9, color="red")

    # Flecha difusor
    ax.quiver(0, 0, x_diff, y_diff, angles="xy", scale_units="xy", scale=1,
              color="blue", width=0.006, alpha=0.9)
    ax.scatter([x_diff], [y_diff], color="blue", s=35)
    ax.text(x_diff + 0.03, y_diff + 0.03, label_diff, fontsize=9, color="blue")

    # Segmentos de la reflexion de esta iteracion
    ax.plot([x_start, x_oracle], [y_start, y_oracle], linestyle="--", linewidth=1.8, color="red", alpha=0.8)
    ax.plot([x_oracle, x_diff], [y_oracle, y_diff], linestyle="--", linewidth=1.8, color="blue", alpha=0.8)

    ax.set_title(f"Iteracion {iteration_number}", fontsize=12)
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)


def plot_grover_by_iteration(states, labels, n, solutions, choice, number):
    iterations = (len(states) - 2) // 2

    if iterations <= 0:
        print("No hay iteraciones para representar.")
        return

    points = [project_state(s, solutions, n) for s in states]

    ncols = min(3, iterations)
    nrows = math.ceil(iterations / 3)

    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 6 * nrows))

    if isinstance(axes, np.ndarray):
        axes = axes.ravel()
    else:
        axes = [axes]

    for i in range(1, iterations + 1):
        draw_iteration_subplot(axes[i - 1], points, labels, i)

    for j in range(iterations, len(axes)):
        axes[j].axis("off")

    fig.suptitle(
        f"Evolucion de Grover por iteraciones | tipo={choice}, numero={number}, qubits={n}",
        fontsize=15
    )

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()


# #########################
# EXPORTAR DATOS PARA MANIM
# #########################

def exportar_datos_manim(states, labels, n, solutions, choice, number):
    points = [project_state(s, solutions, n) for s in states]
    iterations = (len(states) - 2) // 2

    data = {
        "points": [[float(x), float(y)] for x, y in points],
        "labels": labels,
        "iterations": iterations,
        "title": f"Grover: tipo={choice}, numero={number}, qubits={n}"
    }

    with open(MANIM_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def renderizar_con_manim():
    if not MANIM_AVAILABLE:
        print("Manim no está instalado.")
        print("Instalalo con: pip install manim")
        return

    comando = [sys.executable, "-m", "manim", MANIM_QUALITY, __file__, "GroverScene"]
    subprocess.run(comando)


# #########################
# ANALIZAR GROVER
# #########################

def analyze_grover(n, number, choice):
    qc = QuantumCircuit(n)

    states = []
    labels = []

    state = get_state(qc)
    print("\n--- Estado inicial |0...0> ---")
    print(state)
    states.append(state)
    labels.append("init")

    qc.h(range(n))
    state = get_state(qc)
    print("\n--- Estado |s> ---")
    print(state)
    states.append(state)
    labels.append("|s>")

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
        print("Tipo de oraculo no soportado")
        return [], []

    solutions = get_solution_indices(choice, number, n)
    M = len(solutions)

    print("\nNumero de soluciones (M):", M)
    print("Soluciones:", solutions)

    iterations = optimal_iterations(n, M)
    print("Numero de iteraciones:", iterations)

    if iterations == 0:
        print("No hay iteraciones interesantes")
        return [], []

    for i in range(iterations):
        qc.append(oracle_circuit.to_gate(), list(range(n)))
        state = get_state(qc)
        print(f"\n--- Estado tras Oraculo {i+1} ({oracle_label}) ---")
        print(state)
        states.append(state)
        labels.append(f"O_{i+1}")

        diffuser(qc, n)
        state = get_state(qc)
        print(f"\n--- Estado tras Difusor {i+1} ---")
        print(state)
        states.append(state)
        labels.append(f"D_{i+1}")

    return states, labels


# #########################
# UTILIDADES DE ANALISIS DEL QASM
# #########################

def qindex(q):
    if hasattr(q, "_index"):
        return q._index
    return q.index

# Convertimos nuestro circuito QASM a QuantumCircuit de Qiskit para analizarlo
def cargar_circuito(path):
    with open(path, "r") as f:
        return loads(
            f.read(),
            custom_instructions=LEGACY_CUSTOM_INSTRUCTIONS
        )

# Pedimos al usuario que introduzca un numero valido para el tipo de oraculo detectado
def pedir_numero_valido(n):
    root = tk.Tk()
    root.withdraw()

    max_val = 2**n - 1

    while True:
        numero = simpledialog.askinteger(
            "Entrada",
            f"Introduce la solucion (0 - {max_val}):"
        )

        if numero is None:
            return None

        if 0 <= numero <= max_val:
            return numero
        else:
            messagebox.showerror("Error", f"Numero fuera de rango (0 - {max_val})")

# Comprobamos que todos los qubits empiezan con una puerta Hadamart
def es_capa_h_inicial(qc):
    n = qc.num_qubits
    if len(qc.data) < n:
        return False

    primeras = qc.data[:n]
    # Aqui comprobamos que todas las primeras n sean puertas h
    if not all(instr.operation.name == "h" for instr in primeras):
        return False

    qubits = [qindex(instr.qubits[0]) for instr in primeras]
    return sorted(qubits) == list(range(n))

# Este metodo tiene como objetivo detectar un patrón de inicio de difusor
def detectar_inicio_difusor(qc):
    # Sacamos el numero de operaciones del circuito
    ops = qc.data
    n = qc.num_qubits
    total = len(ops)

    for i in range(n, total):
        if i + 2 * n + 3 > total:
            break

        bloque_h = ops[i:i+n]
        bloque_x = ops[i+n:i+2*n]

        # Reccoremos todo el circuito buscando en cada posición si hay n Hadamartas seguidas de n puertas X,
        # tras esto comprobamos que actuan sobre todos los qubits, y si lo encuentro devuelve la posicion de inicio
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

# Este metodo se encarga de extraer el bloque de operaciones que corresponde al oraculo
def extraer_bloque_oraculo(qc):
    if not es_capa_h_inicial(qc):
        return None

    inicio_difusor = detectar_inicio_difusor(qc)
    if inicio_difusor is None:
        return None

    n = qc.num_qubits
    # Cogemos la informacion desde n hasta el inicio del difusor
    oracle_ops = qc.data[n:inicio_difusor]

    oracle_qc = QuantumCircuit(n)
    for instr in oracle_ops:
        # Recorremos indices de los qubits sobre los tu actua la instruccion
        qargs = [qindex(q) for q in instr.qubits]
        # Aniadimos la instruccion al circuito del oraculo con los qubits corregidos
        oracle_qc.append(instr.operation, qargs, [])

    return oracle_qc

# Detectamos que tipo de oraculo tenemos
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

    # Abrimos explorador de archivos para seleccionar el circuito QASM
    path = filedialog.askopenfilename(
        title="Selecciona un circuito Grover (.qasm)",
        filetypes=[("Archivos QASM", "*.qasm")]
    )

    root.destroy()

    if not path:
        print("No se selecciono archivo")
        return None

    qc = cargar_circuito(path)
    n = qc.num_qubits

    # Comprobamos que el circuito empieza con una capa de Hadamards (superposicion uniforme)
    if not es_capa_h_inicial(qc):
        print("El circuito no empieza con una superposicion uniforme de Grover")
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
        print("No se pudo detectar el tipo de oraculo")
        return None

    print("Numero de qubits:", n)
    print("Tipo detectado:", choice)
    print("Numero introducido:", number)

    return n, number, choice


# #########################
# MAIN
# #########################

def main():
    params = obtener_parametros_desde_qasm()

    if params is None:
        return

    n, number, choice = params

    states, labels = analyze_grover(n, number, choice)

    if not states:
        print("No hay estados para representar.")
        return

    solutions = get_solution_indices(choice, number, n)

    if GENERAR_GRAFICAS:
        plot_grover_by_iteration(states, labels, n, solutions, choice, number)

    if GENERAR_VIDEO_MANIM:
        exportar_datos_manim(states, labels, n, solutions, choice, number)
        renderizar_con_manim()


if __name__ == "__main__":
    main()