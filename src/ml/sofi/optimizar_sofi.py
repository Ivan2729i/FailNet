from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import confusion_matrix

# ==================================================
# 1. CONFIGURACIÓN
# ==================================================

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "raw" / "sofi"
REPORTS = BASE / "reports"

REPORTS.mkdir(parents=True, exist_ok=True)

archivo = next(DATA.rglob("SOFI CoreSwitch-I.csv"), None)

if archivo is None:
    raise FileNotFoundError(f"No se encontró SOFI CoreSwitch-I.csv dentro de {DATA}")

print(f"Dataset encontrado: {archivo}")

df = pd.read_csv(archivo)
df.columns = df.columns.str.strip()
df = df.sort_values("timestamp").reset_index(drop=True)

y = df["class"].str.strip().map({"NE": 0, "F": 1})

if y.isna().any():
    raise ValueError("Hay etiquetas desconocidas")

y = y.astype(int)

X = df.drop(columns=["class", "timestamp", "range"])

if X.isna().any().any():
    raise ValueError("Hay valores faltantes")

# Reservar el último 20% para la prueba final
corte = int(len(df) * 0.80)

X_dev = X.iloc[:corte]
y_dev = y.iloc[:corte]

print("=" * 65)
print("OPTIMIZACIÓN DEL MODELO SOFI")
print("=" * 65)

print("Registros de desarrollo:", len(X_dev))
print("Registros reservados:", len(df) - corte)
print("Características:", X_dev.shape[1])

# ==================================================
# 2. VALIDACIÓN CRUZADA TEMPORAL
# ==================================================

cv = TimeSeriesSplit(n_splits=3, gap=24)

splits = list(cv.split(X_dev))

# Identificar episodios consecutivos de falla
fallas = y_dev.eq(1)

episodios = (fallas & ~fallas.shift(fill_value=False)).cumsum().where(fallas, 0)

splits_validos = []

print("\nVENTANAS DE VALIDACIÓN")

for i, (train_idx, val_idx) in enumerate(splits, 1):

    # Evitar compartir un episodio de falla
    ids_train = set(episodios.iloc[train_idx]) - {0}

    ids_val = set(episodios.iloc[val_idx]) - {0}

    compartidos = ids_train.intersection(ids_val)

    if compartidos:
        mascara = ~episodios.iloc[train_idx].isin(compartidos).to_numpy()

        train_idx = train_idx[mascara]

    n_fallas_train = int(y_dev.iloc[train_idx].sum())
    n_fallas_val = int(y_dev.iloc[val_idx].sum())

    print(
        f"\nVentana {i}: "
        f"entrenamiento={len(train_idx)}, "
        f"validación={len(val_idx)}"
    )

    print(
        f"Fallas entrenamiento={n_fallas_train}, " f"fallas validación={n_fallas_val}"
    )

    if n_fallas_train == 0:
        print("Omitida: no tiene fallas para aprender")
        continue

    splits_validos.append((train_idx, val_idx))

if len(splits_validos) < 2:
    raise ValueError(
        "Hay menos de dos ventanas utilizables. "
        "Necesitamos revisar la distribución temporal."
    )

# ==================================================
# 3. CONFIGURACIONES A COMPARAR
# ==================================================

modelos = {
    "RF_original": RandomForestClassifier(
        n_estimators=200,
        min_samples_leaf=3,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    ),
    "RF_depth8_leaf2": RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    ),
    "RF_depth12_leaf2": RandomForestClassifier(
        n_estimators=250,
        max_depth=12,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    ),
    "RF_depth16_leaf1": RandomForestClassifier(
        n_estimators=250,
        max_depth=16,
        min_samples_leaf=1,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    ),
    "RF_leaf5": RandomForestClassifier(
        n_estimators=200,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    ),
    "RF_sin_pesos": RandomForestClassifier(
        n_estimators=200, min_samples_leaf=2, random_state=42, n_jobs=-1
    ),
    "ExtraTrees": ExtraTreesClassifier(
        n_estimators=200,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    ),
    "DecisionTree": DecisionTreeClassifier(
        max_depth=8, min_samples_leaf=3, class_weight="balanced", random_state=42
    ),
}

umbrales = [
    0.05,
    0.08,
    0.10,
    0.12,
    0.15,
    0.18,
    0.20,
    0.22,
    0.25,
    0.30,
    0.35,
    0.40,
    0.50,
]

# ==================================================
# 4. ENTRENAR CADA CONFIGURACIÓN
# ==================================================

resultados = []

