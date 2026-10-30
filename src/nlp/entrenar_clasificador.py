from pathlib import Path

import joblib
import pandas as pd

from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

# ==================================================
# 1. CONFIGURACIÓN
# ==================================================

BASE = Path(__file__).resolve().parents[2]

DATA = BASE / "data" / "raw" / "nlp"
MODELS = BASE / "models"
REPORTS = BASE / "reports"

MODELS.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

archivo = DATA / "reportes_red.csv"

if not archivo.exists():
    raise FileNotFoundError(f"No se encontró el dataset: {archivo}")

# ==================================================
# 2. CARGAR DATASET
# ==================================================

df = pd.read_csv(archivo, encoding="utf-8-sig")

columnas_requeridas = {"texto", "categoria"}

if not columnas_requeridas.issubset(df.columns):
    raise ValueError("El CSV debe contener texto y categoria")

df = df.dropna(subset=["texto", "categoria"]).copy()

df["texto"] = df["texto"].astype(str).str.strip()
df["categoria"] = df["categoria"].astype(str).str.strip()

df = df[(df["texto"] != "") & (df["categoria"] != "")].copy()

# Evitar textos duplicados
df = df.drop_duplicates(subset=["texto"]).reset_index(drop=True)

X = df["texto"]
y = df["categoria"]

categorias = sorted(y.unique())

print("=" * 65)
print("ENTRENAMIENTO DEL CLASIFICADOR PNL")
print("=" * 65)

print("Reportes:", len(df))
print("Categorías:", len(categorias))

print("\nDISTRIBUCIÓN")
print(y.value_counts().to_string())

if y.value_counts().min() < 5:
    raise ValueError(
        "Se requieren al menos 5 ejemplos por categoría "
        "para esta validación cruzada."
    )

# ==================================================
# 3. MODELOS A COMPARAR
# ==================================================


def crear_pipeline(clasificador):

    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                ),
            ),
            ("clasificador", clasificador),
        ]
    )


modelos = {
    "Dummy": crear_pipeline(DummyClassifier(strategy="most_frequent")),
    "LogisticRegression": crear_pipeline(
        LogisticRegression(max_iter=2000, random_state=42)
    ),
    "LinearSVC": crear_pipeline(LinearSVC(random_state=42)),
}

# ==================================================
# 4. VALIDACIÓN CRUZADA
# ==================================================

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

resultados = []
predicciones_modelos = {}

for nombre, pipeline in modelos.items():

    print("\n" + "=" * 65)
    print("MODELO:", nombre)
    print("=" * 65)

    # Cada reporte se evalúa con un modelo
    # que no fue entrenado con ese reporte.
    predicciones = cross_val_predict(pipeline, X, y, cv=cv, n_jobs=-1)

    accuracy = accuracy_score(y, predicciones)

    macro_f1 = f1_score(
        y, predicciones, average="macro", labels=categorias, zero_division=0
    )

    print(f"Accuracy: {accuracy:.4f}")
    print(f"Macro-F1: {macro_f1:.4f}")

    print("\nREPORTE POR CATEGORÍA")

    print(classification_report(y, predicciones, labels=categorias, zero_division=0))

    predicciones_modelos[nombre] = predicciones

    resultados.append({"modelo": nombre, "accuracy": accuracy, "macro_f1": macro_f1})

# ==================================================
# 5. COMPARACIÓN
# ==================================================

tabla = pd.DataFrame(resultados)

tabla = tabla.sort_values(
    ["macro_f1", "accuracy"], ascending=[False, False]
).reset_index(drop=True)

print("\n" + "=" * 65)
print("COMPARACIÓN FINAL DE ALGORITMOS")
print("=" * 65)

print(tabla.to_string(index=False, float_format=lambda n: f"{n:.4f}"))

mejor_nombre = tabla.iloc[0]["modelo"]

print("\nMEJOR MODELO PROVISIONAL:", mejor_nombre)

# ==================================================
# 6. MATRIZ DE CONFUSIÓN
# ==================================================

matriz = confusion_matrix(y, predicciones_modelos[mejor_nombre], labels=categorias)

print("\nMATRIZ DE CONFUSIÓN")

print(
    pd.DataFrame(
        matriz,
        index=[f"Real: {c}" for c in categorias],
        columns=[f"Pred: {c}" for c in categorias],
    ).to_string()
)

# ==================================================
# 7. ENTRENAMIENTO DEL PROTOTIPO
# ==================================================

# Después de la validación cruzada,
# entrenamos con los 60 reportes.
#
# Este es un prototipo inicial,
# NO una validación definitiva.

modelo_final = clone(modelos[mejor_nombre])

modelo_final.fit(X, y)

artefacto = {
    "pipeline": modelo_final,
    "categorias": categorias,
    "algoritmo": mejor_nombre,
    "tipo": "clasificacion_reportes_red",
    "estado": "prototipo_inicial",
}

ruta_modelo = MODELS / "nlp_clasificador.joblib"

joblib.dump(artefacto, ruta_modelo)

# ==================================================
# 8. PROBAR CON UN REPORTE NUEVO
# ==================================================

ejemplo = (
    "Se detectó pérdida de conectividad "
    "en el router R3 hacia la dirección "
    "192.168.1.10 mediante la interfaz "
    "GigabitEthernet0/1."
)

prediccion = modelo_final.predict([ejemplo])[0]

print("\n" + "=" * 65)
print("PRUEBA DE FUNCIONAMIENTO")
print("=" * 65)

print("Reporte:", ejemplo)
print("Categoría predicha:", prediccion)

# ==================================================
# 9. GUARDAR RESULTADOS
# ==================================================

ruta_reporte = REPORTS / "nlp_comparacion_modelos.csv"

tabla.to_csv(ruta_reporte, index=False, encoding="utf-8-sig")

print("\n" + "=" * 65)
print("ARCHIVOS GENERADOS")
print("=" * 65)

print("Modelo:", ruta_modelo)
print("Comparación:", ruta_reporte)

print("\nEntrenamiento inicial finalizado.")
print("Modelo guardado como prototipo.")
