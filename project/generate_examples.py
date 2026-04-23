from qiskit import QuantumCircuit
from qiskit.qasm2 import dumps

qc = QuantumCircuit(2)

qc.h(0)
qc.h(1)

# ORÁCULO LESS
qc.x(1)
qc.z(1)
qc.x(1)

# DIFUSOR
qc.h(0)
qc.h(1)
qc.x(0)
qc.x(1)

qc.h(1)
qc.cx(0, 1)
qc.h(1)

qc.x(0)
qc.x(1)
qc.h(0)
qc.h(1)

with open("less.qasm", "w") as f:
    f.write(dumps(qc))

print("Generado less.qasm")