from pathlib import Path
import pandas as pd

# Directorio raíz del proyecto
BASE_DIR = Path(__file__).resolve().parents[2]

# Ubicación del dataset original
DATA_DIR = BASE_DIR / "data" / "raw" / "sofi"

# Buscar archivos procesados de SOFI
archivos = sorted(DATA_DIR.rglob("SOFI CoreSwitch-*.csv"))

if not archivos:
    raise FileNotFoundError("No se encontraron los CSV de SOFI")

print("=" * 60)
print("ANÁLISIS EXPLORATORIO DEL DATASET SOFI")
print("=" * 60)

for archivo in archivos:
    print(f"\nARCHIVO: {archivo.name}")

    try:
        df = pd.read_csv(archivo, sep=None, engine="python", encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(archivo, sep=None, engine="python", encoding="latin-1")

    print(f"\nRegistros: {df.shape[0]}")
    print(f"Columnas: {df.shape[1]}")

    print("\nNOMBRES DE COLUMNAS:")
    for columna in df.columns:
        print(f" - {columna}")

    print("\nTIPOS DE DATOS:")
    print(df.dtypes.to_string())

    print("\nVALORES NULOS:")
    print(df.isnull().sum().to_string())

    print("\nREGISTROS DUPLICADOS:")
    print(df.duplicated().sum())

    # Buscar la columna de clasificación
    posibles_etiquetas = [
        col
        for col in df.columns
        if str(col).strip().lower() in {"class", "label", "target", "status"}
    ]

    for etiqueta in posibles_etiquetas:
        print(f"\nDISTRIBUCIÓN DE {etiqueta}:")
        print(df[etiqueta].value_counts(dropna=False))

    print("\nPRIMEROS 3 REGISTROS:")
    print(df.head(3).to_string(index=False))

    print("\n" + "=" * 60)

print("\nAnálisis inicial finalizado.")
