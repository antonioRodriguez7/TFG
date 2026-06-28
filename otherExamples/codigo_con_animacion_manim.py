from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.circuit.library import MCXGate
from qiskit.qasm2 import loads, LEGACY_CUSTOM_INSTRUCTIONS
import math
import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
from tkinter import filedialog
from matplotlib.patches import Circle as MplCircle, FancyBboxPatch
from matplotlib.offsetbox import TextArea, VPacker, HPacker, AnchoredOffsetbox, DrawingArea

import json
import os
import sys
import subprocess

# CONFIGURACION VIDEO
GENERAR_VIDEO_MANIM = True
MANIM_QUALITY = "-pql"
MANIM_DATA_FILE = "grover_manim_data.json"

try:
    from manim import *
    MANIM_AVAILABLE = True
except ImportError:
    MANIM_AVAILABLE = False

# UTILIDADES BASICAS
def qindex(q):
    if hasattr(q, "_index"):
        return q._index
    return q.index

# CONVERTIMOS NUESTRO ARCHIVO .QASM EN UN QUANTUM CIRCUIT DE QISKIT Y LO DEVOLVEMOS
def cargar_circuito(path):
    with open(path, "r", encoding="utf-8") as f:
        return loads(
            f.read(),
            custom_instructions=LEGACY_CUSTOM_INSTRUCTIONS
        )

# Metodo para reconstruir un circuito
def construir_subcircuito_desde_ops(ops, n):
    sub_qc = QuantumCircuit(n)
    for instr in ops:
        qargs = [qindex(q) for q in instr.qubits]
        sub_qc.append(instr.operation, qargs, [])
    return sub_qc

# =========================
# DIFFUSOR
# =========================
def diffuser(qc, n):
    qc.h(range(n))
    qc.x(range(n))

    qc.h(n - 1)
    qc.append(MCXGate(n - 1), list(range(n)))
    qc.h(n - 1)

    qc.x(range(n))
    qc.h(range(n))

    # Corrige la fase global para obtener D = 2|u><u| - I
    qc.global_phase += np.pi

def optimal_iterations(n, M):
    N = 2**n

    if M == 0:
        return 0

    return int(np.floor((np.pi / 4) * np.sqrt(N / M)))

# =========================
# ORACULOS INTERNOS
# =========================
def mark_one(number, nqubits, name=None):
    if isinstance(number, str):
        binary = number.zfill(nqubits)
    else:
        binary = format(number, f"0{nqubits}b")

    circuit = QuantumCircuit(nqubits, name=name if name else f"== {number}")

    for i, bit in enumerate(reversed(binary)):
        if bit == "0":
            circuit.x(i)

    circuit.h(nqubits - 1)
    circuit.append(MCXGate(nqubits - 1), list(range(nqubits)))
    circuit.h(nqubits - 1)

    for i, bit in enumerate(reversed(binary)):
        if bit == "0":
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

        if value == "0":
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
        if value == "0":
            circuit.x(nqubits - position - 1)

    return circuit

def es_primo(n):
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False

    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2

    return True

def oracle_from_marked_states(marked_states, nqubits, name=None):
    circuit = QuantumCircuit(nqubits, name=name if name else "oracle_marked_states")

    for state in sorted(set(marked_states)):
        circuit.append(mark_one(state, nqubits).to_gate(), range(nqubits))

    return circuit

def oracle_greater(number, nqubits, name=None):
    marked = list(range(number + 1, 2**nqubits))
    return oracle_from_marked_states(
        marked,
        nqubits,
        name=name if name else f"> {number}"
    )

def oracle_evens(nqubits, name=None):
    marked = [i for i in range(2**nqubits) if i % 2 == 0]
    return oracle_from_marked_states(
        marked,
        nqubits,
        name=name if name else "evens"
    )

def oracle_primes(nqubits, name=None):
    marked = [i for i in range(2**nqubits) if es_primo(i)]
    return oracle_from_marked_states(
        marked,
        nqubits,
        name=name if name else "primes"
    )

# =========================
# ORACULO ESPERADO DESDE CSV
# =========================
def construir_oraculo_esperado_desde_csv(soluciones_csv, n):
    return oracle_from_marked_states(soluciones_csv, n, name="oracle_csv")

def obtener_vector_esperado_desde_csv(psi_in, soluciones_csv, n):
    oracle_esperado = construir_oraculo_esperado_desde_csv(soluciones_csv, n)
    psi_out_esperado = psi_in.evolve(oracle_esperado)
    return psi_out_esperado

# =========================
# ANALISIS DEL CIRCUITO
# =========================
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
        if i + 2 * n + 3 > total:
            break

        bloque_h = ops[i:i + n]
        bloque_x = ops[i + n:i + 2 * n]

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

def extraer_componentes_grover(qc):
    if not es_capa_h_inicial(qc):
        return None

    inicio_difusor = detectar_inicio_difusor(qc)
    if inicio_difusor is None:
        return None

    n = qc.num_qubits

    ops_h = qc.data[:n]
    ops_h_y_oraculo = qc.data[:inicio_difusor]

    prep_qc = construir_subcircuito_desde_ops(ops_h, n)
    full_until_oracle_qc = construir_subcircuito_desde_ops(ops_h_y_oraculo, n)

    return {
        "n": n,
        "inicio_difusor": inicio_difusor,
        "prep_qc": prep_qc,
        "full_until_oracle_qc": full_until_oracle_qc
    }

def obtener_vectores_oraculo_usuario(qc):
    componentes = extraer_componentes_grover(qc)
    if componentes is None:
        return None

    prep_qc = componentes["prep_qc"]
    full_until_oracle_qc = componentes["full_until_oracle_qc"]

    psi_in = Statevector.from_instruction(prep_qc)
    psi_out = Statevector.from_instruction(full_until_oracle_qc)

    componentes["psi_in"] = psi_in
    componentes["psi_out"] = psi_out

    return componentes

