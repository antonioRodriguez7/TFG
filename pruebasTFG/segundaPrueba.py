from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from qiskit.circuit.library import MCXGate
import random

# =========================
# ORACULOS
# =========================

def mark_one(number, nqubits, name=None):

    if isinstance(number, str):
        binary = number.zfill(nqubits)
    else:
        binary = format(number, f"0{nqubits}b")

    if name:
        circuit = QuantumCircuit(nqubits, name=name)
    else:
        circuit = QuantumCircuit(nqubits, name=f"== {number}")

    # Preparación
    for i, bit in enumerate(reversed(binary)):
        if bit == '0':
            circuit.x(i)

    # Fase
    circuit.h(nqubits - 1)
    circuit.mcx(list(range(nqubits - 1)), nqubits - 1)
    circuit.h(nqubits - 1)

    # Deshacer
    for i, bit in enumerate(reversed(binary)):
        if bit == '0':
            circuit.x(i)

    return circuit

# =========================
# ORACULO MAYOR QUE
# =========================

def oracle_greater(number, nqubits, name=None):

    if isinstance(number, str):
        number = int(number, 2)

    if name:
        circuit = QuantumCircuit(nqubits, name=name)
    else:
        circuit = QuantumCircuit(nqubits, name=f"> {number}")

    if number < (2**nqubits):
        number = number + 1

    less_than = oracle_less(number, nqubits)

    circuit.append(less_than.to_gate(), list(range(nqubits)))

    circuit.global_phase += np.pi

    return circuit
# =========================
# ORACULO MENOR QUE
# =========================
def oracle_less(number:int, nqubits:int, name=None):

    if name:
        circuit = QuantumCircuit(nqubits, name=name)
    else:
        circuit = QuantumCircuit(nqubits, name=f"< {number}")

    num_binary = to_binary(number, nqubits)
    num_binary = to_binary(number, nqubits)

    if num_binary[0] == "1":
        circuit.x(nqubits-1)
        circuit.z(nqubits-1)
        circuit.x(nqubits-1)
    else:
        circuit.x(nqubits-1)

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


def to_binary(number:int, nbits: int | None = None) -> str:
    # Convertir el número a binario y eliminar el prefijo '0b'
    binary = bin(number)[2:]  

    # Sin nbits devuelve el binario "natural"
    if nbits is None:
        return binary
    
    if nbits < len(binary):
        raise ValueError(f"nbits must be >= {len(binary)} ")
    
    return binary.zfill(nbits)  # Rellenar con ceros a la izquierda para alcanzar nbits


def multi_control_z(nqubits:int) -> QuantumCircuit:

    '''
    Function to create a multi-controlled Z gate.

    Input:
    nqubits: Integer (int) of the number of qubits in the gate (controls and target)
        This means that the gate has nqubits-1 controls and 1 target.

    Output:
    circuit: QuantumCircuit containing a multi-controlled Z gate.
        It has to be transformed with method .to_gate() to append to a QuantumCircuit larger.

    Example:

    main_circuit = QuantumCircuit(nqubits)

    gate_multi_z = multi_control_z(nqubits)

    main_circuit.append(gate_multi_z.to_gate(), range(nqubits))

    '''

    # Crea un circuito con nqubits y le asigna un nombre que indica que es una puerta MCZ con nqubits
    circuit = QuantumCircuit(nqubits, name = f"MCZ({nqubits})")

    # Aplica una puerta Hadamard al último qubit para preparar el estado de control
    circuit.h(nqubits-1)
    # Esto convertira todos los qubits en controles menos el ultimo que sera el target
    # El objetivo es que si todos los qubits de control son 1, aplicamos NOT al ultimo qubit, lo que equivale a aplicar una puerta Z al estado |1> del ultimo qubit
    circuit.append(MCXGate(nqubits - 1), range (nqubits))
    # Deshacemos cambios en el ultimo qubit para volver a su estado original
    circuit.h(nqubits-1)

    # CAMBIA LA FASE DEL ESTADO OBJETIVO

    return circuit









