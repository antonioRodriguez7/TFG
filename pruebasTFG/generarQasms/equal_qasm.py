from qiskit import QuantumCircuit
from qiskit.qasm2 import dumps

n = 5
qc = QuantumCircuit(n)

target = n - 1
controls = list(range(n - 1))

qc.h(range(n))

qc.h(target)
qc.mcx(controls, target)
qc.h(target)

qc.h(range(n))
qc.x(range(n))
qc.h(target)
qc.mcx(controls, target)
qc.h(target)
qc.x(range(n))
qc.h(range(n))

with open("equal.qasm", "w") as f:
    f.write(dumps(qc))