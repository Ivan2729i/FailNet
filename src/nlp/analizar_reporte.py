import json
from pathlib import Path
from functools import lru_cache

import joblib

try:
    from .extraer_entidades import extraer_entidades
    from .resumir_reporte import resumir_reporte
except ImportError:
    from extraer_entidades import extraer_entidades
    from resumir_reporte import resumir_reporte


# ==================================================
# 1. CONFIGURACIÓN
# ==================================================

BASE = Path(__file__).resolve().parents[2]

MODELO_PATH = BASE / "models" / "nlp_clasificador.joblib"


# ==================================================
# 2. CARGAR MODELO ENTRENADO
# ==================================================


@lru_cache(maxsize=1)
def cargar_modelo():

    if not MODELO_PATH.exists():
        raise FileNotFoundError(f"No se encontró el modelo: {MODELO_PATH}")

    artefacto = joblib.load(MODELO_PATH)

    if "pipeline" not in artefacto:
        raise ValueError(
            "El modelo guardado no contiene " "el pipeline de clasificación."
        )

    return artefacto["pipeline"]


# ==================================================
# 3. CLASIFICACIÓN DEL REPORTE
# ==================================================


def clasificar_reporte(texto):

    modelo = cargar_modelo()

    prediccion = modelo.predict([texto])[0]

    return str(prediccion)


# ==================================================
# 4. ANÁLISIS COMPLETO
# ==================================================


def analizar_reporte(texto):

    if not isinstance(texto, str):
        raise TypeError("El reporte debe ser texto.")

    texto = texto.strip()

    if not texto:
        raise ValueError("El reporte no puede estar vacío.")

    # Funcionalidad 1: clasificación ML
    categoria = clasificar_reporte(texto)

    # Funcionalidad 2: entidades
    entidades = extraer_entidades(texto)

    # Funcionalidad 3: resumen extractivo
    resumen = resumir_reporte(texto, max_oraciones=2, max_palabras=50)

    resultado = {
        "reporte_original": texto,
        "categoria": categoria,
        "entidades": entidades,
        "resumen": resumen,
    }

    return resultado


# ==================================================
# 5. MOSTRAR RESULTADOS
# ==================================================


def mostrar_resultado(texto):

    resultado = analizar_reporte(texto)

    print(json.dumps(resultado, indent=4, ensure_ascii=False))


# ==================================================
# 6. PRUEBAS DEL SISTEMA
# ==================================================

if __name__ == "__main__":

    reportes = [
        (
            "Se detectó pérdida de conectividad "
            "en el router R3 hacia la dirección "
            "192.168.1.10 mediante la interfaz "
            "GigabitEthernet0/1."
        ),
        (
            "El switch SW5 registró errores CRC "
            "en GigabitEthernet0/4. "
            "El enlace cambió a estado down. "
            "El personal técnico registró "
            "el incidente para su revisión."
        ),
        (
            "Los equipos no reciben direcciones "
            "del servidor DHCP. "
            "El servicio dejó de asignar "
            "configuraciones IP. "
            "Los usuarios reportaron problemas "
            "para conectarse a la red."
        ),
    ]

    print("=" * 65)
    print("NETINSIGHT AI - SISTEMA INTEGRADO DE PNL")
    print("=" * 65)

    print("\nModelo:", MODELO_PATH.name)
    print("Funciones: clasificación, entidades y resumen")

    for numero, reporte in enumerate(reportes, start=1):

        print("\n" + "=" * 65)
        print(f"PRUEBA INTEGRADA {numero}")
        print("=" * 65)

        mostrar_resultado(reporte)

    # ==========================================
    # 7. PRUEBAS INTERACTIVAS
    # ==========================================

    print("\n" + "=" * 65)
    print("MODO INTERACTIVO")
    print("=" * 65)

    print("Escribe un reporte técnico para analizarlo.")
    print("Presiona ENTER sin escribir nada para salir.")

    while True:

        try:
            texto = input("\nReporte > ").strip()

        except (EOFError, KeyboardInterrupt):
            print("\nPrograma finalizado.")
            break

        if not texto:
            print("Programa finalizado.")
            break

        print("\nRESULTADO DEL ANÁLISIS")

        try:
            mostrar_resultado(texto)

        except (ValueError, TypeError) as error:
            print("Error:", error)
