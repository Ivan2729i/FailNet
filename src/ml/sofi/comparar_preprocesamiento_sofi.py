from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import TimeSeriesSplit
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
    raise FileNotFoundError("No se encontró SOFI CoreSwitch-I.csv")

df = pd.read_csv(archivo)
df.columns = df.columns.str.strip()
df = df.sort_values("timestamp").reset_index(drop=True)

y = df["class"].str.strip().map({"NE": 0, "F": 1})

if y.isna().any():
    raise ValueError("Se encontraron clases desconocidas")

y = y.astype(int)

X = df.drop(columns=["class", "timestamp", "range"])

# Reservar el último 20%
corte = int(len(df) * 0.80)

X_dev = X.iloc[:corte]
y_dev = y.iloc[:corte]

UMBRAL = 0.30

ESTRATEGIAS = ["original", "imputacion", "imputacion_indicadores", "pocas_ausencias"]

# ==================================================
# 2. PREPARACIÓN DE DATOS
# ==================================================


def preparar_datos(x_train, x_val, estrategia):

    train = x_train.copy()
    val = x_val.copy()

    if estrategia == "original":
        return (train.to_numpy(dtype=float), val.to_numpy(dtype=float), train.shape[1])

    if estrategia == "pocas_ausencias":

        # Selección basada solo en entrenamiento
        porcentaje_negativos = (train < 0).mean()

        columnas = porcentaje_negativos[porcentaje_negativos <= 0.05].index.tolist()

        if not columnas:
            raise ValueError("No hay variables con pocas ausencias")

        train = train[columnas]
        val = val[columnas]

    # Valores negativos considerados mediciones no disponibles
    train = train.mask(train < 0)
    val = val.mask(val < 0)

    # La imputación se ajusta solo al entrenamiento
    imputador = SimpleImputer(
        strategy="median",
        add_indicator=(estrategia == "imputacion_indicadores"),
        keep_empty_features=True,
    )

    train_procesado = imputador.fit_transform(train)
    val_procesado = imputador.transform(val)

    return (train_procesado, val_procesado, train.shape[1])


# ==================================================
# 3. PREPARAR VALIDACIÓN TEMPORAL
# ==================================================

cv = TimeSeriesSplit(n_splits=3, gap=24)

# Identificar bloques consecutivos de falla
fallas = y_dev.eq(1)

episodios = (fallas & ~fallas.shift(fill_value=False)).cumsum().where(fallas, 0)

splits = []

for train_idx, val_idx in cv.split(X_dev):

    ids_train = set(episodios.iloc[train_idx]) - {0}

    ids_val = set(episodios.iloc[val_idx]) - {0}

    compartidos = ids_train.intersection(ids_val)

    if compartidos:
        conservar = ~episodios.iloc[train_idx].isin(compartidos).to_numpy()

        train_idx = train_idx[conservar]

    splits.append((train_idx, val_idx))


# ==================================================
# 4. ENTRENAMIENTO Y EVALUACIÓN
# ==================================================

resultados = []

print("=" * 65)
print("COMPARACIÓN DE PREPROCESAMIENTO - SOFI")
print("=" * 65)
print("Umbral fijo:", UMBRAL)
print("Registros de desarrollo:", len(X_dev))
print("Registros de prueba reservados:", len(X) - corte)

for estrategia in ESTRATEGIAS:

    print("\n" + "=" * 65)
    print("ESTRATEGIA:", estrategia.upper())
    print("=" * 65)

    for numero, (train_idx, val_idx) in enumerate(splits, 1):

        x_train = X_dev.iloc[train_idx]
        x_val = X_dev.iloc[val_idx]

        y_train = y_dev.iloc[train_idx]
        y_val = y_dev.iloc[val_idx]

        X_train_p, X_val_p, n_variables = preparar_datos(x_train, x_val, estrategia)

        modelo = RandomForestClassifier(
            n_estimators=200, min_samples_leaf=2, random_state=42, n_jobs=-1
        )

        modelo.fit(X_train_p, y_train)

        indice_falla = list(modelo.classes_).index(1)

        probs = modelo.predict_proba(X_val_p)[:, indice_falla]

        pred = (probs >= UMBRAL).astype(int)

        tn, fp, fn, tp = confusion_matrix(y_val, pred, labels=[0, 1]).ravel()

        precision = tp / (tp + fp) if tp + fp > 0 else 0

        recall = tp / (tp + fn) if tp + fn > 0 else 0

        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall > 0
            else 0
        )

        resultados.append(
            {
                "estrategia": estrategia,
                "ventana": numero,
                "variables_originales": n_variables,
                "tp": int(tp),
                "fp": int(fp),
                "fn": int(fn),
                "tn": int(tn),
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )

        print(f"\nVentana {numero}")
        print(f"Variables seleccionadas: {n_variables}")
        print(f"Fallas reales: {tp + fn}")
        print(f"Detectadas: {tp}")
        print(f"Omitidas: {fn}")
        print(f"Falsas alarmas: {fp}")

        if tp + fn > 0:
            print(f"Precision: {precision:.3f}")
            print(f"Recall: {recall:.3f}")
            print(f"F1-score: {f1:.3f}")
        else:
            print("Sin fallas reales en esta ventana")


# ==================================================
# 5. RESULTADOS GLOBALES
# ==================================================

tabla = pd.DataFrame(resultados)

resumen = tabla.groupby("estrategia", as_index=False)[["tp", "fp", "fn", "tn"]].sum()

resumen["precision"] = (
    resumen["tp"] / (resumen["tp"] + resumen["fp"]).replace(0, np.nan)
).fillna(0)

resumen["recall"] = (
    resumen["tp"] / (resumen["tp"] + resumen["fn"]).replace(0, np.nan)
).fillna(0)

resumen["f1"] = (
    2
    * resumen["precision"]
    * resumen["recall"]
    / (resumen["precision"] + resumen["recall"]).replace(0, np.nan)
).fillna(0)

resumen = resumen.sort_values("f1", ascending=False)

print("\n" + "=" * 65)
print("COMPARACIÓN FINAL DE ESTRATEGIAS")
print("=" * 65)

print(resumen.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

tabla.to_csv(
    REPORTS / "sofi_preprocesamiento_ventanas.csv", index=False, encoding="utf-8-sig"
)

resumen.to_csv(
    REPORTS / "sofi_preprocesamiento_resumen.csv", index=False, encoding="utf-8-sig"
)

print("\nExperimento finalizado.")
print("La prueba final permanece reservada.")
print("Ningún modelo definitivo ha sido exportado.")
