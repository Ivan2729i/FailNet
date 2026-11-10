from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# ==================================================
# 1. CONFIGURACIÓN
# ==================================================

BASE = Path(__file__).resolve().parents[3]

MODELO_PATH = BASE / "models" / "sofi_combinado.joblib"

DATA_PATH = BASE / "data" / "raw" / "sofi" / "data_sofi"


# ==================================================
# 2. CARGAR MODELO ENTRENADO
# ==================================================


@lru_cache(maxsize=1)
def cargar_modelo_sofi():

    if not MODELO_PATH.is_file():
        raise FileNotFoundError(f"No se encontró el modelo: {MODELO_PATH}")

    artefacto = joblib.load(MODELO_PATH)

    campos = {
        "modelo",
        "imputador",
        "columnas",
        "umbral",
    }

    if not isinstance(artefacto, dict):
        raise TypeError("El modelo SOFI tiene un formato inválido.")

    faltantes = campos - set(artefacto)

    if faltantes:
        raise ValueError("Faltan componentes en el modelo: " + ", ".join(sorted(faltantes)))

    if len(artefacto["columnas"]) != 64:
        raise ValueError("El modelo no contiene las 64 características esperadas.")

    return artefacto


# ==================================================
# 3. LEER Y VALIDAR CSV
# ==================================================


def preparar_csv(archivo, sufijo):

    if hasattr(archivo, "seek"):
        archivo.seek(0)

    df = pd.read_csv(archivo, low_memory=False)

    if df.empty:
        raise ValueError(f"El archivo del switch {sufijo} está vacío.")

    if "timestamp" not in df.columns:
        raise ValueError(f"El switch {sufijo} no tiene la columna timestamp.")

    # Comprobar que los timestamps sean válidos.
    timestamps = pd.to_numeric(df["timestamp"], errors="coerce")

    if timestamps.isna().any():
        raise ValueError(f"El switch {sufijo} contiene timestamps inválidos.")

    if (timestamps % 1 != 0).any():
        raise ValueError(f"El switch {sufijo} contiene timestamps no enteros.")

    df["timestamp"] = timestamps.astype("int64")

    # Evitar uniones muchos-a-muchos.
    duplicados = df["timestamp"].duplicated().sum()

    if duplicados:
        raise ValueError(f"El switch {sufijo} tiene {duplicados} timestamps duplicados.")

    # Los campos originales no utilizados
    # por el modelo se eliminan.
    #
    # Especialmente "class", para evitar
    # utilizar la etiqueta verdadera
    # como característica de entrada.

    columnas_excluidas = [columna for columna in ("range", "class") if columna in df.columns]

    df = df.drop(columns=columnas_excluidas)

    # Cada switch tiene sus propias variables.
    # Sufijos compatibles con el entrenamiento.
    renombrar = {columna: f"{columna}_{sufijo}" for columna in df.columns if columna != "timestamp"}

    df = df.rename(columns=renombrar)

    return df


# ==================================================
# 4. ALINEAR LAS 64 CARACTERÍSTICAS
# ==================================================


def preparar_caracteristicas(combinados, columnas_modelo):

    # La diferencia entre SNMP_Availability
    # y SNMP_availability no debe causar
    # que falte una característica.
    disponibles = {}

    for columna in combinados.columns:
        clave = str(columna).casefold()

        if clave in disponibles:
            raise ValueError(f"Columnas ambiguas: {columna}")

        disponibles[clave] = columna

    faltantes = [columna for columna in columnas_modelo if columna.casefold() not in disponibles]

    if faltantes:
        raise ValueError(
            "Los CSV no contienen las "
            "características requeridas:\n" + "\n".join(f" - {c}" for c in faltantes)
        )

    # Respetar exactamente el orden de columnas
    # utilizado durante el entrenamiento.
    columnas_reales = [disponibles[columna.casefold()] for columna in columnas_modelo]

    X = combinados[columnas_reales].copy()

    X.columns = columnas_modelo

    # Validar los datos numéricos.
    X_numerico = X.apply(pd.to_numeric, errors="coerce")

    valores_invalidos = (X.notna() & X_numerico.isna()).sum().sum()

    if valores_invalidos:
        raise ValueError(
            f"Se encontraron {valores_invalidos} valores no numéricos en las características."
        )

    # Mantener el tratamiento utilizado
    # al entrenar SOFI: valores negativos
    # como datos faltantes.
    X_numerico = X_numerico.mask(X_numerico < 0)

    X_numerico = X_numerico.replace([np.inf, -np.inf], np.nan)

    return X_numerico


# ==================================================
# 5. ANALIZAR LOS DOS SWITCHES
# ==================================================


