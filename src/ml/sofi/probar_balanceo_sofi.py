from pathlib import Path

import numpy as np
import pandas as pd

from imblearn.over_sampling import RandomOverSampler, SMOTE

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix

# ==================================================
# 1. CONFIGURACIÓN
# ==================================================

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "raw" / "sofi"
REPORTS = BASE / "reports"

REPORTS.mkdir(parents=True, exist_ok=True)

CONFIGURACIONES = [
    ("Original", "original", None),
    ("ROS_10", "ros", 0.10),
    ("ROS_25", "ros", 0.25),
    ("ROS_50", "ros", 0.50),
    ("SMOTE_10", "smote", 0.10),
    ("SMOTE_25", "smote", 0.25),
    ("SMOTE_50", "smote", 0.50),
]

UMBRALES = np.round(np.arange(0.10, 0.601, 0.025), 3)

# ==================================================
# 2. CARGAR Y COMBINAR SWITCHES
# ==================================================


def cargar_switch(nombre):

    archivo = next(DATA.rglob(nombre), None)

    if archivo is None:
        raise FileNotFoundError(nombre)

    datos = pd.read_csv(archivo)
    datos.columns = datos.columns.str.strip()

    datos = datos.rename(columns={"SNMP_availability": "SNMP_Availability"})

    return datos.sort_values("timestamp").reset_index(drop=True)


sw1 = cargar_switch("SOFI CoreSwitch-I.csv")
sw2 = cargar_switch("SOFI CoreSwitch-II.csv")

df = sw1.merge(
    sw2, on="timestamp", how="inner", suffixes=("_I", "_II"), validate="one_to_one"
)

df = df.sort_values("timestamp").reset_index(drop=True)

if not (df["class_I"] == df["class_II"]).all():
    raise ValueError("Las etiquetas no coinciden")

y = df["class_I"].str.strip().map({"NE": 0, "F": 1})

if y.isna().any():
    raise ValueError("Hay clases desconocidas")

y = y.astype(int)

X = df.drop(columns=["timestamp", "class_I", "class_II", "range_I", "range_II"])

X = X.apply(pd.to_numeric, errors="raise")

# ==================================================
# 3. RESERVAR PRUEBA FINAL
# ==================================================

corte = int(len(df) * 0.80)

X_dev = X.iloc[:corte]
y_dev = y.iloc[:corte]

print("=" * 65)
print("EXPERIMENTO DE BALANCEO - SOFI")
print("=" * 65)

print("Registros sincronizados:", len(df))
print("Características:", X.shape[1])
print("Registros de desarrollo:", len(X_dev))
print("Prueba final reservada:", len(df) - corte)

# ==================================================
# 4. CREAR VENTANAS TEMPORALES
# ==================================================

cv = TimeSeriesSplit(n_splits=3, gap=24)

fallas = y_dev.eq(1)

episodios = (fallas & ~fallas.shift(fill_value=False)).cumsum().where(fallas, 0)

splits = []

for numero, (train_idx, val_idx) in enumerate(cv.split(X_dev), 1):

    ids_train = set(episodios.iloc[train_idx]) - {0}

    ids_val = set(episodios.iloc[val_idx]) - {0}

    compartidos = ids_train.intersection(ids_val)

    if compartidos:
        conservar = ~episodios.iloc[train_idx].isin(compartidos).to_numpy()

        train_idx = train_idx[conservar]

    splits.append((train_idx, val_idx))

    print(
        f"Ventana {numero}: "
        f"train={len(train_idx)}, "
        f"validación={len(val_idx)}, "
        f"fallas_validación={int(y_dev.iloc[val_idx].sum())}"
    )

# ==================================================
# 5. FUNCIÓN PARA CALCULAR MÉTRICAS
# ==================================================


