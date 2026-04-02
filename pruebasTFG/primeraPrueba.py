from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
import numpy as np
import matplotlib.pyplot as plt

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
    # Aplicamos H a todos los qubits
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
# |t> = solución
# |r> = superposición uniforme de los no-solución
# Esto nos permite reducir el problema de muchas dimensiones a solo 2
###########################
def build_grover_basis(n, solution_index):
    # Calculamos el número total de estados posibles con n qubits, que es 2^n
    N = 2**n

    # Creamos el vector solucion, poniendo todo los elementos 0 menos el índice de la solución, que ponemos a 1
    ket_t = np.zeros(N, dtype=complex)
    ket_t[solution_index] = 1.0
    # Creamos el siguiente vector, poniendo todo los elementos a 1, excepto el índice de la solución, que ponemos a 0
    ket_r = np.ones(N, dtype=complex)
    ket_r[solution_index] = 0.0
    # Ahora vamos a normaliar el vector para que se valido en cuantica, teniendo en cuenta que todos los valores deben de sumar 1 para que sea valido
    # Si tenemos [1, 1, 0, 1], se hace raíz de (1² + 1² + 0² + 1²), que es √(1 + 1 + 0 + 1) = √3, por lo tanto luego se hace ket_r / √3, quedando [1/√3, 1/√3, 0, 1/√3], asi de esta forma:(1/√3)² + (1/√3)² + (1/√3)² = 1 
    ket_r /= np.linalg.norm(ket_r)

    return ket_r, ket_t


###########################
# PROYECCIÓN CORRECTA
# con corrección de fase global
###########################
def project_state(statevector, solution_index, n):
    # Sacamos amplitudes
    amps = statevector.data
    print("Aplitudes:", amps)
    # Construimos los vectores
    ket_r, ket_t = build_grover_basis(n, solution_index)

    # coeficientes en la base {|r>, |t>}
    c_r = np.vdot(ket_r, amps)
    c_t = np.vdot(ket_t, amps)

    # fijar fase global para que c_r sea real positivo
    if abs(c_r) > 1e-12:
        phase = np.exp(-1j * np.angle(c_r))
        c_r *= phase
        c_t *= phase
    print(f"Después de corrección de fase: c_r = {c_r.real}, c_t = {c_t.real}")
    return c_r.real, c_t.real


# =========================
# ITERACIONES ÓPTIMAS
# para una sola solución
# =========================
def optimal_iterations(n):
    N = 2**n
    return int(np.floor((np.pi / 4) * np.sqrt(N)))


# =========================
# CIRCUITO + CAPTURA DE ESTADOS
# =========================
def build_grover_states(n, solution, iterations=None):
    if len(solution) != n:
        raise ValueError("La longitud de solution debe coincidir con n.")

    if iterations is None:
        #iterations = optimal_iterations(n) CON OVERSHOOT
        #SIN OVERSHOOT, PARA VER LA ROTACIÓN COMPLETA
        iterations = optimal_iterations(n) - 1

    qc = QuantumCircuit(n)
    states = []
    labels = []

    # estado inicial |0...0>
    states.append(get_state(qc))
    print(states)
    labels.append("init")

    # superposición uniforme
    qc.h(range(n))
    states.append(get_state(qc))
    labels.append("H")

    for i in range(iterations):
        oracle(qc, solution)
        states.append(get_state(qc))
        labels.append(f"oracle_{i+1}")

        diffuser(qc, n)
        states.append(get_state(qc))
        labels.append(f"diffuser_{i+1}")

    return qc, states, labels


# =========================
# DIBUJO
# =========================
def plot_grover_rotation(n, solution, iterations=None):
    qc, states, labels = build_grover_states(n, solution, iterations)

    solution_index = int(solution, 2)
    points = [project_state(s, solution_index, n) for s in states]

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    plt.figure(figsize=(8, 6))

    # ejes del plano
    plt.axhline(0, linewidth=1)
    plt.axvline(0, linewidth=1)

    # vectores desde el origen
    for (x, y), label in zip(points, labels):
        plt.quiver(
            0, 0, x, y,
            angles="xy",
            scale_units="xy",
            scale=1,
            width=0.004
        )
        plt.text(x + 0.01, y + 0.01, label)

    # trayectoria entre puntos
    plt.plot(xs, ys, "--", marker="o")

    plt.xlabel("componente en |r⟩ (no-solución uniforme)")
    plt.ylabel("componente en |t⟩ (solución)")
    plt.title(f"Grover con {n} qubits, solución = |{solution}⟩")

    plt.xlim(-0.1, 1.05)
    plt.ylim(-1.05, 1.05)
    plt.grid(True)

    plt.show()

    return qc, states, labels, points


# =========================
# EJEMPLO
# =========================
qc, states, labels, points = plot_grover_rotation(
    n=5,
    solution="10101"
)