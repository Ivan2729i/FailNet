from copy import deepcopy

from src.blockchain.registro_blockchain import RegistroBlockchain

# Cargar la cadena original.
blockchain = RegistroBlockchain()
original = blockchain.obtener_bloques()

print("=" * 50)
print("PRUEBA 1: CADENA ORIGINAL")
print("=" * 50)

print(blockchain.verificar_cadena(original))

# Crear una copia independiente en memoria.
alterada = deepcopy(original)

# Cambiar el contenido del bloque 1.
alterada[1]["tipo"] = "ALTERADO_PRUEBA"

print("\n" + "=" * 50)
print("PRUEBA 2: CADENA MODIFICADA")
print("=" * 50)

print(blockchain.verificar_cadena(alterada))

print("\nEl archivo original no fue modificado.")
