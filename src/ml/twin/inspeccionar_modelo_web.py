from pathlib import Path

import joblib
import pandas as pd

# ==================================================
# FAILNET - INSPECCIÓN DEL MODELO DIGITAL TWIN
# ==================================================

BASE = Path(__file__).resolve().parents[3]
MODELO = BASE / "models" / "digital_twin_clasificador.joblib"
DATA = BASE / "data" / "raw" / "digital_twin"


def main():
    print("=" * 65)
    print("FAILNET - PREPARACIÓN DEL MÓDULO DIGITAL TWIN")
    print("=" * 65)

    # Inspeccionar el modelo entrenado.
    if not MODELO.is_file():
        raise FileNotFoundError(f"Modelo no encontrado: {MODELO}")

    artefacto = joblib.load(MODELO)

    print("\nMODELO ENTRENADO")
    print("Archivo:", MODELO.name)
    print("Tipo:", type(artefacto).__name__)

    if isinstance(artefacto, dict):
        print("\nCOMPONENTES GUARDADOS")

        for clave, valor in artefacto.items():
            print(f"\n{clave}: {type(valor).__name__}")

            if isinstance(valor, (list, tuple)):
                print("Elementos:", len(valor))
                print("Primeros valores:", valor[:10])

            elif isinstance(valor, (str, int, float, bool)):
                print("Valor:", valor)

            elif hasattr(valor, "classes_"):
                print("Clases:", valor.classes_)

            elif hasattr(valor, "n_features_in_"):
                print("Características:", valor.n_features_in_)

    # Localizar los datasets disponibles.
    print("\n" + "=" * 65)
    print("DATASETS DISPONIBLES")
    print("=" * 65)

    archivos = sorted(DATA.glob("*.csv"))

    if not archivos:
        print("No se encontraron archivos CSV.")
        return

    for archivo in archivos:
        print(f"{archivo.name} ({archivo.stat().st_size / 1024**2:.2f} MiB)")

    # Revisar estructura del primer dataset.
    archivo = archivos[0]
    df = pd.read_csv(archivo, nrows=5, low_memory=False)

    print("\n" + "=" * 65)
    print("ESTRUCTURA DEL PRIMER DATASET")
    print("=" * 65)
    print("Archivo:", archivo.name)
    print("Columnas:", len(df.columns))

    print("\nNOMBRES DE COLUMNAS")
    for columna in df.columns:
        print("-", columna)

    print("\nPRIMERAS 3 FILAS DE METADATOS")
    metadatos = [
        columna for columna in ["Timestamp", "Host Name", "LABEL"] if columna in df.columns
    ]

    if metadatos:
        print(df[metadatos].head(3).to_string(index=False))

    print("\nINSPECCIÓN FINALIZADA")


if __name__ == "__main__":
    main()
