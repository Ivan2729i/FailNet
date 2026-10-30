from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import confusion_matrix

# ==================================================
# 1. CARGAR DATOS
# ==================================================

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "raw" / "sofi"

archivo = next(DATA.rglob("SOFI CoreSwitch-I.csv"))

df = pd.read_csv(archivo)
df.columns = df.columns.str.strip()
df = df.sort_values("timestamp").reset_index(drop=True)

y = df["class"].str.strip().map({"NE": 0, "F": 1}).astype(int)

X = df.drop(columns=["class", "timestamp", "range"])

# Reservamos el último 20%
corte = int(len(df) * 0.80)

X_dev = X.iloc[:corte]
y_dev = y.iloc[:corte]

# Identificación de episodios consecutivos
es_falla = y_dev.eq(1)

episodios = (es_falla & ~es_falla.shift(fill_value=False)).cumsum().where(es_falla, 0)

cv = TimeSeriesSplit(n_splits=3, gap=24)

# ==================================================
# 2. MODELO CANDIDATO
# ==================================================

# RF sin pesos, umbral 0.30
UMBRAL = 0.30

print("=" * 60)
print("DIAGNÓSTICO DEL MODELO SOFI")
print("=" * 60)

for numero, (train_idx, val_idx) in enumerate(cv.split(X_dev), 1):

    # Analizar las ventanas 2 y 3
    if numero == 1:
        continue

    # Evitar compartir episodios de falla
    ids_train = set(episodios.iloc[train_idx]) - {0}

    ids_val = set(episodios.iloc[val_idx]) - {0}

    compartidos = ids_train.intersection(ids_val)

    if compartidos:
        conservar = ~episodios.iloc[train_idx].isin(compartidos).to_numpy()

        train_idx = train_idx[conservar]

    X_train = X_dev.iloc[train_idx]
    y_train = y_dev.iloc[train_idx]

    X_val = X_dev.iloc[val_idx]
    y_val = y_dev.iloc[val_idx]

    modelo = RandomForestClassifier(
        n_estimators=200, min_samples_leaf=2, random_state=42, n_jobs=-1
    )

    modelo.fit(X_train, y_train)

    probs = modelo.predict_proba(X_val)[:, 1]
    pred = (probs >= UMBRAL).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_val, pred, labels=[0, 1]).ravel()

    print(f"\n{'=' * 60}")
    print(f"VENTANA {numero}")
    print("=" * 60)

    print(f"Fallas detectadas: {tp}")
    print(f"Fallas omitidas: {fn}")
    print(f"Falsas alarmas: {fp}")
    print(f"Normales correctos: {tn}")

    # ==================================================
    # 3. IMPORTANCIA DE CARACTERÍSTICAS
    # ==================================================

    importancia = pd.Series(modelo.feature_importances_, index=X.columns).sort_values(
        ascending=False
    )

    top = importancia.head(8)

    print("\n8 VARIABLES MÁS IMPORTANTES:")
    print(top.to_string())

    # ==================================================
    # 4. COMPARACIÓN ENTRE REGISTROS
    # ==================================================

    reales = y_val.to_numpy()

    falsas = X_val.iloc[np.where((reales == 0) & (pred == 1))[0]]

    normales_train = X_train.loc[y_train == 0]
    normales_val = X_val.loc[y_val == 0]

    columnas = top.index.tolist()

    comparacion = pd.DataFrame(
        {
            "Entrenamiento normal": normales_train[columnas].median(),
            "Validación normal": normales_val[columnas].median(),
            "Falsas alarmas": falsas[columnas].median() if len(falsas) else np.nan,
        }
    )

    print("\nMEDIANAS DE VARIABLES IMPORTANTES:")
    print(comparacion.to_string(float_format=lambda valor: f"{valor:.3g}"))

    # ==================================================
    # 5. EJEMPLOS DE FALSAS ALARMAS
    # ==================================================

    mascara_fp = (reales == 0) & (pred == 1)

    posiciones = np.flatnonzero(mascara_fp)[:5]

    if len(posiciones):
        muestra = df.iloc[val_idx[posiciones]][["timestamp"] + columnas[:3]].copy()

        muestra["timestamp"] = pd.to_datetime(muestra["timestamp"], unit="s", utc=True)

        print("\nEJEMPLOS DE FALSAS ALARMAS:")
        print(muestra.to_string(index=False))
    else:
        print("\nNo hubo falsas alarmas.")

print("\nDiagnóstico finalizado.")
print("No se utilizaron los datos de prueba final.")
