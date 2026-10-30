from pathlib import Path
import pandas as pd

# ==========================================
# 1. UBICAR DATASET
# ==========================================

BASE = Path(__file__).resolve().parents[3]
DATA = BASE / "data" / "raw" / "digital_twin"

archivo = next(DATA.rglob("dataset_01_TC31_05062025_labeled_final.csv"), None)

if archivo is None:
    raise FileNotFoundError(f"No se encontró el dataset dentro de {DATA}")

print("=" * 65)
print("EXPLORACIÓN - NETWORK DIGITAL TWIN")
print("=" * 65)
print("Archivo:", archivo)

# ==========================================
# 2. CARGAR INFORMACIÓN
# ==========================================

df = pd.read_csv(archivo, low_memory=False)
df.columns = df.columns.str.strip()

print("\nDIMENSIONES")
print("Registros:", len(df))
print("Columnas:", len(df.columns))

print("\nCOLUMNAS Y TIPOS DE DATOS")

for columna in df.columns:
    print(f"{columna}: {df[columna].dtype}")

# ==========================================
# 3. CALIDAD DE LOS DATOS
# ==========================================

print("\nVALORES NULOS")

nulos = df.isna().sum()
nulos = nulos[nulos > 0].sort_values(ascending=False)

if nulos.empty:
    print("No hay valores nulos")
else:
    print(nulos.to_string())

print("\nREGISTROS DUPLICADOS")
print(df.duplicated().sum())

# ==========================================
# 4. POSIBLES ETIQUETAS
# ==========================================

print("\nCOLUMNAS CON POCOS VALORES ÚNICOS")

for columna in df.columns:

    unicos = df[columna].nunique(dropna=False)

    if unicos <= 10:
        print(f"\n{columna}")
        print(df[columna].value_counts(dropna=False).to_string())

# ==========================================
# 5. POSIBLES VARIABLES DE FUGA
# ==========================================

print("\nPOSIBLES VARIABLES DE TRÁFICO")

palabras = [
    "bandwidth",
    "throughput",
    "mbps",
    "traffic",
    "rate",
    "speed",
    "label",
    "class",
    "target",
]

for columna in df.columns:
    if any(palabra in columna.lower() for palabra in palabras):
        print(columna)

# ==========================================
# 6. MUESTRA DE REGISTROS
# ==========================================

print("\nPRIMEROS 5 REGISTROS")
print(df.head(5).to_string(index=False))

print("\nEXPLORACIÓN FINALIZADA")
