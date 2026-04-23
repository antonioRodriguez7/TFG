import tkinter as tk
from tkinter import filedialog
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit.qasm2 import loads, LEGACY_CUSTOM_INSTRUCTIONS  
import numpy as np


class CircuitAnalyzer:

    def obtener_parametros_desde_qasm(self):
        root = tk.Tk()
        root.withdraw()
        root.update()

        path = filedialog.askopenfilename(
            title="Selecciona un circuito Grover (.qasm)",
            initialdir="examples",
            filetypes=[("Archivos QASM", "*.qasm")]
        )

        root.destroy()

        if not path:
            print("No se seleccionó archivo")
            return None

        qc = self.cargar_circuito(path)

        resultado = self.detectar_oraculo(qc)

        if resultado is None:
            print("No es un circuito de Grover válido")
            return None

        print(f"Oráculo detectado: {resultado}")

        if "equal" in resultado:
            choice = "one"
            number = int(resultado.split("(")[1].replace(")", ""))
        elif "less" in resultado:
            choice = "less"
            number = int(resultado.split("(")[1].replace(")", ""))
        elif "greater" in resultado:
            choice = "greater"
            number = int(resultado.split("(")[1].replace(")", ""))
        else:
            print("Tipo de oráculo no soportado")
            return None

        n = qc.num_qubits
        return n, number, choice
    

    ###################################################3

    def detectar_oraculo(self, qc):

        ops = qc.data
        n = qc.num_qubits

        # 1️⃣ Detectar fin de Hadamards iniciales
        h_count = 0
        inicio_oraculo = 0

        for i, instr in enumerate(ops):
            if instr.operation.name == "h":
                h_count += 1
                if h_count == n:
                    inicio_oraculo = i + 1
                    break

        # 2️⃣ Detectar inicio del difusor
        inicio_difusor = self.detectar_inicio_difusor(
            ops, inicio_oraculo, n
        )

        if inicio_difusor is None:
            return None

        # 3️⃣ Extraer bloque ORÁCULO limpio
        bloque = ops[inicio_oraculo:inicio_difusor]
        oracle_qc = self.construir_subcircuito(bloque, n)

        # 4️⃣ Analizar
        solutions = self.soluciones_de_oraculo(oracle_qc)

        if solutions is None:
            return None

        # 5️⃣ Corregir endianness
        solutions_corr = self.corregir_endianness(solutions, n)

        # 6️⃣ Clasificar
        return self.clasificar_soluciones(solutions_corr, n)

    def cargar_circuito(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return loads(
                f.read(),
                custom_instructions=LEGACY_CUSTOM_INSTRUCTIONS
            )

    def detectar_inicio_difusor(self, ops, inicio, n):

        for i in range(inicio, len(ops) - 3):

            nombres = [
                ops[i + k].operation.name
                for k in range(min(6, len(ops) - i))
            ]

            if (
                nombres.count("x") >= n and
                nombres.count("h") >= n and
                any(g in nombres for g in ["cx", "ccx", "mcx"])
            ):
                return i

        return None

    def clasificar_soluciones(self, solutions, n):

        N = 2 ** n
        solutions = sorted(solutions)

        if len(solutions) == 1:
            return f"equal({solutions[0]})"

        for k in range(N + 1):
            if solutions == list(range(k)):
                return f"less_than({k})"

        for k in range(-1, N):
            if solutions == list(range(k + 1, N)):
                return f"greater_than({k})"

        return "desconocido"

    def corregir_endianness(self, indices, n):
        corregidos = []

        for i in indices:
            b = format(i, f"0{n}b")
            b_inv = b[::-1]
            corregidos.append(int(b_inv, 2))

        return sorted(corregidos)

    def construir_subcircuito(self, ops, n):
        qc = QuantumCircuit(n)
        for instr in ops:
            qc.append(instr.operation, instr.qubits, instr.clbits)
        return qc

    def soluciones_de_oraculo(self, qc):
        n = qc.num_qubits

        init = QuantumCircuit(n)
        init.h(range(n))

        before = Statevector.from_instruction(init)
        after = Statevector.from_instruction(init.compose(qc))

        amps_before = before.data
        amps_after = after.data

        solutions = []
        mezcla = False

        for i in range(len(amps_before)):
            if np.isclose(amps_after[i], -amps_before[i]):
                solutions.append(i)
            elif not np.isclose(amps_after[i], amps_before[i]):
                mezcla = True

        if mezcla or len(solutions) == 0:
            return None

        return solutions