###########################
# ORÁCULO GENERAL
# Marcamos la solucion con fase negativa
###########################
def oracle(qc, solution):
    n = len(solution)
    # Si tenemos 1011 nosotros interpretamos como q0, q1, q2, q3 pero qiskit lo interpreta al revés, esto sucede porque en informatica clasica, los numeros binarios se interpretan
    # de esa forma, siendo el bit de la derecha el menos significativo, por eso Qiskit lo interpreta al revés.
    # Para ello usamos el 'reserved' para invertir el orden de los bits, así el bit de la derecha (menos significativo) se corresponde con el qubit 0, y el bit de la izquierda (más significativo) se corresponde con el qubit n-1.
    # Tras esto recorremos bit a bit y cambiamos 0 por 1, para luego modificar la fase del estado objetivo.
    for i, bit in enumerate(reversed(solution)):
        if bit == '0':
            qc.x(i)
    # Al aplicar H convertimos |1> en |->, ya que  convertimos: |+> = (|0> + |1>) y |-> = (|0> - |1>)
    qc.h(n - 1)
    # Aplicamos MCX, que en Qiskit significa: “Si TODOS los qubits de control están a 1 → aplica una X al qubit objetivo”
    # El list(range(n - 1)): genera una lista para los qubits de control, si tenemos 5 qubits genera [0, 1, 2, y 3]
    # El n - 1: es el qubit objetivo, en este caso el qubit 4 (el más significativo)
    # Esto quiere decir: “Si los qubits 0,1,2,3 están TODOS en 1 → aplica una X al qubit 4”
    # Con mode="noancilla" le decimos a Qiskit que no use qubits auxiliares para implementar el MCX, lo cual es posible si el número de qubits de control es menor o igual a 4.
    qc.mcx(list(range(n - 1)), n - 1, mode="noancilla")
    # Volvemos a aplicar H para convertir |-> de nuevo en |1>, pero ya con la fase negativa aplicada al estado objetivo.
    qc.h(n - 1)
    # Vueve al estado original pero con la fase negativa aplicada al estado objetivo, por eso volvemos a recorrer los bits y cambiamos 0 por 1.
    for i, bit in enumerate(reversed(solution)):
        if bit == '0':
            qc.x(i)

###########################
# DIFUSOR GENERAL
# #########################
def diffuser(qc, n):
    qc.h(range(n))
    qc.x(range(n))

    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1, mode="noancilla")
    qc.h(n - 1)

    qc.x(range(n))
    qc.h(range(n))

###########################
# EXTRAER ESTADO
###########################
def get_state(qc):
    return Statevector.from_instruction(qc)

###########################
# BASE DEL PLANO DE GROVER
# |t> = superposición uniforme de las soluciones
# |r> = superposición uniforme de las no-soluciones
# Esto nos permite reducir el problema de muchas dimensiones a solo 2
###########################
def build_grover_basis(n, solution_indices):
    # Calculamos el número total de estados posibles con n qubits, que es 2^n
    N = 2**n

    # Creamos el vector solucion, poniendo a 1 las posiciones que son solucion y a 0 el resto
    ket_t = np.zeros(N, dtype=complex)
    for index in solution_indices:
        ket_t[index] = 1.0

    # Normalizamos el vector solucion para que sea valido en cuantica
    # Si por ejemplo hay 3 soluciones, el vector tendra tres unos y se divide entre raiz de 3
    if np.linalg.norm(ket_t) > 1e-12:
        ket_t /= np.linalg.norm(ket_t)

    # Creamos el vector no-solucion, poniendo a 1 las posiciones que no son solucion y a 0 las soluciones
    ket_r = np.ones(N, dtype=complex)
    for index in solution_indices:
        ket_r[index] = 0.0

    # Normalizamos el vector de no-solucion
    if np.linalg.norm(ket_r) > 1e-12:
        ket_r /= np.linalg.norm(ket_r)

    return ket_r, ket_t