def calcular_metricas(reales, pred):

    tn, fp, fn, tp = confusion_matrix(reales, pred, labels=[0, 1]).ravel()

    precision = tp / (tp + fp) if tp + fp > 0 else 0

    recall = tp / (tp + fn) if tp + fn > 0 else 0

    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0

    return {
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


# ==================================================
# 6. ENTRENAMIENTO DE CONFIGURACIONES
# ==================================================

resultados = []
predicciones_cv = {}

for nombre, metodo, proporcion in CONFIGURACIONES:

    print("\n" + "=" * 65)
    print("CONFIGURACIÓN:", nombre)
    print("=" * 65)

    probabilidades = np.full(len(X_dev), np.nan)

    for numero, (train_idx, val_idx) in enumerate(splits, 1):

        x_train = X_dev.iloc[train_idx].copy()
        x_val = X_dev.iloc[val_idx].copy()

        y_train = y_dev.iloc[train_idx].copy()

        # ------------------------------------------
        # 6.1 TRATAMIENTO DE VALORES NEGATIVOS
        # ------------------------------------------

        x_train = x_train.mask(x_train < 0)
        x_val = x_val.mask(x_val < 0)

        imputador = SimpleImputer(strategy="median", keep_empty_features=True)

        train_p = imputador.fit_transform(x_train)
        val_p = imputador.transform(x_val)

        y_train_p = y_train.to_numpy()

        # ------------------------------------------
        # 6.2 BALANCEO: SOLO ENTRENAMIENTO
        # ------------------------------------------

        if metodo == "ros":

            sampler = RandomOverSampler(sampling_strategy=proporcion, random_state=42)

            train_p, y_train_p = sampler.fit_resample(train_p, y_train_p)

        elif metodo == "smote":

            # SMOTE utiliza vecinos cercanos.
            # Escalar evita que variables de magnitud
            # alta dominen las distancias.
            escalador = StandardScaler()

            train_p = escalador.fit_transform(train_p)
            val_p = escalador.transform(val_p)

            n_fallas = int((y_train_p == 1).sum())

            if n_fallas < 2:
                raise ValueError("No hay suficientes fallas para SMOTE")

            sampler = SMOTE(
                sampling_strategy=proporcion,
                random_state=42,
                k_neighbors=min(5, n_fallas - 1),
            )

            train_p, y_train_p = sampler.fit_resample(train_p, y_train_p)

        # ------------------------------------------
        # 6.3 ENTRENAMIENTO
        # ------------------------------------------

        modelo = RandomForestClassifier(
            n_estimators=200, min_samples_leaf=2, random_state=42, n_jobs=-1
        )

        modelo.fit(train_p, y_train_p)

        indice_falla = list(modelo.classes_).index(1)

        probs = modelo.predict_proba(val_p)[:, indice_falla]

        probabilidades[val_idx] = probs

        normales = int((y_train_p == 0).sum())
        fallas_train = int((y_train_p == 1).sum())

        print(
            f"Ventana {numero}: "
            f"entrenamiento final "
            f"NE={normales}, F={fallas_train}"
        )

    predicciones_cv[nombre] = probabilidades

    # ----------------------------------------------
    # 6.4 PROBAR UMBRALES
    # ----------------------------------------------

    mascara = np.isfinite(probabilidades)

    reales = y_dev.to_numpy()[mascara]
    probs = probabilidades[mascara]

    for umbral in UMBRALES:

        pred = (probs >= umbral).astype(int)

        metricas = calcular_metricas(reales, pred)

        resultados.append(
            {
                "configuracion": nombre,
                "metodo": metodo,
                "proporcion": proporcion,
                "umbral": float(umbral),
                **metricas,
            }
        )

# ==================================================
# 7. RANKING DE RESULTADOS
# ==================================================

tabla = pd.DataFrame(resultados)

tabla = tabla.sort_values(
    ["f1", "recall", "fp"], ascending=[False, False, True]
).reset_index(drop=True)

# Mejor umbral de cada configuración
mejores = tabla.drop_duplicates(subset=["configuracion"], keep="first").reset_index(
    drop=True
)

columnas_resumen = [
    "configuracion",
    "umbral",
    "precision",
    "recall",
    "f1",
    "tp",
    "fp",
    "fn",
]

print("\n" + "=" * 65)
print("MEJOR RESULTADO DE CADA CONFIGURACIÓN")
print("=" * 65)

print(
    mejores[columnas_resumen].to_string(index=False, float_format=lambda n: f"{n:.3f}")
)

print("\n" + "=" * 65)
print("TOP 15 COMBINACIONES GLOBALES")
print("=" * 65)

print(
    tabla[columnas_resumen]
    .head(15)
    .to_string(index=False, float_format=lambda n: f"{n:.3f}")
)

# ==================================================
# 8. COMPARACIÓN POR VENTANA
# ==================================================

print("\n" + "=" * 65)
print("ESTABILIDAD POR VENTANA")
print("=" * 65)

for _, candidato in mejores.iterrows():

    nombre = candidato["configuracion"]
    umbral = float(candidato["umbral"])

    probs = predicciones_cv[nombre]

    print(f"\n{nombre} | Umbral={umbral:.3f}")

    for numero, (_, val_idx) in enumerate(splits, 1):

        reales = y_dev.iloc[val_idx].to_numpy()

        pred = (probs[val_idx] >= umbral).astype(int)

        m = calcular_metricas(reales, pred)

        print(
            f"  Ventana {numero}: "
            f"TP={m['tp']} "
            f"FN={m['fn']} "
            f"FP={m['fp']} "
            f"F1={m['f1']:.3f}"
        )

# ==================================================
# 9. RESULTADO PROVISIONAL
# ==================================================

mejor = mejores.iloc[0]

print("\n" + "=" * 65)
print("MEJOR CONFIGURACIÓN PROVISIONAL")
print("=" * 65)

print("Configuración:", mejor["configuracion"])
print(f"Umbral: {mejor['umbral']:.3f}")

print(f"Precision: {mejor['precision']:.3f}")
print(f"Recall: {mejor['recall']:.3f}")
print(f"F1-score: {mejor['f1']:.3f}")

print("Fallas detectadas:", int(mejor["tp"]))
print("Fallas omitidas:", int(mejor["fn"]))
print("Falsas alarmas:", int(mejor["fp"]))

# ==================================================
# 10. GUARDAR REPORTES
# ==================================================

ruta_todos = REPORTS / "sofi_balanceo_todas_pruebas_sintetico.csv"

ruta_mejores = REPORTS / "sofi_balanceo_mejores_sintetico.csv"

tabla.to_csv(ruta_todos, index=False, encoding="utf-8-sig")

mejores.to_csv(ruta_mejores, index=False, encoding="utf-8-sig")

print("\nArchivos generados:")
print(ruta_todos)
print(ruta_mejores)

print("\nLa prueba final permanece reservada.")
print("No se exportó ningún modelo definitivo.")