def analizar_sofi(archivo_i, archivo_ii):

    artefacto = cargar_modelo_sofi()

    modelo = artefacto["modelo"]
    imputador = artefacto["imputador"]
    columnas = artefacto["columnas"]
    umbral = float(artefacto["umbral"])

    if not 0 <= umbral <= 1:
        raise ValueError("El umbral guardado es inválido.")

    # ------------------------------------------
    # A. CARGAR ARCHIVOS
    # ------------------------------------------

    switch_i = preparar_csv(archivo_i, "I")

    switch_ii = preparar_csv(archivo_ii, "II")

    cantidad_i = len(switch_i)
    cantidad_ii = len(switch_ii)

    # ------------------------------------------
    # B. SINCRONIZAR POR TIMESTAMP
    # ------------------------------------------

    combinados = pd.merge(
        switch_i,
        switch_ii,
        on="timestamp",
        how="inner",
        validate="one_to_one",
        sort=True,
    )

    if combinados.empty:
        raise ValueError("No existen timestamps comunes entre ambos switches.")

    total = len(combinados)

    # ------------------------------------------
    # C. PREPARAR CARACTERÍSTICAS
    # ------------------------------------------

    X = preparar_caracteristicas(combinados, columnas)

    # Utilizamos el imputador ORIGINAL.
    # No ajustamos uno nuevo.
    X_imputado = imputador.transform(X)

    # ------------------------------------------
    # D. PREDECIR PROBABILIDADES
    # ------------------------------------------

    if not hasattr(modelo, "predict_proba"):
        raise ValueError("El modelo no permite obtener probabilidades.")

    clases = list(modelo.classes_)

    if 1 not in clases:
        raise ValueError("El modelo no tiene la clase positiva de falla (1).")

    indice_falla = clases.index(1)

    probabilidades = modelo.predict_proba(X_imputado)[:, indice_falla]

    # Aplicar umbral que ya seleccionamos
    # durante el entrenamiento.
    predicciones = (probabilidades >= umbral).astype(int)

    # ------------------------------------------
    # E. PREPARAR RESULTADOS
    # ------------------------------------------

    resultados = pd.DataFrame(
        {
            "timestamp": combinados["timestamp"].to_numpy(),
            "probabilidad_falla": probabilidades,
            "prediccion": predicciones,
        }
    )

    resultados["fecha_utc"] = pd.to_datetime(resultados["timestamp"], unit="s", utc=True)

    resultados["clasificacion"] = np.where(resultados["prediccion"] == 1, "Falla", "Normal")

    # Orden de las columnas para exportación.
    resultados = resultados[
        [
            "timestamp",
            "fecha_utc",
            "probabilidad_falla",
            "prediccion",
            "clasificacion",
        ]
    ]

    # ------------------------------------------
    # F. ESTADÍSTICAS
    # ------------------------------------------

    fallas = int((predicciones == 1).sum())

    normales = int((predicciones == 0).sum())

    resumen = {
        "modelo": "SOFI",
        "algoritmo": "Random Forest",
        "umbral": umbral,
        "caracteristicas": len(columnas),
        "registros_switch_i": cantidad_i,
        "registros_switch_ii": cantidad_ii,
        "registros_sincronizados": total,
        "registros_no_emparejados_i": (cantidad_i - total),
        "registros_no_emparejados_ii": (cantidad_ii - total),
        "normales": normales,
        "fallas": fallas,
        "porcentaje_normales": round(normales * 100 / total, 2),
        "porcentaje_fallas": round(fallas * 100 / total, 2),
    }

    return {
        "resumen": resumen,
        "predicciones": resultados,
    }


# ==================================================
# 6. PRUEBA LOCAL
# ==================================================


def main():

    print("=" * 65)
    print("FAILNET - INFERENCIA SOFI")
    print("=" * 65)

    archivo_i = DATA_PATH / "SOFI CoreSwitch-I.csv"

    archivo_ii = DATA_PATH / "SOFI CoreSwitch-II.csv"

    print("\nARCHIVOS")
    print("Switch I:", archivo_i.name)
    print("Switch II:", archivo_ii.name)

    resultado = analizar_sofi(archivo_i, archivo_ii)

    print("\n" + "=" * 65)
    print("RESUMEN DEL ANÁLISIS")
    print("=" * 65)

    for clave, valor in resultado["resumen"].items():
        print(f"{clave}: {valor}")

    print("\n" + "=" * 65)
    print("PRIMERAS 10 PREDICCIONES")
    print("=" * 65)

    print(resultado["predicciones"].head(10).to_string(index=False))

    print("\n" + "=" * 65)
    print("ÚLTIMAS 5 PREDICCIONES")
    print("=" * 65)

    print(resultado["predicciones"].tail(5).to_string(index=False))

    print("\nServicio SOFI ejecutado correctamente.")


if __name__ == "__main__":
    main()
