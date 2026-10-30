from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, classification_report

# ==========================================
# 1. CARGAR DATOS
# ==========================================

BASE = Path(__file__).resolve().parents[3]
DATA = BASE / "data" / "raw" / "digital_twin"
REPORTS = BASE / "reports"

REPORTS.mkdir(parents=True, exist_ok=True)

archivo = next(DATA.rglob("dataset_01_TC31_05062025_labeled_final.csv"), None)

if archivo is None:
    raise FileNotFoundError("No se encontró el dataset")

df = pd.read_csv(archivo, low_memory=False)
df.columns = df.columns.str.strip()

df = df.sort_values(["Timestamp", "Host Name"]).reset_index(drop=True)

# ==========================================
# 2. DIVISIÓN TEMPORAL
# ==========================================

instantes = np.sort(df["Timestamp"].unique())

corte_test = int(len(instantes) * 0.80)
corte_val = int(corte_test * 0.80)

inicio_val = instantes[corte_val]
inicio_test = instantes[corte_test]

train = df[df["Timestamp"] < inicio_val].copy()

val = df[(df["Timestamp"] >= inicio_val) & (df["Timestamp"] < inicio_test)].copy()

# ==========================================
# 3. CARACTERÍSTICAS DEL EXPERIMENTO B
# ==========================================

columnas = [
    c
    for c in df.columns
    if c not in ["LABEL", "Timestamp", "Host Name"]
    and not c.startswith(("bw_rx.", "bw_tx."))
    and "octets" not in c.lower()
]

X_train = train[columnas].apply(pd.to_numeric, errors="coerce")

X_val = val[columnas].apply(pd.to_numeric, errors="coerce")

X_train = X_train.replace([np.inf, -np.inf], np.nan)

X_val = X_val.replace([np.inf, -np.inf], np.nan)

columnas_validas = [c for c in X_train.columns if X_train[c].nunique(dropna=True) > 1]

X_train = X_train[columnas_validas]
X_val = X_val[columnas_validas]

y_train = train["LABEL"].astype(int)
y_val = val["LABEL"].astype(int)

imputador = SimpleImputer(strategy="median", keep_empty_features=True)

train_p = imputador.fit_transform(X_train).astype(np.float32)

val_p = imputador.transform(X_val).astype(np.float32)

# ==========================================
# 4. ENTRENAR RANDOM FOREST
# ==========================================

print("=" * 65)
print("DIAGNÓSTICO - DIGITAL TWIN")
print("=" * 65)

modelo = RandomForestClassifier(
    n_estimators=120,
    max_depth=18,
    min_samples_leaf=5,
    class_weight="balanced_subsample",
    random_state=42,
    n_jobs=-1,
)

modelo.fit(train_p, y_train)

pred = modelo.predict(val_p)

print("Características:", len(columnas_validas))
print("Registros de validación:", len(val))
print(
    "Macro-F1:",
    round(
        f1_score(y_val, pred, average="macro", labels=[0, 1, 2, 3, 4], zero_division=0),
        4,
    ),
)

# ==========================================
# 5. IMPORTANCIA DE VARIABLES
# ==========================================

importancia = pd.Series(
    modelo.feature_importances_, index=columnas_validas
).sort_values(ascending=False)

print("\n" + "=" * 65)
print("20 CARACTERÍSTICAS MÁS IMPORTANTES")
print("=" * 65)

print(importancia.head(20).to_string())

importancia.to_csv(
    REPORTS / "twin_importancia_variables.csv",
    header=["importancia"],
    encoding="utf-8-sig",
)

# ==========================================
# 6. RESULTADOS POR ROUTER
# ==========================================

print("\n" + "=" * 65)
print("DESEMPEÑO POR ROUTER")
print("=" * 65)

hosts = val["Host Name"].to_numpy()
reales = y_val.to_numpy()

for host in sorted(np.unique(hosts)):

    mascara = hosts == host

    real_host = reales[mascara]
    pred_host = pred[mascara]

    accuracy = accuracy_score(real_host, pred_host)

    print(f"\n{host}: " f"{mascara.sum()} registros, " f"accuracy={accuracy:.4f}")

    if len(np.unique(real_host)) > 1:
        macro_f1 = f1_score(
            real_host,
            pred_host,
            average="macro",
            labels=[0, 1, 2, 3, 4],
            zero_division=0,
        )

        print(f"Macro-F1: {macro_f1:.4f}")
    else:
        print("Una sola clase real: " "macro-F1 multiclase no comparable")

# ==========================================
# 7. ERRORES CERCA DE LOS LIMITES
# ==========================================

columnas_bw = [c for c in val.columns if c.startswith(("bw_rx.", "bw_tx."))]

# Únicamente para analizar los errores.
# Estas columnas NO se utilizaron en el modelo.
max_bw = val[columnas_bw].max(axis=1).fillna(0).to_numpy()

limites = np.array([10, 40, 70, 90])

distancias = np.min(np.abs(max_bw[:, None] - limites), axis=1)

errores = pred != reales

print("\n" + "=" * 65)
print("ANÁLISIS DE ERRORES")
print("=" * 65)

print("Errores totales:", int(errores.sum()))

for margen in [0.5, 1.0, 2.0, 5.0]:

    cercanos = distancias <= margen

    errores_cercanos = int(np.sum(errores & cercanos))

    print(f"Errores a <= {margen} Mbps " f"de una frontera: {errores_cercanos}")

print("\nREPORTE FINAL POR CLASE")

print(classification_report(reales, pred, labels=[0, 1, 2, 3, 4], zero_division=0))

print("\nDiagnóstico finalizado.")
print("Prueba final intacta.")
