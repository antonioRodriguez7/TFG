from pruebasTFG.generador_oraculos import generar_qasm_y_csv
# equal
generar_qasm_y_csv("equal", 3, 5)
generar_qasm_y_csv("equal", 5, 17)
generar_qasm_y_csv("equal", 7, 85)

# less
generar_qasm_y_csv("less", 3, 5)
generar_qasm_y_csv("less", 5, 12)
generar_qasm_y_csv("less", 7, 40)

# greater
generar_qasm_y_csv("greater", 3, 5)
generar_qasm_y_csv("greater", 5, 12)
generar_qasm_y_csv("greater", 7, 40)

# evens
generar_qasm_y_csv("evens", 3)
generar_qasm_y_csv("evens", 5)
generar_qasm_y_csv("evens", 7)

# primes
generar_qasm_y_csv("primes", 3)
generar_qasm_y_csv("primes", 5)
generar_qasm_y_csv("primes", 7)