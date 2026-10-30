from pathlib import Path

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

# ==============================================
# 1. CONFIGURACIÓN
# ==============================================

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

CLASES = [0, 1, 2, 3, 4]

# ==============================================
# 2. UTILIZAR SOLO DATOS DE DESARROLLO
# ==============================================

instantes = np.sort(df["Timestamp"].unique())

corte = int(len(instantes) * 0.80)

instantes_dev = instantes[:corte]

dev = df[df["Timestamp"].isin(instantes_dev)].copy()

bloques = np.array_split(instantes_dev, 10)

# Entrenar con bloques anteriores y validar
# exclusivamente con bloques posteriores.
ventanas = [(4, 6), (6, 8), (8, 10)]

print("=" * 65)
print("VALIDACIÓN TEMPORAL - NETWORK DIGITAL TWIN")
print("=" * 65)

print("Registros de desarrollo:", len(dev))
print("Bloques:", len(bloques))
print("Pruebas temporales:", len(ventanas))

# ==============================================
# 3. SELECCIÓN DE CARACTERÍSTICAS
# ==============================================

# Mantener el experimento B seleccionado:
# sin ancho de banda ni contadores de octetos.

columnas = [
    c
    for c in dev.columns
    if c not in ["LABEL", "Timestamp", "Host Name"]
    and not c.startswith(("bw_rx.", "bw_tx."))
    and "octets" not in c.lower()
]

resultados = []

# ==============================================
# 4. VALIDAR DIFERENTES PERIODOS
# ==============================================

for numero, (fin_train, fin_val) in enumerate(ventanas, 1):

    print("\n" + "=" * 65)
    print(f"PRUEBA TEMPORAL {numero}")
    print("=" * 65)

    ultimo_train = bloques[fin_train - 1][-1]

    primer_val = bloques[fin_train][0]
    ultimo_val = bloques[fin_val - 1][-1]

    train = dev[dev["Timestamp"] <= ultimo_train].copy()

    val = dev[dev["Timestamp"].between(primer_val, ultimo_val)].copy()

    print("Entrenamiento:", len(train))
    print("Validación:", len(val))

    print("\nCLASES DE VALIDACIÓN")
    print(
        val["LABEL"]
        .value_counts()
        .reindex(CLASES, fill_value=0)
        .sort_index()
        .to_string()
    )

    # ==========================================
    # 5. PREPARAR DATOS
    # ==========================================

    X_train = train[columnas].apply(pd.to_numeric, errors="coerce")

    X_val = val[columnas].apply(pd.to_numeric, errors="coerce")

    X_train = X_train.replace([np.inf, -np.inf], np.nan)

    X_val = X_val.replace([np.inf, -np.inf], np.nan)

    columnas_validas = [
        c for c in X_train.columns if X_train[c].nunique(dropna=True) > 1
    ]

    X_train = X_train[columnas_validas]
    X_val = X_val[columnas_validas]

    y_train = train["LABEL"].astype(int)
    y_val = val["LABEL"].astype(int)

    imputador = SimpleImputer(strategy="median", keep_empty_features=True)

    train_p = imputador.fit_transform(X_train).astype(np.float32)

    val_p = imputador.transform(X_val).astype(np.float32)

    # ==========================================
    # 6. ENTRENAR RANDOM FOREST
    # ==========================================

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

    # ==========================================
    # 7. EVALUAR
    # ==========================================

    accuracy = accuracy_score(y_val, pred)

    macro_f1 = f1_score(y_val, pred, average="macro", labels=CLASES, zero_division=0)

    macro_recall = recall_score(
        y_val, pred, average="macro", labels=CLASES, zero_division=0
    )

    errores = int((y_val.to_numpy() != pred).sum())

    print("\nRESULTADOS")

    print(f"Accuracy: {accuracy:.4f}")
    print(f"Macro-F1: {macro_f1:.4f}")
    print(f"Macro-Recall: {macro_recall:.4f}")
    print("Errores:", errores)

    print("\nREPORTE POR CLASE")

    print(classification_report(y_val, pred, labels=CLASES, zero_division=0))

    print("\nMATRIZ DE CONFUSIÓN")

    print(confusion_matrix(y_val, pred, labels=CLASES))

    resultados.append(
        {
            "prueba": numero,
            "bloques_entrenamiento": f"1-{fin_train}",
            "bloques_validacion": (f"{fin_train + 1}-{fin_val}"),
            "registros_train": len(train),
            "registros_val": len(val),
            "caracteristicas": len(columnas_validas),
            "accuracy": accuracy,
            "macro_f1": macro_f1,
            "macro_recall": macro_recall,
            "errores": errores,
        }
    )

    # Examinar por separado el bloque 10
    if fin_val == 10:

        mascara = val["Timestamp"] >= bloques[9][0]

        reales_b10 = y_val.to_numpy()[mascara]
        pred_b10 = pred[mascara]

        print("\nDESEMPEÑO ESPECÍFICO DEL BLOQUE 10")

        print("Accuracy:", round(accuracy_score(reales_b10, pred_b10), 4))

        print(
            "Macro-F1:",
            round(
                f1_score(
                    reales_b10,
                    pred_b10,
                    average="macro",
                    labels=CLASES,
                    zero_division=0,
                ),
                4,
            ),
        )

# ==============================================
# 8. COMPARACIÓN FINAL
# ==============================================

tabla = pd.DataFrame(resultados)

print("\n" + "=" * 65)
print("COMPARACIÓN DE VALIDACIONES TEMPORALES")
print("=" * 65)

print(tabla.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

print("\nRESUMEN")

print("Macro-F1 promedio:", round(tabla["macro_f1"].mean(), 4))

print("Macro-F1 mínimo:", round(tabla["macro_f1"].min(), 4))

print("Macro-F1 máximo:", round(tabla["macro_f1"].max(), 4))

ruta = REPORTS / "twin_validacion_temporal.csv"

tabla.to_csv(ruta, index=False, encoding="utf-8-sig")

print("\nReporte guardado:", ruta)

print("Validación temporal finalizada.")
print("No se modificó el modelo exportado.")
