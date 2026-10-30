from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    recall_score,
    classification_report,
    confusion_matrix,
)

# ==================================================
# 1. CONFIGURACIÓN DEFINITIVA
# ==================================================

BASE = Path(__file__).resolve().parents[3]

DATA = BASE / "data" / "raw" / "digital_twin"
MODELS = BASE / "models"
REPORTS = BASE / "reports"

MODELS.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

archivo = next(DATA.rglob("dataset_01_TC31_05062025_labeled_final.csv"), None)

if archivo is None:
    raise FileNotFoundError("No se encontró Digital Twin")

CLASES = [0, 1, 2, 3, 4]

NOMBRES = {
    0: "Menos de 10 Mbps",
    1: "10 a menos de 40 Mbps",
    2: "40 a menos de 70 Mbps",
    3: "70 a menos de 90 Mbps",
    4: "90 Mbps o más",
}

# ==================================================
# 2. CARGAR DATASET
# ==================================================

df = pd.read_csv(archivo, low_memory=False)

df.columns = df.columns.str.strip()

df = df.sort_values(["Timestamp", "Host Name"]).reset_index(drop=True)

if df["LABEL"].isna().any():
    raise ValueError("Existen etiquetas nulas")

if not set(df["LABEL"].unique()).issubset(CLASES):
    raise ValueError("Existen etiquetas desconocidas")

# ==================================================
# 3. SEPARACIÓN TEMPORAL FINAL
# ==================================================

instantes = np.sort(df["Timestamp"].unique())

corte = int(len(instantes) * 0.80)

inicio_prueba = instantes[corte]

train = df[df["Timestamp"] < inicio_prueba].copy()

test = df[df["Timestamp"] >= inicio_prueba].copy()

y_train = train["LABEL"].astype(int)
y_test = test["LABEL"].astype(int)

print("=" * 65)
print("EVALUACIÓN FINAL - NETWORK DIGITAL TWIN")
print("=" * 65)

print("Registros totales:", len(df))
print("Entrenamiento:", len(train))
print("Prueba final:", len(test))

print("\nCLASES DE ENTRENAMIENTO")
print(y_train.value_counts().sort_index())

print("\nCLASES DE PRUEBA")
print(y_test.value_counts().sort_index())

print("\nPRIMER INSTANTE DE PRUEBA")
print(pd.to_datetime(inicio_prueba, unit="s", utc=True))

# ==================================================
# 4. SELECCIONAR CARACTERÍSTICAS
# ==================================================

# Experimento B:
# Sin ancho de banda directo, sin octetos,
# sin identificación ni timestamp.

columnas = [
    c
    for c in df.columns
    if c not in ["LABEL", "Timestamp", "Host Name"]
    and not c.startswith(("bw_rx.", "bw_tx."))
    and "octets" not in c.lower()
]

X_train = train[columnas].apply(pd.to_numeric, errors="coerce")

X_test = test[columnas].apply(pd.to_numeric, errors="coerce")

X_train = X_train.replace([np.inf, -np.inf], np.nan)

X_test = X_test.replace([np.inf, -np.inf], np.nan)

# Eliminar características constantes usando
# solamente el conjunto de entrenamiento.

columnas_validas = [c for c in X_train.columns if X_train[c].nunique(dropna=True) > 1]

X_train = X_train[columnas_validas]
X_test = X_test[columnas_validas]

print("\nCaracterísticas seleccionadas:", len(columnas_validas))

# ==================================================
# 5. IMPUTACIÓN
# ==================================================

imputador = SimpleImputer(strategy="median", keep_empty_features=True)

train_p = imputador.fit_transform(X_train).astype(np.float32)

test_p = imputador.transform(X_test).astype(np.float32)

# ==================================================
# 6. ENTRENAMIENTO FINAL
# ==================================================

print("\nEntrenando Random Forest...")

modelo = RandomForestClassifier(
    n_estimators=120,
    max_depth=18,
    min_samples_leaf=5,
    class_weight="balanced_subsample",
    random_state=42,
    n_jobs=-1,
)

modelo.fit(train_p, y_train)

# ==================================================
# 7. EVALUACIÓN FINAL
# ==================================================

pred = modelo.predict(test_p)

accuracy = accuracy_score(y_test, pred)

macro_f1 = f1_score(y_test, pred, average="macro", labels=CLASES, zero_division=0)

macro_recall = recall_score(
    y_test, pred, average="macro", labels=CLASES, zero_division=0
)

weighted_f1 = f1_score(y_test, pred, average="weighted", labels=CLASES, zero_division=0)

errores = int((y_test.to_numpy() != pred).sum())