def detectar_estados_marcados_desde_vectores(psi_in, psi_out, tol=1e-8):
    marcados = []

    amps_in = psi_in.data
    amps_out = psi_out.data

    for i in range(len(amps_in)):
        if np.allclose(amps_out[i], -amps_in[i], atol=tol):
            marcados.append(i)

    return marcados

def clasificar_oraculo_por_estados(marcados, n):
    marcados = sorted(marcados)
    N = 2**n

    if len(marcados) == 0:
        return {
            "tipo": "unknown",
            "parametro": None,
            "descripcion": "No marca ningun estado"
        }

    if len(marcados) == 1:
        return {
            "tipo": "equal",
            "parametro": marcados[0],
            "descripcion": f"equal({marcados[0]})"
        }

    for k in range(N + 1):
        if marcados == list(range(k)):
            return {
                "tipo": "less",
                "parametro": k,
                "descripcion": f"less({k})"
            }

    for k in range(-1, N):
        if marcados == list(range(k + 1, N)):
            return {
                "tipo": "greater",
                "parametro": k,
                "descripcion": f"greater({k})"
            }

    pares = [i for i in range(N) if i % 2 == 0]
    if marcados == pares:
        return {
            "tipo": "evens",
            "parametro": None,
            "descripcion": "evens"
        }

    primos = [i for i in range(N) if es_primo(i)]
    if marcados == primos:
        return {
            "tipo": "primes",
            "parametro": None,
            "descripcion": "primes"
        }

    return {
        "tipo": "unknown",
        "parametro": None,
        "descripcion": "oraculo arbitrario o no clasificado"
    }

def mostrar_resumen_qasm(componentes):
    n = componentes["n"]
    inicio_difusor = componentes["inicio_difusor"]
    psi_in = componentes["psi_in"]
    psi_out = componentes["psi_out"]

    print("RESUMEN DEL QASM ANALIZADO")
    print("==============================")
    print("Numero de qubits:", n)
    print("Inicio del difusor en la operacion:", inicio_difusor)

    print("\n--- Vector de estado inicial del oraculo (tras H) ---")
    print(psi_in)

    print("\n--- Vector de estado final del oraculo (tras H + oraculo) ---")
    print(psi_out)

    marcados = detectar_estados_marcados_desde_vectores(psi_in, psi_out)
    componentes["marcados_detectados"] = marcados

    print("\n--- Estados marcados detectados por el oraculo ---")
    print(marcados)

    clasificacion = clasificar_oraculo_por_estados(marcados, n)
    componentes["clasificacion_oraculo"] = clasificacion

    print("\n--- Clasificacion semantica del oraculo ---")
    print(clasificacion["descripcion"])

# =========================
# CSV
# =========================
def pedir_qasm():
    root = tk.Tk()
    root.withdraw()
    root.update()

    path = filedialog.askopenfilename(
        title="Selecciona un circuito Grover (.qasm)",
        filetypes=[("Archivos QASM", "*.qasm")]
    )

    root.destroy()

    if not path:
        return None

    return path

def pedir_csv_soluciones():
    root = tk.Tk()
    root.withdraw()
    root.update()

    path = filedialog.askopenfilename(
        title="Selecciona el archivo CSV con los estados marcados o el statevector esperado",
        filetypes=[("Archivos CSV", "*.csv")]
    )

    root.destroy()

    if not path:
        return None

    return path

