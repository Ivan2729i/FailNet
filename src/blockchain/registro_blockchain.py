import hashlib
import json
import os

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

# ==================================================
# 1. CONFIGURACIÓN
# ==================================================

BASE = Path(__file__).resolve().parents[2]

DATA = BASE / "data" / "blockchain"
DATA.mkdir(parents=True, exist_ok=True)

ARCHIVO_CADENA = DATA / "cadena.json"

HASH_INICIAL = "0" * 64


# ==================================================
# 2. CLASE BLOCKCHAIN
# ==================================================


class RegistroBlockchain:

    def __init__(self):

        self.archivo = ARCHIVO_CADENA
        self.cadena = []

        if self.archivo.exists():

            self.cargar_cadena()

            valido, mensaje = self.verificar_cadena()

            if not valido:
                raise ValueError("La cadena almacenada está alterada: " + mensaje)

            print("Blockchain existente cargado correctamente.")

        else:

            self.crear_bloque_genesis()

            self.guardar_cadena()

            print("Blockchain nuevo creado correctamente.")

    # ==============================================
    # 3. GENERAR HASH SHA-256
    # ==============================================

    @staticmethod
    def calcular_hash(bloque):

        # El hash no debe incluirse a sí mismo.
        contenido = {clave: valor for clave, valor in bloque.items() if clave != "hash"}

        texto = json.dumps(
            contenido,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )

        return hashlib.sha256(texto.encode("utf-8")).hexdigest()

    # ==============================================
    # 4. CREAR BLOQUE GÉNESIS
    # ==============================================

    def crear_bloque_genesis(self):

        bloque = {
            "indice": 0,
            "fecha": datetime.now(timezone.utc).isoformat(),
            "tipo": "genesis",
            "datos": {"descripcion": ("Bloque inicial de NetInsight AI")},
            "hash_anterior": HASH_INICIAL,
        }

        bloque["hash"] = self.calcular_hash(bloque)

        self.cadena.append(bloque)

    # ==============================================
    # 5. AGREGAR UN BLOQUE
    # ==============================================

    def agregar_bloque(self, tipo, datos):

        if not isinstance(tipo, str) or not tipo.strip():
            raise ValueError("El tipo de análisis es obligatorio.")

        if not isinstance(datos, dict):
            raise TypeError("Los datos deben ser un diccionario.")

        valido, mensaje = self.verificar_cadena()

        if not valido:
            raise ValueError("No se puede agregar un bloque: " + mensaje)

        anterior = self.cadena[-1]

        bloque = {
            "indice": len(self.cadena),
            "fecha": datetime.now(timezone.utc).isoformat(),
            "tipo": tipo.strip(),
            "datos": deepcopy(datos),
            "hash_anterior": anterior["hash"],
        }

        bloque["hash"] = self.calcular_hash(bloque)

        self.cadena.append(bloque)

        self.guardar_cadena()

        return deepcopy(bloque)

    # ==============================================
    # 6. VERIFICAR INTEGRIDAD
    # ==============================================

    def verificar_cadena(self, cadena=None):

        if cadena is None:
            cadena = self.cadena

        if not isinstance(cadena, list) or not cadena:
            return False, "La cadena está vacía o es inválida."

        campos = {"indice", "fecha", "tipo", "datos", "hash_anterior", "hash"}

        for indice, bloque in enumerate(cadena):

            if not isinstance(bloque, dict):
                return False, (f"Estructura incorrecta en bloque {indice}")

            if set(bloque.keys()) != campos:
                return False, (f"Campos incorrectos en bloque {indice}")

            if type(bloque["indice"]) is not int:
                return False, (f"Índice inválido en bloque {indice}")

            if bloque["indice"] != indice:
                return False, (f"Índice incorrecto en bloque {indice}")

            if not isinstance(bloque["datos"], dict):
                return False, (f"Datos incorrectos en bloque {indice}")

            if not isinstance(bloque["hash"], str):
                return False, (f"Hash inválido en bloque {indice}")

            if not isinstance(bloque["hash_anterior"], str):
                return False, (f"Enlace inválido en bloque {indice}")

            try:
                hash_calculado = self.calcular_hash(bloque)

            except (TypeError, ValueError):
                return False, (f"No se puede calcular el hash " f"del bloque {indice}")

            if bloque["hash"] != hash_calculado:
                return False, (f"Hash incorrecto en bloque {indice}")

            if indice == 0:

                if bloque["tipo"] != "genesis":
                    return False, ("El bloque inicial no es génesis.")

                if bloque["hash_anterior"] != HASH_INICIAL:
                    return False, ("Referencia inicial incorrecta.")

            else:

                anterior = cadena[indice - 1]

                if bloque["hash_anterior"] != anterior["hash"]:
                    return False, (f"Enlace incorrecto en bloque {indice}")

        return True, ("Todos los hashes y enlaces son correctos.")

    # ==============================================
    # 7. GUARDAR CADENA EN JSON
    # ==============================================

    def guardar_cadena(self):

        contenido = json.dumps(
            self.cadena, indent=4, ensure_ascii=False, allow_nan=False
        )

        temporal = self.archivo.with_suffix(".json.tmp")

        temporal.write_text(contenido, encoding="utf-8")

        os.replace(temporal, self.archivo)

    # ==============================================
    # 8. CARGAR CADENA GUARDADA
    # ==============================================

    def cargar_cadena(self):

        contenido = self.archivo.read_text(encoding="utf-8")

        self.cadena = json.loads(contenido)

    # ==============================================
    # 9. CONSULTAR BLOQUES
    # ==============================================

    def obtener_bloques(self):

        return deepcopy(self.cadena)

    def obtener_total_bloques(self):

        return len(self.cadena)

    # ==============================================
    # 10. IDENTIFICAR DEMOSTRACIONES EXISTENTES
    # ==============================================

    def existe_demo(self, demo_id):

        return any(
            isinstance(bloque.get("datos"), dict)
            and bloque["datos"].get("demo_id") == demo_id
            for bloque in self.cadena
        )


