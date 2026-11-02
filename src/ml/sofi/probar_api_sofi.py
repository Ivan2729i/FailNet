
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(BASE))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "failnet_web.settings" )
import django

django.setup()

from django.test import Client

DATA = (
    BASE / "data" / "raw" / "sofi" / "data_sofi"
)



def main():

    print("=" * 65)
    print("FAILNET - PRUEBA DE API SOFI")
    print("=" * 65)

    switch_i = DATA / "SOFI CoreSwitch-I.csv"
    switch_ii = DATA / "SOFI CoreSwitch-II.csv"

    cliente = Client(
        enforce_csrf_checks=True,
        HTTP_HOST="127.0.0.1"
    )

    # ======================================
    # 1. SOLICITAR TOKEN CSRF
    # ======================================

    respuesta_csrf = cliente.get(
        "/api/csrf/"
    )

    print(
        "\nCSRF HTTP:",
        respuesta_csrf.status_code
    )

    if respuesta_csrf.status_code != 200:
        print(
            respuesta_csrf.content.decode(
                "utf-8",
                errors="replace"
            )[:500]
        )
        return

    token = respuesta_csrf.json()["csrfToken"]

    # ======================================
    # 2. ENVIAR ARCHIVOS
    # ======================================

    with (
        switch_i.open("rb") as archivo_i,
        switch_ii.open("rb") as archivo_ii
    ):

        respuesta = cliente.post(
            "/api/sofi/analizar/",
            data={
                "switch_i": archivo_i,
                "switch_ii": archivo_ii,
            },
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="http://127.0.0.1:5173",
        )

    print(
        "Análisis HTTP:",
        respuesta.status_code
    )

    datos = respuesta.json()

    if respuesta.status_code != 200:
        print("Error:", datos)
        return

    # ======================================
    # 3. RESULTADOS
    # ======================================

    resumen = datos["resumen"]

    print("\nRESUMEN")

    for clave, valor in resumen.items():
        print(f"{clave}: {valor}")

    print(
        "\nDías procesados:",
        len(datos["distribucion_diaria"])
    )

    print(
        "Predicciones en la muestra:",
        len(datos["primeras_predicciones"])
    )

    print(
        "Fallas en la muestra:",
        len(datos["primeras_fallas"])
    )

    print("\nPRIMERAS 3 PREDICCIONES")

    for fila in datos["primeras_predicciones"][:3]:
        print(fila)

    # ======================================
    # 4. COMPROBACIONES
    # ======================================

    assert resumen["registros_sincronizados"] == 12970

    assert (
        resumen["normales"] + resumen["fallas"]
        == resumen["registros_sincronizados"]
    )

    print("\nAPI SOFI VALIDADA CORRECTAMENTE")


if __name__ == "__main__":
    main()
