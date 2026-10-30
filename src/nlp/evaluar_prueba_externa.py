from pathlib import Path
import unicodedata
import re

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

BASE = Path(__file__).resolve().parents[2]
RUTA_MODELO = BASE / "models" / "nlp_clasificador.joblib"
RUTA_PRUEBA = BASE / "data" / "raw" / "nlp" / "reportes_prueba_externa.csv"
RUTA_ENTRENAMIENTO = BASE / "data" / "raw" / "nlp" / "reportes_red.csv"
REPORTES = BASE / "reports"
REPORTES.mkdir(parents=True, exist_ok=True)

CLASES = ["conectividad", "interfaces", "rendimiento", "servicios"]


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip()


def evaluar():
    for ruta in (RUTA_MODELO, RUTA_PRUEBA):
        if not ruta.is_file():
            raise FileNotFoundError(f"Falta el archivo: {ruta}")

    prueba = pd.read_csv(RUTA_PRUEBA, encoding="utf-8-sig")
    if not {"texto", "categoria"}.issubset(prueba.columns):
        raise ValueError("El CSV necesita las columnas texto y categoria")
    if prueba[["texto", "categoria"]].isna().any().any():
        raise ValueError("Hay reportes sin texto o sin categoría")

    prueba["texto"] = prueba["texto"].astype(str).str.strip()
    prueba["categoria"] = prueba["categoria"].astype(str).str.strip().str.lower()
    if (prueba["texto"] == "").any():
        raise ValueError("Existen reportes vacíos")
    if set(prueba["categoria"]) != set(CLASES):
        raise ValueError("La prueba debe incluir las cuatro categorías")
    if prueba["texto"].map(normalizar).duplicated().any():
        raise ValueError("Hay reportes duplicados dentro de la prueba")

    # Verificar que el CSV de prueba no reutilice textos de entrenamiento.
    # Esto detecta coincidencias exactas normalizadas, no todas las paráfrasis.
    if RUTA_ENTRENAMIENTO.exists():
        entrenamiento = pd.read_csv(RUTA_ENTRENAMIENTO, encoding="utf-8-sig")
        textos_train = set(entrenamiento["texto"].dropna().map(normalizar))
        comunes = prueba["texto"].map(normalizar).isin(textos_train)
        if comunes.any():
            raise ValueError(
                f"Se encontraron {comunes.sum()} textos presentes en el "
                "entrenamiento. No evaluar hasta corregir el solapamiento."
            )
    else:
        print("Aviso: no se pudo comparar con reportes_red.csv")

    artefacto = joblib.load(RUTA_MODELO)
    if "pipeline" not in artefacto:
        raise ValueError("El artefacto .joblib no contiene 'pipeline'")
    modelo = artefacto["pipeline"]

    # Solo inferencia: deliberadamente NO se llama fit() ni fit_transform().
    prueba["prediccion"] = modelo.predict(prueba["texto"])
    prueba["correcto"] = prueba["categoria"] == prueba["prediccion"]

    y_true, y_pred = prueba["categoria"], prueba["prediccion"]
    exactitud = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, labels=CLASES, average="macro", zero_division=0)
    macro_precision = precision_score(
        y_true, y_pred, labels=CLASES, average="macro", zero_division=0
    )
    macro_recall = recall_score(
        y_true, y_pred, labels=CLASES, average="macro", zero_division=0
    )
    aciertos = int(prueba["correcto"].sum())

    print("=" * 65)
    print("PRUEBA ADICIONAL DE PNL - NETINSIGHT AI")
    print("=" * 65)
    print("Modelo utilizado:", RUTA_MODELO.name)
    print("Modelo reentrenado: NO")
    print("Origen de los 40 reportes: simulados, redactados por separado")
    print("Total:", len(prueba))
    print("\nDISTRIBUCIÓN DE LAS CLASES")
    print(y_true.value_counts().reindex(CLASES, fill_value=0).to_string())
    print("\nRESULTADOS")
    print(f"Aciertos: {aciertos}/{len(prueba)}")
    print(f"Errores: {len(prueba) - aciertos}")
    print(f"Accuracy: {exactitud:.4f} ({exactitud:.2%})")
    print(f"Macro-Precision: {macro_precision:.4f}")
    print(f"Macro-Recall: {macro_recall:.4f}")
    print(f"Macro-F1: {macro_f1:.4f} ({macro_f1:.2%})")
    print("\nREPORTE POR CLASE")
    print(classification_report(y_true, y_pred, labels=CLASES, zero_division=0))
    matriz = confusion_matrix(y_true, y_pred, labels=CLASES)
    print("MATRIZ DE CONFUSIÓN")
    print(
        pd.DataFrame(
            matriz,
            index=["Real: " + x for x in CLASES],
            columns=["Pred: " + x for x in CLASES],
        ).to_string()
    )

    print("\nERRORES DE CLASIFICACIÓN")
    errores = prueba.loc[~prueba["correcto"]]
    if errores.empty:
        print("No se detectaron errores en esta muestra.")
    else:
        for _, fila in errores.iterrows():
            print("-" * 65)
            print("Texto:", fila["texto"])
            print("Real:", fila["categoria"], "| Predicción:", fila["prediccion"])

    ruta_detalle = REPORTES / "nlp_prueba_externa_predicciones.csv"
    ruta_resumen = REPORTES / "nlp_prueba_externa_metricas.csv"
    prueba.to_csv(ruta_detalle, index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {
                "registros": len(prueba),
                "aciertos": aciertos,
                "errores": len(prueba) - aciertos,
                "accuracy": exactitud,
                "macro_precision": macro_precision,
                "macro_recall": macro_recall,
                "macro_f1": macro_f1,
                "origen": "simulado, evaluacion adicional separada",
            }
        ]
    ).to_csv(ruta_resumen, index=False, encoding="utf-8-sig")
    print("\nCSV detallado:", ruta_detalle)
    print("CSV de métricas:", ruta_resumen)
    print("Modelo conservado sin cambios.")


if __name__ == "__main__":
    evaluar()
