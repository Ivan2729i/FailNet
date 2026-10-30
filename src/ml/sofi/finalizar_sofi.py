from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    confusion_matrix,
    classification_report,
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
)

# ==================================================
# 1. CONFIGURACIÓN FINAL
# ==================================================

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "raw" / "sofi"
MODELS = BASE / "models"
REPORTS = BASE / "reports"

MODELS.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

UMBRAL = 0.40
RANDOM_STATE = 42


def cargar_switch(nombre):
    archivo = next(DATA.rglob(nombre), None)

    if archivo is None:
        raise FileNotFoundError(nombre)

    df = pd.read_csv(archivo)
    df.columns = df.columns.str.strip()

    df = df.rename(columns={"SNMP_availability": "SNMP_Availability"})

    return df.sort_values("timestamp").reset_index(drop=True)


# ==================================================
# 2. SINCRONIZAR LOS SWITCHES
# ==================================================

sw1 = cargar_switch("SOFI CoreSwitch-I.csv")
sw2 = cargar_switch("SOFI CoreSwitch-II.csv")

df = sw1.merge(
    sw2, on="timestamp", how="inner", suffixes=("_I", "_II"), validate="one_to_one"
)

df = df.sort_values("timestamp").reset_index(drop=True)

if not (df["class_I"] == df["class_II"]).all():
    raise ValueError("Las clases de los switches no coinciden")

y = df["class_I"].str.strip().map({"NE": 0, "F": 1})

if y.isna().any():
    raise ValueError("Existen etiquetas desconocidas")

y = y.astype(int)

X = df.drop(columns=["timestamp", "class_I", "class_II", "range_I", "range_II"])

X = X.apply(pd.to_numeric, errors="raise")

if X.shape[1] != 64:
    raise ValueError(f"Se esperaban 64 características, hay {X.shape[1]}")

columnas = X.columns.tolist()

# ==================================================
# 3. DIVISIÓN FINAL
# ==================================================

corte = int(len(df) * 0.80)

X_train = X.iloc[:corte].copy()
X_test = X.iloc[corte:].copy()

y_train = y.iloc[:corte]
y_test = y.iloc[corte:]

timestamps_test = df["timestamp"].iloc[corte:]

print("=" * 65)
print("EVALUACIÓN FINAL - SOFI")
print("=" * 65)

print("Registros totales:", len(df))
print("Características:", X.shape[1])

print("\nENTRENAMIENTO")
print("Registros:", len(X_train))
print("Normales:", int((y_train == 0).sum()))
print("Fallas:", int((y_train == 1).sum()))

print("\nPRUEBA FINAL")
print("Registros:", len(X_test))
print("Normales:", int((y_test == 0).sum()))
print("Fallas:", int((y_test == 1).sum()))

if y.iloc[corte - 1] == 1 and y.iloc[corte] == 1:
    print("\nADVERTENCIA: el corte temporal divide " "un bloque consecutivo de falla.")

# ==================================================
# 4. PREPROCESAMIENTO
# ==================================================

# Aplicar la misma regla elegida en validación
X_train = X_train.mask(X_train < 0)
X_test = X_test.mask(X_test < 0)

# Ajustar SOLO con entrenamiento
imputador = SimpleImputer(strategy="median", keep_empty_features=True)

X_train_p = imputador.fit_transform(X_train)
X_test_p = imputador.transform(X_test)

# ==================================================
# 5. ENTRENAMIENTO DEFINITIVO
# ==================================================

modelo = RandomForestClassifier(
    n_estimators=200, min_samples_leaf=2, random_state=RANDOM_STATE, n_jobs=-1
)

modelo.fit(X_train_p, y_train)

# ==================================================
# 6. EVALUACIÓN FINAL
# ==================================================

indice_falla = list(modelo.classes_).index(1)

probabilidades = modelo.predict_proba(X_test_p)[:, indice_falla]

predicciones = (probabilidades >= UMBRAL).astype(int)

reales = y_test.to_numpy()

tn, fp, fn, tp = confusion_matrix(reales, predicciones, labels=[0, 1]).ravel()

precision = precision_score(reales, predicciones, zero_division=0)

recall = recall_score(reales, predicciones, zero_division=0)

f1 = f1_score(reales, predicciones, zero_division=0)

ap = average_precision_score(reales, probabilidades)

print("\n" + "=" * 65)
print("RESULTADOS FINALES")
print("=" * 65)

print("\nMATRIZ DE CONFUSIÓN")
print(f"TN={tn}  FP={fp}")
print(f"FN={fn}  TP={tp}")

print(f"\nPrecision falla: {precision:.4f}")
print(f"Recall falla: {recall:.4f}")
print(f"F1-score falla: {f1:.4f}")
print(f"Average Precision: {ap:.4f}")

print("\nREPORTE DE CLASIFICACIÓN")
print(
    classification_report(
        reales,
        predicciones,
        labels=[0, 1],
        target_names=["Normal", "Falla"],
        zero_division=0,
    )
)

# ==================================================
# 7. EVALUACIÓN POR BLOQUES DE FALLA
# ==================================================

# Cada bloque de filas consecutivas con F=1
# se considera un episodio observado.

mask_falla = reales == 1

inicios = np.flatnonzero(mask_falla & ~np.r_[False, mask_falla[:-1]])

finales = np.flatnonzero(mask_falla & ~np.r_[mask_falla[1:], False]) + 1

episodios_totales = len(inicios)

episodios_detectados = sum(
    np.any(predicciones[inicio:fin] == 1) for inicio, fin in zip(inicios, finales)
)

recall_episodios = episodios_detectados / episodios_totales if episodios_totales else 0

# Bloques consecutivos de falsas alarmas
mask_fp = (reales == 0) & (predicciones == 1)

bloques_fp = int(np.sum(mask_fp & ~np.r_[False, mask_fp[:-1]]))

print("\n" + "=" * 65)
print("EVALUACIÓN POR EPISODIOS")
print("=" * 65)

print("Episodios de falla:", episodios_totales)
print("Episodios detectados:", episodios_detectados)
print("Recall de episodios:", f"{recall_episodios:.4f}")
print("Bloques de falsas alarmas:", bloques_fp)

# ==================================================
# 8. GUARDAR EL MODELO COMPLETO
# ==================================================

artefacto = {
    "modelo": modelo,
    "imputador": imputador,
    "columnas": columnas,
    "umbral": UMBRAL,
    "etiquetas": {0: "Normal", 1: "Falla"},
    "preprocesamiento": "reemplazar_negativos_por_nan",
    "fuente": "SOFI CoreSwitch-I + CoreSwitch-II",
}

ruta_modelo = MODELS / "sofi_combinado.joblib"

joblib.dump(artefacto, ruta_modelo)

# ==================================================
# 9. GUARDAR PREDICCIONES DE PRUEBA
# ==================================================

predicciones_df = pd.DataFrame(
    {
        "timestamp": pd.to_datetime(timestamps_test.to_numpy(), unit="s", utc=True),
        "clase_real": reales,
        "probabilidad_falla": probabilidades,
        "clase_predicha": predicciones,
        "acierto": reales == predicciones,
    }
)

ruta_predicciones = REPORTS / "sofi_predicciones_prueba_final.csv"

predicciones_df.to_csv(ruta_predicciones, index=False, encoding="utf-8-sig")

print("\n" + "=" * 65)
print("ARCHIVOS GENERADOS")
print("=" * 65)

print("Modelo:", ruta_modelo)
print("Predicciones:", ruta_predicciones)
print("\nEvaluación final completada.")
print("No reajustar usando estos datos de prueba.")
