from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.circuit.library import MCXGate
from qiskit.qasm2 import loads, LEGACY_CUSTOM_INSTRUCTIONS

import numpy as np
import tkinter as tk
from tkinter import filedialog


# =========================
# UTILIDADES BASICAS
# =========================

def qindex(q):
    if hasattr(q, "_index"):
        return q._index
    return q.index


def cargar_circuito(path):
    with open(path, "r", encoding="utf-8") as f:
        return loads(
            f.read(),
            custom_instructions=LEGACY_CUSTOM_INSTRUCTIONS
        )


def construir_subcircuito_desde_ops(ops, n):
    sub_qc = QuantumCircuit(n)
    for instr in ops:
        qargs = [qindex(q) for q in instr.qubits]
        sub_qc.append(instr.operation, qargs, [])
    return sub_qc


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
# ANALISIS DEL QASM
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
    ops_oraculo = qc.data[n:inicio_difusor]
    ops_h_y_oraculo = qc.data[:inicio_difusor]

    prep_qc = construir_subcircuito_desde_ops(ops_h, n)
    oracle_qc = construir_subcircuito_desde_ops(ops_oraculo, n)
    full_until_oracle_qc = construir_subcircuito_desde_ops(ops_h_y_oraculo, n)

    return {
        "n": n,
        "inicio_difusor": inicio_difusor,
        "prep_qc": prep_qc,
        "oracle_qc": oracle_qc,
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


# =========================
# CLASIFICACION SEMANTICA
# =========================

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

    print("\n==============================")
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
                    f"Valor fuera de rango en el CSV: {numero} (debe estar entre 0 y {max_val})"
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
        raise ValueError(
            f"El statevector debe tener exactamente {N} amplitudes y tiene {len(amplitudes)}"
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


# =========================
# FLUJO PRINCIPAL
# =========================

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

    componentes["qc_original"] = qc
    componentes["path_qasm"] = path

    return componentes


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
        print(f"\nError al leer el CSV: {e}")
        return

    psi_out_usuario = componentes["psi_out"]

    if entrada_csv["tipo_csv"] == "numbers":
        soluciones_csv = entrada_csv["soluciones"]

        print("\n--- CSV interpretado como lista de estados marcados ---")
        print(soluciones_csv)

        marcados_detectados = componentes["marcados_detectados"]

        if comparar_soluciones_detectadas_con_csv(marcados_detectados, soluciones_csv):
            print("\n✅ El oraculo del QASM coincide con los estados del CSV")
        else:
            print("\n❌ El oraculo del QASM NO coincide con los estados del CSV")

        psi_in = componentes["psi_in"]
        psi_out_esperado = obtener_vector_esperado_desde_csv(
            psi_in,
            soluciones_csv,
            componentes["n"]
        )

        print("\n--- Vector de estado esperado segun el CSV ---")
        print(psi_out_esperado)

        if comparar_statevectors_hasta_fase_global(psi_out_usuario, psi_out_esperado):
            print("\n✅ El vector final del oraculo coincide con el esperado (salvo fase global)")
        else:
            print("\n❌ El vector final del oraculo NO coincide con el esperado")

    elif entrada_csv["tipo_csv"] == "statevector":
        psi_out_esperado = entrada_csv["statevector"]

        print("\n--- CSV interpretado como statevector esperado ---")
        print(psi_out_esperado)

        if comparar_statevectors_hasta_fase_global(psi_out_usuario, psi_out_esperado):
            print("\n✅ El vector final del oraculo coincide con el statevector del CSV (salvo fase global)")
        else:
            print("\n❌ El vector final del oraculo NO coincide con el statevector del CSV")

    print("\n--- Resumen final del oraculo del circuito ---")
    print(f"Tipo detectado por comportamiento: {componentes['clasificacion_oraculo']['tipo']}")
    print(f"Descripcion: {componentes['clasificacion_oraculo']['descripcion']}")

    oraculo_interno = construir_oraculo_interno_desde_clasificacion(
        componentes["clasificacion_oraculo"],
        componentes["n"]
    )

    if oraculo_interno is not None:
        componentes["oraculo_interno"] = oraculo_interno
        print("✅ Se ha construido el oraculo interno correspondiente para usarlo despues en Grover")
    else:
        print("⚠️ No se ha podido asociar un oraculo interno especifico; se tratara como oraculo arbitrario")


if __name__ == "__main__":
    main()