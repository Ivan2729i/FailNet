
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
import joblib
import numpy as np
import pandas as pd



BASE = Path(__file__).resolve().parents[3]
MODELO_PATH = BASE / "models" / "digital_twin_clasificador.joblib"
DATA_PATH = BASE / "data" / "raw" / "digital_twin"
REPORTES_PATH = BASE / "reports"

RANGOS = {
    0: "Menos de 10 Mbps",
    1: "10 a menos de 40 Mbps",
    2: "40 a menos de 70 Mbps",
    3: "70 a menos de 90 Mbps",
    4: "90 Mbps o más",
}


# ==================================================
# Cargar el modelo entrenado
# ==================================================

@lru_cache(maxsize=1)
def cargar_modelo_twin():
    if not MODELO_PATH.is_file():
        raise FileNotFoundError(f"Modelo no encontrado: {MODELO_PATH}")

    artefacto = joblib.load(MODELO_PATH)

    if not isinstance(artefacto, dict):
        raise ValueError("Formato del modelo Digital Twin inválido.")

    requeridos = {"modelo", "imputador", "columnas"}
    faltantes = requeridos - artefacto.keys()

    if faltantes:
        raise ValueError(f"Componentes faltantes: {sorted(faltantes)}")

    columnas = list(artefacto["columnas"])
    modelo = artefacto["modelo"]
    imputador = artefacto["imputador"]

    if len(columnas) != 67 or len(set(columnas)) != 67:
        raise ValueError("El modelo debe contener 67 características únicas.")

    if getattr(imputador, "n_features_in_", None) != 67:
        raise ValueError("El imputador no corresponde a las 67 características.")

    clases = set(int(c) for c in modelo.classes_)
    if clases != set(range(5)):
        raise ValueError(f"Clases inesperadas en el modelo: {clases}")

    prohibidas = [
        c for c in columnas
        if c in {"LABEL", "Timestamp", "Host Name"}
        or c.lower().startswith(("bw_rx.", "bw_tx."))
        or "octets" in c.lower()
    ]

    if prohibidas:
        raise ValueError(f"Características no permitidas: {prohibidas}")

    return artefacto


# ==================================================
# Validar estructura del archivo
# ==================================================

def validar_estructura_twin(archivo, columnas):
    if hasattr(archivo, "seek"):
        archivo.seek(0)

    encabezado = pd.read_csv(archivo, nrows=0).columns.tolist()

    if len(encabezado) != len(set(encabezado)):
        raise ValueError("El CSV contiene columnas duplicadas.")

    obligatorias = set(columnas) | {"Timestamp", "Host Name"}
    faltantes = sorted(obligatorias - set(encabezado))

    if faltantes:
        raise ValueError(
            "El CSV no contiene las columnas necesarias:\n"
            + "\n".join(f"- {c}" for c in faltantes)
        )

    if hasattr(archivo, "seek"):
        archivo.seek(0)


# ==================================================
# Ejecutar inferencia por lotes
# ==================================================

