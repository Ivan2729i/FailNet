from pathlib import Path

import numpy as np
import pandas as pd

# ==================================================
# 1. CARGAR LOS DATOS
# ==================================================

BASE = Path(__file__).resolve().parents[3]
DATA = BASE / "data" / "raw" / "digital_twin"

archivo = next(DATA.rglob("dataset_01_TC31_05062025_labeled_final.csv"), None)

if archivo is None:
    raise FileNotFoundError("No se encontró el dataset")

df = pd.read_csv(archivo, low_memory=False)
df.columns = df.columns.str.strip()

df = df.sort_values(["Timestamp", "Host Name"]).reset_index(drop=True)

# Usar únicamente el 80% de desarrollo
instantes = np.sort(df["Timestamp"].unique())
corte = int(len(instantes) * 0.80)

desarrollo = df[df["Timestamp"].isin(instantes[:corte])].copy()

# ==================================================
# 2. OBTENER ANCHO DE BANDA MÁXIMO
# ==================================================

columnas_bw = [
    columna
    for columna in desarrollo.columns
    if columna.startswith(("bw_rx.", "bw_tx."))
]

max_bw = desarrollo[columnas_bw].max(axis=1).fillna(0)

# ==================================================
# 3. PROBAR FRONTERAS CORREGIDAS
# ==================================================

predicciones = np.select(
    [max_bw < 10, max_bw < 40, max_bw < 70, max_bw < 90], [0, 1, 2, 3], default=4
)

reales = desarrollo["LABEL"].to_numpy()

aciertos = int((predicciones == reales).sum())
errores = int((predicciones != reales).sum())

exactitud = aciertos / len(reales)

print("=" * 65)
print("VERIFICACIÓN DE ETIQUETAS - DIGITAL TWIN")
print("=" * 65)

print("Registros evaluados:", len(reales))
print("Aciertos:", aciertos)
print("Errores:", errores)
print(f"Coincidencia: {exactitud * 100:.4f}%")

print("\nMATRIZ DE COINCIDENCIAS")

print(
    pd.crosstab(
        reales, predicciones, rownames=["LABEL real"], colnames=["Regla"]
    ).to_string()
)

# ==================================================
# 4. MOSTRAR DISCREPANCIAS
# ==================================================

mascara_error = predicciones != reales

if errores > 0:

    diferencias = desarrollo.loc[
        mascara_error, ["Timestamp", "Host Name", "LABEL"]
    ].copy()

    diferencias["max_bw"] = max_bw.loc[mascara_error]

    diferencias["prediccion_regla"] = predicciones[mascara_error]

    print("\nPRIMERAS 20 DISCREPANCIAS")

    print(
        diferencias.head(20).to_string(index=False, float_format=lambda x: f"{x:.8f}")
    )

else:
    print("\nLas etiquetas se reproducen exactamente " "con los rangos de max_bw.")

print("\nVerificación terminada.")
print("La prueba final sigue reservada.")
