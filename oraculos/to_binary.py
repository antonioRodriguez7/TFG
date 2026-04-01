'''
    This fucntion transforms an integer to its binary form (string).
    If a determined number of bits is required (more than the needed ones),
    it can be passed as a parameter too, nbits, None by default.
    It is needed that the number of bits passed as a parameter is larger
    than the number of bits needed to write the number in binary. 

    Input:
    number: integer (int).
    nbits: integer (int), None by default

    Output:
    binary: string (str) containing the number in its binary form.
    It writes 0s in front if nbits is larger than the number of bits needed
    to write the binary form.
    '''

# number:int -> number debe ser un numero entero de tipo int
# nbits: int | None -> nbits debe ser un numero entero de tipo int o None. Sera el numero de qubits del sistema
# -> str -> El retorno que se espera es una cadena de texto que representa el numero en binario
def to_binary(number:int, nbits: int | None = None) -> str:
    # Convertir el número a binario y eliminar el prefijo '0b'
    binary = bin(number)[2:]  

    # Sin nbits devuelve el binario "natural"
    if nbits is None:
        return binary
    
    if nbits < len(binary):
        raise ValueError(f"nbits must be >= {len(binary)} ")
    
    return binary.zfill(nbits)  # Rellenar con ceros a la izquierda para alcanzar nbits
    
n = 7
numbits = 7
print(to_binary(n, numbits))  # Salida: '0000111'