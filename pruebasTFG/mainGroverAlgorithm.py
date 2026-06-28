from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.circuit.library import MCXGate
from qiskit.qasm2 import loads, LEGACY_CUSTOM_INSTRUCTIONS
import math
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
import tkinter as tk
from tkinter import filedialog
from matplotlib.patches import Circle, FancyBboxPatch
from matplotlib.offsetbox import TextArea, VPacker, HPacker, AnchoredOffsetbox, DrawingArea

# This method retrieves the index of a qubit. It is used because, depending on the Qiskit version or object type,
# the index may be stored as "_index" or "index". This unifies how the qubit number is accessed, allowing the rest
# of the code to always work in the same way.
def qindex(q):
    if hasattr(q, "_index"):
        return q._index
    return q.index

# This method loads a .qasm file from disk and converts it into a Qiskit QuantumCircuit for later analysis.
# The "path" parameter is the file path selected by the user.
# LEGACY_CUSTOM_INSTRUCTIONS is used to ensure compatibility with certain legacy QASM instructions that might appear.
def cargar_circuito(path):
    with open(path, "r", encoding="utf-8") as f:
        return loads(
            f.read(),
            custom_instructions=LEGACY_CUSTOM_INSTRUCTIONS
        )

# This method reconstructs a subcircuit from a list of operations. It receives:
# - "ops": the operations extracted from the original circuit
# - "n": the total number of qubits in the subcircuit
# It is used to isolate specific parts of the circuit, such as the initial preparation or the block leading up to the oracle.
# For each instruction, it retrieves the qubits it acts upon and adds it to the new subcircuit, maintaining its structure.
def construir_subcircuito_desde_ops(ops, n):
    sub_qc = QuantumCircuit(n)
    for instr in ops:
        qargs = [qindex(q) for q in instr.qubits]
        sub_qc.append(instr.operation, qargs, [])
    return sub_qc
# ********
# DIFFUSOR
# ********
def diffuser(qc, n):
    qc.h(range(n))
    qc.x(range(n))

    qc.h(n - 1)
    qc.append(MCXGate(n - 1), list(range(n)))
    qc.h(n - 1)

    qc.x(range(n))
    qc.h(range(n))

    # Corrects the global phase to obtain D = 2|u><u| - I
    qc.global_phase += np.pi

# This method calculates the optimal number of Grover iterations.
# First, it calculates N = 2^n, which is the total size of the search space. If there are no solutions (M = 0), it returns 0 to avoid an invalid division.
# Otherwise, it applies Grover's theoretical formula and returns the floor value (lower integer part) of the recommended iterations.
def optimal_iterations(n, M):
    N = 2**n

    if M == 0:
        return 0

    return int(np.floor((np.pi / 4) * np.sqrt(N / M)))

# ****************
# INTERNAL ORACLES
# ****************

# This method constructs an oracle that marks a single specific state.
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

# This method converts an integer to binary.
# If "nbits" is not specified, it returns the binary string without padding.
# If "nbits" is specified, it pads with leading zeros until reaching that length.
# It also checks that the requested number of bits is not less than the actual length of the binary number.
def to_binary(number: int, nbits: int | None = None) -> str:
    binary = bin(number)[2:]
    if nbits is None:
        return binary
    if nbits < len(binary):
        raise ValueError(f"nbits must be >= {len(binary)}")
    return binary.zfill(nbits)

# This method constructs a multi-controlled Z gate.
# The implementation temporarily transforms a multi-controlled X gate into a multi-controlled Z gate by applying Hadamard gates before and after on the last qubit.
def multi_control_z(nqubits: int) -> QuantumCircuit:
    circuit = QuantumCircuit(nqubits, name=f"MCZ({nqubits})")
    circuit.h(nqubits - 1)
    circuit.append(MCXGate(nqubits - 1), range(nqubits))
    circuit.h(nqubits - 1)
    return circuit

# This method constructs an oracle that marks all states less than a given number.
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

# This method checks if a number is prime.
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