def analizar_twin(archivo, salida_csv=None, tamano_lote=20000):
    artefacto = cargar_modelo_twin()

    modelo = artefacto["modelo"]
    imputador = artefacto["imputador"]
    columnas = list(artefacto["columnas"])

    validar_estructura_twin(archivo, columnas)

    if tamano_lote < 1:
        raise ValueError("El tamaño del lote debe ser positivo.")

    necesarias = set(columnas) | {"Timestamp", "Host Name"}

    lector = pd.read_csv(
        archivo,
        usecols=lambda c: c in necesarias,
        chunksize=tamano_lote,
        low_memory=False,
    )

    conteo_niveles = Counter()
    conteo_routers = defaultdict(Counter)
    conteo_dias = defaultdict(Counter)

    total = 0
    muestra = []

    ruta_salida = Path(salida_csv) if salida_csv else None

    if ruta_salida:
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # Abrimos el archivo una sola vez.
    salida = None

    try:
        if ruta_salida:
            salida = ruta_salida.open(
                "w", encoding="utf-8-sig", newline=""
            )

        primer_lote = True

        for numero_lote, lote in enumerate(lector, start=1):
            if lote.empty:
                continue

            # ------------------------------------------
            # Validación de metadatos
            # ------------------------------------------

            timestamps = pd.to_numeric(
                lote["Timestamp"], errors="coerce"
            )

            if (
                timestamps.isna().any()
                or (timestamps % 1 != 0).any()
            ):
                raise ValueError(
                    f"Timestamp inválido en el lote {numero_lote}."
                )

            fechas = pd.to_datetime(
                timestamps,
                unit="s",
                utc=True,
                errors="coerce",
            )

            if fechas.isna().any():
                raise ValueError(
                    f"Fechas inválidas en el lote {numero_lote}."
                )

            if lote["Host Name"].isna().any():
                raise ValueError(
                    f"Routers sin nombre en el lote {numero_lote}."
                )

            routers = lote["Host Name"].astype(str).str.strip()

            if routers.eq("").any():
                raise ValueError(
                    f"Routers vacíos en el lote {numero_lote}."
                )

            # ------------------------------------------
            # Preparar las 67 características
            # ------------------------------------------

            X_original = lote[columnas]

            X = X_original.apply(
                pd.to_numeric, errors="coerce"
            )

            invalidos = (
                X_original.notna() & X.isna()
            ).sum().sum()

            if invalidos:
                raise ValueError(
                    f"El lote {numero_lote} contiene "
                    f"{invalidos} valores no numéricos."
                )

            X = X.replace([np.inf, -np.inf], np.nan)

            # Utilizamos el imputador ORIGINAL.
            X_imputado = imputador.transform(X)

            # ------------------------------------------
            # Predicción multiclase
            # ------------------------------------------

            probabilidades = modelo.predict_proba(X_imputado)
            indices = probabilidades.argmax(axis=1)

            clases = np.asarray(modelo.classes_)
            niveles = clases[indices].astype(int)
            confianza = probabilidades.max(axis=1)

            # La confianza es una puntuación del
            # clasificador, no una probabilidad calibrada.

            resultado_lote = pd.DataFrame({
                "timestamp": timestamps.astype("int64").to_numpy(),
                "fecha_utc": fechas.dt.strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ).to_numpy(),
                "router": routers.to_numpy(),
                "nivel": niveles,
                "rango_trafico": [
                    RANGOS[int(n)] for n in niveles
                ],
                "confianza_modelo": confianza.round(6),
            })

            # ------------------------------------------
            # Actualizar estadísticas
            # ------------------------------------------

            total += len(resultado_lote)
            conteo_niveles.update(
                int(n) for n in niveles
            )

            por_router = resultado_lote.groupby(
                ["router", "nivel"]
            ).size()

            for (router, nivel), cantidad in por_router.items():
                conteo_routers[str(router)][int(nivel)] += int(cantidad)

            resultado_lote["dia"] = (
                resultado_lote["fecha_utc"].str[:10]
            )

            por_dia = resultado_lote.groupby(
                ["dia", "nivel"]
            ).size()

            for (dia, nivel), cantidad in por_dia.items():
                conteo_dias[str(dia)][int(nivel)] += int(cantidad)

            # ------------------------------------------
            # Guardar resultados completos
            # ------------------------------------------

            if salida is not None:
                resultado_lote.drop(columns=["dia"]).to_csv(
                    salida, index=False, header=primer_lote
                )

            if len(muestra) < 10:
                pendientes = 10 - len(muestra)
                muestra.extend(
                    resultado_lote.drop(columns=["dia"])
                    .head(pendientes)
                    .to_dict("records")
                )

            primer_lote = False

            print(
                f"Lote {numero_lote}: "
                f"{len(lote):,} registros | "
                f"Acumulados: {total:,}"
            )

        if total == 0:
            raise ValueError("El archivo CSV no contiene registros.")

    except Exception:
        if salida is not None:
            salida.close()

        if ruta_salida:
            ruta_salida.unlink(missing_ok=True)

        raise

    finally:
        if salida is not None and not salida.closed:
            salida.close()

    # ==================================================
    # Resumen y distribución
    # ==================================================

    distribucion = [
        {
            "nivel": nivel,
            "rango": RANGOS[nivel],
            "registros": conteo_niveles[nivel],
            "porcentaje": round(
                100 * conteo_niveles[nivel] / total, 2
            ),
        }
        for nivel in range(5)
    ]

    routers_resumen = [
        {
            "router": router,
            "total": sum(conteos.values()),
            "niveles": {
                str(n): conteos[n] for n in range(5)
            },
        }
        for router, conteos in sorted(conteo_routers.items())
    ]

    distribucion_diaria = [
        {
            "fecha": dia,
            "total": sum(conteos.values()),
            "niveles": {
                str(n): conteos[n] for n in range(5)
            },
        }
        for dia, conteos in sorted(conteo_dias.items())
    ]

    return {
        "resumen": {
            "modelo": "Digital Twin",
            "total_registros": total,
            "total_routers": len(conteo_routers),
            "caracteristicas": len(columnas),
            "niveles": distribucion,
        },
        "routers": routers_resumen,
        "distribucion_diaria": distribucion_diaria,
        "muestra": muestra,
        "archivo_resultado": str(ruta_salida) if ruta_salida else None,
    }


# ==================================================
# Prueba local del servicio
# ==================================================

def main():
    print("=" * 65)
    print("FAILNET - INFERENCIA DIGITAL TWIN")
    print("=" * 65)

    archivo = DATA_PATH / "dataset_01_TC31_05062025_labeled_final.csv"
    salida = REPORTES_PATH / "twin_inferencia_prueba_web.csv"

    if not archivo.is_file():
        raise FileNotFoundError(f"Dataset no encontrado: {archivo}")

    print("\nDataset:", archivo.name)
    print("Modelo:", MODELO_PATH.name)

    resultado = analizar_twin(archivo, salida_csv=salida)

    print("\n" + "=" * 65)
    print("RESUMEN")
    print("=" * 65)

    resumen = resultado["resumen"]
    print("Total de registros:", resumen["total_registros"])
    print("Routers detectados:", resumen["total_routers"])
    print("Características:", resumen["caracteristicas"])

    print("\nDISTRIBUCIÓN DE NIVELES")

    for item in resumen["niveles"]:
        print(
            f"Nivel {item['nivel']}: "
            f"{item['registros']:,} registros "
            f"({item['porcentaje']:.2f}%) | "
            f"{item['rango']}"
        )

    print("\nRESULTADOS POR ROUTER")

    for router in resultado["routers"]:
        print(
            f"{router['router']}: "
            f"{router['total']:,} registros | "
            f"{router['niveles']}"
        )

    print("\nPRIMERAS 5 PREDICCIONES")

    for fila in resultado["muestra"][:5]:
        print(fila)

    print("\nArchivo generado:", salida)
    print("\nInferencia Digital Twin finalizada.")


if __name__ == "__main__":
    main()
