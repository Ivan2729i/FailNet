from pathlib import Path

import pandas as pd

from sklearn.dummy import DummyClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)

# ==========================================================
# 1. CONFIGURACIÓN Y CARGA DEL DATASET
# ==========================================================

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "raw" / "sofi"

archivo = next(DATA.rglob("SOFI CoreSwitch-I.csv"), None)

if archivo is None:
    raise FileNotFoundError("No se encontró SOFI CoreSwitch-I.csv")

df = pd.read_csv(archivo)
df.columns = df.columns.str.strip()

# Ordenar cronológicamente
df = df.sort_values("timestamp").reset_index(drop=True)

print("=" * 60)
print("ENTRENAMIENTO Y EVALUACIÓN - DATASET SOFI")
print("=" * 60)

print(f"\nDataset: {archivo.name}")
print(f"Registros: {len(df)}")

# ==========================================================
# 2. PREPARACIÓN DE CARACTERÍSTICAS Y ETIQUETAS
# ==========================================================

# 0 = Normal (NE)
# 1 = Falla (F)

y = df["class"].str.strip().map({"NE": 0, "F": 1})

if y.isna().any():
    raise ValueError("Existen etiquetas desconocidas")

y = y.astype(int)

# Excluir etiqueta, timestamp y range
X = df.drop(columns=["class", "timestamp", "range"])

if X.isna().any().any():
    raise ValueError("Existen valores faltantes en las características")

print(f"Características utilizadas: {X.shape[1]}")

# ==========================================================
# 3. DIVISIÓN CRONOLÓGICA
# ==========================================================

n = len(df)

corte1 = int(n * 0.60)
corte2 = int(n * 0.80)


def ajustar_corte(corte):
    """Evita dividir un bloque consecutivo de fallas."""
    while corte < n and y.iloc[corte - 1] == 1 and y.iloc[corte] == 1:
        corte += 1

    return corte


corte1 = ajustar_corte(corte1)
corte2 = ajustar_corte(corte2)

if not 0 < corte1 < corte2 < n:
    raise ValueError("No se pudo realizar la división cronológica")

# Entrenamiento
X_train = X.iloc[:corte1]
y_train = y.iloc[:corte1]

# Validación
X_val = X.iloc[corte1:corte2]
y_val = y.iloc[corte1:corte2]

# Prueba final (reservada)
X_test = X.iloc[corte2:]
y_test = y.iloc[corte2:]

print("\n" + "=" * 60)
print("DISTRIBUCIÓN DE DATOS")
print("=" * 60)

for nombre, etiquetas in [
    ("Entrenamiento", y_train),
    ("Validación", y_val),
    ("Prueba reservada", y_test),
]:
    print(f"\n{nombre}: {len(etiquetas)} registros")
    print(etiquetas.value_counts().sort_index())

# ==========================================================
# 4. DEFINICIÓN DE MODELOS
# ==========================================================

modelos = {
    "Dummy (referencia)": DummyClassifier(strategy="most_frequent"),
    "Decision Tree": DecisionTreeClassifier(
        class_weight="balanced", max_depth=10, min_samples_leaf=5, random_state=42
    ),
    "Random Forest": RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced_subsample",
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    ),
}

# ==========================================================
# 5. ENTRENAMIENTO Y EVALUACIÓN INICIAL
# ==========================================================

for nombre, modelo in modelos.items():

    print("\n" + "=" * 60)
    print(f"MODELO: {nombre}")
    print("=" * 60)

    # Entrenar únicamente con los datos de entrenamiento
    modelo.fit(X_train, y_train)

    # Predecir usando datos de validación
    predicciones = modelo.predict(X_val)

    print("\nMATRIZ DE CONFUSIÓN:")
    print(confusion_matrix(y_val, predicciones, labels=[0, 1]))

    print("\nMÉTRICAS DE VALIDACIÓN:")
    print(
        classification_report(
            y_val,
            predicciones,
            labels=[0, 1],
            target_names=["Normal", "Falla"],
            zero_division=0,
        )
    )

    # ======================================================
    # 6. EVALUACIÓN DE UMBRALES - RANDOM FOREST
    # ======================================================

    if nombre == "Random Forest":

        print("\n" + "=" * 60)
        print("COMPARACIÓN DE UMBRALES - RANDOM FOREST")
        print("=" * 60)

        # Probabilidad estimada de la clase Falla (1)
        indice_falla = list(modelo.classes_).index(1)

        probabilidades = modelo.predict_proba(X_val)[:, indice_falla]

        umbrales = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]

        resultados = []

        for umbral in umbrales:

            # Clasificación según el umbral actual
            pred = (probabilidades >= umbral).astype(int)

            precision = precision_score(y_val, pred, zero_division=0)

            recall = recall_score(y_val, pred, zero_division=0)

            f1 = f1_score(y_val, pred, zero_division=0)

            matriz = confusion_matrix(y_val, pred, labels=[0, 1])

            tn, fp, fn, tp = matriz.ravel()

            resultados.append(
                {
                    "Umbral": umbral,
                    "Precision": precision,
                    "Recall": recall,
                    "F1": f1,
                    "Detectadas": int(tp),
                    "Omitidas": int(fn),
                    "Falsas alarmas": int(fp),
                }
            )

        # Mostrar tabla comparativa
        tabla = pd.DataFrame(resultados)

        print("\nRESULTADOS POR UMBRAL:\n")
        print(tabla.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

        # Identificar mejor umbral según F1
        mejor = tabla.loc[tabla["F1"].idxmax()]

        print("\n" + "=" * 60)
        print("MEJOR UMBRAL SEGÚN F1 DE VALIDACIÓN")
        print("=" * 60)

        print(f"Umbral: {mejor['Umbral']:.2f}")
        print(f"Precision: {mejor['Precision']:.3f}")
        print(f"Recall: {mejor['Recall']:.3f}")
        print(f"F1-score: {mejor['F1']:.3f}")

        print(f"\nFallas detectadas: {int(mejor['Detectadas'])}")
        print(f"Fallas omitidas: {int(mejor['Omitidas'])}")
        print(f"Falsas alarmas: {int(mejor['Falsas alarmas'])}")

        print(
            "\nNOTA: Este umbral es provisional. "
            "Todavía no se ha evaluado en la prueba final."
        )

# ==========================================================
# 7. FINALIZACIÓN
# ==========================================================

print("\n" + "=" * 60)
print("VALIDACIÓN FINALIZADA")
print("=" * 60)

print("Se entrenaron y compararon los tres algoritmos.")
print("Se evaluaron diferentes umbrales de Random Forest.")
print("El conjunto de prueba final permanece reservado.")
print("No se ha seleccionado ni exportado un modelo definitivo.")