# This method constructs a general oracle from an explicit list of marked states.
# For each state in the list, it adds the block generated by "mark_one". Duplicates are removed and values are sorted before construction.
def oracle_from_marked_states(marked_states, nqubits, name=None):
    circuit = QuantumCircuit(nqubits, name=name if name else "oracle_marked_states")

    for state in sorted(set(marked_states)):
        circuit.append(mark_one(state, nqubits).to_gate(), range(nqubits))

    return circuit

# This method constructs an oracle that marks all states greater than a given value.
def oracle_greater(number, nqubits, name=None):
    marked = list(range(number + 1, 2**nqubits))
    return oracle_from_marked_states(
        marked,
        nqubits,
        name=name if name else f"> {number}"
    )

# This method constructs an oracle that marks all even states within the search space defined by "nqubits".
def oracle_evens(nqubits, name=None):
    marked = [i for i in range(2**nqubits) if i % 2 == 0]
    return oracle_from_marked_states(
        marked,
        nqubits,
        name=name if name else "evens"
    )

# This method constructs an oracle that marks all prime states within the search space defined by "nqubits".
def oracle_primes(nqubits, name=None):
    marked = [i for i in range(2**nqubits) if es_primo(i)]
    return oracle_from_marked_states(
        marked,
        nqubits,
        name=name if name else "primes"
    )

# This method constructs an expected oracle from the marked states read from the CSV file.
# It uses: "soluciones_csv": list of states that should be marked and "n": number of qubits in the circuit
def construir_oraculo_esperado_desde_csv(soluciones_csv, n):
    return oracle_from_marked_states(soluciones_csv, n, name="oracle_csv")

# This method calculates what the oracle's output vector should be if the circuit behaves exactly as indicated by the CSV.
# It uses:
# - "psi_in": input state to the oracle
# - "soluciones_csv": states that should be marked
# - "n": number of qubits
# First, it constructs the expected oracle and then applies it to the input state to obtain the theoretical output vector.
def obtener_vector_esperado_desde_csv(psi_in, soluciones_csv, n):
    oracle_esperado = construir_oraculo_esperado_desde_csv(soluciones_csv, n)
    psi_out_esperado = psi_in.evolve(oracle_esperado)
    return psi_out_esperado

# This method checks if the circuit begins with a Hadamard layer applied to all qubits, as expected in the initial preparation
# of Grover's algorithm. First, it verifies that the circuit has at least n operations.Then, it checks that the first n
# operations are H gates and that they cover exactly all qubits in the circuit.
def es_capa_h_inicial(qc):
    n = qc.num_qubits

    if len(qc.data) < n:
        return False

    primeras = qc.data[:n]

    if not all(instr.operation.name == "h" for instr in primeras):
        return False

    qubits = [qindex(instr.qubits[0]) for instr in primeras]
    return sorted(qubits) == list(range(n))

# This method finds the position in the circuit where the diffuser begins. To do this, it iterates through
# the operations and tries to recognize the characteristic pattern formed by a Hadamard layer followed by a layer
# of X gates on all qubits. If it finds this pattern, it returns the start position of the diffuser.
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

# This method separates from the circuit the main parts needed to analyze Grover. First, it checks that an initial
# Hadamard layer exists and that the start of the diffuser can be detected. If both conditions are met, it extracts:
# - the initial preparation
# - the block ranging from the beginning to the end of the oracle
# and returns this information in an organized structure.
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

# This method obtains the two main vectors used to analyze the behavior of the user's oracle.
# First, it extracts the relevant components from the Grover circuit. Then, it calculates:
# - "psi_in": the state after the uniform preparation
# - "psi_out": the state after applying the oracle
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

# This method detects which states have been marked by the oracle by comparing the input vector and the output vector.
# The idea is simple: if an amplitude goes from "a" to "-a", it means that state has undergone the oracle's phase inversion.
def detectar_estados_marcados_desde_vectores(psi_in, psi_out, tol=1e-8):
    marcados = []

    amps_in = psi_in.data
    amps_out = psi_out.data

    for i in range(len(amps_in)):
        if np.allclose(amps_out[i], -amps_in[i], atol=tol):
            marcados.append(i)

    return marcados

