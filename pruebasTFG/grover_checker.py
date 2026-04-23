import tkinter as tk
from tkinter import filedialog
from qiskit.qasm2 import loads
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
import numpy as np


#############################
# SELECTOR ARCHIVO
#############################
def seleccionar_archivo():
    root = tk.Tk()
    root.withdraw()
    root.update()

    file_path = filedialog.askopenfilename(
        title="Selecciona un archivo QASM",
        filetypes=[("Archivos QASM", "*.qasm")]
    )

    root.destroy()
    return file_path


#############################
# CARGAR CIRCUITO
#############################
def cargar_circuito(path):
    with open(path, "r") as f:
        qasm_text = f.read()
    # La puerta 'p' (phase) no esta en qelib1.inc pero es equivalente a 'u1'
    qasm_text = qasm_text.replace("p(", "u1(")
    return loads(qasm_text)


#############################
# CONSTRUIR SUBCIRCUITO
#############################
def construir_subcircuito(ops, n):
    qc = QuantumCircuit(n)
    for instr in ops:
        qc.append(instr.operation, instr.qubits, instr.clbits)
    return qc


#############################
# DETECTAR DIFUSOR
#############################
def detectar_inicio_difusor(ops, inicio, n):
    # El difusor tiene: n H + n X + MCX + n X + n H ≈ 4n+1 puertas
    ventana = max(8, 4 * n + 4)

    for i in range(inicio, len(ops) - 2):
        nombres = [ops[i + k].operation.name for k in range(min(ventana, len(ops) - i))]

        if (
            nombres.count("x") >= n and
            nombres.count("h") >= n and
            any(g in nombres for g in ["cx", "ccx", "mcx"])
        ):
            return i

    return None


#############################
# DETECTAR SOLUCIONES
#############################
def soluciones_de_oraculo(qc):
    n = qc.num_qubits

    init = QuantumCircuit(n)
    init.h(range(n))

    before = Statevector.from_instruction(init)
    after = Statevector.from_instruction(init.compose(qc))

    amps_before = before.data
    amps_after = after.data

    solutions_neg = []
    solutions_pos = []
    mezcla_neg = False
    mezcla_pos = False

    for i in range(len(amps_before)):
        if np.isclose(amps_after[i], -amps_before[i]):
            solutions_neg.append(i)
        elif np.isclose(amps_after[i], amps_before[i]):
            solutions_pos.append(i)
        else:
            mezcla_neg = True
            mezcla_pos = True

    # Caso normal: oráculo marca con fase −1
    if not mezcla_neg and len(solutions_neg) > 0:
        return solutions_neg

    # Caso oráculo greater: fase global π, los marcados quedan en +1
    if not mezcla_pos and len(solutions_pos) > 0 and len(solutions_pos) < len(amps_before):
        return solutions_pos

    return None


#############################
# CORREGIR ENDIANNESS
#############################
def corregir_endianness(indices, n):
    corregidos = []

    for i in indices:
        b = format(i, f"0{n}b")
        b_inv = b[::-1]
        corregidos.append(int(b_inv, 2))

    return sorted(corregidos)


#############################
# CLASIFICAR
#############################
def clasificar_soluciones(solutions, n):
    N = 2 ** n

    if len(solutions) == 1:
        return f"equal({solutions[0]})"

    for k in range(N + 1):
        if solutions == list(range(k)):
            return f"less_than({k})"

    for k in range(-1, N):
        if solutions == list(range(k + 1, N)):
            return f"greater_than({k})"

    return "desconocido"


#############################
# DETECTAR ORÁCULO
#############################
def detectar_oraculo(qc):

    ops = qc.data
    n = qc.num_qubits

    # ── Detectar inicio del oraculo ──────────────────────────────────────────
    # Intento 1: primer barrier (generado por generar_qasm.py)
    inicio_oraculo = None
    for i, instr in enumerate(ops):
        if instr.operation.name == "barrier":
            inicio_oraculo = i + 1
            break

    # Intento 2: primeros n H sobre qubits distintos (QASM sin barrier)
    if inicio_oraculo is None:
        h_qubits = set()
        for i, instr in enumerate(ops):
            if instr.operation.name == "h":
                h_qubits.add(instr.qubits[0])
                if len(h_qubits) == n:
                    inicio_oraculo = i + 1
                    break

    if inicio_oraculo is None:
        return None

    # ── Detectar difusor ─────────────────────────────────────────────────────
    inicio_difusor = detectar_inicio_difusor(ops, inicio_oraculo, n)

    if inicio_difusor is None:
        return None

    # ── Extraer oraculo (sin barriers) ───────────────────────────────────────
    bloque = [op for op in ops[inicio_oraculo:inicio_difusor]
              if op.operation.name != "barrier"]
    oracle_qc = construir_subcircuito(bloque, n)

    solutions = soluciones_de_oraculo(oracle_qc)

    if solutions is None:
        return None

    # ── Corregir endianness y clasificar ─────────────────────────────────────
    solutions_corr = corregir_endianness(solutions, n)

    return clasificar_soluciones(solutions_corr, n)



#############################
# MAIN
#############################
def main():

    print("Selecciona circuito QASM")

    path = seleccionar_archivo()

    if not path:
        print("No se seleccionó archivo")
        return

    try:
        qc = cargar_circuito(path)

        resultado = detectar_oraculo(qc)

        if resultado is None:
            print("No es un circuito de Grover válido")
        else:
            print(f"Resultado: {resultado}")

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    main()