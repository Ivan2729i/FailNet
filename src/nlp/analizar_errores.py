from pathlib import Path

import pandas as pd

from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedKFold, cross_val_predict

# ==========================================
# 1. RUTAS
# ==========================================

BASE = Path(__file__).resolve().parents[2]

DATA = BASE / "data" / "raw" / "nlp"
REPORTS = BASE / "reports"

REPORTS.mkdir(parents=True, exist_ok=True)

archivo = DATA / "reportes_red.csv"

df = pd.read_csv(archivo, encoding="utf-8-sig")

df = (
    df.dropna(subset=["texto", "categoria"])
    .drop_duplicates(subset=["texto"])
    .reset_index(drop=True)
)

# ==========================================
# 2. RECONSTRUIR EL MODELO
# ==========================================

modelo = Pipeline(
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
        ("clasificador", LinearSVC(random_state=42)),
    ]
)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# Obtener predicciones de validación cruzada
predicciones = cross_val_predict(modelo, df["texto"], df["categoria"], cv=cv, n_jobs=-1)

# ==========================================
# 3. IDENTIFICAR ERRORES
# ==========================================

df["prediccion"] = predicciones

errores = df[df["categoria"] != df["prediccion"]].copy()

print("=" * 65)
print("ANÁLISIS DE ERRORES - PNL")
print("=" * 65)

print("Reportes evaluados:", len(df))
print("Aciertos:", len(df) - len(errores))
print("Errores:", len(errores))

print("\n" + "=" * 65)
print("REPORTES CLASIFICADOS INCORRECTAMENTE")
print("=" * 65)

for _, fila in errores.iterrows():

    print("\n" + "-" * 60)

    print("REPORTE:")
    print(fila["texto"])

    print("Categoría real:", fila["categoria"])
    print("Categoría predicha:", fila["prediccion"])

# ==========================================
# 4. RESUMEN DE CONFUSIONES
# ==========================================

print("\n" + "=" * 65)
print("CONFUSIONES MÁS FRECUENTES")
print("=" * 65)

if not errores.empty:

    resumen = (
        errores.groupby(["categoria", "prediccion"])
        .size()
        .reset_index(name="cantidad")
        .sort_values("cantidad", ascending=False)
    )

    print(resumen.to_string(index=False))

else:
    print("No hubo errores")

# ==========================================
# 5. GUARDAR REPORTE
# ==========================================

ruta = REPORTS / "nlp_errores_clasificacion.csv"

errores.to_csv(ruta, index=False, encoding="utf-8-sig")

print("\nReporte guardado:", ruta)
print("Análisis finalizado.")