for nombre, configuracion in modelos.items():

    print("\n" + "=" * 65)
    print("EVALUANDO:", nombre)
    print("=" * 65)

    # Predicciones de las ventanas de validación
    probabilidades = np.full(len(X_dev), np.nan)

    for i, (train_idx, val_idx) in enumerate(splits_validos, 1):

        modelo = clone(configuracion)

        modelo.fit(X_dev.iloc[train_idx], y_dev.iloc[train_idx])

        indice_falla = list(modelo.classes_).index(1)

        pred_prob = modelo.predict_proba(X_dev.iloc[val_idx])[:, indice_falla]

        probabilidades[val_idx] = pred_prob

        print(f"Ventana {i}: evaluada")

        # Diagnóstico individual de las configuraciones candidatas
        candidatos = {"RF_original": 0.20, "RF_sin_pesos": 0.30}

        if nombre in candidatos:
            umbral_candidato = candidatos[nombre]

            pred_clases = (pred_prob >= umbral_candidato).astype(int)

            y_real_fold = y_dev.iloc[val_idx].to_numpy()

            tn, fp, fn, tp = confusion_matrix(
                y_real_fold, pred_clases, labels=[0, 1]
            ).ravel()

            precision_fold = tp / (tp + fp) if tp + fp > 0 else 0

            recall_fold = tp / (tp + fn) if tp + fn > 0 else 0

            f1_fold = (
                2 * precision_fold * recall_fold / (precision_fold + recall_fold)
                if precision_fold + recall_fold > 0
                else 0
            )

            print(f"  Umbral: {umbral_candidato:.2f}")
            print(f"  Fallas reales: {tp + fn}")
            print(f"  Detectadas: {tp}")
            print(f"  Omitidas: {fn}")
            print(f"  Falsas alarmas: {fp}")
            print(f"  Normales correctos: {tn}")
            print(f"  Precision: {precision_fold:.3f}")

            if tp + fn > 0:
                print(f"  Recall: {recall_fold:.3f}")
                print(f"  F1-score: {f1_fold:.3f}")
            else:
                print(
                    "  Recall y F1: no evaluables "
                    "(sin fallas reales en esta ventana)"
                )

    # Utilizar solamente predicciones de validación
    mascara = ~np.isnan(probabilidades)

    y_real = y_dev.to_numpy()[mascara]
    probs = probabilidades[mascara]

    for umbral in umbrales:

        pred = (probs >= umbral).astype(int)

        tn, fp, fn, tp = confusion_matrix(y_real, pred, labels=[0, 1]).ravel()

        precision = tp / (tp + fp) if tp + fp > 0 else 0

        recall = tp / (tp + fn) if tp + fn > 0 else 0

        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall > 0
            else 0
        )

        tasa_falsas_alarmas = fp / (fp + tn) if fp + tn > 0 else 0

        resultados.append(
            {
                "modelo": nombre,
                "umbral": umbral,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "fpr": tasa_falsas_alarmas,
                "tp": int(tp),
                "fp": int(fp),
                "fn": int(fn),
                "tn": int(tn),
            }
        )

# ==================================================
# 5. COMPARAR RESULTADOS
# ==================================================

tabla = pd.DataFrame(resultados)

tabla = tabla.sort_values(
    by=["f1", "recall", "fp"], ascending=[False, False, True]
).reset_index(drop=True)

ruta = REPORTS / "sofi_optimizacion_cv.csv"

tabla.to_csv(ruta, index=False, encoding="utf-8-sig")

print("\n" + "=" * 65)
print("MEJORES 15 CONFIGURACIONES")
print("=" * 65)

columnas = ["modelo", "umbral", "precision", "recall", "f1", "tp", "fp", "fn"]

print(
    tabla[columnas].head(15).to_string(index=False, float_format=lambda x: f"{x:.3f}")
)

# ==================================================
# 6. MEJOR CONFIGURACIÓN PROVISIONAL
# ==================================================

mejor = tabla.iloc[0]

print("\n" + "=" * 65)
print("MEJOR CONFIGURACIÓN SEGÚN F1")
print("=" * 65)

print("Modelo:", mejor["modelo"])
print(f"Umbral: {mejor['umbral']:.2f}")
print(f"Precision: {mejor['precision']:.3f}")
print(f"Recall: {mejor['recall']:.3f}")
print(f"F1: {mejor['f1']:.3f}")

print("Fallas detectadas:", int(mejor["tp"]))
print("Fallas omitidas:", int(mejor["fn"]))
print("Falsas alarmas:", int(mejor["fp"]))

print("\nResultados guardados en:", ruta)

print("\nIMPORTANTE: " "El conjunto de prueba final sigue reservado.")
