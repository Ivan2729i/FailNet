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

UMBRAL = 0.375

# ==================================================
# 2. CARGAR LOS DOS SWITCHES
# ==================================================


def cargar_switch(nombre):
    archivo = next(DATA.rglob(nombre), None)

    if archivo is None:
        raise FileNotFoundError(nombre)

    df = pd.read_csv(archivo)
    df.columns = df.columns.str.strip()

    # Normalizar diferencia de nombres
    df = df.rename(columns={"SNMP_availability": "SNMP_Availability"})

    return df.sort_values("timestamp").reset_index(drop=True)


switch1 = cargar_switch("SOFI CoreSwitch-I.csv")
switch2 = cargar_switch("SOFI CoreSwitch-II.csv")

# ==================================================
# 3. SINCRONIZAR POR TIMESTAMP
# ==================================================

datos = switch1.merge(
    switch2, on="timestamp", how="inner", suffixes=("_I", "_II"), validate="one_to_one"
)

datos = datos.sort_values("timestamp").reset_index(drop=True)

if not (datos["class_I"] == datos["class_II"]).all():
    raise ValueError("Existen etiquetas diferentes entre switches")

print("=" * 65)
print("COMPARACIÓN DE SWITCHES - SOFI")
print("=" * 65)

print("Registros sincronizados:", len(datos))

# ==================================================
# 4. PREPARAR ETIQUETAS Y CARACTERÍSTICAS
# ==================================================

y = datos["class_I"].map({"NE": 0, "F": 1})

if y.isna().any():
    raise ValueError("Etiquetas desconocidas")

y = y.astype(int)

columnas = [
    col for col in switch1.columns if col not in ["timestamp", "class", "range"]
]

columnas_I = [f"{col}_I" for col in columnas]
columnas_II = [f"{col}_II" for col in columnas]

datasets = {
    "CoreSwitch-I": datos[columnas_I],
    "CoreSwitch-II": datos[columnas_II],
    "Ambos switches": datos[columnas_I + columnas_II],
}

# ==================================================
# 5. DIVISIÓN TEMPORAL
# ==================================================

corte = int(len(datos) * 0.80)

y_dev = y.iloc[:corte]

cv = TimeSeriesSplit(n_splits=3, gap=24)

episodios_falla = y_dev.eq(1)

episodios = (
    (episodios_falla & ~episodios_falla.shift(fill_value=False))
    .cumsum()
    .where(episodios_falla, 0)
)

splits = []

for train_idx, val_idx in cv.split(y_dev):

    ids_train = set(episodios.iloc[train_idx]) - {0}

    ids_val = set(episodios.iloc[val_idx]) - {0}

    compartidos = ids_train.intersection(ids_val)

    if compartidos:
        conservar = ~episodios.iloc[train_idx].isin(compartidos).to_numpy()

        train_idx = train_idx[conservar]

    splits.append((train_idx, val_idx))

# ==================================================
# 6. ENTRENAMIENTO Y EVALUACIÓN
# ==================================================

resultados = []

for nombre, X in datasets.items():

    print("\n" + "=" * 65)
    print("MODELO:", nombre)
    print("=" * 65)

    X_dev = X.iloc[:corte]

    totales = np.zeros(4, dtype=int)

    for numero, (train_idx, val_idx) in enumerate(splits, 1):

        x_train = X_dev.iloc[train_idx].copy()
        x_val = X_dev.iloc[val_idx].copy()

        y_train = y_dev.iloc[train_idx]
        y_val = y_dev.iloc[val_idx]

        # Valores negativos como mediciones no disponibles
        x_train = x_train.mask(x_train < 0)
        x_val = x_val.mask(x_val < 0)

        # Imputación solo con entrenamiento
        imputador = SimpleImputer(strategy="median", keep_empty_features=True)

        train_p = imputador.fit_transform(x_train)
        val_p = imputador.transform(x_val)

        modelo = RandomForestClassifier(
            n_estimators=200, min_samples_leaf=2, random_state=42, n_jobs=-1
        )

        modelo.fit(train_p, y_train)

        indice = list(modelo.classes_).index(1)

        probabilidades = modelo.predict_proba(val_p)[:, indice]

        pred = (probabilidades >= UMBRAL).astype(int)

        tn, fp, fn, tp = confusion_matrix(y_val, pred, labels=[0, 1]).ravel()

        totales += np.array([tn, fp, fn, tp])

        print(f"\nVentana {numero}")
        print(f"Fallas detectadas: {tp}")
        print(f"Fallas omitidas: {fn}")
        print(f"Falsas alarmas: {fp}")

    # ==================================================
    # 7. MÉTRICAS GLOBALES
    # ==================================================

    tn, fp, fn, tp = totales

    precision = tp / (tp + fp) if tp + fp > 0 else 0

    recall = tp / (tp + fn) if tp + fn > 0 else 0

    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0

    resultados.append(
        {
            "modelo": nombre,
            "variables": X.shape[1],
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "detectadas": int(tp),
            "omitidas": int(fn),
            "falsas_alarmas": int(fp),
        }
    )

# ==================================================
# 8. COMPARACIÓN FINAL
# ==================================================

tabla = pd.DataFrame(resultados)

tabla = tabla.sort_values("f1", ascending=False)

print("\n" + "=" * 65)
print("COMPARACIÓN FINAL")
print("=" * 65)

print(tabla.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

ruta = REPORTS / "sofi_comparacion_switches.csv"

tabla.to_csv(ruta, index=False, encoding="utf-8-sig")

print("\nResultados guardados:", ruta)
print("Prueba final reservada.")
