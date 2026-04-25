from qiskit import QuantumCircuit
from qiskit.qasm2 import dumps

def mark_state_phase(qc, state_bits):
    n = len(state_bits)

    for i, bit in enumerate(reversed(state_bits)):
        if bit == "0":
            qc.x(i)

    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)

    for i, bit in enumerate(reversed(state_bits)):
        if bit == "0":
            qc.x(i)

def add_diffuser(qc, n):
    qc.h(range(n))
    qc.x(range(n))
    qc.h(n - 1)
    qc.mcx(list(range(n - 1)), n - 1)
    qc.h(n - 1)
    qc.x(range(n))
    qc.h(range(n))

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

def estados_marcados(tipo, n, parametro=None):
    N = 2**n

    if tipo == "equal":
        return [parametro]

    if tipo == "less":
        return list(range(parametro))

    if tipo == "greater":
        return list(range(parametro + 1, N))

    if tipo == "evens":
        return [i for i in range(N) if i % 2 == 0]

    if tipo == "primes":
        return [i for i in range(N) if es_primo(i)]

    raise ValueError("Tipo no valido")

def generar_qasm_y_csv(tipo, n, parametro=None):
    marcados = estados_marcados(tipo, n, parametro)

    qc = QuantumCircuit(n)
    qc.h(range(n))

    for value in marcados:
        bits = format(value, f"0{n}b")
        mark_state_phase(qc, bits)

    add_diffuser(qc, n)

    if parametro is None:
        base = f"{tipo}_{n}q"
    else:
        base = f"{tipo}_{parametro}_{n}q"

    qasm_name = f"{base}.qasm"
    csv_name = f"{base}.csv"

    with open(qasm_name, "w") as f:
        f.write(dumps(qc))

    with open(csv_name, "w") as f:
        for value in marcados:
            f.write(f"{value}\n")

    print(f"Generados: {qasm_name} y {csv_name}")