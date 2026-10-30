from pathlib import Path

import numpy as np
import pandas as pd

# ==========================================
# 1. CARGAR DATASET
# ==========================================

BASE = Path(__file__).resolve().parents[3]
DATA = BASE / "data" / "raw" / "digital_twin"

archivo = next(DATA.rglob("dataset_01_TC31_05062025_labeled_final.csv"), None)

if archivo is None:
    raise FileNotFoundError("No se encontró el dataset")

df = pd.read_csv(archivo, low_memory=False)
df.columns = df.columns.str.strip()

df = df.sort_values(["Timestamp", "Host Name"]).reset_index(drop=True)

print("=" * 65)
print("AUDITORÍA - NETWORK DIGITAL TWIN")
print("=" * 65)

# ==========================================
# 2. ANALIZAR TEMPORALIDAD
# ==========================================

instantes = np.sort(df["Timestamp"].unique())

print("\nTEMPORALIDAD")
print("Registros:", len(df))
print("Instantes únicos:", len(instantes))
print("Dispositivos:", df["Host Name"].nunique())

print("Fecha inicial:", pd.to_datetime(instantes[0], unit="s", utc=True))

print("Fecha final:", pd.to_datetime(instantes[-1], unit="s", utc=True))

duplicados = df.duplicated(subset=["Timestamp", "Host Name"]).sum()

print("Pares timestamp-dispositivo duplicados:", duplicados)

print("\nREGISTROS POR INSTANTE")
print(df.groupby("Timestamp").size().describe().to_string())

# ==========================================
# 3. RESERVAR 20% DE INSTANTES
# ==========================================

# Todos los dispositivos del mismo instante
# deben pertenecer al mismo conjunto.

corte = int(len(instantes) * 0.80)

instantes_dev = instantes[:corte]
instantes_test = instantes[corte:]

dev = df[df["Timestamp"].isin(instantes_dev)].copy()

print("\nDIVISIÓN TEMPORAL")
print("Desarrollo:", len(dev), "registros")
print("Prueba reservada:", len(df) - len(dev), "registros")

# La auditoría siguiente usa SOLO desarrollo.

# ==========================================
# 4. REVISAR DISTRIBUCIÓN POR DISPOSITIVO
# ==========================================

print("\nCLASES POR DISPOSITIVO")

tabla_hosts = pd.crosstab(dev["Host Name"], dev["LABEL"])

print(tabla_hosts.to_string())

# ==========================================
# 5. ANALIZAR VALORES FALTANTES
# ==========================================

print("\nINTERFACES DETECTADAS")
print(dev["Nº de interfacesdetectadas"].value_counts().to_string())

print("\nAUSENCIA DE BW_RX.6 SEGÚN INTERFACES")

print(pd.crosstab(dev["Nº de interfacesdetectadas"], dev["bw_rx.6"].isna()).to_string())

# ==========================================
# 6. VARIABLES DE ANCHO DE BANDA
# ==========================================

columnas_bw = [col for col in dev.columns if col.startswith(("bw_rx.", "bw_tx."))]

print("\nCOLUMNAS DE ANCHO DE BANDA")
print(columnas_bw)

bw = dev[columnas_bw].apply(pd.to_numeric, errors="coerce")

# Dos indicadores de tráfico posibles
max_bw = bw.max(axis=1).fillna(0)
sum_bw = bw.sum(axis=1).fillna(0)

analisis = pd.DataFrame({"LABEL": dev["LABEL"], "max_bw": max_bw, "sum_bw": sum_bw})

print("\nTRÁFICO POR CLASE")
print(
    analisis.groupby("LABEL")[["max_bw", "sum_bw"]]
    .agg(["min", "median", "max"])
    .round(2)
    .to_string()
)

# ==========================================
# 7. COMPROBAR REGLAS DE RANGOS
# ==========================================


def clasificar_por_rango(valores):

    # Regla aproximada para investigar
    # la relación con las etiquetas.
    return np.select(
        [valores <= 10, valores <= 40, valores <= 70, valores <= 90],
        [0, 1, 2, 3],
        default=4,
    )


for nombre, valores in [
    ("Máximo ancho de banda", max_bw),
    ("Suma de anchos de banda", sum_bw),
]:

    pred = clasificar_por_rango(valores)

    coincidencia = (pred == dev["LABEL"].to_numpy()).mean()

    print("\n" + "=" * 65)
    print("REGLA:", nombre)
    print("=" * 65)

    print(f"Coincidencia con LABEL: " f"{coincidencia * 100:.2f}%")

    print("\nETIQUETA REAL VS REGLA")

    print(
        pd.crosstab(
            dev["LABEL"], pred, rownames=["Real"], colnames=["Regla"]
        ).to_string()
    )

# ==========================================
# 8. COLUMNAS CONSTANTES
# ==========================================

constantes = [col for col in dev.columns if dev[col].nunique(dropna=False) <= 1]

print("\nCOLUMNAS CONSTANTES")
print(constantes)

print("\nAUDITORÍA FINALIZADA")
print("La prueba final permanece reservada.")
