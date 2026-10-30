from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
CARPETA = BASE / "data" / "raw" / "sofi"

archivos = sorted(CARPETA.rglob("SOFI CoreSwitch-*.csv"))
datos = {}

for archivo in archivos:
    df = pd.read_csv(archivo)

    df.columns = df.columns.str.strip()
    df = df.sort_values("timestamp").reset_index(drop=True)

    datos[archivo.name] = df

    print(f"\n{'=' * 50}")
    print(f"ARCHIVO: {archivo.name}")

    print("\nFechas de monitoreo:")
    fechas = pd.to_datetime(df["timestamp"], unit="s", utc=True)

    print("Inicio:", fechas.min())
    print("Fin:", fechas.max())

    print("\nTimestamps duplicados:")
    print(df["timestamp"].duplicated().sum())

    print("\nValores de 'range':")
    print(df["range"].value_counts().head(10))

    print("\nColumnas constantes:")
    constantes = [col for col in df.columns if df[col].nunique(dropna=False) == 1]
    print(constantes)

    print("\nDistribución temporal de fallas:")
    fallas = df["class"].eq("F")

    print("Total de registros F:", fallas.sum())
    print("Bloques consecutivos F:", (fallas & ~fallas.shift(fill_value=False)).sum())

    corte = int(len(df) * 0.8)

    print("\nPrimer 80%:")
    print(df.iloc[:corte]["class"].value_counts())

    print("\nÚltimo 20%:")
    print(df.iloc[corte:]["class"].value_counts())


# Comparación entre los dos switches
if len(datos) == 2:
    nombres = list(datos.keys())

    a = datos[nombres[0]]
    b = datos[nombres[1]]

    print(f"\n{'=' * 50}")
    print("COMPARACIÓN ENTRE SWITCHES")

    comparacion = a[["timestamp", "class"]].merge(
        b[["timestamp", "class"]], on="timestamp", how="inner", suffixes=("_I", "_II")
    )

    print("\nTimestamps compartidos:")
    print(comparacion["timestamp"].nunique())

    print("\nRegistros con etiquetas iguales:")
    iguales = (comparacion["class_I"] == comparacion["class_II"]).sum()

    print(iguales)

    print("\nRegistros con etiquetas diferentes:")
    print(len(comparacion) - iguales)

print("\nVerificación finalizada.")
