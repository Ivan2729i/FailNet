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


def cargar(nombre):
    archivo = next(DATA.rglob(nombre), None)

    if archivo is None:
        raise FileNotFoundError(nombre)

    df = pd.read_csv(archivo)
    df.columns = df.columns.str.strip()

    df = df.rename(columns={"SNMP_availability": "SNMP_Availability"})

    return df.sort_values("timestamp").reset_index(drop=True)


# ==================================================
# 2. COMBINAR AMBOS SWITCHES
# ==================================================

sw1 = cargar("SOFI CoreSwitch-I.csv")
sw2 = cargar("SOFI CoreSwitch-II.csv")

df = sw1.merge(
    sw2, on="timestamp", how="inner", suffixes=("_I", "_II"), validate="one_to_one"
)

df = df.sort_values("timestamp").reset_index(drop=True)

if not (df["class_I"] == df["class_II"]).all():
    raise ValueError("Las etiquetas no coinciden")

y = df["class_I"].map({"NE": 0, "F": 1}).astype(int)

X = df.drop(columns=["timestamp", "class_I", "class_II", "range_I", "range_II"])

# Reservar el último 20%
corte = int(len(df) * 0.80)

X_dev = X.iloc[:corte]
y_dev = y.iloc[:corte]

print("=" * 60)
print("OPTIMIZACIÓN SOFI - AMBOS SWITCHES")
print("=" * 60)
print("Registros sincronizados:", len(df))
print("Características:", X.shape[1])
print("Registros de desarrollo:", len(X_dev))
print("Registros reservados:", len(df) - corte)

# ==================================================
# 3. VALIDACIÓN CRUZADA TEMPORAL
# ==================================================

cv = TimeSeriesSplit(n_splits=3, gap=24)

fallas = y_dev.eq(1)

episodios = (fallas & ~fallas.shift(fill_value=False)).cumsum().where(fallas, 0)

probabilidades = np.full(len(X_dev), np.nan)

ventanas = []

for numero, (train_idx, val_idx) in enumerate(cv.split(X_dev), 1):

    ids_train = set(episodios.iloc[train_idx]) - {0}
    ids_val = set(episodios.iloc[val_idx]) - {0}

    compartidos = ids_train.intersection(ids_val)

    if compartidos:
        conservar = ~episodios.iloc[train_idx].isin(compartidos).to_numpy()

        train_idx = train_idx[conservar]

    x_train = X_dev.iloc[train_idx].copy()
    x_val = X_dev.iloc[val_idx].copy()

    y_train = y_dev.iloc[train_idx]
    y_val = y_dev.iloc[val_idx]

    # Negativos como valores no disponibles
    x_train = x_train.mask(x_train < 0)
    x_val = x_val.mask(x_val < 0)

    # Ajustar imputador únicamente con entrenamiento
    imputador = SimpleImputer(strategy="median", keep_empty_features=True)

    train_p = imputador.fit_transform(x_train)
    val_p = imputador.transform(x_val)

    modelo = RandomForestClassifier(
        n_estimators=200, min_samples_leaf=2, random_state=42, n_jobs=-1
    )

    modelo.fit(train_p, y_train)

    indice = list(modelo.classes_).index(1)

    probabilidades[val_idx] = modelo.predict_proba(val_p)[:, indice]

    ventanas.append((numero, val_idx))

    print(
        f"Ventana {numero}: " f"{len(val_idx)} registros, " f"{int(y_val.sum())} fallas"
    )

# ==================================================
# 4. COMPARAR UMBRALES
# ==================================================

mascara = np.isfinite(probabilidades)

y_real = y_dev.to_numpy()[mascara]
probs = probabilidades[mascara]

umbrales = np.round(np.arange(0.20, 0.501, 0.025), 3)

resultados = []

for umbral in umbrales:

    pred = (probs >= umbral).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_real, pred, labels=[0, 1]).ravel()

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0

    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0

    resultados.append(
        {
            "umbral": umbral,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "detectadas": int(tp),
            "omitidas": int(fn),
            "falsas_alarmas": int(fp),
        }
    )

tabla = pd.DataFrame(resultados)

tabla = tabla.sort_values(
    ["f1", "recall", "falsas_alarmas"], ascending=[False, False, True]
)

print("\n" + "=" * 60)
print("COMPARACIÓN DE UMBRALES")
print("=" * 60)

print(tabla.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

# ==================================================
# 5. MEJOR UMBRAL
# ==================================================

mejor = tabla.iloc[0]
umbral_finalista = float(mejor["umbral"])

print("\n" + "=" * 60)
print("MEJOR UMBRAL PROVISIONAL")
print("=" * 60)

print(f"Umbral: {umbral_finalista:.3f}")
print(f"Precision: {mejor['precision']:.3f}")
print(f"Recall: {mejor['recall']:.3f}")
print(f"F1: {mejor['f1']:.3f}")
print(f"Detectadas: {int(mejor['detectadas'])}")
print(f"Omitidas: {int(mejor['omitidas'])}")
print(f"Falsas alarmas: {int(mejor['falsas_alarmas'])}")

print("\nRESULTADOS POR VENTANA")

for numero, val_idx in ventanas:

    reales = y_dev.iloc[val_idx].to_numpy()
    pred = (probabilidades[val_idx] >= umbral_finalista).astype(int)

    tn, fp, fn, tp = confusion_matrix(reales, pred, labels=[0, 1]).ravel()

    print(f"Ventana {numero}: " f"TP={tp}, FP={fp}, FN={fn}, TN={tn}")

# ==================================================
# 6. GUARDAR RESULTADOS
# ==================================================

ruta = REPORTS / "sofi_umbrales_combinado.csv"

tabla.to_csv(ruta, index=False, encoding="utf-8-sig")

print("\nResultados guardados:", ruta)
print("Prueba final intacta.")
print("Modelo definitivo todavía no exportado.")