# This method attempts to classify the detected oracle based on the pattern of marked states.
# It checks if that pattern matches any of the supported types: "equal", "less", "greater", "evens", or "primes".
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

# This method displays a summary of the analysis performed on the QASM circuit.
# Additionally, it detects the marked states and classifies the oracle type,
# storing both results inside "componentes" to reuse them later in validation and simulation.
def mostrar_resumen_qasm(componentes):
    n = componentes["n"]
    inicio_difusor = componentes["inicio_difusor"]
    psi_in = componentes["psi_in"]
    psi_out = componentes["psi_out"]

    print("RESUMEN DEL QASM ANALIZADO")
    print("--------------------------")
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

# *******
# CSV
# *******

# This method opens a window for the user to select the QASM file containing the circuit to be analyzed.
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

# This method opens a window for the user to select the reference CSV file.
# That CSV can contain marked states or an expected statevector.
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

# This method reads a CSV file, interpreting it as a list of marked states.
# It verifies that each line is a valid integer and that it falls within the allowed range, which goes from 0 to 2^n - 1.
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

# This method decides how the CSV content should be interpreted. It reads the first non-empty line and checks if
# it can be converted to an integer. If it can, the CSV is interpreted as a list of marked states.
# If it cannot, it is interpreted as a statevector.
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

# This method reads a CSV file, interpreting it as a statevector. Each line must contain a complex amplitude. It also verifies that:
# - the number of amplitudes matches 2^n
# - the vector does not have a norm of zero
# - the vector is normalized
# If everything is correct, it returns the statevector as a Qiskit object.
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

# First, it detects whether the content represents a list of states or a statevector. It returns a structure with:
# - the detected CSV type
# - the list of solutions, if it exists
# - or the statevector, if it exists
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


# This method compares the list of marked states detected in the QASM with the list of states read from the CSV.
# It sorts both lists before comparing them to prevent the result from depending on the order in which the states appear.
def comparar_soluciones_detectadas_con_csv(soluciones_detectadas, soluciones_csv):
    return sorted(soluciones_detectadas) == sorted(soluciones_csv)

# This method compares two statevectors allowing for a global phase difference, since that phase does not change the physical state.
# It first looks for a non-zero reference amplitude in the second vector and uses it to calculate the phase factor.
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

# This method compares two classifications. For both to match, they must have the same oracle type
# and also the same associated parameter, if it exists.
def comparar_clasificaciones(clasificacion_qasm, clasificacion_csv):
    return (
        clasificacion_qasm["tipo"] == clasificacion_csv["tipo"] and
        clasificacion_qasm["parametro"] == clasificacion_csv["parametro"]
    )

# This method validates whether the behavior of the oracle contained in the QASM matches the external reference provided in the CSV.
# It uses the information previously extracted from the circuit and compares:
# - the marked states
# - the final vector of the oracle
# - the semantic classification
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

# This method constructs an internal oracle equivalent to the one that has
# been previously detected and validated.
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

# *************
# MAIN WORKFLOW
# *************

# This method runs the main Grover simulation using the already validated internal oracle.
# First, it starts from the initial state, then it creates the uniform state by applying Hadamard to all qubits.
# Next, it calculates the optimal number of iterations and, in each one, applies the oracle and the diffuser.
# After each step, it stores the corresponding statevector, as those states will be used later in the geometric representation.
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

# It prompts the user for the QASM file, loads it, and checks that it has a structure compatible with Grover.
# If the circuit is valid, it obtains the vectors needed to analyze the oracle's behavior.
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

# **************
# REPRESENTATION
# **************

# This method constructs the two-dimensional basis used in the geometric representation. It generates two vectors:
# - "ket_t": the direction associated with the solution states
# - "ket_s": the direction associated with the non-solution states
# Both vectors are normalized to correctly project the quantum states onto the visualization plane.
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

