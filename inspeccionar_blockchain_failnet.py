
import ast
import json
from pathlib import Path

RAIZ = Path.cwd()
CARPETA = RAIZ / "src" / "blockchain"
ARCHIVO = CARPETA / "registro_blockchain.py"
CADENA = RAIZ / "data" / "blockchain" / "cadena.json"


def describir(nodo):
    parametros = [arg.arg for arg in nodo.args.posonlyargs + nodo.args.args]
    if nodo.args.vararg:
        parametros.append("*" + nodo.args.vararg.arg)
    parametros += [arg.arg for arg in nodo.args.kwonlyargs]
    if nodo.args.kwarg:
        parametros.append("**" + nodo.args.kwarg.arg)
    return f"{nodo.name}({', '.join(parametros)})"


print("=== FAILNET | INSPECCIÓN BLOCKCHAIN ===")
print("Raíz:", RAIZ)

print("\nARCHIVOS EN src/blockchain:")

if CARPETA.exists():
    for archivo in sorted(CARPETA.glob("*.py")):
        print("-", archivo.name)
else:
    print("No existe la carpeta.")

print("\nCLASES Y FUNCIONES:")

if ARCHIVO.is_file():
    codigo = ARCHIVO.read_text(encoding="utf-8-sig")
    arbol = ast.parse(codigo)

    for nodo in arbol.body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            print("Función:", describir(nodo))

        elif isinstance(nodo, ast.ClassDef):
            print("Clase:", nodo.name)

            for metodo in nodo.body:
                if isinstance(metodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    print("  Método:", describir(metodo))

    print("Utiliza SHA-256:", "sha256" in codigo)
else:
    print("No se encontró registro_blockchain.py")

print("\nARCHIVO DE CADENA:")

if CADENA.is_file():
    print("Ruta:", CADENA)
    print("Tamaño:", CADENA.stat().st_size, "bytes")

    estructura = json.loads(CADENA.read_text(encoding="utf-8-sig"))

    if isinstance(estructura, list):
        bloques = estructura
        print("Estructura: lista")

    elif isinstance(estructura, dict):
        print("Claves principales:", list(estructura.keys()))

        listas = [
            (clave, valor)
            for clave, valor in estructura.items()
            if isinstance(valor, list)
        ]

        if listas:
            nombre, bloques = listas[0]
            print("Lista detectada:", nombre)
        else:
            bloques = []

    else:
        bloques = []

    print("Cantidad de bloques:", len(bloques))

    if bloques:
        for nombre, bloque in [
            ("Primer bloque", bloques[0]),
            ("Último bloque", bloques[-1]),
        ]:
            print(f"\n{nombre}:")

            if isinstance(bloque, dict):
                print("Campos:", list(bloque.keys()))

                for clave, valor in bloque.items():
                    if isinstance(valor, dict):
                        print(clave, "subcampos:", list(valor.keys()))
                    elif "hash" in clave.lower():
                        print(clave, ":", str(valor)[:20] + "...")
                    elif clave.lower() in ("indice", "index", "tipo"):
                        print(clave, ":", valor)

else:
    print("No se encontró cadena.json")

print("\nInspección finalizada.")
print("No se modificaron archivos.")
print("Esta inspección no valida todavía la integridad.")
