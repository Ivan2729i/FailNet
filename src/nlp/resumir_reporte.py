import re
import unicodedata

import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from .extraer_entidades import extraer_entidades
except ImportError:
    from extraer_entidades import extraer_entidades


# ==================================================
# 1. PALABRAS Y EXPRESIONES RELEVANTES
# ==================================================

EVENTOS = [
    r"\bperdida\b",
    r"\bsin conexion\b",
    r"\bno responde\b",
    r"\bfalla(?:s)?\b",
    r"\bcaida\b",
    r"\binterrupcion\b",
    r"\blatencia\b",
    r"\blentitud\b",
    r"\bcongestion\b",
    r"\berror(?:es)?\b",
    r"\bdesconectad\w*\b",
    r"\bintermitent\w*\b",
    r"\binalcanzable\b",
    r"\btimeout\b",
    r"\bdown\b",
    r"\bno resuelve\b",
    r"\bno asigna\b",
    r"\brechaz\w*\b",
    r"\binactiv\w*\b",
    r"\bno disponible\b",
    r"\bretraso(?:s)?\b",
    r"\brestableci\w*\b",
    r"\brecuper\w*\b",
    r"\bnormaliz\w*\b",
]

PATRONES_EVENTOS = [re.compile(evento) for evento in EVENTOS]


# ==================================================
# 2. NORMALIZAR TEXTO PARA COMPARACIONES
# ==================================================


def normalizar(texto):

    texto = unicodedata.normalize("NFD", texto.lower())

    texto = "".join(
        caracter for caracter in texto if unicodedata.category(caracter) != "Mn"
    )

    return texto


# ==================================================
# 3. SEPARAR ORACIONES
# ==================================================


def separar_oraciones(texto):

    texto = re.sub(r"\s+", " ", texto).strip()

    if not texto:
        return []

    # No divide direcciones IPv4 por sus puntos.
    oraciones = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÜÑ¿¡0-9])", texto)

    return [oracion.strip() for oracion in oraciones if oracion.strip()]


# ==================================================
# 4. VALORAR EVENTOS Y ENTIDADES
# ==================================================


def calcular_bono(oracion):

    texto = normalizar(oracion)

    puntuacion = 0.0

    # Priorizar oraciones con eventos técnicos.
    coincidencias = sum(bool(patron.search(texto)) for patron in PATRONES_EVENTOS)

    puntuacion += min(coincidencias, 3) * 0.30

    # Dar prioridad adicional a información
    # técnica que ya identifica el extractor.
    entidades = extraer_entidades(oracion)

    if entidades["dispositivos"]:
        puntuacion += 0.12

    if entidades["direcciones_ip"]:
        puntuacion += 0.10

    if entidades["interfaces"]:
        puntuacion += 0.12

    if entidades["protocolos"]:
        puntuacion += 0.08

    return puntuacion


# ==================================================
# 5. GENERAR RESUMEN EXTRACTIVO
# ==================================================


def resumir_reporte(texto, max_oraciones=2, max_palabras=60):

    if not isinstance(texto, str):
        raise TypeError("El reporte debe ser texto.")

    if max_oraciones < 1 or max_palabras < 1:
        raise ValueError("Los límites deben ser positivos.")

    oraciones = separar_oraciones(texto)

    if not oraciones:
        return ""

    # Si existe una sola oración,
    # se conserva íntegra.
    if len(oraciones) == 1:
        return oraciones[0]

    # ------------------------------------------
    # A. TF-IDF DE LAS ORACIONES
    # ------------------------------------------

    vectorizador = TfidfVectorizer(
        lowercase=True, strip_accents="unicode", ngram_range=(1, 2)
    )

    try:
        matriz = vectorizador.fit_transform(oraciones)

        # Representación promedio del reporte.
        centro = np.asarray(matriz.mean(axis=0))

        relevancia = cosine_similarity(matriz, centro).ravel()

    except ValueError:
        relevancia = np.zeros(len(oraciones))

    # ------------------------------------------
    # B. RELEVANCIA + EVENTOS + ENTIDADES
    # ------------------------------------------

    puntuaciones = []

    for indice, oracion in enumerate(oraciones):

        puntuacion = float(relevancia[indice]) + calcular_bono(oracion)

        puntuaciones.append((indice, puntuacion, oracion))

    # Ordenar por relevancia descendente.
    candidatos = sorted(puntuaciones, key=lambda item: (-item[1], item[0]))

    # ------------------------------------------
    # C. SELECCIONAR ORACIONES
    # ------------------------------------------

    seleccionadas = []
    palabras_usadas = 0

    for indice, _, oracion in candidatos:

        cantidad = len(oracion.split())

        # Seleccionar la mejor oración aunque
        # supere el límite: no cortamos frases
        # porque podrían perder su significado.
        if not seleccionadas:
            seleccionadas.append((indice, oracion))
            palabras_usadas += cantidad

        elif palabras_usadas + cantidad <= max_palabras:
            seleccionadas.append((indice, oracion))
            palabras_usadas += cantidad

        if len(seleccionadas) >= max_oraciones:
            break

    # Recuperar el orden cronológico original.
    seleccionadas.sort(key=lambda item: item[0])

    return " ".join(oracion for _, oracion in seleccionadas)


# ==================================================
# 6. PRUEBAS
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
            "El administrador inició la revisión "
            "de la infraestructura. "
            "El router R2 dejó de responder "
            "a las solicitudes ICMP. "
            "Se confirmó la pérdida de "
            "conectividad con 10.0.0.8. "
            "El incidente fue registrado "
            "para su seguimiento."
        ),
        (
            "Durante una revisión rutinaria "
            "se observaron cambios en la red. "
            "La interfaz Fa0/10 del switch SW2 "
            "cambió a estado down. "
            "También se registraron errores "
            "de transmisión en el enlace. "
            "El técnico documentó los resultados."
        ),
        (
            "El equipo de soporte recibió "
            "una notificación. "
            "El servicio DNS dejó de resolver "
            "los nombres de dominio. "
            "Los usuarios reportaron errores "
            "al acceder a sitios web. "
            "Se abrió un ticket de seguimiento."
        ),
        (
            "Se inició la supervisión del enlace. "
            "El router R4 presentó latencia elevada. "
            "La transferencia de datos fue lenta "
            "durante el periodo analizado. "
            "Posteriormente se restableció "
            "la operación normal del servicio."
        ),
    ]

    print("=" * 65)
    print("RESUMEN AUTOMÁTICO - NETINSIGHT AI")
    print("=" * 65)

    for numero, reporte in enumerate(reportes, start=1):

        print("\n" + "=" * 65)
        print(f"PRUEBA {numero}")
        print("=" * 65)

        print("\nREPORTE ORIGINAL:")
        print(reporte)

        resumen = resumir_reporte(reporte, max_oraciones=2, max_palabras=60)

        print("\nRESUMEN GENERADO:")
        print(resumen)

        print("\nPalabras originales:", len(reporte.split()))

        print("Palabras del resumen:", len(resumen.split()))

    print("\nPruebas finalizadas.")
