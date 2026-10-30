from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.dummy import DummyClassifier
from sklearn.tree import DecisionTreeClassifier
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
# 1. CONFIGURACIÓN
# ==================================================

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

print("=" * 65)
print("ENTRENAMIENTO - NETWORK DIGITAL TWIN")
print("=" * 65)

print("Registros:", len(df))
print("Columnas:", len(df.columns))

# ==================================================
# 2. DIVISIÓN TEMPORAL
# ==================================================

instantes = np.sort(df["Timestamp"].unique())

# Último 20% reservado
corte_test = int(len(instantes) * 0.80)

# Del 80% de desarrollo, usar 80% para
# entrenamiento y 20% para validación
corte_val = int(corte_test * 0.80)

inicio_val = instantes[corte_val]
inicio_test = instantes[corte_test]

train = df[df["Timestamp"] < inicio_val].copy()

val = df[(df["Timestamp"] >= inicio_val) & (df["Timestamp"] < inicio_test)].copy()

print("\nDISTRIBUCIÓN TEMPORAL")
print("Entrenamiento:", len(train))
print("Validación:", len(val))
print("Prueba final reservada:", len(df) - len(train) - len(val))

print("\nCLASES DE ENTRENAMIENTO")
print(train["LABEL"].value_counts().sort_index())

print("\nCLASES DE VALIDACIÓN")
print(val["LABEL"].value_counts().sort_index())

# ==================================================
# 3. CARACTERÍSTICAS
# ==================================================

# Estas columnas NO deben usarse para entrenar
excluir = ["LABEL", "Timestamp", "Host Name"]

# Excluir ancho de banda, pues determina la etiqueta
columnas_bw = [c for c in df.columns if c.startswith(("bw_rx.", "bw_tx."))]

excluir += columnas_bw

# Experimento A:
# Métricas SNMP sin columnas directas de ancho de banda
columnas_a = [c for c in df.columns if c not in excluir]

# Experimento B:
# También excluir contadores de octetos
columnas_b = [c for c in columnas_a if "octets" not in c.lower()]

experimentos = {"A_sin_bw": columnas_a, "B_sin_bw_ni_octetos": columnas_b}

# ==================================================
# 4. MODELOS
# ==================================================

modelos = {
    "Dummy": DummyClassifier(strategy="most_frequent"),
    "DecisionTree": DecisionTreeClassifier(
        max_depth=12, min_samples_leaf=20, class_weight="balanced", random_state=42
    ),
    "RandomForest": RandomForestClassifier(
        n_estimators=120,
        max_depth=18,
        min_samples_leaf=5,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    ),
}

# ==================================================
# 5. ENTRENAMIENTO
# ==================================================

resultados = []

y_train = train["LABEL"].astype(int)
y_val = val["LABEL"].astype(int)

for experimento, columnas in experimentos.items():

    print("\n" + "=" * 65)
    print("EXPERIMENTO:", experimento)
    print("=" * 65)

    X_train = train[columnas].apply(pd.to_numeric, errors="coerce")

    X_val = val[columnas].apply(pd.to_numeric, errors="coerce")

    X_train = X_train.replace([np.inf, -np.inf], np.nan)

    X_val = X_val.replace([np.inf, -np.inf], np.nan)

    # Seleccionar variables no constantes,
    # usando exclusivamente entrenamiento.
    columnas_validas = [
        c for c in X_train.columns if X_train[c].nunique(dropna=True) > 1
    ]

    X_train = X_train[columnas_validas]
    X_val = X_val[columnas_validas]

    print("Características utilizadas:", len(columnas_validas))

    # Imputación ajustada solo con entrenamiento
    imputador = SimpleImputer(strategy="median", keep_empty_features=True)

    train_p = imputador.fit_transform(X_train).astype(np.float32)

    val_p = imputador.transform(X_val).astype(np.float32)

    for nombre, modelo in modelos.items():

        print("\n" + "-" * 55)
        print("MODELO:", nombre)
        print("-" * 55)

        modelo.fit(train_p, y_train)

        pred = modelo.predict(val_p)

        accuracy = accuracy_score(y_val, pred)

        macro_f1 = f1_score(
            y_val, pred, average="macro", labels=[0, 1, 2, 3, 4], zero_division=0
        )

        macro_recall = recall_score(
            y_val, pred, average="macro", labels=[0, 1, 2, 3, 4], zero_division=0
        )

        # Comprobar desempeño sin r7,
        # porque ese router solo tiene clase 0
        mascara_sin_r7 = val["Host Name"].to_numpy() != "r7"

        f1_sin_r7 = f1_score(
            y_val.to_numpy()[mascara_sin_r7],
            pred[mascara_sin_r7],
            average="macro",
            labels=[0, 1, 2, 3, 4],
            zero_division=0,
        )

        print(f"Accuracy: {accuracy:.4f}")
        print(f"Macro-F1: {macro_f1:.4f}")
        print(f"Macro-Recall: {macro_recall:.4f}")
        print(f"Macro-F1 sin r7: {f1_sin_r7:.4f}")

        print("\nREPORTE POR CLASE")

        print(
            classification_report(
                y_val,
                pred,
                labels=[0, 1, 2, 3, 4],
                target_names=["Clase 0", "Clase 1", "Clase 2", "Clase 3", "Clase 4"],
                zero_division=0,
            )
        )

        print("MATRIZ DE CONFUSIÓN")

        matriz = confusion_matrix(y_val, pred, labels=[0, 1, 2, 3, 4])

        print(matriz)

        resultados.append(
            {
                "experimento": experimento,
                "modelo": nombre,
                "caracteristicas": len(columnas_validas),
                "accuracy": accuracy,
                "macro_f1": macro_f1,
                "macro_recall": macro_recall,
                "macro_f1_sin_r7": f1_sin_r7,
            }
        )

# ==================================================
# 6. COMPARACIÓN FINAL
# ==================================================

tabla = pd.DataFrame(resultados)

tabla = tabla.sort_values("macro_f1", ascending=False)

print("\n" + "=" * 65)
print("COMPARACIÓN FINAL - DIGITAL TWIN")
print("=" * 65)

print(tabla.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

ruta = REPORTS / "twin_entrenamiento_inicial.csv"

tabla.to_csv(ruta, index=False, encoding="utf-8-sig")

print("\nResultados guardados:", ruta)

print("\nEntrenamiento inicial finalizado.")
print("Prueba final intacta.")
print("Ningún modelo definitivo exportado.")
