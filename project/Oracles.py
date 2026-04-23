from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate
import numpy as np


class Oracles:

    def mark_one(self, number, nqubits, name=None):

        if isinstance(number, str):
            binary = number.zfill(nqubits)
        else:
            binary = format(number, f"0{nqubits}b")

        if name:
            circuit = QuantumCircuit(nqubits, name=name)
        else:
            circuit = QuantumCircuit(nqubits, name=f"== {number}")

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

    def oracle_greater(self, number, nqubits, name=None):

        if isinstance(number, str):
            number = int(number, 2)

        if name:
            circuit = QuantumCircuit(nqubits, name=name)
        else:
            circuit = QuantumCircuit(nqubits, name=f"> {number}")

        if number < (2**nqubits):
            number = number + 1

        less_than = self.oracle_less(number, nqubits)

        circuit.append(less_than.to_gate(), list(range(nqubits)))
        circuit.global_phase += np.pi

        return circuit

    def oracle_less(self, number: int, nqubits: int, name=None):

        if name:
            circuit = QuantumCircuit(nqubits, name=name)
        else:
            circuit = QuantumCircuit(nqubits, name=f"< {number}")

        num_binary = self.to_binary(number, nqubits)

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

                multi_z = self.multi_control_z(position + 1)
                circuit.append(
                    multi_z.to_gate(),
                    list(range(nqubits - 1, nqubits - position - 2, -1))
                )

                circuit.x(nqubits - position - 1)

        for position, value in enumerate(num_binary):
            if value == '0':
                circuit.x(nqubits - position - 1)

        return circuit

    def to_binary(self, number: int, nbits: int | None = None) -> str:
        binary = bin(number)[2:]

        if nbits is None:
            return binary

        if nbits < len(binary):
            raise ValueError(f"nbits must be >= {len(binary)} ")

        return binary.zfill(nbits)

    def multi_control_z(self, nqubits: int) -> QuantumCircuit:
        circuit = QuantumCircuit(nqubits, name=f"MCZ({nqubits})")
        circuit.h(nqubits - 1)
        circuit.append(MCXGate(nqubits - 1), range(nqubits))
        circuit.h(nqubits - 1)
        return circuit