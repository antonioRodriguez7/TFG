from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
import numpy as np
from Oracles import Oracles


class GroverEngine:

    def diffuser(self, qc, n):
        qc.h(range(n))
        qc.x(range(n))

        qc.h(n - 1)
        qc.mcx(list(range(n - 1)), n - 1, mode="noancilla")
        qc.h(n - 1)

        qc.x(range(n))
        qc.h(range(n))

    def get_state(self, qc):
        return Statevector.from_instruction(qc)

    def optimal_iterations(self, n, M, choice):
        N = 2**n

        if choice == "one":
            return max(0, int(np.floor((np.pi / 4) * np.sqrt(N))) - 1)

        if M == 0:
            return 0

        return int(np.floor((np.pi / 4) * np.sqrt(N / M)))

    def analyze_grover(self, n, number, choice):
        qc = QuantumCircuit(n)

        states = []
        labels = []

        states.append(self.get_state(qc))
        labels.append("init")

        qc.h(range(n))
        states.append(self.get_state(qc))
        labels.append("|s⟩")

        oracles = Oracles()

        if choice == "one":
            oracle_circuit = oracles.mark_one(number, n)
            oracle_label = f"== {number}"

        elif choice == "less":
            oracle_circuit = oracles.oracle_less(number, n)
            oracle_label = f"< {number}"

        else:
            oracle_circuit = oracles.oracle_greater(number, n)
            oracle_label = f"> {number}"

        M = self.compute_M(choice, number, n)
        print("Numero de soluciones (M):", M)

        iterations = self.optimal_iterations(n, M, choice)
        if iterations == 0:
            print("Caso no interesante para visualizar")
            return [], [], choice

        print("Numero de iteraciones:", iterations)

        for i in range(iterations):
            qc.append(oracle_circuit.to_gate(), list(range(n)))
            states.append(self.get_state(qc))
            labels.append(rf"$O_{{{i+1}}}$ ({oracle_label})")

            self.diffuser(qc, n)
            states.append(self.get_state(qc))
            labels.append(rf"$D_{{{i+1}}}$")

        for i in range(len(states)):
            print("Estados:", states[i])

        print(qc.draw())

        return states, labels, choice

    def get_solution_indices(self, choice, number, n):
        N = 2**n

        if choice == "one":
            return [number]
        elif choice == "less":
            return list(range(number))
        else:
            return list(range(number + 1, N))

    def compute_M(self, choice, number, n):
        N = 2**n

        if choice == "one":
            return 1
        elif choice == "less":
            return number
        else:
            return N - (number + 1)