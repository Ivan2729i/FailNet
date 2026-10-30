from pathlib import Path

import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

# ==================================================
# 1. CARGAR DATASET
# ==================================================

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "raw" / "sofi"
REPORTS = BASE / "reports"

REPORTS.mkdir(parents=True, exist_ok=True)

archivo = next(DATA.rglob("SOFI CoreSwitch-I.csv"))

df = pd.read_csv(archivo)
df.columns = df.columns.str.strip()
df = df.sort_values("timestamp").reset_index(drop=True)

# Mantenemos intacta la prueba final
corte = int(len(df) * 0.80)
dev = df.iloc[:corte].copy()

X = dev.drop(columns=["class", "timestamp", "range"])

y = dev["class"]

print("=" * 60)
print("AUDITORÍA DE VALORES NEGATIVOS - SOFI")
print("=" * 60)

# ==================================================
# 2. AUDITAR VARIABLES
# ==================================================

resultados = []

for columna in X.columns:

    negativos = X[columna] < 0

    cantidad = int(negativos.sum())

    if cantidad == 0:
        continue

    resultados.append(
        {
            "variable": columna,
            "negativos": cantidad,
            "porcentaje": round(negativos.mean() * 100, 2),
            "menos_1": int((X[columna] == -1).sum()),
            "menos_2": int((X[columna] == -2).sum()),
            "otros_negativos": int(
                ((X[columna] < 0) & ~X[columna].isin([-1, -2])).sum()
            ),
        }
    )

tabla = pd.DataFrame(resultados)

tabla = tabla.sort_values("negativos", ascending=False)

print("\nVARIABLES CON VALORES NEGATIVOS:")
print(tabla.to_string(index=False))

tabla.to_csv(REPORTS / "sofi_valores_negativos.csv", index=False, encoding="utf-8-sig")

# ==================================================
# 3. COMPARACIÓN ENTRE PERIODOS
# ==================================================

cv = TimeSeriesSplit(n_splits=3, gap=24)

variables = [
    "Device_uptime",
    "ICMP_response_time",
    "IN_Inbound_packets_with_errors",
    "IN_Bits_received",
    "EX_Bits_sent",
]

print("\n" + "=" * 60)
print("COMPARACIÓN POR VENTANAS Y CLASES")
print("=" * 60)

for numero, (train_idx, val_idx) in enumerate(cv.split(X), 1):

    if numero == 1:
        continue

    print(f"\nVENTANA {numero}")

    for nombre, indices in [("ENTRENAMIENTO", train_idx), ("VALIDACIÓN", val_idx)]:

        datos = X.iloc[indices]
        etiquetas = y.iloc[indices]

        print(f"\n{nombre}")

        for clase in ["NE", "F"]:

            subconjunto = datos.loc[etiquetas == clase]

            if subconjunto.empty:
                continue

            print(f"\nClase {clase}: " f"{len(subconjunto)} registros")

            for variable in variables:

                porcentaje = (subconjunto[variable] < 0).mean() * 100

                print(f"  {variable}: " f"{porcentaje:.2f}% negativos")

print("\nAuditoría finalizada.")
print("No se modificaron los datos originales.")
print("No se utilizó la prueba final.")