print("\n" + "=" * 65)
print("RESULTADOS FINALES")
print("=" * 65)

print(f"Accuracy: {accuracy:.4f}")
print(f"Macro-F1: {macro_f1:.4f}")
print(f"Macro-Recall: {macro_recall:.4f}")
print(f"Weighted-F1: {weighted_f1:.4f}")

print("Aciertos:", len(test) - errores)
print("Errores:", errores)

print("\nREPORTE POR CLASE")

print(
    classification_report(
        y_test,
        pred,
        labels=CLASES,
        target_names=[f"Clase {i}" for i in CLASES],
        zero_division=0,
    )
)

matriz = confusion_matrix(y_test, pred, labels=CLASES)

print("\nMATRIZ DE CONFUSIÓN")
print(
    pd.DataFrame(
        matriz,
        index=[f"Real {i}" for i in CLASES],
        columns=[f"Pred {i}" for i in CLASES],
    ).to_string()
)

# ==================================================
# 8. RESULTADOS POR ROUTER
# ==================================================

print("\n" + "=" * 65)
print("EVALUACIÓN POR ROUTER")
print("=" * 65)

hosts = test["Host Name"].to_numpy()
reales = y_test.to_numpy()

resultados_routers = []

for host in sorted(np.unique(hosts)):

    mascara = hosts == host

    reales_host = reales[mascara]
    pred_host = pred[mascara]

    acc = accuracy_score(reales_host, pred_host)

    clases_presentes = np.unique(reales_host)

    if len(clases_presentes) > 1:

        f1_host = f1_score(
            reales_host, pred_host, average="macro", labels=CLASES, zero_division=0
        )

        texto_f1 = f"{f1_host:.4f}"

    else:
        f1_host = np.nan
        texto_f1 = "No comparable: una sola clase"

    resultados_routers.append(
        {
            "router": host,
            "registros": int(mascara.sum()),
            "accuracy": acc,
            "macro_f1": f1_host,
        }
    )

    print(f"{host}: " f"accuracy={acc:.4f} | " f"macro-F1={texto_f1}")

# ==================================================
# 9. GUARDAR MODELO Y PREPROCESAMIENTO
# ==================================================

artefacto = {
    "modelo": modelo,
    "imputador": imputador,
    "columnas": columnas_validas,
    "clases": NOMBRES,
    "configuracion": {
        "n_estimators": 120,
        "max_depth": 18,
        "min_samples_leaf": 5,
        "class_weight": "balanced_subsample",
        "random_state": 42,
    },
    "objetivo": "clasificacion_nivel_trafico",
    "modelo_tipo": "clasificacion_contemporanea",
}

ruta_modelo = MODELS / "digital_twin_clasificador.joblib"

joblib.dump(artefacto, ruta_modelo)

# ==================================================
# 10. GUARDAR PREDICCIONES FINALES
# ==================================================

probabilidades = modelo.predict_proba(test_p)

reporte = pd.DataFrame(
    {
        "Timestamp": pd.to_datetime(test["Timestamp"].to_numpy(), unit="s", utc=True),
        "Host Name": hosts,
        "LABEL_real": reales,
        "LABEL_predicho": pred,
        "acierto": reales == pred,
    }
)

for posicion, clase in enumerate(modelo.classes_):
    reporte[f"probabilidad_clase_{clase}"] = probabilidades[:, posicion]

ruta_predicciones = REPORTS / "twin_predicciones_prueba_final.csv"

reporte.to_csv(ruta_predicciones, index=False, encoding="utf-8-sig")

pd.DataFrame(resultados_routers).to_csv(
    REPORTS / "twin_resultados_routers.csv", index=False, encoding="utf-8-sig"
)

metricas = pd.DataFrame(
    [
        {
            "accuracy": accuracy,
            "macro_f1": macro_f1,
            "macro_recall": macro_recall,
            "weighted_f1": weighted_f1,
            "aciertos": len(test) - errores,
            "errores": errores,
            "registros_prueba": len(test),
            "caracteristicas": len(columnas_validas),
        }
    ]
)

metricas.to_csv(
    REPORTS / "twin_metricas_finales.csv", index=False, encoding="utf-8-sig"
)

print("\n" + "=" * 65)
print("ARCHIVOS GENERADOS")
print("=" * 65)

print("Modelo:", ruta_modelo)
print("Predicciones:", ruta_predicciones)
print("Métricas:", REPORTS / "twin_metricas_finales.csv")
print("Routers:", REPORTS / "twin_resultados_routers.csv")

print("\nEvaluación final completada.")
print("No reajustar utilizando los resultados de prueba.")