###########################
# PROYECCIÓN CORRECTA
# con corrección de fase global
###########################
def project_state(statevector, solution_indices, n):
    # Sacamos amplitudes
    amps = statevector.data

    # Construimos los vectores
    ket_r, ket_t = build_grover_basis(n, solution_indices)

    # Calculamos c_r y c_t que es simplemente multiplicando nuestros vectores por las amplitudes
    c_r = np.vdot(ket_r, amps)
    c_t = np.vdot(ket_t, amps)

    # Primero comprobamos que c_r no es prácticamente cero, para evitar problemas de división por cero al calcular la fase.
    if abs(c_r) > 1e-12:
        # Creamos un numero que corrige ese angulo
        phase = np.exp(-1j * np.angle(c_r))

        # Multiplicamos para corregir la fase global del estado y hacer que c_r sea real positivo
        c_r *= phase
        c_t *= phase

    return c_r.real, c_t.real

###########################
# ITERACIONES ÓPTIMAS
###########################
def optimal_iterations(n, M, choice):

    # Calculamos el numero total de estados posibles
    N = 2**n

    # Si el oraculo es de tipo "one" usamos la formula clasica
    # Esto corresponde al caso de una unica solucion
    # Le restamos 1 para que se comporte igual que el programa antiguo
    if choice == "one":
        return max(0, int(np.floor((np.pi / 4) * np.sqrt(N))) - 1)

    # Si no, usamos la formula general para multiples soluciones
    # Evitamos division por cero por seguridad
    if M == 0:
        return 0

    return int(np.floor((np.pi / 4) * np.sqrt(N / M)))

###########################
# ANALIZAR GROVER
# Este metodo contruye la evolucion de Grover paso a paso y guarda el estado después de cada paso
###########################
def analyze_grover(n, number, choice):
    qc = QuantumCircuit(n)

    # Lista que ira almacenando los estados después de cada paso
    states = []  

    # Lista que ira almacenando las etiquetas para cada estado, por ejemplo "oracle_1", "diffuser_1", etc.
    labels = []

    # Al principio guardamos el estado inicial, que es |0>
    states.append(get_state(qc))
    labels.append("init")

    # Aplicamos Hadamard a todos los qubits para crear la superposición uniforme |s⟩
    qc.h(range(n))
    states.append(get_state(qc))
    labels.append("|s⟩")

    # Elegimos el oraculo una sola vez
    if choice == "one":
        oracle_circuit = mark_one(number, n)
        oracle_label = f"== {number}"

    elif choice == "less":
        oracle_circuit = oracle_less(number, n)
        oracle_label = f"< {number}"

    else:
        oracle_circuit = oracle_greater(number, n)
        oracle_label = f"> {number}"

    # Calculamos numero de soluciones
    M = compute_M(choice, number, n)
    print("Numero de soluciones (M):", M)

    # Calculamos numero de iteraciones optimas
    iterations = optimal_iterations(n, M, choice)
    if iterations == 0:
        print("Caso no interesante para visualizar")
        return [], [], choice
    print("Numero de iteraciones:", iterations)

    # Aplicamos las iteraciones de Grover con el mismo esquema del programa antiguo:
    # oraculo -> difusor
    for i in range(iterations):
        # Marcamos solucion
        qc.append(oracle_circuit.to_gate(), list(range(n)))
        states.append(get_state(qc))
        labels.append(rf"$O_{{{i+1}}}$ ({oracle_label})")

        # Applicamos el difusor para amplificar la solucion
        diffuser(qc, n)
        states.append(get_state(qc))
        labels.append(rf"$D_{{{i+1}}}$")

    # DEBUG
    for i in range(len(states)):
        print("Estados:", states[i])

    print(qc.draw())

    return states, labels, choice

###########################
# OBTENER SOLUCIONES DEL ORACULO
# Devuelve los indices de los estados que son solucion segun el oraculo usado
###########################
def get_solution_indices(choice, number, n):

    # Calculamos el numero total de estados posibles
    N = 2**n

    # Si el oraculo marca solo un numero, la unica solucion es ese numero
    if choice == "one":
        return [number]

    # Si el oraculo marca los menores, las soluciones son desde 0 hasta number-1
    elif choice == "less":
        return list(range(number))

    # Si el oraculo marca los mayores, las soluciones son desde number+1 hasta N-1
    else:
        return list(range(number + 1, N))

