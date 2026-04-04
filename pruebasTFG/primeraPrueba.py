from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

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

    # Calculamos c_r y c_t que es simplemente multiplicando nuestros vectores por las amplitudes
    c_r = np.vdot(ket_r, amps)
    c_t = np.vdot(ket_t, amps)

    # Primero comprobamos que c_r no es prácticamente cero, para evitar problemas de división por cero al calcular la fase. Si c_r es muy pequeño, no aplicamos corrección de fase.
    if abs(c_r) > 1e-12:
        # Creamos un numero que corrige ese angulo, por ejemplo si c_r = -0.866 entonces phase = -1
        phase = np.exp(-1j * np.angle(c_r))
        # Multiplicamos y si antes teniamos que c_r = -0.866, ahora c_r = -0.866 * (-1) = 0.866, es decir, ahora c_r es real positivo, y lo mismo para c_t, si antes teniamos c_t = 0.5 + 0.5j, ahora c_t = (0.5 + 0.5j) * (-1) = -0.5 - 0.5j, es decir, hemos corregido la fase global de nuestro estado para que c_r sea real positivo.
        c_r *= phase
        c_t *= phase
    return c_r.real, c_t.real

###########################
# ITERACIONES ÓPTIMAS
###########################
def optimal_iterations(n):
    N = 2**n
    return int(np.floor((np.pi / 4) * np.sqrt(N)))


###########################
# ANALIZAR GROVER
# Este metodo contruye la evolucion de Grover paso a paso y guarda el estado después de cada paso
###########################
def analyze_grover(n, solution, iterations):
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

    for i in range(iterations):
        # Marcamos solucion
        oracle(qc, solution)
        states.append(get_state(qc))
        labels.append(rf"$O_{{{i+1}}}$")
        # Applicamos el difusor para amplificar la solucion
        diffuser(qc, n)
        states.append(get_state(qc))
        labels.append(rf"$D_{{{i+1}}}$")

    for i in range(len(states)):
        print("Estados:", states[i])

    print(qc.draw())
        
    return states, labels

###########################
# VISUALIZACIÓN MEJORADA
###########################
def plot_grover(states, labels, n, solution):
    # Convertimos binario a numero
    solution_index = int(solution, 2)
    # Convertimos en puntos todos los estados
    points = []

    for s in states:
        punto = project_state(s, solution_index, n)
        points.append(punto)    
    # Extraemos las componentes x e y de cada punto para graficar la trayectoria
    xs = []
    ys = []

    for p in points:
        xs.append(p[0])
        ys.append(p[1])

    # Creamos la figura
    plt.figure(figsize=(9, 7))

    # Ejes
    plt.axhline(0, linewidth=1.2)
    plt.axvline(0, linewidth=1.2)

    # Base |r⟩ y |t⟩
    plt.quiver(0, 0, 1, 0, angles="xy", scale_units="xy", scale=1,
               linestyle='dashed', color="black")
    plt.text(1.05, 0, "|r⟩", fontsize=12)

    plt.quiver(0, 0, 0, 1, angles="xy", scale_units="xy", scale=1,
               linestyle='dashed', color="black")
    plt.text(0, 1.05, "|t⟩", fontsize=12)

    # Dibujar vectores
    for (x, y), label in zip(points, labels):
        color = "black"

        if "O" in label:
            color = "red"
        elif "D" in label:
            color = "blue"
        elif label == "|s⟩":
            color = "green"
        # Dibujamos la flecha
        plt.quiver(
            0, 0, x, y,
            color=color,
            scale=1,
            scale_units="xy",
            width=0.006,
            alpha=0.85
        )
        # Añadimos la etiqueta al lado de la flecha
        plt.text(x + 0.04, y + 0.04, label, fontsize=9)

    # Trayectoria
    plt.plot(xs, ys, linestyle="--", linewidth=2, marker="o", color="gray")

    # Leyenda
    red_patch = mpatches.Patch(color='red', label='Oráculo')
    blue_patch = mpatches.Patch(color='blue', label='Difusor')
    green_patch = mpatches.Patch(color='green', label='Estado inicial |s⟩')

    plt.legend(handles=[red_patch, blue_patch, green_patch])

    # Labels
    plt.xlabel("Componente en |r⟩", fontsize=12)
    plt.ylabel("Componente en |t⟩", fontsize=12)
    plt.title(f"Evolución geométrica de Grover (n={n}, solución={solution})", fontsize=14)

    plt.axis("equal")
    plt.xlim(-0.2, 1.2)
    plt.ylim(-1.1, 1.1)
    plt.grid(alpha=0.3)

    plt.show()


# =========================
# MAIN
# =========================
def main():
    n = int(input("Número de qubits: "))
    solution = input("Solución en binario: ")

    iterations = optimal_iterations(n) - 1

    states, labels = analyze_grover(n, solution, iterations)
    plot_grover(states, labels, n, solution)


if __name__ == "__main__":
    main()