# ==================================================
# 11. PRUEBAS DEL SISTEMA
# ==================================================

if __name__ == "__main__":

    print("=" * 65)
    print("BLOCKCHAIN SIMULADO - NETINSIGHT AI")
    print("=" * 65)

    blockchain = RegistroBlockchain()

    # ----------------------------------------------
    # DEMOSTRACIÓN 1 - SOFI
    # ----------------------------------------------

    demostraciones = [
        {
            "demo_id": "demo_sofi_001",
            "tipo": "SOFI",
            "datos": {
                "resultado": "Falla",
                "modelo": "Random Forest",
                "descripcion": ("Ejemplo de detección de falla " "en tráfico de red."),
            },
        },
        {
            "demo_id": "demo_twin_001",
            "tipo": "Digital Twin",
            "datos": {
                "nivel_trafico": 3,
                "modelo": "Random Forest",
                "descripcion": (
                    "Ejemplo de clasificación " "de intensidad de tráfico."
                ),
            },
        },
        {
            "demo_id": "demo_nlp_001",
            "tipo": "PNL",
            "datos": {
                "categoria": "conectividad",
                "dispositivo": "R3",
                "descripcion": ("Ejemplo de análisis de " "un reporte técnico."),
            },
        },
    ]

    # ----------------------------------------------
    # REGISTRAR BLOQUES SIN DUPLICAR
    # ----------------------------------------------

    print("\nREGISTRO DE ANÁLISIS")

    for demo in demostraciones:

        if blockchain.existe_demo(demo["demo_id"]):

            print(f"Ya existe: {demo['tipo']}")

            continue

        datos = {**demo["datos"], "demo_id": demo["demo_id"], "simulado": True}

        bloque = blockchain.agregar_bloque(tipo=demo["tipo"], datos=datos)

        print(f"Agregado {demo['tipo']}: " f"bloque {bloque['indice']}")

    # ----------------------------------------------
    # VERIFICAR CADENA ORIGINAL
    # ----------------------------------------------

    print("\n" + "=" * 65)
    print("VERIFICACIÓN DE INTEGRIDAD")
    print("=" * 65)

    valido, mensaje = blockchain.verificar_cadena()

    print("Total de bloques:", blockchain.obtener_total_bloques())

    print("Cadena válida:", valido)
    print("Resultado:", mensaje)

    # ----------------------------------------------
    # MOSTRAR LOS BLOQUES
    # ----------------------------------------------

    print("\n" + "=" * 65)
    print("BLOQUES REGISTRADOS")
    print("=" * 65)

    for bloque in blockchain.obtener_bloques():

        print(f"\nBloque: {bloque['indice']}")

        print(f"Tipo: {bloque['tipo']}")

        print(f"Fecha: {bloque['fecha']}")

        print(f"Hash SHA-256: {bloque['hash']}")

        print(f"Hash anterior: " f"{bloque['hash_anterior']}")

    # ----------------------------------------------
    # PRUEBA DE MANIPULACIÓN
    # ----------------------------------------------

    print("\n" + "=" * 65)
    print("PRUEBA DE MANIPULACIÓN")
    print("=" * 65)

    # Modificamos únicamente una copia en memoria.
    # El archivo real NO se altera.

    copia = blockchain.obtener_bloques()

    copia[-1]["datos"]["descripcion"] = "Este registro fue modificado."

    valido_copia, mensaje_copia = blockchain.verificar_cadena(copia)

    print("Copia manipulada válida:", valido_copia)

    print("Detección:", mensaje_copia)

    # ----------------------------------------------
    # COMPROBAR QUE LA ORIGINAL SIGUE ÍNTEGRA
    # ----------------------------------------------

    valido_original, _ = blockchain.verificar_cadena()

    print("\nCadena original válida:", valido_original)

    print("Archivo:", ARCHIVO_CADENA)

    print("\nPruebas finalizadas.")
