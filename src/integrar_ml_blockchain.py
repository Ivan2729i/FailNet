import csv
import hashlib
from pathlib import Path

from blockchain.registro_blockchain import RegistroBlockchain

# ==================================================
# CONFIGURACIÓN
# ==================================================

BASE = Path(__file__).resolve().parents[1]
REPORTS = BASE / "reports"

ARCHIVOS = {
    "SOFI": (REPORTS / "sofi_predicciones_prueba_final.csv"),
    "Digital Twin": (REPORTS / "twin_predicciones_prueba_final.csv"),
}


# ==================================================
# CALCULAR SHA-256 DEL ARCHIVO CSV
# ==================================================


def calcular_hash_archivo(ruta):

    sha256 = hashlib.sha256()

    with ruta.open("rb") as archivo:

        for fragmento in iter(lambda: archivo.read(1024 * 1024), b""):
            sha256.update(fragmento)

    return sha256.hexdigest()


# ==================================================
# LEER UNA PREDICCIÓN GUARDADA
# ==================================================


def leer_primera_prediccion(ruta):

    with ruta.open("r", encoding="utf-8-sig", newline="") as archivo:

        lector = csv.DictReader(archivo)

        if not lector.fieldnames:
            raise ValueError(f"El CSV no tiene encabezados: {ruta.name}")

        fila = next(lector, None)

        if fila is None:
            raise ValueError(f"El CSV está vacío: {ruta.name}")

        return fila


# ==================================================
# IDENTIFICADOR PARA EVITAR DUPLICADOS
# ==================================================


def crear_identificador(tipo, hash_archivo):

    contenido = f"{tipo}|{hash_archivo}|fila_1"

    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def ya_registrado(blockchain, identificador):

    for bloque in blockchain.obtener_bloques():

        datos = bloque.get("datos", {})

        if datos.get("id_registro") == identificador:
            return True

    return False


# ==================================================
# REGISTRAR RESULTADOS
# ==================================================


def main():

    print("=" * 65)
    print("NETINSIGHT AI - ML + BLOCKCHAIN")
    print("=" * 65)

    blockchain = RegistroBlockchain()

    for tipo, ruta in ARCHIVOS.items():

        print("\n" + "=" * 65)
        print("MODELO:", tipo)
        print("=" * 65)

        if not ruta.exists():

            print("No se encontró:", ruta)

            continue

        # Leer el resultado que ya generó
        # nuestro modelo durante la evaluación.
        try:
            prediccion = leer_primera_prediccion(ruta)

            hash_archivo = calcular_hash_archivo(ruta)

        except (OSError, ValueError) as error:

            print("Error leyendo el CSV:", error)
            continue

        identificador = crear_identificador(tipo, hash_archivo)

        # No registrar la misma fila del
        # mismo archivo más de una vez.
        if ya_registrado(blockchain, identificador):

            print("Esta predicción ya fue registrada.")

            continue

        # Datos que se guardarán en el bloque.
        datos = {
            "origen": "prediccion_historica_csv",
            "archivo": ruta.name,
            "numero_fila": 1,
            "id_registro": identificador,
            "sha256_archivo_origen": hash_archivo,
            "registro": prediccion,
            "simulado": False,
        }

        bloque = blockchain.agregar_bloque(tipo=tipo, datos=datos)

        print("\nPREDICCIÓN REGISTRADA")

        print("Archivo:", ruta.name)

        print("Campos originales:", len(prediccion))

        print("Bloque creado:", bloque["indice"])

        print("Hash SHA-256:", bloque["hash"])

        print("Hash anterior:", bloque["hash_anterior"])

    # ==================================================
    # VERIFICACIÓN FINAL
    # ==================================================

    print("\n" + "=" * 65)
    print("VERIFICACIÓN FINAL")
    print("=" * 65)

    valido, mensaje = blockchain.verificar_cadena()

    print("Cadena válida:", valido)
    print("Resultado:", mensaje)

    print("Total de bloques:", blockchain.obtener_total_bloques())

    print("\nIntegración ML + blockchain finalizada.")


if __name__ == "__main__":
    main()
