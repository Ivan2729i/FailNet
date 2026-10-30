from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import confusion_matrix

# ==============================================
# 1. CARGAR DATOS
# ==============================================

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "raw" / "sofi"
REPORTS = BASE / "reports"

REPORTS.mkdir(parents=True, exist_ok=True)

archivo = next(DATA.rglob("SOFI CoreSwitch-I.csv"), None)

if archivo is None:
    raise FileNotFoundError("No se encontró SOFI")

df = pd.read_csv(archivo)

df.columns = df.columns.str.strip()
df = df.sort_values("timestamp").reset_index(drop=True)

y = df["class"].str.strip().map({"NE": 0, "F": 1})

if y.isna().any():
    raise ValueError("Etiquetas desconocidas")

y = y.astype(int)

X = df.drop(columns=["class", "timestamp", "range"])

# Último 20% reservado
corte = int(len(df) * 0.80)

X_dev = X.iloc[:corte]
y_dev = y.iloc[:corte]

# ==============================================
# 2. VALIDACIÓN TEMPORAL
# ==============================================

cv = TimeSeriesSplit(n_splits=3, gap=24)

fallas = y_dev.eq(1)

episodios = (fallas & ~fallas.shift(fill_value=False)).cumsum().where(fallas, 0)

resultados_ventanas = []

print("=" * 60)
print("OPTIMIZACIÓN DE UMBRALES - SOFI")
print("=" * 60)

for numero, (train_idx, val_idx) in enumerate(cv.split(X_dev), 1):

    # Evitar compartir episodios de falla
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

    # ==========================================
    # 3. IMPUTACIÓN
    # ==========================================

    # Tratar negativos como valores no disponibles
    x_train = x_train.mask(x_train < 0)
    x_val = x_val.mask(x_val < 0)

    imputador = SimpleImputer(strategy="median", keep_empty_features=True)

    train_p = imputador.fit_transform(x_train)
    val_p = imputador.transform(x_val)

    # ==========================================
    # 4. ENTRENAMIENTO
    # ==========================================

    modelo = RandomForestClassifier(
        n_estimators=200, min_samples_leaf=2, random_state=42, n_jobs=-1
    )

    modelo.fit(train_p, y_train)

    indice = list(modelo.classes_).index(1)

    probabilidades = modelo.predict_proba(val_p)[:, indice]

    resultados_ventanas.append(
        {
            "ventana": numero,
            "y_real": y_val.to_numpy(),
            "probabilidades": probabilidades,
        }
    )

    print(
        f"Ventana {numero}: " f"{len(y_val)} registros, " f"{int(y_val.sum())} fallas"
    )

# ==============================================
# 5. EVALUAR UMBRALES
# ==============================================

umbrales = np.round(np.arange(0.05, 0.501, 0.025), 3)

resultados = []

for umbral in umbrales:

    tp_total = 0
    fp_total = 0
    fn_total = 0
    tn_total = 0

    for ventana in resultados_ventanas:

        y_real = ventana["y_real"]

        pred = (ventana["probabilidades"] >= umbral).astype(int)

        tn, fp, fn, tp = confusion_matrix(y_real, pred, labels=[0, 1]).ravel()

        tp_total += tp
        fp_total += fp
        fn_total += fn
        tn_total += tn

    precision = tp_total / (tp_total + fp_total) if tp_total + fp_total > 0 else 0

    recall = tp_total / (tp_total + fn_total) if tp_total + fn_total > 0 else 0

    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0

    resultados.append(
        {
            "umbral": umbral,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "detectadas": int(tp_total),
            "omitidas": int(fn_total),
            "falsas_alarmas": int(fp_total),
        }
    )

# ==============================================
# 6. MOSTRAR COMPARACIÓN
# ==============================================

tabla = pd.DataFrame(resultados)

tabla = tabla.sort_values(["f1", "recall"], ascending=[False, False])

print("\n" + "=" * 60)
print("COMPARACIÓN DE UMBRALES")
print("=" * 60)

print(tabla.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

mejor = tabla.iloc[0]

print("\n" + "=" * 60)
print("MEJOR UMBRAL PROVISIONAL")
print("=" * 60)

print(f"Umbral: {mejor['umbral']:.3f}")
print(f"Precision: {mejor['precision']:.3f}")
print(f"Recall: {mejor['recall']:.3f}")
print(f"F1: {mejor['f1']:.3f}")

print("Detectadas:", int(mejor["detectadas"]))
print("Omitidas:", int(mejor["omitidas"]))
print("Falsas alarmas:", int(mejor["falsas_alarmas"]))

# ==============================================
# 7. RESULTADOS POR VENTANA
# ==============================================

print("\nRESULTADOS DEL MEJOR UMBRAL POR VENTANA")

for ventana in resultados_ventanas:

    pred = (ventana["probabilidades"] >= mejor["umbral"]).astype(int)

    tn, fp, fn, tp = confusion_matrix(ventana["y_real"], pred, labels=[0, 1]).ravel()

    print(f"Ventana {ventana['ventana']}: " f"TP={tp}, FP={fp}, FN={fn}, TN={tn}")

# Guardar reporte
ruta = REPORTS / "sofi_optimizacion_umbrales.csv"

tabla.to_csv(ruta, index=False, encoding="utf-8-sig")

print("\nResultados guardados:", ruta)
print("Prueba final intacta.")
