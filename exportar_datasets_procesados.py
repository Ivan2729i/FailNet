from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
MODELS = ROOT / "models"


def localizar(base: Path, patron: str) -> Path:
    encontrados = sorted(base.rglob(patron))
    if not encontrados:
        raise FileNotFoundError(f"No se encontro {patron} dentro de {base}")
    return encontrados[0]


def guardar(df: pd.DataFrame, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    print(
        f"Generado: {ruta.relative_to(ROOT)} | filas={len(df):,} | columnas={len(df.columns)}"
    )


def exportar_sofi() -> None:
    print("\n=== SOFI: ambos switches ===")
    artefacto = joblib.load(MODELS / "sofi_combinado.joblib")
    columnas = artefacto["columnas"]
    imputador = artefacto["imputador"]

    def leer(nombre: str) -> pd.DataFrame:
        df = pd.read_csv(localizar(RAW / "sofi", nombre), low_memory=False)
        df.columns = df.columns.str.strip()
        df = df.rename(columns={"SNMP_availability": "SNMP_Availability"})
        return df

    uno = leer("SOFI CoreSwitch-I.csv")
    dos = leer("SOFI CoreSwitch-II.csv")
    unido = uno.merge(
        dos, on="timestamp", how="inner", suffixes=("_I", "_II"), validate="one_to_one"
    )
    unido = unido.sort_values("timestamp").reset_index(drop=True)
    if not unido["class_I"].eq(unido["class_II"]).all():
        raise ValueError("SOFI: hay etiquetas diferentes para un mismo timestamp")
    if len(unido) != 12970:
        raise ValueError(f"SOFI: filas inesperadas: {len(unido)}")
    if len(columnas) != 64:
        raise ValueError(
            f"SOFI: el modelo tiene {len(columnas)} columnas, se esperaban 64"
        )

    X = unido[columnas].apply(pd.to_numeric, errors="raise")
    X = X.mask(X < 0)  # Misma regla de limpieza del entrenamiento final
    X_procesado = imputador.transform(X)
    columnas_df = pd.DataFrame(X_procesado, columns=columnas)
    columnas_df.insert(0, "timestamp", unido["timestamp"].to_numpy())
    columnas_df["class"] = unido["class_I"].astype(str).to_numpy()
    corte = int(len(unido) * 0.80)

    guardar(
        columnas_df.iloc[:corte].copy(),
        PROCESSED / "sofi" / "sofi_desarrollo_procesado.csv",
    )
    guardar(
        columnas_df.iloc[corte:].copy(),
        PROCESSED / "sofi" / "sofi_prueba_procesado.csv",
    )


def exportar_twin() -> None:
    print("\n=== Network Digital Twin: escenario 01 ===")
    artefacto = joblib.load(MODELS / "digital_twin_clasificador.joblib")
    columnas = artefacto["columnas"]
    imputador = artefacto["imputador"]

    df = pd.read_csv(
        localizar(RAW / "digital_twin", "dataset_01_TC31_05062025_labeled_final.csv"),
        low_memory=False,
    )
    df.columns = df.columns.str.strip()
    df = df.sort_values(["Timestamp", "Host Name"]).reset_index(drop=True)
    if len(df) != 227838:
        raise ValueError(f"Twin: filas inesperadas: {len(df)}")
    if len(columnas) != 67:
        raise ValueError(
            f"Twin: el modelo tiene {len(columnas)} columnas, se esperaban 67"
        )

    X = df[columnas].apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan)
    X_procesado = imputador.transform(X).astype(np.float32)
    columnas_df = pd.DataFrame(X_procesado, columns=columnas)
    columnas_df.insert(0, "Host Name", df["Host Name"].to_numpy())
    columnas_df.insert(0, "Timestamp", df["Timestamp"].to_numpy())
    columnas_df["LABEL"] = df["LABEL"].astype(int).to_numpy()

    instantes = np.sort(df["Timestamp"].unique())
    inicio_prueba = instantes[int(len(instantes) * 0.80)]
    desarrollo = columnas_df["Timestamp"] < inicio_prueba
    prueba = ~desarrollo

    guardar(
        columnas_df.loc[desarrollo].copy(),
        PROCESSED / "twin" / "twin01_desarrollo_procesado.csv",
    )
    guardar(
        columnas_df.loc[prueba].copy(),
        PROCESSED / "twin" / "twin01_prueba_procesado.csv",
    )


if __name__ == "__main__":
    print("Exportando datasets procesados sin reentrenar...")
    exportar_sofi()
    exportar_twin()
    print("\nExportacion completada. Los CSV originales no fueron modificados.")