###########################
# VISUALIZACIÓN 
###########################
def plot_grover_step_by_step(states, labels, n, number, choice):

    solution_indices = get_solution_indices(choice, number, n)

    num_plots = (len(states) - 2) // 2
    fig, axes = plt.subplots(1, num_plots, figsize=(5 * num_plots, 5))

    # Si solo hay una iteración, axes no es lista → lo convertimos
    if num_plots == 1:
        axes = [axes]

    plot_idx = 0

    for k in range(4, len(states) + 1, 2):

        ax = axes[plot_idx]
        plot_idx += 1

        partial_states = states[:k]
        partial_labels = labels[:k]

        # Proyección
        points = [project_state(s, solution_indices, n) for s in partial_states]

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        # Ejes
        ax.axhline(0, linewidth=1.2)
        ax.axvline(0, linewidth=1.2)

        # Base |r⟩
        ax.quiver(
            0, 0, 1, 0,
            angles="xy",
            scale_units="xy",
            scale=1,
            linestyle='dashed',
            color="black"
        )
        ax.text(1.05, 0, "|r⟩", fontsize=12)

        # Base |t⟩
        ax.quiver(
            0, 0, 0, 1,
            angles="xy",
            scale_units="xy",
            scale=1,
            linestyle='dashed',
            color="black"
        )
        ax.text(0, 1.05, "|t⟩", fontsize=12)

        # Dibujar vectores
        for (x, y), label in zip(points[1:], partial_labels[1:]):

            color = "black"

            if "O" in label:
                color = "red"
            elif "D" in label:
                color = "blue"
            elif label == "|s⟩":
                color = "green"

            ax.quiver(
                0, 0, x, y,
                angles="xy",
                scale_units="xy",
                scale=1,
                color=color,
                width=0.006,
                alpha=0.85
            )

            ax.text(x + 0.04, y + 0.04, label, fontsize=9)

        # Trayectoria
        ax.plot(xs, ys, linestyle="--", linewidth=2, marker="o", color="gray")

        # Título por iteración
        iteracion = (k // 2) - 1
        ax.set_title(f"Iter {iteracion}")

        # Escala fija (IMPORTANTE)
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1.2, 1.2)

        ax.set_aspect('equal')
        ax.grid(alpha=0.3)

    # Título general
    plt.suptitle(f"Grover paso a paso (n={n}, número={number}, tipo={choice})")

    plt.tight_layout()
    plt.show()

        


###########################
# NUMERO DE SOLUCIONES
# M = numero de estados que cumplen la condicion del oraculo
###########################
def compute_M(choice, number, n):

    # Calculamos el numero total de estados posibles
    N = 2**n

    # Si el oraculo marca solo un numero, entonces solo hay una solucion
    if choice == "one":
        return 1

    # Si el oraculo marca los menores, las soluciones son:
    # 0, 1, 2, ..., number-1
    elif choice == "less":
        return number

    # Si el oraculo marca los mayores, las soluciones son:
    # number+1, ..., N-1
    else:
        return N - (number + 1)
# =========================
# MAIN
# =========================
import random

def main():
    while True:
        n = random.randint(3, 7)
        number = random.randint(0, 2**n - 1)

        choice = random.choice(["one","less", "greater"])

        M = compute_M(choice, number, n)
        N = 2**n

        # FILTRO → SOLO casos buenos
        if 1 <= M <= N // 4:
            break

    print("Número de qubits:", n)
    print("Número objetivo:", number)
    print("Oraculo elegido:", choice)

    states, labels, choice = analyze_grover(n, number, choice)
    if not states:
        print("No hay estados para graficar.")
        return
    
    plot_grover_step_by_step(states, labels, n, number, choice)
    

if __name__ == "__main__":
    main()