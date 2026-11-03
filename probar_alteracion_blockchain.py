"""FailNet: prueba REVERSIBLE de integridad del archivo blockchain local.

Ejemplos:
    python probar_alteracion_blockchain.py alterar 6
    python probar_alteracion_blockchain.py estado
    python probar_alteracion_blockchain.py restaurar 6

NO ejecutar análisis nuevos mientras la cadena esté alterada.
"""

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path


RAIZ = Path(__file__).resolve().parent
CADENA = RAIZ / "data" / "blockchain" / "cadena.json"
RESPALDO = CADENA.with_name("cadena.json.prueba.respaldo")
ESTADO = CADENA.with_name("cadena.json.prueba.estado.json")


def sha256(contenido):
    return hashlib.sha256(contenido).hexdigest()


def escribir_atomico(ruta, contenido):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=ruta.parent, delete=False) as salida:
            temporal = Path(salida.name)
            salida.write(contenido)
            salida.flush()
            os.fsync(salida.fileno())
        os.replace(temporal, ruta)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)


def leer_bloques(contenido):
    bloques = json.loads(contenido.decode("utf-8-sig"))
    if not isinstance(bloques, list):
        raise ValueError("cadena.json no contiene una lista de bloques.")
    return bloques


def encontrar_bloque(bloques, indice):
    coincidencias = [
        b for b in bloques
        if isinstance(b, dict) and b.get("indice") == indice
    ]
    if len(coincidencias) != 1:
        raise ValueError(f"Se esperó exactamente un bloque con índice {indice}; encontrados: {len(coincidencias)}.")
    return coincidencias[0]


def alterar(indice):
    if ESTADO.exists() or RESPALDO.exists():
        raise RuntimeError(
            "Ya existe un respaldo o una prueba activa. Restaura primero la prueba anterior; "
            "no se sobrescribirá el respaldo."
        )
    if not CADENA.is_file():
        raise FileNotFoundError(f"No se encontró: {CADENA}")

    original = CADENA.read_bytes()
    bloques = leer_bloques(original)
    bloque = encontrar_bloque(bloques, indice)
    hash_original = bloque.get("hash")
    if not isinstance(hash_original, str) or len(hash_original) != 64 or any(c not in "0123456789abcdefABCDEF" for c in hash_original):
        raise ValueError("El bloque no tiene un hash SHA-256 hexadecimal válido de 64 caracteres.")

    # Cambia UN carácter del hash del bloque. No recalcula bloques siguientes.
    hash_modificado = ("0" if hash_original[0] != "0" else "1") + hash_original[1:]
    bloque["hash"] = hash_modificado
    modificado = (json.dumps(bloques, ensure_ascii=False, indent=4) + "\n").encode("utf-8")

    informacion = {
        "indice": indice,
        "sha256_archivo_original": sha256(original),
        "sha256_archivo_modificado": sha256(modificado),
        "hash_original": hash_original,
        "hash_modificado": hash_modificado,
    }

    # El respaldo se crea de forma exclusiva; nunca sobrescribe uno anterior.
    with RESPALDO.open("xb") as salida:
        salida.write(original)
        salida.flush()
        os.fsync(salida.fileno())
    try:
        with ESTADO.open("x", encoding="utf-8") as salida:
            json.dump(informacion, salida, indent=2, ensure_ascii=False)
            salida.flush()
            os.fsync(salida.fileno())
        escribir_atomico(CADENA, modificado)
    except Exception:
        # Mantener respaldo; posible recuperación manual si la operación se interrumpió.
        raise

    print(f"Bloque alterado: índice {indice} (de {len(bloques)} bloques).")
    print(f"Hash anterior: {hash_original[:20]}...")
    print(f"Hash alterado: {hash_modificado[:20]}...")
    print("Respaldo original guardado en:", RESPALDO)
    print("Ahora abre /blockchain y pulsa 'Verificar integridad'.")
    print(f"Para restaurar: python probar_alteracion_blockchain.py restaurar {indice}")
    print("ATENCIÓN: no ejecutes nuevos análisis mientras la cadena esté alterada.")


def restaurar(indice):
    if not ESTADO.is_file() or not RESPALDO.is_file():
        raise RuntimeError("No existe una prueba con respaldo completo que se pueda restaurar.")
    info = json.loads(ESTADO.read_text(encoding="utf-8"))
    if info.get("indice") != indice:
        raise ValueError(f"La prueba activa corresponde al bloque {info.get('indice')}, no al {indice}.")

    respaldo = RESPALDO.read_bytes()
    if sha256(respaldo) != info.get("sha256_archivo_original"):
        raise RuntimeError("El respaldo fue modificado. No se restaurará automáticamente.")
    actual = CADENA.read_bytes()
    if sha256(actual) != info.get("sha256_archivo_modificado"):
        raise RuntimeError(
            "La cadena cambió después de la alteración (quizá se añadieron bloques). "
            "No se sobrescribirá para evitar perder registros nuevos. "
            "Conserva el respaldo y revisa el archivo antes de restaurarlo manualmente."
        )

    # Restauración exacta, byte por byte, del archivo original.
    escribir_atomico(CADENA, respaldo)
    ESTADO.unlink()
    RESPALDO.unlink()
    print(f"Bloque {indice} restaurado. cadena.json volvió a su contenido ORIGINAL exacto.")
    print("Abre /blockchain y pulsa nuevamente 'Verificar integridad'.")


def estado():
    if not ESTADO.is_file():
        print("No hay una prueba activa registrada.")
        if RESPALDO.exists():
            print("ATENCIÓN: existe un respaldo sin estado. No lo borres antes de revisarlo.")
        return
    info = json.loads(ESTADO.read_text(encoding="utf-8"))
    print("Prueba activa en bloque:", info.get("indice"))
    print("Respaldo presente:", RESPALDO.is_file())
    print("Archivo modificado tal como lo dejó la prueba:", CADENA.is_file() and sha256(CADENA.read_bytes()) == info.get("sha256_archivo_modificado"))
    print("Restaurar usando: python probar_alteracion_blockchain.py restaurar", info.get("indice"))


def main():
    parser = argparse.ArgumentParser(description="Prueba reversible de integridad blockchain de FailNet")
    parser.add_argument("accion", choices=["alterar", "restaurar", "estado"])
    parser.add_argument("indice", nargs="?", type=int, help="Índice de bloque, por ejemplo 6")
    args = parser.parse_args()
    if args.accion in ("alterar", "restaurar") and args.indice is None:
        parser.error("Indica el índice del bloque, por ejemplo: alterar 6")
    if args.accion == "estado":
        estado()
    elif args.accion == "alterar":
        alterar(args.indice)
    else:
        restaurar(args.indice)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        raise SystemExit(f"ERROR: {error}")