# This method projects a full quantum state onto the two-dimensional basis formed by the solution and non-solution subspaces.
# It returns two real coordinates:
# - component along |s>
# - component along |t>
# These coordinates are the ones used later to plot the geometric evolution of the algorithm on the plane.
def project_state(statevector, solution_indices, n):
    amps = statevector.data
    ket_s, ket_t = build_grover_basis(n, solution_indices)

    c_s = np.vdot(ket_s, amps)
    c_t = np.vdot(ket_t, amps)

    c_s = np.real_if_close(c_s, tol=1000)
    c_t = np.real_if_close(c_t, tol=1000)

    return float(np.real(c_s)), float(np.real(c_t))

# This method formats a number to display it legibly in LaTeX notation.
def format_number_latex(x, sig=4):
    if abs(x) < 1e-12:
        return "0"

    ax = abs(x)
    if ax >= 1e3 or ax < 1e-3:
        exp = int(math.floor(math.log10(ax)))
        mant = x / (10**exp)
        return rf"{mant:.{sig-1}f}\times 10^{{{exp}}}"
    return rf"{x:.{sig}f}"

# This method constructs the LaTeX expression of a state projected into the plane
def state_expression_latex(x, y):
    x_ltx = format_number_latex(x)
    y_abs_ltx = format_number_latex(abs(y))
    signo = "+" if y >= 0 else "-"
    return rf"{x_ltx}\,|s\rangle\ {signo}\ {y_abs_ltx}\,|t\rangle"

# This method groups consecutive values into intervals. For example, a sequence like [3,4,5] is stored as the range (3,5).
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

# This method generates a LaTeX description. It attempts to display that information as naturally as possible according
# to the detected oracle type: equal, less, greater, evens, or primes.
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

# This method generates an additional interpretive text when the number of solutions is high relative to the total size of the space.
# It is used to warn that, in those cases, Grover's advantage is reduced and the geometric rotation may become less intuitive to observe.
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

# This method draws the side panel of the mathematical summary.
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

# This method organizes the complete step-by-step Grover visualization.
# Based on the calculated states, it projects each one onto the representation plane and, for each iteration, creates a figure containing:
# - the main representation
# - the legend
# - the mathematical summary
# - and, if needed, an additional interpretive text.
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

        # main representation panel
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

        # right side
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

        # legend panel
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

        # mathematical summary panel
        ax_math = fig.add_axes([panel_x, y_math, panel_w, h_math])
        dibujar_resumen_matematico(ax_math, datos)

        # additional interpretive text panel
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

        # open the figure in maximized mode, if possible
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

