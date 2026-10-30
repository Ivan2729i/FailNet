from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    recall_score,
    classification_report,
    confusion_matrix,
)

# ==========================================
# 1. RUTAS
# ==========================================

BASE = Path(__file__).resolve().parents[3]

DATA = BASE / "data" / "raw" / "digital_twin"
MODELS = BASE / "models"
REPORTS = BASE / "reports"

REPORTS.mkdir(parents=True, exist_ok=True)

ruta_modelo = MODELS / "digital_twin_clasificador.joblib"

if not ruta_modelo.exists():
    raise FileNotFoundError(f"No se encontró el modelo: {ruta_modelo}")

# ==========================================
# 2. CARGAR MODELO YA ENTRENADO
# ==========================================

artefacto = joblib.load(ruta_modelo)

modelo = artefacto["modelo"]
imputador = artefacto["imputador"]
columnas = artefacto["columnas"]

CLASES = [0, 1, 2, 3, 4]

print("=" * 65)
print("VALIDACIÓN EN OTROS DATASETS - DIGITAL TWIN")
print("=" * 65)

print("Modelo cargado:", ruta_modelo.name)
print("Características esperadas:", len(columnas))
print("No se realizará ningún entrenamiento.")

# ==========================================
# 3. LOCALIZAR DATASETS ADICIONALES
# ==========================================

archivos = []

for prefijo in ["dataset_02", "dataset_03"]:

    coincidencias = sorted(
        p for p in DATA.rglob("*.csv") if p.name.lower().startswith(prefijo)
    )

    if coincidencias:
        archivos.extend(coincidencias)
    else:
        print(f"\nNo se encontró un archivo " f"que comience con {prefijo}")

if not archivos:
    raise FileNotFoundError(
        "Coloca los CSV de los datasets 02 " "y 03 en data/raw/digital_twin/"
    )

# ==========================================
# 4. EVALUACIÓN SIN REENTRENAMIENTO
# ==========================================

resultados = []

for archivo in archivos:

    print("\n" + "=" * 65)
    print("DATASET:", archivo.name)
    print("=" * 65)

    df = pd.read_csv(archivo, low_memory=False)

    df.columns = df.columns.str.strip()

    if "LABEL" not in df.columns:
        print("Omitido: no tiene columna LABEL")
        continue

    faltantes = [col for col in columnas if col not in df.columns]

    if faltantes:
        print("Omitido: faltan características:")
        for col in faltantes:
            print(" -", col)
        continue

    if df["LABEL"].isna().any():
        print("Omitido: existen etiquetas nulas")
        continue

    y = df["LABEL"].astype(int)

    if not set(y.unique()).issubset(CLASES):
        print("Omitido: etiquetas desconocidas")
        continue

    print("Registros:", len(df))

    print("\nDISTRIBUCIÓN DE CLASES")
    print(y.value_counts().reindex(CLASES, fill_value=0).sort_index().to_string())

    # Se preservan exactamente las
    # características y su orden original.
    X = df[columnas].apply(pd.to_numeric, errors="coerce")

    X = X.replace([np.inf, -np.inf], np.nan)

    # Imputador previamente entrenado:
    # solo transformamos, nunca fit().
    X_p = imputador.transform(X).astype(np.float32)

    pred = modelo.predict(X_p)

    acc = accuracy_score(y, pred)

    macro_f1 = f1_score(y, pred, average="macro", labels=CLASES, zero_division=0)

    macro_recall = recall_score(
        y, pred, average="macro", labels=CLASES, zero_division=0
    )

    # Métrica adicional, considerando
    # únicamente las clases reales presentes.
    clases_presentes = sorted(y.unique())

    f1_presentes = f1_score(
        y, pred, average="macro", labels=clases_presentes, zero_division=0
    )

    errores = int((y.to_numpy() != pred).sum())

    print("\nRESULTADOS")
    print(f"Accuracy: {acc:.4f}")
    print(f"Macro-F1 (5 clases): {macro_f1:.4f}")
    print(f"Macro-Recall (5 clases): {macro_recall:.4f}")
    print(f"Macro-F1 (clases presentes): " f"{f1_presentes:.4f}")

    print("Errores:", errores)

    print("\nREPORTE POR CLASE")
    print(classification_report(y, pred, labels=CLASES, zero_division=0))

    print("\nMATRIZ DE CONFUSIÓN")
    print(confusion_matrix(y, pred, labels=CLASES))

    resultados.append(
        {
            "dataset": archivo.name,
            "registros": len(df),
            "clases_presentes": len(clases_presentes),
            "accuracy": acc,
            "macro_f1_5_clases": macro_f1,
            "macro_recall_5_clases": macro_recall,
            "macro_f1_clases_presentes": f1_presentes,
            "errores": errores,
        }
    )

# ==========================================
# 5. RESUMEN
# ==========================================

if resultados:

    tabla = pd.DataFrame(resultados)

    print("\n" + "=" * 65)
    print("COMPARACIÓN ENTRE DATASETS")
    print("=" * 65)

    print(tabla.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    ruta = REPORTS / "twin_validacion_otros_datasets.csv"

    tabla.to_csv(ruta, index=False, encoding="utf-8-sig")

    print("\nReporte guardado:", ruta)

else:
    print("\nNo se pudo evaluar ningún dataset.")

print("\nModelo original sin modificaciones.")
