from pathlib import Path
import numpy as np
import pandas as pd

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================

BASE = Path(__file__).resolve().parents[3]
DATA = BASE / "data" / "raw" / "digital_twin"
REPORTS = BASE / "reports"

REPORTS.mkdir(parents=True, exist_ok=True)

archivo = next(DATA.rglob("dataset_01_TC31_05062025_labeled_final.csv"), None)

if archivo is None:
    raise FileNotFoundError("No se encontró el dataset")

# Solo necesitamos fecha y etiqueta
df = pd.read_csv(archivo, usecols=["Timestamp", "LABEL"])

df = df.sort_values("Timestamp").reset_index(drop=True)

# ==========================================
# 2. SEPARACIÓN ORIGINAL
# ==========================================

instantes = np.sort(df["Timestamp"].unique())

corte = int(len(instantes) * 0.80)

instantes_dev = instantes[:corte]

desarrollo = df[df["Timestamp"] <= instantes_dev[-1]].copy()

# ==========================================
# 3. ANALIZAR BLOQUES CRONOLÓGICOS
# ==========================================

bloques = np.array_split(instantes_dev, 10)

resultados = []

print("=" * 85)
print("DISTRIBUCIÓN TEMPORAL DE CLASES - DIGITAL TWIN")
print("=" * 85)

for numero, bloque in enumerate(bloques, 1):

    inicio = bloque[0]
    fin = bloque[-1]

    datos = desarrollo[desarrollo["Timestamp"].between(inicio, fin)]

    conteos = datos["LABEL"].value_counts().reindex(range(5), fill_value=0)

    presentes = [int(clase) for clase in range(5) if conteos[clase] > 0]

    resultados.append(
        {
            "bloque": numero,
            "inicio": pd.to_datetime(inicio, unit="s", utc=True),
            "fin": pd.to_datetime(fin, unit="s", utc=True),
            "registros": len(datos),
            "clase_0": int(conteos[0]),
            "clase_1": int(conteos[1]),
            "clase_2": int(conteos[2]),
            "clase_3": int(conteos[3]),
            "clase_4": int(conteos[4]),
            "clases_presentes": len(presentes),
        }
    )

    print(f"\nBLOQUE {numero}")
    print(
        "Periodo:",
        pd.to_datetime(inicio, unit="s", utc=True),
        "a",
        pd.to_datetime(fin, unit="s", utc=True),
    )

    print("Registros:", len(datos))
    print("Clases presentes:", presentes)

    print("Distribución:", conteos.to_dict())

# ==========================================
# 4. RESUMEN
# ==========================================

tabla = pd.DataFrame(resultados)

print("\n" + "=" * 85)
print("RESUMEN DE LOS 10 BLOQUES")
print("=" * 85)

columnas = [
    "bloque",
    "clase_0",
    "clase_1",
    "clase_2",
    "clase_3",
    "clase_4",
    "clases_presentes",
]

print(tabla[columnas].to_string(index=False))

ruta = REPORTS / "twin_distribucion_temporal.csv"

tabla.to_csv(ruta, index=False, encoding="utf-8-sig")

print("\nReporte guardado en:", ruta)
print("Auditoría finalizada.")
print("No se entrenó ni modificó ningún modelo.")