# This method draws a specific iteration of Grover's algorithm. It represents on the plane:
# - the input state of the iteration
# - the state after applying the oracle
# - the state after applying the diffuser
# Additionally, it draws the circle, axes, arrows, rotation arc, and prepares the information used later in the legend and the mathematical summary.
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

    bg_color = "#f3f3f3"
    axis_color = "#222222"
    circle_color = "#444444"
    start_color = "#a9783f"
    oracle_color = "#a9783f"
    diffuser_color = "#f5a623"
    text_red = "#ff2d48"

    R = 0.82

    def normalize(x, y):
        norm = math.sqrt(x * x + y * y)
        if norm < 1e-12:
            return 0.0, 0.0
        return x / norm, y / norm

    def angle_of(x, y):
        return math.atan2(y, x)

    def point_on_circle(r, angle):
        return r * math.cos(angle), r * math.sin(angle)

    def angle_diff(a1, a2):
        diff = a2 - a1
        while diff <= -math.pi:
            diff += 2 * math.pi
        while diff > math.pi:
            diff -= 2 * math.pi
        return diff

    def iteration_theta_label(iteration_number):
        factor = 2 * iteration_number
        if factor == 1:
            return r"$\theta$"
        return rf"${factor}\theta$"

    def draw_base():
        ax.set_facecolor(bg_color)
        ax.set_axisbelow(True)

        circ = Circle(
            (0, 0),
            R,
            fill=False,
            linewidth=1.35,
            edgecolor=circle_color,
            zorder=4
        )
        ax.add_patch(circ)

        ax.plot([-R, R], [0, 0], linewidth=1.25, color=axis_color, zorder=5)
        ax.plot([0, 0], [-R, R], linewidth=1.25, color=axis_color, zorder=5)

        ax.annotate(
            "",
            xy=(R, 0),
            xytext=(0, 0),
            arrowprops=dict(
                arrowstyle="-|>",
                lw=1.25,
                color=axis_color,
                mutation_scale=13,
                shrinkA=0,
                shrinkB=0
            ),
            zorder=6
        )

        ax.annotate(
            "",
            xy=(0, R),
            xytext=(0, 0),
            arrowprops=dict(
                arrowstyle="-|>",
                lw=1.25,
                color=axis_color,
                mutation_scale=13,
                shrinkA=0,
                shrinkB=0
            ),
            zorder=6
        )

        ax.text(
            0,
            R + 0.13,
            r"$|good\rangle$",
            fontsize=15,
            color=axis_color,
            ha="center",
            va="bottom",
            clip_on=False
        )

        ax.text(
            R + 0.065,
            0,
            r"$|bad\rangle$",
            fontsize=15,
            color=axis_color,
            ha="left",
            va="center",
            clip_on=False
        )

    def draw_vector(
        angle,
        color,
        label=None,
        linestyle="-",
        lw=2.0,
        label_r=None,
        label_shift=(0.0, 0.0),
        label_ha="center",
        label_va="center"
    ):
        if label_r is None:
            label_r = R + 0.09

        x2, y2 = point_on_circle(R * 0.99, angle)

        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(0, 0),
            arrowprops=dict(
                arrowstyle="-|>",
                color=color,
                lw=lw,
                linestyle=linestyle,
                mutation_scale=14,
                shrinkA=0,
                shrinkB=0
            ),
            zorder=8
        )

        if label is not None:
            lx, ly = point_on_circle(label_r, angle)
            lx += label_shift[0]
            ly += label_shift[1]

            ax.text(
                lx,
                ly,
                label,
                fontsize=16,
                color=color,
                ha=label_ha,
                va=label_va,
                rotation=0,
                clip_on=False,
                zorder=9
            )

    def draw_arc_from_oracle_to_diffuser(a_oracle, a_diff, label):
        delta = angle_diff(a_oracle, a_diff)
        angles = np.linspace(a_oracle, a_oracle + delta, 120)

        r = 0.34
        xs = r * np.cos(angles)
        ys = r * np.sin(angles)

        ax.plot(
            xs,
            ys,
            color=text_red,
            lw=1.8,
            zorder=7
        )

        if len(xs) >= 3:
            ax.annotate(
                "",
                xy=(xs[-1], ys[-1]),
                xytext=(xs[-3], ys[-3]),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=text_red,
                    lw=1.8,
                    mutation_scale=12
                ),
                zorder=8
            )

        mid = len(xs) // 2

        ax.text(
            xs[mid] + 0.10,
            ys[mid],
            label,
            fontsize=15,
            color="#444444",
            ha="center",
            va="center",
            clip_on=False,
            zorder=9
        )

    xs, ys = normalize(x_start, y_start)
    xo, yo = normalize(x_oracle, y_oracle)
    xd, yd = normalize(x_diff, y_diff)

    theta_start = angle_of(xs, ys)
    theta_oracle = angle_of(xo, yo)
    theta_diff = angle_of(xd, yd)

    draw_base()

    if iteration_number == 1:
        start_display = r"$|all\rangle$"
        start_legend = "u: estado uniforme inicial"
    else:
        start_display = rf"$\psi_{{{iteration_number-1}}}$"
        start_legend = rf"$\psi_{{{iteration_number-1}}}$: estado de entrada a esta iteración"

    draw_vector(
        theta_start,
        start_color,
        label=start_display,
        linestyle=(0, (3, 3)),
        lw=1.45,
        label_r=R + 0.09
    )

    draw_vector(
        theta_oracle,
        oracle_color,
        label=rf"$O_{{{iteration_number}}}$",
        linestyle=(0, (3, 3)),
        lw=1.35,
        label_r=R + 0.09
    )

    draw_vector(
        theta_diff,
        diffuser_color,
        label=rf"$D_{{{iteration_number}}}$",
        linestyle="-",
        lw=2.25,
        label_r=R + 0.09
    )

    label_rotacion = iteration_theta_label(iteration_number)

    draw_arc_from_oracle_to_diffuser(
        theta_oracle,
        theta_diff,
        label_rotacion
    )

    ax.text(
        0.82, 0.97,
        f"Iteración {iteration_number}",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=20,
        fontweight="bold",
        color="black",
        zorder=20
    )

    ax.set_xlim(-1.08, 1.30)
    ax.set_ylim(-1.16, 1.14)
    ax.set_aspect("equal")

    ticks = np.arange(-1.0, 1.01, 0.25)
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.tick_params(axis="both", length=0)

    ax.grid(False)

    for spine in ax.spines.values():
        spine.set_visible(False)

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

