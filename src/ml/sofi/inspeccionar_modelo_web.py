
from pathlib import Path

import joblib
import pandas as pd


# ==========================================
# INSPECCIÓN DEL MODELO SOFI
# ==========================================

BASE = Path(__file__).resolve().parents[3]

MODELO = BASE / "models" / "sofi_combinado.joblib"

DATA = BASE / "data" / "raw" / "sofi" / "data_sofi"


def main():

    print("=" * 65)
    print("FAILNET - PREPARACIÓN DEL MÓDULO SOFI")
    print("=" * 65)

    # ======================================
    # 1. REVISAR MODELO ENTRENADO
    # ======================================

    print("\nMODELO ENTRENADO")

    if not MODELO.is_file():
        raise FileNotFoundError(MODELO)

    artefacto = joblib.load(MODELO)

    print("Archivo:", MODELO.name)
    print("Tipo:", type(artefacto).__name__)

    if isinstance(artefacto, dict):

        print("\nCONTENIDO DEL MODELO")

        for clave, valor in artefacto.items():

            print(
                f"{clave}: {type(valor).__name__}"
            )

            if isinstance(valor, (list, tuple)):
                print(
                    "  Elementos:", len(valor)
                )

                print(
                    "  Primeros valores:",
                    valor[:5]
                )

            elif isinstance(
                valor, (int, float, str)
            ):
                print("  Valor:", valor)

    # ======================================
    # 2. REVISAR DATASETS ORIGINALES
    # ======================================

    archivos = [
        DATA / "SOFI CoreSwitch-I.csv",
        DATA / "SOFI CoreSwitch-II.csv",
    ]

    for ruta in archivos:

        print("\n" + "=" * 65)
        print("DATASET:", ruta.name)
        print("=" * 65)

        if not ruta.is_file():
            print("NO ENCONTRADO:", ruta)
            continue

        # Leer solo el encabezado y unas
        # pocas filas, sin cargar todo el CSV.
        df = pd.read_csv(
            ruta,
            nrows=5
        )

        print("Columnas:", len(df.columns))

        print("\nNOMBRES DE COLUMNAS")

        for columna in df.columns:
            print(" -", columna)

        print("\nPrimeras 2 filas")

        print(
            df.head(2).to_string(index=False)
        )

    print("\n" + "=" * 65)
    print("INSPECCIÓN TERMINADA")
    print("=" * 65)


if __name__ == "__main__":
    main()