def leer_soluciones_desde_csv(path_csv, n):
    max_val = 2**n - 1
    soluciones = []

    with open(path_csv, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()

            if not linea:
                continue

            try:
                numero = int(linea)
            except ValueError:
                raise ValueError(f"Valor no valido en el CSV: '{linea}'")

            if numero < 0 or numero > max_val:
                raise ValueError(
                    f"El CSV contiene el valor {numero}, pero con {n} qubits solo se permiten estados entre 0 y {max_val}. "
                    "Esto indica que el CSV probablemente corresponde a un numero distinto de qubits."
                )

            soluciones.append(numero)

    return sorted(set(soluciones))

def detectar_tipo_csv(path_csv):
    with open(path_csv, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue

            try:
                int(linea)
                return "numbers"
            except ValueError:
                return "statevector"

    raise ValueError("El CSV esta vacio")

def leer_statevector_desde_csv(path_csv, n):
    amplitudes = []

    with open(path_csv, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue

            try:
                valor = complex(linea.replace("i", "j"))
            except ValueError:
                raise ValueError(f"Amplitud no valida en el CSV: '{linea}'")

            amplitudes.append(valor)

    N = 2**n

    if len(amplitudes) != N:
        qubits_csv = math.log2(len(amplitudes)) if len(amplitudes) > 0 else None

        if qubits_csv is not None and qubits_csv.is_integer():
            raise ValueError(
                f"El statevector del CSV tiene {len(amplitudes)} amplitudes, lo que corresponde a {int(qubits_csv)} qubits, "
                f"pero el QASM analizado utiliza {n} qubits."
            )
        else:
            raise ValueError(
                f"El statevector del CSV tiene {len(amplitudes)} amplitudes, pero para {n} qubits deberían existir exactamente {N}. "
                "Esto indica que el CSV no corresponde al mismo tamaño de sistema que el QASM."
            )

    vector = np.array(amplitudes, dtype=complex)

    norma = np.linalg.norm(vector)
    if norma < 1e-12:
        raise ValueError("El statevector del CSV no puede tener norma cero")

    if not np.isclose(norma, 1.0, atol=1e-8):
        raise ValueError(f"El statevector del CSV no esta normalizado. Norma detectada: {norma}")

    return Statevector(vector)

def leer_csv_entrada(path_csv, n):
    tipo = detectar_tipo_csv(path_csv)

    if tipo == "numbers":
        soluciones = leer_soluciones_desde_csv(path_csv, n)
        return {
            "tipo_csv": "numbers",
            "soluciones": soluciones,
            "statevector": None
        }

    if tipo == "statevector":
        statevector = leer_statevector_desde_csv(path_csv, n)
        return {
            "tipo_csv": "statevector",
            "soluciones": None,
            "statevector": statevector
        }

    raise ValueError("Tipo de CSV no soportado")

# =========================
# COMPARACIONES
# =========================
def comparar_soluciones_detectadas_con_csv(soluciones_detectadas, soluciones_csv):
    return sorted(soluciones_detectadas) == sorted(soluciones_csv)

def comparar_statevectors_hasta_fase_global(psi1, psi2, tol=1e-8):
    v1 = psi1.data
    v2 = psi2.data

    idx = None
    for i in range(len(v1)):
        if abs(v2[i]) > tol:
            idx = i
            break

    if idx is None:
        return np.allclose(v1, v2, atol=tol)

    fase = v1[idx] / v2[idx]
    return np.allclose(v1, fase * v2, atol=tol)

def comparar_clasificaciones(clasificacion_qasm, clasificacion_csv):
    return (
        clasificacion_qasm["tipo"] == clasificacion_csv["tipo"] and
        clasificacion_qasm["parametro"] == clasificacion_csv["parametro"]
    )

def validar_qasm_con_csv(componentes, entrada_csv):
    psi_in = componentes["psi_in"]
    psi_out_usuario = componentes["psi_out"]
    marcados_detectados = componentes["marcados_detectados"]
    clasificacion_qasm = componentes["clasificacion_oraculo"]
    n = componentes["n"]

    resultado = {
        "es_valido": False,
        "solution_indices": None,
        "psi_out_esperado": None,
        "marcados_csv": None,
        "clasificacion_csv": None
    }

    if entrada_csv["tipo_csv"] == "numbers":
        soluciones_csv = entrada_csv["soluciones"]

        print("\n--- CSV interpretado como lista de estados marcados ---")
        print(soluciones_csv)

        listas_coinciden = comparar_soluciones_detectadas_con_csv(
            marcados_detectados,
            soluciones_csv
        )

        psi_out_esperado = obtener_vector_esperado_desde_csv(
            psi_in,
            soluciones_csv,
            n
        )

        print("\n--- Vector de estado esperado segun el CSV ---")
        print(psi_out_esperado)

        vectores_coinciden = comparar_statevectors_hasta_fase_global(
            psi_out_usuario,
            psi_out_esperado
        )

        clasificacion_csv = clasificar_oraculo_por_estados(soluciones_csv, n)
        clasificacion_coincide = comparar_clasificaciones(
            clasificacion_qasm,
            clasificacion_csv
        )

        print("\n--- Clasificacion del CSV ---")
        print(clasificacion_csv["descripcion"])

        if listas_coinciden:
            print("\nLos estados marcados del QASM coinciden con los del CSV")
        else:
            print("\nLos estados marcados del QASM no coinciden con los del CSV")

        if vectores_coinciden:
            print("\nEl vector final del oraculo coincide con el esperado (salvo fase global)")
        else:
            print("\nEl vector final del oraculo no coincide con el esperado")

        if clasificacion_coincide:
            print("\nLa clasificacion semantica del QASM coincide con la del CSV")
        else:
            print("\nLa clasificacion semantica del QASM no coincide con la del CSV")

        resultado["es_valido"] = listas_coinciden and vectores_coinciden and clasificacion_coincide
        resultado["solution_indices"] = soluciones_csv
        resultado["psi_out_esperado"] = psi_out_esperado
        resultado["marcados_csv"] = soluciones_csv
        resultado["clasificacion_csv"] = clasificacion_csv
        return resultado

    if entrada_csv["tipo_csv"] == "statevector":
        psi_out_esperado = entrada_csv["statevector"]

        print("\n--- CSV interpretado como statevector esperado ---")
        print(psi_out_esperado)

        vectores_coinciden = comparar_statevectors_hasta_fase_global(
            psi_out_usuario,
            psi_out_esperado
        )

        marcados_csv = detectar_estados_marcados_desde_vectores(
            psi_in,
            psi_out_esperado
        )

        clasificacion_csv = clasificar_oraculo_por_estados(marcados_csv, n)
        listas_coinciden = comparar_soluciones_detectadas_con_csv(
            marcados_detectados,
            marcados_csv
        )
        clasificacion_coincide = comparar_clasificaciones(
            clasificacion_qasm,
            clasificacion_csv
        )

        print("\n--- Estados marcados deducidos desde el statevector del CSV ---")
        print(marcados_csv)

        print("\n--- Clasificacion del CSV ---")
        print(clasificacion_csv["descripcion"])

        if vectores_coinciden:
            print("\nEl vector final del oraculo coincide con el statevector del CSV (salvo fase global)")
        else:
            print("\nEl vector final del oraculo no coincide con el statevector del CSV")

        if listas_coinciden:
            print("\nLos estados marcados del QASM coinciden con los deducidos del statevector del CSV")
        else:
            print("\nLos estados marcados del QASM no coinciden con los deducidos del statevector del CSV")

        if clasificacion_coincide:
            print("\nLa clasificacion semantica del QASM coincide con la del CSV")
        else:
            print("\nLa clasificacion semantica del QASM no coincide con la del CSV")

        resultado["es_valido"] = vectores_coinciden and listas_coinciden and clasificacion_coincide
        resultado["solution_indices"] = marcados_csv
        resultado["psi_out_esperado"] = psi_out_esperado
        resultado["marcados_csv"] = marcados_csv
        resultado["clasificacion_csv"] = clasificacion_csv
        return resultado

    return resultado

# =========================
# ORACULO INTERNO DESDE CLASIFICACION
# =========================
def construir_oraculo_interno_desde_clasificacion(clasificacion, n):
    tipo = clasificacion["tipo"]
    parametro = clasificacion["parametro"]

    if tipo == "equal":
        return mark_one(parametro, n, name=f"== {parametro}")

    if tipo == "less":
        return oracle_less(parametro, n, name=f"< {parametro}")

    if tipo == "greater":
        return oracle_greater(parametro, n, name=f"> {parametro}")

    if tipo == "evens":
        return oracle_evens(n)

    if tipo == "primes":
        return oracle_primes(n)

    return None

# FLUJO PRINCIPAL
def analyze_grover_with_internal_oracle(n, oracle_circuit, solution_indices):
    qc = QuantumCircuit(n)

    states = []
    labels = []

    state = Statevector.from_instruction(qc)
    print("\n--- Estado inicial |0...0> ---")
    print(state)
    states.append(state)
    labels.append("init")

    qc.h(range(n))
    state = Statevector.from_instruction(qc)
    print("\n--- Estado uniforme inicial |u> ---")
    print(state)
    states.append(state)
    labels.append("u")

    M = len(solution_indices)
    print("\nNumero de soluciones (M):", M)
    print("Soluciones:", solution_indices)

    iterations = optimal_iterations(n, M)
    print("Numero de iteraciones de Grover:", iterations)

    if iterations == 0:
        print("No hay iteraciones interesantes")
        return states, labels

    for i in range(iterations):
        qc.append(oracle_circuit.to_gate(), list(range(n)))
        state = Statevector.from_instruction(qc)
        print(f"\n--- Estado tras Oraculo {i + 1} ---")
        print(state)
        states.append(state)
        labels.append(f"O_{i+1}")

        diffuser(qc, n)
        state = Statevector.from_instruction(qc)
        print(f"\n--- Estado tras Difusor {i + 1} ---")
        print(state)
        states.append(state)
        labels.append(f"D_{i+1}")

    return states, labels

def obtener_qasm_y_vectores():
    path = pedir_qasm()
    if path is None:
        print("No se selecciono archivo QASM")
        return None

    qc = cargar_circuito(path)

    if not es_capa_h_inicial(qc):
        print("El circuito no empieza con una superposicion uniforme de Grover")
        return None

    if detectar_inicio_difusor(qc) is None:
        print("No se ha detectado un difusor con estructura de Grover")
        return None

    componentes = obtener_vectores_oraculo_usuario(qc)
    if componentes is None:
        print("No se pudieron extraer correctamente los componentes del circuito")
        return None

    return componentes

# =========================
# REPRESENTACION
# =========================
def build_grover_basis(n, solution_indices):
    N = 2**n

    ket_t = np.zeros(N, dtype=complex)
    for index in solution_indices:
        ket_t[index] = 1.0

    if np.linalg.norm(ket_t) > 1e-12:
        ket_t /= np.linalg.norm(ket_t)

    ket_s = np.ones(N, dtype=complex)
    for index in solution_indices:
        ket_s[index] = 0.0

    if np.linalg.norm(ket_s) > 1e-12:
        ket_s /= np.linalg.norm(ket_s)

    return ket_s, ket_t

def project_state(statevector, solution_indices, n):
    amps = statevector.data
    ket_s, ket_t = build_grover_basis(n, solution_indices)

    c_s = np.vdot(ket_s, amps)
    c_t = np.vdot(ket_t, amps)

    c_s = np.real_if_close(c_s, tol=1000)
    c_t = np.real_if_close(c_t, tol=1000)

    return float(np.real(c_s)), float(np.real(c_t))

def format_number_latex(x, sig=4):
    if abs(x) < 1e-12:
        return "0"

    ax = abs(x)
    if ax >= 1e3 or ax < 1e-3:
        exp = int(math.floor(math.log10(ax)))
        mant = x / (10**exp)
        return rf"{mant:.{sig-1}f}\times 10^{{{exp}}}"
    return rf"{x:.{sig}f}"

def state_expression_latex(x, y):
    x_ltx = format_number_latex(x)
    y_abs_ltx = format_number_latex(abs(y))
    signo = "+" if y >= 0 else "-"
    return rf"{x_ltx}\,|s\rangle\ {signo}\ {y_abs_ltx}\,|t\rangle"

def compact_ranges(values):
    if not values:
        return []

    values = sorted(set(values))
    ranges = []
    start = values[0]
    prev = values[0]

    for value in values[1:]:
        if value == prev + 1:
            prev = value
        else:
            ranges.append((start, prev))
            start = value
            prev = value

    ranges.append((start, prev))
    return ranges

def marked_states_latex(solution_indices, n):
    N = 2**n
    values = sorted(set(solution_indices))

    if not values:
        return r"\mathrm{Estados\ marcados:}\ \varnothing"

    clasificacion = clasificar_oraculo_por_estados(values, n)
    tipo = clasificacion["tipo"]
    parametro = clasificacion["parametro"]

    if tipo == "equal":
        return rf"\mathrm{{Estado\ marcado:}}\ x={parametro}"

    if tipo == "less" and parametro is not None:
        if parametro == 0:
            return r"\mathrm{Estados\ marcados:}\ \varnothing"
        return rf"\mathrm{{Estados\ marcados:}}\ x<{parametro},\quad x\in\{{0,\ldots,{N-1}\}}"

    if tipo == "greater" and parametro is not None:
        if parametro == N - 1:
            return r"\mathrm{Estados\ marcados:}\ \varnothing"
        return rf"\mathrm{{Estados\ marcados:}}\ x>{parametro},\quad x\in\{{0,\ldots,{N-1}\}}"

    if tipo == "evens":
        return rf"\mathrm{{Estados\ marcados:}}\ x\ \mathrm{{par}},\quad x\in\{{0,\ldots,{N-1}\}}"

    if tipo == "primes":
        return rf"\mathrm{{Estados\ marcados:}}\ x\ \mathrm{{primo}},\quad x\in\{{0,\ldots,{N-1}\}}"

    ranges = compact_ranges(values)

    if len(ranges) == 1 and ranges[0][0] != ranges[0][1]:
        a, b = ranges[0]
        return rf"\mathrm{{Estados\ marcados:}}\ {a}\leq x\leq {b},\quad x\in\{{0,\ldots,{N-1}\}}"

    partes = []
    for a, b in ranges[:4]:
        if a == b:
            partes.append(rf"\{{{a}\}}")
        else:
            partes.append(rf"\{{{a},\ldots,{b}\}}")

    if len(ranges) > 4:
        partes.append(r"\cdots")

    return r"\mathrm{Estados\ marcados:}\ " + r"\cup ".join(partes)

def high_solution_case_explanation(n, solution_indices):
    N = 2**n
    M = len(solution_indices)

    if M > N / 2:
        return (
            "Interpretación:\n"
            "El oráculo marca muchos estados solución respecto al espacio total.\n"
            "En estos casos, Grover no es especialmente óptimo, ya que su ventaja aparece cuando hay pocas soluciones.\n"
            "Por eso la rotación geométrica puede verse menos clara."
        )

    if M >= N / 4:
        return (
            "Interpretación:\n"
            "El oráculo marca una cantidad relativamente alta de estados solución.\n"
            "Por ello, Grover pierde parte de su ventaja práctica y la amplificación resulta menos evidente.\n"
            "Aun así, la evolución sigue siendo matemáticamente correcta."
        )

    return None

def dibujar_resumen_matematico(ax_math, datos):
    ax_math.axis("off")

    caja = FancyBboxPatch(
        (0.0, 0.0),
        1.0,
        1.0,
        transform=ax_math.transAxes,
        boxstyle="round,pad=0.0,rounding_size=0.025",
        facecolor="white",
        edgecolor="#cccccc",
        linewidth=1.0,
        clip_on=False
    )

    ax_math.add_patch(caja)

    elementos = []

    for linea in datos["resumen_matematico"]:
        if len(linea) == 2:
            texto, tam = linea
            indent = 0
        else:
            texto, tam, indent = linea

        if texto == "":
            elementos.append(
                TextArea(
                    " ",
                    textprops=dict(size=tam)
                )
            )
        else:
            espacio = DrawingArea(indent, 1, 0, 0)

            contenido = TextArea(
                texto,
                textprops=dict(size=tam)
            )

            fila = HPacker(
                children=[espacio, contenido],
                align="baseline",
                pad=0,
                sep=0
            )

            elementos.append(fila)

    bloque = VPacker(
        children=elementos,
        align="left",
        pad=0,
        sep=5
    )

    resumen = AnchoredOffsetbox(
        loc="upper left",
        child=bloque,
        frameon=False,
        bbox_to_anchor=(0.025, 0.965),
        bbox_transform=ax_math.transAxes,
        borderpad=0
    )

    ax_math.add_artist(resumen)

def plot_grover_by_iteration(states, labels, n, solution_indices, titulo="Evolución de Grover"):
    iterations = (len(states) - 2) // 2

    if iterations <= 0:
        print("No hay iteraciones para representar.")
        return
    
    N = 2**n
    ket_u = np.ones(N, dtype=complex) / np.sqrt(N)

    points = [project_state(s, solution_indices, n) for s in states]

    for iteration_number in range(1, iterations + 1):
        fig = plt.figure(figsize=(16, 9))

        # Representación principal
        ax = fig.add_axes([0.04, 0.08, 0.49, 0.74])

        datos = draw_single_iteration(
            ax,
            points,
            labels,
            iteration_number,
            n,
            solution_indices
        )

        fig.suptitle(
            titulo,
            fontsize=28,
            fontweight="bold",
            y=0.955
        )

        # -----------------------------
        # PANEL DERECHO
        # -----------------------------
        panel_x = 0.545
        panel_w = 0.25

        h_legend = 0.25
        h_math = 0.31
        h_info = 0.12

        gap_legend_math = 0.035
        gap_math_info = 0.045

        top = 0.875

        y_legend = top - h_legend
        y_math = y_legend - gap_legend_math - h_math
        y_info = y_math - gap_math_info - h_info

        # -----------------------------
        # LEYENDA
        # -----------------------------
        ax_leg = fig.add_axes([panel_x, y_legend, panel_w, h_legend])
        ax_leg.axis("off")

        legend = ax_leg.legend(
            handles=datos["handles"],
            loc="upper left",
            bbox_to_anchor=(0.0, 0.0, 1.0, 1.0),
            bbox_transform=ax_leg.transAxes,
            mode="expand",
            fontsize=11,
            frameon=True,
            title="Leyenda",
            title_fontsize=14,
            borderpad=0.9,
            labelspacing=0.65,
            handlelength=2.0,
            handletextpad=0.8,
            borderaxespad=0.0
        )

        try:
            legend._legend_box.align = "left"
        except Exception:
            pass

        # -----------------------------
        # RESUMEN MATEMÁTICO
        # -----------------------------
        ax_math = fig.add_axes([panel_x, y_math, panel_w, h_math])
        dibujar_resumen_matematico(ax_math, datos)

        # -----------------------------
        # INTERPRETACIÓN
        # -----------------------------
        if datos["explicacion_extra"] is not None:
            ax_info = fig.add_axes([panel_x, y_info, panel_w, h_info])
            ax_info.axis("off")

            ax_info.text(
                0.02,
                0.98,
                datos["explicacion_extra"],
                transform=ax_info.transAxes,
                fontsize=10.3,
                va="top",
                ha="left",
                linespacing=1.25,
                bbox=dict(
                    boxstyle="round,pad=0.55",
                    facecolor="white",
                    edgecolor="#cccccc"
                )
            )

        fig.text(
            0.5,
            0.025,
            "Cierra esta ventana para pasar a la siguiente iteración",
            ha="center",
            va="center",
            fontsize=12,
            bbox=dict(
                boxstyle="round,pad=0.35",
                facecolor="white",
                edgecolor="#cccccc"
            )
        )

        # -----------------------------
        # ABRIR VENTANA MAXIMIZADA
        # -----------------------------
        try:
            manager = plt.get_current_fig_manager()

            try:
                manager.window.state("zoomed")
            except Exception:
                try:
                    manager.window.showMaximized()
                except Exception:
                    try:
                        manager.full_screen_toggle()
                    except Exception:
                        pass

        except Exception:
            pass

        plt.show()


def draw_single_iteration(ax, points, labels, iteration_number, n, solution_indices):
    start_idx = 1 if iteration_number == 1 else 2 * iteration_number - 1
    oracle_idx = 2 * iteration_number
    diffuser_idx = 2 * iteration_number + 1

    x_start, y_start = points[start_idx]
    x_oracle, y_oracle = points[oracle_idx]
    x_diff, y_diff = points[diffuser_idx]

    color_start = "#148a1f"
    color_oracle = "#e61919"
    color_diff = "#1749ff"
    color_ref_oracle = "#ff9896"
    color_ref_diff = "#9ecae1"

    ax.set_facecolor("white")

    circ = MplCircle((0, 0), 1.0, fill=False, linewidth=1.8, edgecolor="#606060")
    ax.add_patch(circ)

    ax.plot([-1.0, 1.0], [0, 0], linewidth=1.5, color="black", zorder=1)
    ax.plot([0, 0], [-1.0, 1.0], linewidth=1.5, color="black", zorder=1)

    axis_len = 0.999

    ax.quiver(
        0, 0, axis_len, 0,
        angles="xy",
        scale_units="xy",
        scale=1,
        color="black",
        width=0.0035,
        zorder=2
    )
    ax.text(
        1.045, 0.0, r"$|s\rangle$",
        fontsize=18,
        fontweight="bold",
        ha="left",
        va="center"
    )

    ax.quiver(
        0, 0, 0, axis_len,
        angles="xy",
        scale_units="xy",
        scale=1,
        color="black",
        width=0.0035,
        zorder=2
    )
    ax.text(
        0.0, 1.055, r"$|t\rangle$",
        fontsize=18,
        fontweight="bold",
        ha="center",
        va="bottom"
    )

    ax.plot(
        [x_start, x_oracle],
        [y_start, y_oracle],
        linestyle="--",
        linewidth=3,
        color=color_ref_oracle,
        alpha=0.85,
        zorder=2
    )

    ax.plot(
        [x_oracle, x_diff],
        [y_oracle, y_diff],
        linestyle="--",
        linewidth=3,
        color=color_ref_diff,
        alpha=0.90,
        zorder=2
    )

    ax.quiver(
        0, 0, x_start, y_start,
        angles="xy",
        scale_units="xy",
        scale=1,
        color=color_start,
        width=0.008,
        alpha=0.95,
        zorder=3
    )

    ax.quiver(
        0, 0, x_oracle, y_oracle,
        angles="xy",
        scale_units="xy",
        scale=1,
        color=color_oracle,
        width=0.008,
        alpha=0.95,
        zorder=4
    )

    ax.quiver(
        0, 0, x_diff, y_diff,
        angles="xy",
        scale_units="xy",
        scale=1,
        color=color_diff,
        width=0.008,
        alpha=0.95,
        zorder=5
    )

    ax.scatter([x_start], [y_start], color=color_start, s=140, edgecolors="black", linewidths=0.8, zorder=6)
    ax.scatter([x_oracle], [y_oracle], color=color_oracle, s=140, edgecolors="black", linewidths=0.8, zorder=6)
    ax.scatter([x_diff], [y_diff], color=color_diff, s=140, edgecolors="black", linewidths=0.8, zorder=6)

    if iteration_number == 1:
        start_display = "u"
        start_legend = "u: estado uniforme inicial"
    else:
        start_display = rf"$\psi_{{{iteration_number-1}}}$"
        start_legend = rf"$\psi_{{{iteration_number-1}}}$: estado de entrada a esta iteración"

    ax.annotate(
        start_display,
        (x_start, y_start),
        textcoords="offset points",
        xytext=(14, 10),
        fontsize=13,
        fontweight="bold",
        color=color_start,
        bbox=dict(boxstyle="round,pad=0.20", facecolor="white", edgecolor=color_start, alpha=0.9)
    )

    ax.annotate(
        r"$O_f|x\rangle$",
        (x_oracle, y_oracle),
        textcoords="offset points",
        xytext=(14, -24),
        fontsize=13,
        fontweight="bold",
        color=color_oracle,
        bbox=dict(boxstyle="round,pad=0.20", facecolor="white", edgecolor=color_oracle, alpha=0.9)
    )

    ax.annotate(
        "D",
        (x_diff, y_diff),
        textcoords="offset points",
        xytext=(14, 12),
        fontsize=13,
        fontweight="bold",
        color=color_diff,
        bbox=dict(boxstyle="round,pad=0.20", facecolor="white", edgecolor=color_diff, alpha=0.9)
    )

    ax.set_title(f"Iteración {iteration_number}", fontsize=20, fontweight="bold", pad=22)
    ax.set_xlim(-1.10, 1.10)
    ax.set_ylim(-1.10, 1.10)
    ax.set_aspect("equal")

    ticks = np.arange(-1.0, 1.01, 0.5)
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.tick_params(axis="both", length=0)

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.grid(alpha=0.18, linestyle=":")

    handles = [
        plt.Line2D([0], [0], color=color_start, lw=3, label=start_legend),
        plt.Line2D([0], [0], color=color_diff, lw=3, label="D: estado tras aplicar D"),
        plt.Line2D([0], [0], color=color_oracle, lw=3, label=r"$O_f|x\rangle$: estado tras aplicar el oráculo"),
        plt.Line2D([0], [0], color=color_ref_oracle, lw=3, linestyle="--", label="Rotación del oráculo"),
        plt.Line2D([0], [0], color=color_ref_diff, lw=3, linestyle="--", label="Rotación del difusor"),
        plt.Line2D([0], [0], color="black", lw=2, label=r"$|t\rangle$  Estado solución"),
        plt.Line2D([0], [0], color="black", lw=2, label=r"$|s\rangle$  Estado de no soluciones"),
    ]

    conjunto_soluciones = marked_states_latex(solution_indices, n)

    expr_start = state_expression_latex(x_start, y_start)
    expr_oracle = state_expression_latex(x_oracle, y_oracle)
    expr_diff = state_expression_latex(x_diff, y_diff)

    resumen_matematico = [
    (rf"$n={n}$", 10.2),

    ("", 2),

    (
        r"$|u\rangle=\frac{1}{\sqrt{2^n}}\sum_{x=0}^{2^n-1}|x\rangle$",
        13.2
    ),
    (
        rf"${expr_start}$",
        9.4,
        22
    ),

    ("", 3),

    (
        r"$O_f|x\rangle=(-1)^{f(x)}|x\rangle$",
        13.2
    ),
    (
        "$" + conjunto_soluciones + "$",
        9.2,
        22
    ),
    (
        rf"${expr_oracle}$",
        9.4,
        22
    ),

    ("", 3),

    (
        r"$D=2|u\rangle\langle u|-I$",
        13.2
    ),
    (
        rf"${expr_diff}$",
        9.4,
        22
    ),
]
    explicacion_extra = high_solution_case_explanation(n, solution_indices)

    return {
        "handles": handles,
        "resumen_matematico": resumen_matematico,
        "explicacion_extra": explicacion_extra
    }

# ESCENA MANIM
if MANIM_AVAILABLE:
    class GroverScene(Scene):
        def construct(self):
            if not os.path.exists(MANIM_DATA_FILE):
                raise FileNotFoundError(f"No existe {MANIM_DATA_FILE}")

            with open(MANIM_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            points = data["points"]
            labels = data["labels"]
            iterations = data["iterations"]

            # TITULOS
            main_title = Text("Evolución de Grover", font_size=24)
            main_title.move_to(UP * 3.55)

            iter_title = Text("Iteración 1", font_size=20, weight=BOLD)
            iter_title.next_to(main_title, DOWN, buff=0.20)

            # LEYENDA ARRIBA DERECHA
            legend_1 = Text("Verde: estado de partida", font_size=18)
            legend_2 = Text("Rojo: oráculo", font_size=18)
            legend_3 = Text("Azul: difusor", font_size=18)

            legend_group = VGroup(
                legend_1, legend_2, legend_3
            ).arrange(
                DOWN,
                aligned_edge=LEFT,
                buff=0.18
            )

            legend_group.to_corner(UR)
            legend_group.shift(LEFT * 0.1 + DOWN * 3.6)

            self.play(FadeIn(main_title), FadeIn(iter_title), FadeIn(legend_group), run_time=0.8)

            # PLANO Y CIRCULO CENTRADOS
            plane = NumberPlane(
                x_range=[-1.2, 1.2, 0.25],
                y_range=[-1.2, 1.2, 0.25],
                x_length=5.6,
                y_length=5.6,
                background_line_style={
                    "stroke_opacity": 0.22,
                    "stroke_width": 1.2,
                    "stroke_color": BLUE_E
                },
                axis_config={
                    "stroke_opacity": 0
                }
            )

            # Centro de la zona izquierda, un poco más abajo
            plane.move_to(LEFT * 0.1 + DOWN * 0.65)

            circle = Circle(
                radius=plane.x_length / 2,
                color=GREY_B,
                stroke_width=2.2
            ).move_to(plane.get_center())

            origin = plane.c2p(0, 0)

            self.play(Create(plane), Create(circle), run_time=1.0)

            # EJES
            axis_limit = 1.2
            label_offset = 0.16

            eje_s_neg = Line(
                plane.c2p(-axis_limit, 0),
                origin,
                color=WHITE,
                stroke_width=2.2
            )

            eje_t_neg = Line(
                plane.c2p(0, -axis_limit),
                origin,
                color=WHITE,
                stroke_width=2.2
            )

            eje_s = Arrow(
                start=origin,
                end=plane.c2p(axis_limit, 0),
                buff=0,
                color=WHITE,
                stroke_width=3.5,
                max_tip_length_to_length_ratio=0.08
            )

            eje_t = Arrow(
                start=origin,
                end=plane.c2p(0, axis_limit),
                buff=0,
                color=WHITE,
                stroke_width=3.5,
                max_tip_length_to_length_ratio=0.08
            )

            label_s = MathTex(r"|s\rangle", font_size=28)
            label_t = MathTex(r"|t\rangle", font_size=28)

            label_s.next_to(
                plane.c2p(axis_limit, 0),
                RIGHT,
                buff=label_offset
            )

            label_t.next_to(
                plane.c2p(0, axis_limit),
                UP,
                buff=label_offset
            )

            self.play(
                Create(eje_s_neg), Create(eje_t_neg),
                Create(eje_s), Create(eje_t),
                FadeIn(label_s), FadeIn(label_t),
                run_time=0.8
            )

            current_group = None

            for i in range(1, iterations + 1):
                start_idx = 1 if i == 1 else 2 * i - 1
                oracle_idx = 2 * i
                diffuser_idx = 2 * i + 1

                start_x, start_y = points[start_idx]
                oracle_x, oracle_y = points[oracle_idx]
                diff_x, diff_y = points[diffuser_idx]

                start_p = plane.c2p(start_x, start_y)
                oracle_p = plane.c2p(oracle_x, oracle_y)
                diff_p = plane.c2p(diff_x, diff_y)

                # Etiquetas
                if i == 1:
                    start_text = MathTex(r"u", color=GREEN, font_size=28)
                else:
                    start_text = MathTex(rf"\psi_{{{i-1}}}", color=GREEN, font_size=28)

                oracle_text = MathTex(r"O_f|x\rangle", color=RED, font_size=28)
                diff_text = MathTex(r"D", color=BLUE, font_size=28)

                # Vectores
                start_arrow = Arrow(
                    origin, start_p,
                    buff=0,
                    color=GREEN,
                    stroke_width=5,
                    max_tip_length_to_length_ratio=0.10
                )
                oracle_arrow = Arrow(
                    origin, oracle_p,
                    buff=0,
                    color=RED,
                    stroke_width=5,
                    max_tip_length_to_length_ratio=0.10
                )
                diff_arrow = Arrow(
                    origin, diff_p,
                    buff=0,
                    color=BLUE,
                    stroke_width=5,
                    max_tip_length_to_length_ratio=0.10
                )

                start_dot = Dot(start_p, color=GREEN, radius=0.06)
                oracle_dot = Dot(oracle_p, color=RED, radius=0.06)
                diff_dot = Dot(diff_p, color=BLUE, radius=0.06)

                start_text.next_to(start_p, UR, buff=0.08)
                oracle_text.next_to(oracle_p, DR, buff=0.08)
                diff_text.next_to(diff_p, UR, buff=0.08)

                seg_oracle = DashedLine(
                    start_p, oracle_p,
                    color=RED,
                    dash_length=0.08,
                    stroke_width=3
                )

                seg_diff = DashedLine(
                    oracle_p, diff_p,
                    color=BLUE,
                    dash_length=0.08,
                    stroke_width=3
                )

                new_iter_title = Text(f"Iteración {i}", font_size=20, weight=BOLD)
                new_iter_title.next_to(main_title, DOWN, buff=0.20)

                new_group = VGroup(
                    start_arrow, start_dot, start_text,
                    oracle_arrow, oracle_dot, oracle_text,
                    diff_arrow, diff_dot, diff_text,
                    seg_oracle, seg_diff
                )

                if current_group is None:
                    self.play(Transform(iter_title, new_iter_title), run_time=0.3)
                    self.play(
                        Create(start_arrow), FadeIn(start_dot), FadeIn(start_text),
                        run_time=0.7
                    )
                    self.wait(0.25)
                    self.play(
                        Create(oracle_arrow), FadeIn(oracle_dot), FadeIn(oracle_text), Create(seg_oracle),
                        run_time=0.7
                    )
                    self.wait(0.25)
                    self.play(
                        Create(diff_arrow), FadeIn(diff_dot), FadeIn(diff_text), Create(seg_diff),
                        run_time=0.7
                    )
                else:
                    self.play(
                        FadeOut(current_group),
                        Transform(iter_title, new_iter_title),
                        run_time=0.45
                    )
                    self.play(
                        Create(start_arrow), FadeIn(start_dot), FadeIn(start_text),
                        run_time=0.7
                    )
                    self.wait(0.25)
                    self.play(
                        Create(oracle_arrow), FadeIn(oracle_dot), FadeIn(oracle_text), Create(seg_oracle),
                        run_time=0.7
                    )
                    self.wait(0.25)
                    self.play(
                        Create(diff_arrow), FadeIn(diff_dot), FadeIn(diff_text), Create(seg_diff),
                        run_time=0.7
                    )

                self.wait(1.0)
                current_group = new_group

            self.wait(2)

# EXPORTAR DATOS PARA MANIM
def exportar_datos_manim(states, labels, n, solution_indices, titulo="Evolución de Grover"):
    points = [project_state(s, solution_indices, n) for s in states]
    iterations = (len(states) - 2) // 2
    data = {
        "points": [[float(x), float(y)] for x, y in points],
        "labels": labels,
        "iterations": iterations,
        "title": titulo
    }
    with open(MANIM_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def renderizar_con_manim():
    if not MANIM_AVAILABLE:
        print("\nNo se puede generar el vídeo porque Manim no está instalado.")
        print("Instálalo con: pip install manim")
        return
    comando = [sys.executable, "-m", "manim", MANIM_QUALITY, __file__, "GroverScene"]
    subprocess.run(comando)

def main():
    componentes = obtener_qasm_y_vectores()
    if componentes is None:
        return

    mostrar_resumen_qasm(componentes)

    path_csv = pedir_csv_soluciones()
    if path_csv is None:
        print("\nNo se selecciono archivo CSV")
        return

    try:
        entrada_csv = leer_csv_entrada(path_csv, componentes["n"])
    except ValueError as e:
        print("\n--- Error durante la validacion del CSV ---")
        print(str(e))
        print("\nValidacion fallida: el CSV no es compatible con el QASM analizado.")
        print("Motivo: ambos parecen corresponder a un numero distinto de qubits.")
        print("Se detiene la ejecucion y no se pasa a la fase de Grover.")
        return

    validacion = validar_qasm_con_csv(componentes, entrada_csv)

    print("\n--- Resumen final del oraculo del circuito ---")
    print(f"Tipo detectado por comportamiento: {componentes['clasificacion_oraculo']['tipo']}")
    print(f"Descripcion: {componentes['clasificacion_oraculo']['descripcion']}")

    if validacion["clasificacion_csv"] is not None:
        print("\n--- Resumen del CSV ---")
        print(f"Tipo deducido desde el CSV: {validacion['clasificacion_csv']['tipo']}")
        print(f"Descripcion: {validacion['clasificacion_csv']['descripcion']}")

    if not validacion["es_valido"]:
        print("\nValidacion fallida: el QASM y el CSV no describen el mismo oraculo.")
        print("Se detiene la ejecucion y no se pasa a la fase de Grover.")
        return

    print("\nValidacion completada: el QASM y el CSV describen el mismo comportamiento.")

    oraculo_interno = construir_oraculo_interno_desde_clasificacion(
        componentes["clasificacion_oraculo"],
        componentes["n"]
    )

    if oraculo_interno is not None:
        print("Se ha construido el oraculo interno correspondiente para usarlo despues en Grover")

        solution_indices = validacion["solution_indices"]

        states, labels = analyze_grover_with_internal_oracle(
            componentes["n"],
            oraculo_interno,
            solution_indices
        )

        if len(states) > 2:
            plot_grover_by_iteration(
                states,
                labels,
                componentes["n"],
                solution_indices,
                titulo="Evolución de Grover"
            )

            if GENERAR_VIDEO_MANIM:
                exportar_datos_manim(
                    states,
                    labels,
                    componentes["n"],
                    solution_indices,
                    titulo="Evolución de Grover"
                )
                renderizar_con_manim()
    else:
        print("No se ha podido asociar un oraculo interno especifico; se tratara como oraculo arbitrario")

if __name__ == "__main__":
    main()