# This method draws a specific view of the initial state. Its purpose is to show the starting geometric situation in isolation,
# including the uniform state, the angle θ, and a visual annotation that helps interpret the initial point before applying any iterations.
def draw_initial_state_view(ax, points, labels, n, solution_indices):
    x_u, y_u = points[1]

    color_start = "#148a1f"
    color_oracle = "#e61919"
    color_diff = "#1749ff"
    color_ref_oracle = "#ff9896"
    color_ref_diff = "#9ecae1"

    bg_color = "#f3f3f3"
    axis_color = "#222222"
    circle_color = "#444444"
    all_color = "#a9783f"

    R = 0.82
    N = 2**n
    M = len(solution_indices)

    def normalize(x, y):
        norm = math.sqrt(x * x + y * y)
        if norm < 1e-12:
            return 0.0, 0.0
        return x / norm, y / norm

    def angle_of(x, y):
        return math.atan2(y, x)

    def point_on_circle(r, angle):
        return r * math.cos(angle), r * math.sin(angle)

    def draw_base():
        ax.set_facecolor(bg_color)
        ax.set_axisbelow(True)

        circ = Circle(
            (0, 0),
            R,
            fill=False,
            linewidth=1.35,
            edgecolor=circle_color,
            zorder=4
        )
        ax.add_patch(circ)

        ax.plot([-R, R], [0, 0], linewidth=1.25, color=axis_color, zorder=5)
        ax.plot([0, 0], [-R, R], linewidth=1.25, color=axis_color, zorder=5)

        ax.annotate(
            "",
            xy=(R, 0),
            xytext=(0, 0),
            arrowprops=dict(
                arrowstyle="-|>",
                lw=1.25,
                color=axis_color,
                mutation_scale=13,
                shrinkA=0,
                shrinkB=0
            ),
            zorder=6
        )

        ax.annotate(
            "",
            xy=(0, R),
            xytext=(0, 0),
            arrowprops=dict(
                arrowstyle="-|>",
                lw=1.25,
                color=axis_color,
                mutation_scale=13,
                shrinkA=0,
                shrinkB=0
            ),
            zorder=6
        )

        ax.text(
            0,
            R + 0.11,
            r"$|good\rangle$",
            fontsize=15,
            color=axis_color,
            ha="center",
            va="bottom",
            clip_on=False
        )

        ax.text(
            R + 0.065,
            0,
            r"$|bad\rangle$",
            fontsize=15,
            color=axis_color,
            ha="left",
            va="center",
            clip_on=False
        )

    def draw_vector(angle, color, label=None, linestyle="-", lw=1.8):
        x2, y2 = point_on_circle(R * 0.99, angle)

        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(0, 0),
            arrowprops=dict(
                arrowstyle="-|>",
                color=color,
                lw=lw,
                linestyle=linestyle,
                mutation_scale=14,
                shrinkA=0,
                shrinkB=0
            ),
            zorder=8
        )

        if label is not None:
            lx, ly = point_on_circle(R + 0.08, angle)

            ax.text(
                lx,
                ly,
                label,
                fontsize=16,
                color=color,
                ha="center",
                va="center",
                clip_on=False,
                zorder=9
            )

    def draw_arc(a1, a2, label):
        r = 0.27
        angles = np.linspace(a1, a2, 80)
        xs = r * np.cos(angles)
        ys = r * np.sin(angles)

        ax.plot(xs, ys, color="#444444", lw=1.35, zorder=7)

        mid = len(xs) // 2
        ax.text(
            xs[mid] + 0.035,
            ys[mid],
            label,
            fontsize=15,
            color="#444444",
            ha="center",
            va="center",
            zorder=8
        )

    xu, yu = normalize(x_u, y_u)
    theta_u = angle_of(xu, yu)

    draw_base()

    draw_vector(
        theta_u,
        all_color,
        label=r"$|all\rangle$",
        linestyle="-",
        lw=1.55
    )

    draw_arc(0.0, theta_u, r"$\theta$")

    x_target, y_target = point_on_circle(R * 0.70, theta_u)

    ax.annotate(
        "Estado\ninicial",
        xy=(x_target, y_target),
        xytext=(1.30, 0.38),
        fontsize=15,
        color="#222222",
        ha="left",
        va="center",
        arrowprops=dict(
            arrowstyle="-|>",
            color="#222222",
            lw=1.2,
            shrinkA=5,
            shrinkB=5,
            connectionstyle="arc3,rad=-0.35"
        ),
        zorder=10
    )

    ax.set_title("Estado inicial", fontsize=20, fontweight="bold", pad=18)

    ax.set_xlim(-1.06, 1.78)
    ax.set_ylim(-1.08, 1.10)
    ax.set_aspect("equal")

    ticks = np.arange(-1.0, 1.01, 0.25)
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.tick_params(axis="both", length=0)

    ax.grid(
        True,
        alpha=0.30,
        linestyle=":",
        linewidth=0.8,
        zorder=0
    )

    for spine in ax.spines.values():
        spine.set_visible(False)

    handles = [
        plt.Line2D([0], [0], color=color_start, lw=3, label="u: estado uniforme inicial"),
        plt.Line2D([0], [0], color=color_diff, lw=3, label="D: estado tras aplicar D"),
        plt.Line2D([0], [0], color=color_oracle, lw=3, label=r"$O_f|x\rangle$: estado tras aplicar el oráculo"),
        plt.Line2D([0], [0], color=color_ref_oracle, lw=3, linestyle="--", label="Rotación del oráculo"),
        plt.Line2D([0], [0], color=color_ref_diff, lw=3, linestyle="--", label="Rotación del difusor"),
        plt.Line2D([0], [0], color="black", lw=2, label=r"$|t\rangle$  Estado solución"),
        plt.Line2D([0], [0], color="black", lw=2, label=r"$|s\rangle$  Estado de no soluciones"),
    ]

    expr_u = state_expression_latex(x_u, y_u)
    conjunto_soluciones = marked_states_latex(solution_indices, n)

    resumen_matematico = [
        (rf"$n={n}$", 10.2),
        ("", 2),
        (
            r"$|u\rangle=\frac{1}{\sqrt{2^n}}\sum_{x=0}^{2^n-1}|x\rangle$",
            13.2
        ),
        (
            rf"${expr_u}$",
            9.4,
            22
        ),
        ("", 3),
        (
            "$" + conjunto_soluciones + "$",
            9.2,
            22
        ),
        ("", 2),
        (
            r"$\theta=\arcsin\left(\sqrt{\frac{M}{N}}\right)$",
            12.2
        ),
        (
            rf"$M={M},\quad N={N}$",
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

#It is the method that controls the entire application. It coordinates the complete program flow: circuit loading, CSV reading,
#oracle validation, internal oracle construction, Grover's execution, and final representation.
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
    else:
        print("No se ha podido asociar un oraculo interno especifico; se tratara como oraculo arbitrario")

if __name__ == "__main__":
    main()