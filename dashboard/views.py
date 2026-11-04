import csv
import hashlib
import json
import logging
import os
import tempfile
import threading
import uuid
from pathlib import Path

import pandas as pd
from bson import ObjectId
from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from src.blockchain.registro_blockchain import RegistroBlockchain
from src.ml.sofi.servicio_sofi import analizar_sofi
from src.ml.twin.servicio_twin import analizar_twin

from .models import Analisis

# ==================================================
# Resumen general de FailNet
# ==================================================


@require_GET
def obtener_resumen(request):
    resumen = {
        "proyecto": "FailNet",
        "estado": "operativo",
        "total_analisis": Analisis.objects.count(),
        "sofi": Analisis.objects.filter(tipo=Analisis.Tipo.SOFI).count(),
        "digital_twin": Analisis.objects.filter(tipo=Analisis.Tipo.DIGITAL_TWIN).count(),
        "pnl": Analisis.objects.filter(tipo=Analisis.Tipo.PNL).count(),
    }
    return JsonResponse(resumen)


# ==================================================
# Inicio de lógica sofi
# ==================================================

logger = logging.getLogger(__name__)

MAX_CSV_BYTES = 25 * 1024 * 1024
TAMANOS_PAGINA = {25, 50, 100}
BLOQUEO_BLOCKCHAIN = threading.Lock()


# ==================================================
# Protección CSRF
# ==================================================


@require_GET
@ensure_csrf_cookie
def obtener_csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})


# ==================================================
# Validaciones de archivos
# ==================================================


def validar_csv(archivo, nombre):
    if archivo is None:
        raise ValueError(f"Selecciona el archivo {nombre}.")

    if not archivo.name.lower().endswith(".csv"):
        raise ValueError(f"El archivo {nombre} debe ser CSV.")

    if archivo.size == 0:
        raise ValueError(f"El archivo {nombre} está vacío.")

    if archivo.size > MAX_CSV_BYTES:
        raise ValueError(f"El archivo {nombre} supera los 25 MiB.")


# ==================================================
# Generación de hashes SHA-256
# ==================================================


def hash_archivo_cargado(archivo):
    digest = hashlib.sha256()
    archivo.seek(0)

    for fragmento in archivo.chunks():
        digest.update(fragmento)

    archivo.seek(0)
    return digest.hexdigest()


def hash_archivo_disco(ruta):
    digest = hashlib.sha256()

    with ruta.open("rb") as entrada:
        for bloque in iter(lambda: entrada.read(1024 * 1024), b""):
            digest.update(bloque)

    return digest.hexdigest()


# ==================================================
# Procesamiento de resultados
# ==================================================


def distribucion_diaria(df):
    temporal = pd.DataFrame(
        {
            "fecha": df["fecha_utc"].dt.strftime("%Y-%m-%d"),
            "prediccion": df["prediccion"],
        }
    )

    agrupado = temporal.groupby("fecha")["prediccion"].agg(total="size", fallas="sum").reset_index()

    return [
        {
            "fecha": str(f.fecha),
            "total": int(f.total),
            "fallas": int(f.fallas),
            "normales": int(f.total - f.fallas),
        }
        for f in agrupado.itertuples(index=False)
    ]


def serializar_muestra(df, limite=50):
    return [
        {
            "timestamp": int(f.timestamp),
            "fecha_utc": f.fecha_utc.isoformat(),
            "probabilidad_falla": round(float(f.probabilidad_falla), 6),
            "prediccion": int(f.prediccion),
            "clasificacion": str(f.clasificacion),
        }
        for f in df.head(limite).itertuples(index=False)
    ]


# ==================================================
# Almacenamiento del CSV completo
# ==================================================


def guardar_csv_predicciones(df):
    destino = Path(settings.MEDIA_ROOT) / "sofi"
    destino.mkdir(parents=True, exist_ok=True)

    ruta = destino / f"{uuid.uuid4().hex}.csv"
    temporal = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            suffix=".tmp",
            dir=destino,
            delete=False,
        ) as salida:
            temporal = Path(salida.name)
            df.to_csv(salida, index=False)

        os.replace(temporal, ruta)
        return ruta, hash_archivo_disco(ruta)

    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)


# ==================================================
# Consultas de análisis guardados
# ==================================================


def respuesta_analisis(registro):
    datos = registro.resultados or {}

    return {
        "analisis_id": str(registro.pk),
        "fecha_creacion": registro.fecha_creacion.isoformat(),
        "resumen": datos.get("resumen", {}),
        "distribucion_diaria": datos.get("distribucion_diaria", []),
        "archivos": datos.get("archivos", {}),
        "blockchain": {
            "registrado": registro.indice_blockchain is not None,
            "indice": registro.indice_blockchain,
            "hash": registro.hash_blockchain or None,
        },
    }


def cargar_registro(analisis_id):
    if not ObjectId.is_valid(analisis_id):
        return None

    return Analisis.objects.filter(
        pk=ObjectId(analisis_id),
        tipo=Analisis.Tipo.SOFI,
        estado=Analisis.Estado.COMPLETADO,
    ).first()


def ruta_csv_segura(registro):
    raiz = Path(settings.MEDIA_ROOT).resolve()
    ruta = (raiz / registro.archivo_resultado).resolve()

    if not ruta.is_relative_to(raiz / "sofi"):
        raise ValueError("Ruta de resultado inválida.")

    if ruta.suffix.lower() != ".csv":
        raise ValueError("El archivo de resultado no es CSV.")

    if not ruta.is_file():
        raise FileNotFoundError("No se encontró el CSV del análisis en el servidor.")

    return ruta


# ==================================================
# Integración con blockchain simulado
# ==================================================


def verificar_cadena_valida(resultado):
    if isinstance(resultado, bool):
        return resultado

    if isinstance(resultado, (list, tuple)):
        return bool(resultado[0]) if resultado else False

    if isinstance(resultado, dict):
        for clave in (
            "valida",
            "valido",
            "es_valida",
            "valid",
            "cadena_valida",
        ):
            if clave in resultado:
                return resultado[clave] is True

    return False


def agregar_blockchain_sofi(registro, hash_resultado):
    from src.blockchain.registro_blockchain import RegistroBlockchain

    with BLOQUEO_BLOCKCHAIN:
        cadena = RegistroBlockchain()

        if not verificar_cadena_valida(cadena.verificar_cadena()):
            raise RuntimeError("La cadena blockchain no pasó la verificación.")

        bloque = cadena.agregar_bloque(
            tipo="SOFI",
            datos={
                "origen": "FailNet web",
                "analisis_id": str(registro.pk),
                "sha256_entrada": registro.sha256_archivo,
                "sha256_resultado": hash_resultado,
                "registros": registro.total_registros,
            },
        )

        if not isinstance(bloque, dict):
            bloques = cadena.obtener_bloques()
            bloque = bloques[-1] if bloques else None

        if not isinstance(bloque, dict) or not bloque.get("hash") or bloque.get("indice") is None:
            raise RuntimeError("No se pudo identificar el bloque generado.")

        registro.indice_blockchain = int(bloque["indice"])
        registro.hash_blockchain = str(bloque["hash"])

        registro.save(
            update_fields=[
                "indice_blockchain",
                "hash_blockchain",
                "fecha_actualizacion",
            ]
        )


# ==================================================
# Endpoint principal: ejecutar SOFI
# ==================================================


@require_POST
def analizar_archivos_sofi(request):
    entrada_i = request.FILES.get("switch_i")
    entrada_ii = request.FILES.get("switch_ii")

    try:
        validar_csv(entrada_i, "CoreSwitch-I")
        validar_csv(entrada_ii, "CoreSwitch-II")

        huella_i = hash_archivo_cargado(entrada_i)
        huella_ii = hash_archivo_cargado(entrada_ii)

        huella_entrada = hashlib.sha256(f"{huella_i}:{huella_ii}".encode()).hexdigest()

        # Ejecutar el modelo SOFI existente.
        calculo = analizar_sofi(entrada_i, entrada_ii)

        predicciones = calculo["predicciones"]
        resumen = calculo["resumen"]
        dias = distribucion_diaria(predicciones)

        # Guardar todas las predicciones en CSV.
        ruta_csv, huella_salida = guardar_csv_predicciones(predicciones)

        relativa = ruta_csv.relative_to(Path(settings.MEDIA_ROOT)).as_posix()

        # Guardar resumen e información en Atlas.
        try:
            registro = Analisis.objects.create(
                tipo=Analisis.Tipo.SOFI,
                estado=Analisis.Estado.COMPLETADO,
                nombre_archivo=(f"{entrada_i.name[:120]} | {entrada_ii.name[:120]}"),
                sha256_archivo=huella_entrada,
                total_registros=len(predicciones),
                archivo_resultado=relativa,
                resultados={
                    "resumen": resumen,
                    "distribucion_diaria": dias,
                    "archivos": {
                        "switch_i": entrada_i.name,
                        "switch_ii": entrada_ii.name,
                    },
                    "sha256_switch_i": huella_i,
                    "sha256_switch_ii": huella_ii,
                    "sha256_resultado": huella_salida,
                },
            )

        except Exception:
            ruta_csv.unlink(missing_ok=True)
            raise

        advertencia = None

        try:
            agregar_blockchain_sofi(registro, huella_salida)

        except Exception:
            logger.exception("SOFI guardado en Atlas, pero no se pudo registrar en blockchain.")
            advertencia = "Análisis guardado; pendiente registrar su integridad en blockchain."

        respuesta = respuesta_analisis(registro)

        respuesta.update(
            {
                "proyecto": "FailNet",
                "modulo": "SOFI",
                "total_predicciones": len(predicciones),
                "total_fallas": int(resumen["fallas"]),
                "primeras_predicciones": serializar_muestra(predicciones),
                "primeras_fallas": serializar_muestra(
                    predicciones[predicciones["prediccion"] == 1]
                ),
            }
        )

        if advertencia:
            respuesta["advertencia"] = advertencia

        return JsonResponse(respuesta, status=200)

    except (
        ValueError,
        UnicodeError,
        pd.errors.ParserError,
    ) as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    except Exception:
        logger.exception("Error al ejecutar el análisis SOFI")
        return JsonResponse({"error": "No se pudo completar el análisis SOFI."}, status=500)


# ==================================================
# Endpoint: recuperar análisis
# ==================================================


@require_GET
def obtener_analisis_sofi(request, analisis_id):
    registro = cargar_registro(analisis_id)

    if registro is None:
        return JsonResponse({"error": "Análisis SOFI no encontrado."}, status=404)

    return JsonResponse(respuesta_analisis(registro))


# ==================================================
# Endpoint: historial de SOFI
# ==================================================


@require_GET
def listar_analisis_sofi(request):
    registros = Analisis.objects.filter(
        tipo=Analisis.Tipo.SOFI,
        estado=Analisis.Estado.COMPLETADO,
    ).order_by("-fecha_creacion")[:15]

    return JsonResponse({"analisis": [respuesta_analisis(registro) for registro in registros]})


# ==================================================
# Endpoint: paginación de predicciones
# ==================================================


@require_GET
def paginar_predicciones_sofi(request, analisis_id):
    registro = cargar_registro(analisis_id)

    if registro is None:
        return JsonResponse({"error": "Análisis SOFI no encontrado."}, status=404)

    try:
        vista = request.GET.get("vista", "todas")

        if vista not in ("todas", "fallas", "normales"):
            raise ValueError("Filtro de predicciones inválido.")

        pagina = int(request.GET.get("pagina", "1"))
        tamano = int(request.GET.get("tamano", "25"))

        if pagina < 1 or tamano not in TAMANOS_PAGINA:
            raise ValueError("Página o tamaño de página inválidos.")

        ruta = ruta_csv_segura(registro)

        filas = []
        total = 0
        principio = (pagina - 1) * tamano

        with ruta.open(
            "r",
            newline="",
            encoding="utf-8-sig",
        ) as archivo:
            for fila in csv.DictReader(archivo):
                prediccion = int(fila["prediccion"])

                if vista == "fallas" and prediccion != 1:
                    continue

                if vista == "normales" and prediccion != 0:
                    continue

                if principio <= total < principio + tamano:
                    filas.append(
                        {
                            "timestamp": int(fila["timestamp"]),
                            "fecha_utc": fila["fecha_utc"],
                            "probabilidad_falla": float(fila["probabilidad_falla"]),
                            "prediccion": prediccion,
                            "clasificacion": fila["clasificacion"],
                        }
                    )

                total += 1

        paginas = max(1, (total + tamano - 1) // tamano)

        if pagina > paginas:
            raise ValueError("La página solicitada no existe.")

        return JsonResponse(
            {
                "filas": filas,
                "pagina": pagina,
                "tamano": tamano,
                "total": total,
                "paginas": paginas,
                "vista": vista,
            }
        )

    except (ValueError, TypeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    except FileNotFoundError as exc:
        return JsonResponse({"error": str(exc)}, status=404)

    except Exception:
        logger.exception("Error al consultar predicciones SOFI")
        return JsonResponse({"error": "No se pudieron consultar las predicciones."}, status=500)


# ==================================================
# Endpoint: descarga CSV completo
# ==================================================


@require_GET
def descargar_csv_sofi(request, analisis_id):
    registro = cargar_registro(analisis_id)

    if registro is None:
        return JsonResponse({"error": "Análisis SOFI no encontrado."}, status=404)

    try:
        ruta = ruta_csv_segura(registro)

        huella_guardada = (registro.resultados or {}).get("sha256_resultado")

        if not huella_guardada or hash_archivo_disco(ruta) != huella_guardada:
            logger.error(
                "Integridad inválida del CSV: %s",
                analisis_id,
            )

            return JsonResponse(
                {"error": ("El archivo no pasó la verificación de integridad.")},
                status=409,
            )

        return FileResponse(
            ruta.open("rb"),
            as_attachment=True,
            filename=f"failnet_sofi_{analisis_id}.csv",
            content_type="text/csv",
        )

    except FileNotFoundError as exc:
        return JsonResponse({"error": str(exc)}, status=404)

    except Exception:
        logger.exception("Error descargando CSV SOFI")
        return JsonResponse({"error": "No se pudo descargar el CSV."}, status=500)


# ==================================================
# Fin de lógica sofi
# ==================================================


# ==================================================
# Inicio de lógica twin
# ==================================================

MAX_TWIN_CSV_BYTES = 120 * 1024 * 1024
NIVELES_TWIN = {"todas", "0", "1", "2", "3", "4"}


def validar_csv_twin(archivo):
    if archivo is None:
        raise ValueError("Selecciona un archivo CSV de Digital Twin.")
    if not archivo.name.lower().endswith(".csv"):
        raise ValueError("El archivo debe tener extensión .csv.")
    if archivo.size <= 0:
        raise ValueError("El archivo CSV está vacío.")
    if archivo.size > MAX_TWIN_CSV_BYTES:
        raise ValueError("El CSV supera el límite de 120 MiB.")


def ruta_twin_csv(registro):
    raiz = (Path(settings.MEDIA_ROOT) / "twin").resolve()
    ruta = (Path(settings.MEDIA_ROOT) / registro.archivo_resultado).resolve()
    if not ruta.is_relative_to(raiz) or ruta.suffix != ".csv":
        raise ValueError("Ruta de CSV inválida.")
    if not ruta.is_file():
        raise FileNotFoundError("No se encontró el archivo del análisis.")
    return ruta


def _indice_twin(ruta, vista):
    return ruta.with_suffix(f".{vista}.idx")


def crear_indices_twin(ruta):
    import struct
    from contextlib import ExitStack

    temporal = {}
    finales = []
    total = 0
    conteo = {v: 0 for v in NIVELES_TWIN}
    try:
        with ExitStack() as pila:
            salidas = {}
            for vista in sorted(NIVELES_TWIN):
                destino = _indice_twin(ruta, vista)
                parcial = destino.with_name(f".{destino.name}.{uuid.uuid4().hex}.tmp")
                temporal[vista] = parcial
                salidas[vista] = pila.enter_context(parcial.open("wb"))

            entrada = pila.enter_context(ruta.open("r", encoding="utf-8-sig", newline=""))
            lector = csv.DictReader(iter(entrada.readline, ""))
            if not lector.fieldnames or "nivel" not in lector.fieldnames:
                raise ValueError("El CSV generado no contiene la columna nivel.")

            while True:
                posicion = entrada.tell()
                try:
                    fila = next(lector)
                except StopIteration:
                    break
                nivel = str(int(fila["nivel"]))
                if nivel not in NIVELES_TWIN - {"todas"}:
                    raise ValueError(f"Nivel de tráfico inválido: {nivel}")
                posicion_binaria = struct.pack("<Q", posicion)
                for vista in ("todas", nivel):
                    salidas[vista].write(posicion_binaria)
                    conteo[vista] += 1
                total += 1

        for vista, parcial in temporal.items():
            destino = _indice_twin(ruta, vista)
            os.replace(parcial, destino)
            finales.append(destino)
        return total
    except Exception:
        for archivo in list(temporal.values()) + finales:
            archivo.unlink(missing_ok=True)
        raise


def serializar_twin(registro):
    datos = registro.resultados or {}
    return {
        "analisis_id": str(registro.pk),
        "fecha_creacion": registro.fecha_creacion.isoformat(),
        "resumen": datos.get("resumen", {}),
        "routers": datos.get("routers", []),
        "distribucion_diaria": datos.get("distribucion_diaria", []),
        "nombre_archivo": registro.nombre_archivo,
        "blockchain": {
            "registrado": registro.indice_blockchain is not None,
            "indice": registro.indice_blockchain,
            "hash": registro.hash_blockchain or None,
        },
    }


def obtener_registro_twin(analisis_id):
    if not ObjectId.is_valid(analisis_id):
        return None
    return Analisis.objects.filter(
        pk=ObjectId(analisis_id),
        tipo=Analisis.Tipo.DIGITAL_TWIN,
        estado=Analisis.Estado.COMPLETADO,
    ).first()


def agregar_blockchain_twin(registro, hash_resultado):
    # Mismo blockchain local que SOFI, no crea una cadena aparte.
    # Respeta el import que ya corregiste y probaste en SOFI.
    from src.blockchain.registro_blockchain import RegistroBlockchain

    with BLOQUEO_BLOCKCHAIN:
        cadena = RegistroBlockchain()
        if not verificar_cadena_valida(cadena.verificar_cadena()):
            raise RuntimeError("El blockchain existente no superó la verificación.")
        bloque = cadena.agregar_bloque(
            tipo="DIGITAL_TWIN",
            datos={
                "origen": "FailNet web",
                "analisis_id": str(registro.pk),
                "sha256_entrada": registro.sha256_archivo,
                "sha256_resultado": hash_resultado,
                "registros": registro.total_registros,
            },
        )
        if not isinstance(bloque, dict):
            bloques = cadena.obtener_bloques()
            bloque = bloques[-1] if bloques else None
        if not isinstance(bloque, dict) or not bloque.get("hash") or bloque.get("indice") is None:
            raise RuntimeError("No se pudo obtener el bloque de Digital Twin.")
        registro.indice_blockchain = int(bloque["indice"])
        registro.hash_blockchain = str(bloque["hash"])
        registro.save(
            update_fields=[
                "indice_blockchain",
                "hash_blockchain",
                "fecha_actualizacion",
            ]
        )


@require_POST
def analizar_archivo_twin(request):
    archivo = request.FILES.get("archivo")
    ruta_temporal = None
    ruta_csv = None
    registro = None
    try:
        validar_csv_twin(archivo)
        sha_entrada = hash_archivo_cargado(archivo)
        archivo.seek(0)

        directorio = Path(settings.MEDIA_ROOT) / "twin"
        directorio.mkdir(parents=True, exist_ok=True)
        nombre = uuid.uuid4().hex
        ruta_temporal = directorio / f".{nombre}.en_proceso"
        ruta_csv = directorio / f"{nombre}.csv"

        # Analiza por lotes de 20,000 filas y escribe el resultado en disco.
        calculo = analizar_twin(archivo, salida_csv=ruta_temporal, tamano_lote=20000)
        os.replace(ruta_temporal, ruta_csv)
        ruta_temporal = None

        total_indice = crear_indices_twin(ruta_csv)
        resumen = calculo["resumen"]
        if total_indice != int(resumen["total_registros"]):
            raise RuntimeError("El índice CSV no coincide con los registros predichos.")
        sha_salida = hash_archivo_disco(ruta_csv)
        ruta_relativa = ruta_csv.relative_to(Path(settings.MEDIA_ROOT)).as_posix()

        registro = Analisis.objects.create(
            tipo=Analisis.Tipo.DIGITAL_TWIN,
            estado=Analisis.Estado.COMPLETADO,
            nombre_archivo=archivo.name[:240],
            sha256_archivo=sha_entrada,
            total_registros=total_indice,
            archivo_resultado=ruta_relativa,
            resultados={
                "resumen": resumen,
                "routers": calculo["routers"],
                "distribucion_diaria": calculo["distribucion_diaria"],
                "sha256_resultado": sha_salida,
            },
        )

    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        # Ante error no se guardan resultados parciales.
        if ruta_temporal:
            ruta_temporal.unlink(missing_ok=True)
        if ruta_csv and registro is None:
            ruta_csv.unlink(missing_ok=True)
            for vista in NIVELES_TWIN:
                _indice_twin(ruta_csv, vista).unlink(missing_ok=True)
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception:
        logger.exception("Falló la inferencia Digital Twin")
        if ruta_temporal:
            ruta_temporal.unlink(missing_ok=True)
        if ruta_csv and registro is None:
            ruta_csv.unlink(missing_ok=True)
            for vista in NIVELES_TWIN:
                _indice_twin(ruta_csv, vista).unlink(missing_ok=True)
        return JsonResponse({"error": "No se pudo completar el análisis Digital Twin."}, status=500)

    advertencia = None
    try:
        agregar_blockchain_twin(registro, sha_salida)
    except Exception:
        logger.exception("Digital Twin guardado en Atlas, pero falló el registro blockchain")
        advertencia = "Análisis guardado; no se pudo registrar su integridad en blockchain."

    respuesta = serializar_twin(registro)
    if advertencia:
        respuesta["advertencia"] = advertencia
    return JsonResponse(respuesta, status=200)


@require_GET
def listar_analisis_twin(request):
    registros = Analisis.objects.filter(
        tipo=Analisis.Tipo.DIGITAL_TWIN,
        estado=Analisis.Estado.COMPLETADO,
    ).order_by("-fecha_creacion")[:15]
    return JsonResponse({"analisis": [serializar_twin(r) for r in registros]})


@require_GET
def obtener_analisis_twin(request, analisis_id):
    registro = obtener_registro_twin(analisis_id)
    if registro is None:
        return JsonResponse({"error": "Análisis Digital Twin no encontrado."}, status=404)
    return JsonResponse(serializar_twin(registro))


@require_GET
def paginar_predicciones_twin(request, analisis_id):
    import struct

    registro = obtener_registro_twin(analisis_id)
    if registro is None:
        return JsonResponse({"error": "Análisis Digital Twin no encontrado."}, status=404)
    try:
        vista = request.GET.get("vista", "todas")
        pagina = int(request.GET.get("pagina", "1"))
        tamano = int(request.GET.get("tamano", "25"))
        if vista not in NIVELES_TWIN:
            raise ValueError("Filtro de nivel inválido.")
        if pagina < 1 or tamano not in (25, 50, 100):
            raise ValueError("Página o tamaño de página inválido.")

        ruta = ruta_twin_csv(registro)
        indice = _indice_twin(ruta, vista)
        if not indice.is_file():
            raise FileNotFoundError("No se encontró el índice de resultados.")
        bytes_indice = indice.stat().st_size
        if bytes_indice % 8:
            raise ValueError("El índice de predicciones está dañado.")
        total = bytes_indice // 8
        paginas = max(1, (total + tamano - 1) // tamano)
        if pagina > paginas:
            raise ValueError("La página solicitada no existe.")
        inicio = (pagina - 1) * tamano
        cantidad = min(tamano, total - inicio)
        filas = []

        with (
            indice.open("rb") as punteros,
            ruta.open("r", encoding="utf-8-sig", newline="") as entrada,
        ):
            punteros.seek(inicio * 8)
            datos = punteros.read(cantidad * 8)
            if len(datos) != cantidad * 8:
                raise ValueError("No se pudo leer el índice de predicciones.")
            posiciones = struct.unpack(f"<{cantidad}Q", datos) if cantidad else ()
            for posicion in posiciones:
                entrada.seek(posicion)
                valores = next(csv.reader(iter(entrada.readline, "")))
                if len(valores) != 6:
                    raise ValueError("Fila del CSV de resultados inválida.")
                timestamp, fecha, router, nivel, rango, confianza = valores
                filas.append(
                    {
                        "timestamp": int(timestamp),
                        "fecha_utc": fecha,
                        "router": router,
                        "nivel": int(nivel),
                        "rango_trafico": rango,
                        "confianza_modelo": float(confianza),
                    }
                )

        return JsonResponse(
            {
                "filas": filas,
                "pagina": pagina,
                "tamano": tamano,
                "total": total,
                "paginas": paginas,
                "vista": vista,
            }
        )
    except (ValueError, TypeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except FileNotFoundError as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except Exception:
        logger.exception("Error consultando resultados paginados de Digital Twin")
        return JsonResponse({"error": "No se pudieron cargar los resultados."}, status=500)


@require_GET
def descargar_csv_twin(request, analisis_id):
    registro = obtener_registro_twin(analisis_id)
    if registro is None:
        return JsonResponse({"error": "Análisis Digital Twin no encontrado."}, status=404)
    try:
        ruta = ruta_twin_csv(registro)
        esperado = (registro.resultados or {}).get("sha256_resultado")
        if not esperado or hash_archivo_disco(ruta) != esperado:
            return JsonResponse({"error": "El CSV no superó la verificación SHA-256."}, status=409)
        return FileResponse(
            ruta.open("rb"),
            as_attachment=True,
            filename=f"failnet_twin_{analisis_id}.csv",
            content_type="text/csv",
        )
    except FileNotFoundError as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except Exception:
        logger.exception("Error descargando resultados Digital Twin")
        return JsonResponse({"error": "No se pudo descargar el CSV."}, status=500)


# ==================================================
# Fin de lógica twin
# ==================================================


# ==================================================
# Inicio de lógica pnl
# ==================================================

MAX_PNL_CARACTERES = 8000
MAX_PNL_JSON_BYTES = 40000
CATEGORIAS_PNL = {"conectividad", "interfaces", "rendimiento", "servicios"}


def _registro_pnl(analisis_id):
    if not ObjectId.is_valid(analisis_id):
        return None
    return Analisis.objects.filter(
        pk=ObjectId(analisis_id),
        tipo=Analisis.Tipo.PNL,
        estado=Analisis.Estado.COMPLETADO,
    ).first()


def _hash_resultado_pnl(categoria, resumen, entidades):
    contenido = json.dumps(
        {"categoria": categoria, "resumen": resumen, "entidades": entidades},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def _respuesta_pnl(registro, incluir_texto=True):
    datos = registro.resultados or {}
    respuesta = {
        "analisis_id": str(registro.pk),
        "fecha_creacion": registro.fecha_creacion.isoformat(),
        "categoria": datos.get("categoria", ""),
        "resumen": registro.resumen_texto or "",
        "entidades": datos.get("entidades", {}),
        "blockchain": {
            "registrado": registro.indice_blockchain is not None,
            "indice": registro.indice_blockchain,
            "hash": registro.hash_blockchain or None,
        },
    }
    if incluir_texto:
        respuesta["reporte_original"] = registro.texto_reporte or ""
    else:
        respuesta["vista_previa"] = (registro.texto_reporte or "")[:160]
    return respuesta


def _registrar_blockchain_pnl(registro, sha_resultado):
    # Se conecta a la cadena original; nunca se crea otra independiente.
    from src.blockchain.registro_blockchain import RegistroBlockchain

    with BLOQUEO_BLOCKCHAIN:
        cadena = RegistroBlockchain()
        if not verificar_cadena_valida(cadena.verificar_cadena()):
            raise RuntimeError("La cadena de integridad no superó la verificación.")
        bloque = cadena.agregar_bloque(
            tipo="PNL",
            datos={
                "origen": "FailNet web",
                "analisis_id": str(registro.pk),
                "sha256_entrada": registro.sha256_archivo,
                "sha256_resultado": sha_resultado,
                "registros": 1,
            },
        )
        if not isinstance(bloque, dict):
            bloques = cadena.obtener_bloques()
            bloque = bloques[-1] if bloques else None
        if not isinstance(bloque, dict) or not bloque.get("hash") or bloque.get("indice") is None:
            raise RuntimeError("No se pudo identificar el bloque PNL.")
        registro.indice_blockchain = int(bloque["indice"])
        registro.hash_blockchain = str(bloque["hash"])
        registro.save(
            update_fields=[
                "indice_blockchain",
                "hash_blockchain",
                "fecha_actualizacion",
            ]
        )


@require_POST
def analizar_texto_pnl(request):
    # Mantiene CSRF habilitado; React envía X-CSRFToken.
    if request.content_type != "application/json":
        return JsonResponse({"error": "Envía un JSON con el campo texto."}, status=415)
    if len(request.body) > MAX_PNL_JSON_BYTES:
        return JsonResponse({"error": "El reporte excede el tamaño permitido."}, status=413)
    try:
        cuerpo = json.loads(request.body)
        if not isinstance(cuerpo, dict):
            raise ValueError("El cuerpo debe ser un objeto JSON.")
        texto = cuerpo.get("texto")
        if not isinstance(texto, str):
            raise ValueError("El campo texto debe ser una cadena.")
        texto = texto.strip()
        if len(texto) < 3:
            raise ValueError("Escribe un reporte de al menos 3 caracteres.")
        if len(texto) > MAX_PNL_CARACTERES:
            raise ValueError(f"El reporte supera los {MAX_PNL_CARACTERES} caracteres.")
        # Evita el costo excesivo de TF-IDF para miles de micro-oraciones.
        if texto.count(".") + texto.count("!") + texto.count("?") > 200:
            raise ValueError("El reporte contiene demasiadas oraciones.")
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    try:
        # Reutilizamos las tres funciones originales, desde un solo punto de entrada.
        from src.nlp.analizar_reporte import analizar_reporte

        resultado = analizar_reporte(texto)
        categoria = resultado["categoria"]
        entidades = resultado["entidades"]
        resumen = resultado["resumen"]
        if (
            categoria not in CATEGORIAS_PNL
            or not isinstance(resumen, str)
            or not isinstance(entidades, dict)
        ):
            raise ValueError("El analizador devolvió un resultado inesperado.")

        sha_entrada = hashlib.sha256(texto.encode("utf-8")).hexdigest()
        sha_resultado = _hash_resultado_pnl(categoria, resumen, entidades)
        registro = Analisis.objects.create(
            tipo=Analisis.Tipo.PNL,
            estado=Analisis.Estado.COMPLETADO,
            nombre_archivo="Reporte de texto",
            sha256_archivo=sha_entrada,
            total_registros=1,
            archivo_resultado="",
            texto_reporte=texto,
            resumen_texto=resumen,
            resultados={
                "categoria": categoria,
                "entidades": entidades,
                "sha256_resultado": sha_resultado,
                "tipo_resumen": "extractivo",
            },
        )
    except Exception:
        logger.exception("Error al analizar o guardar reporte PNL")
        return JsonResponse({"error": "No se pudo analizar o guardar el reporte PNL."}, status=500)

    advertencia = None
    try:
        _registrar_blockchain_pnl(registro, sha_resultado)
    except Exception:
        logger.exception("PNL guardado en Atlas, pero falló el registro blockchain")
        advertencia = "Análisis guardado; no se pudo registrar su integridad en blockchain."

    respuesta = _respuesta_pnl(registro)
    if advertencia:
        respuesta["advertencia"] = advertencia
    return JsonResponse(respuesta, status=200)


@require_GET
def historial_pnl(request):
    registros = Analisis.objects.filter(
        tipo=Analisis.Tipo.PNL,
        estado=Analisis.Estado.COMPLETADO,
    ).order_by("-fecha_creacion")[:15]
    return JsonResponse({"analisis": [_respuesta_pnl(r, incluir_texto=False) for r in registros]})


@require_GET
def detalle_pnl(request, analisis_id):
    registro = _registro_pnl(analisis_id)
    if registro is None:
        return JsonResponse({"error": "Análisis PNL no encontrado."}, status=404)
    return JsonResponse(_respuesta_pnl(registro))


@require_GET
def descargar_pnl(request, analisis_id):
    registro = _registro_pnl(analisis_id)
    if registro is None:
        return JsonResponse({"error": "Análisis PNL no encontrado."}, status=404)
    datos = registro.resultados or {}
    texto = registro.texto_reporte or ""
    categoria = datos.get("categoria", "")
    resumen = registro.resumen_texto or ""
    entidades = datos.get("entidades", {})
    if hashlib.sha256(
        texto.encode("utf-8")
    ).hexdigest() != registro.sha256_archivo or _hash_resultado_pnl(
        categoria, resumen, entidades
    ) != datos.get("sha256_resultado"):
        return JsonResponse({"error": "El análisis no pasó la verificación SHA-256."}, status=409)
    documento = "\n".join(
        [
            "FAILNET - REPORTE PNL",
            f"Identificador: {registro.pk}",
            f"Fecha: {registro.fecha_creacion.isoformat()}",
            f"Categoría: {categoria}",
            "",
            "REPORTE ORIGINAL",
            texto,
            "",
            "RESUMEN EXTRACTIVO",
            resumen,
            "",
            "ENTIDADES DETECTADAS",
            json.dumps(entidades, indent=2, ensure_ascii=False),
            "",
        ]
    )
    respuesta = HttpResponse(documento, content_type="text/plain; charset=utf-8")
    respuesta["Content-Disposition"] = f'attachment; filename="failnet_pnl_{analisis_id}.txt"'
    return respuesta


# ==================================================
# Fin de lógica pnl
# ==================================================


# ==================================================
# Inicio de lógica blockchain
# ==================================================


def _bloques_actuales():
    ruta = Path(settings.BASE_DIR) / "data" / "blockchain" / "cadena.json"
    with ruta.open("r", encoding="utf-8-sig") as archivo:
        bloques = json.load(archivo)
    if not isinstance(bloques, list) or any(not isinstance(b, dict) for b in bloques):
        raise ValueError("cadena.json debe contener una lista de bloques JSON.")
    return None, bloques


def _verificar_cadena_detallada(bloques):
    incidencias = []
    if not bloques:
        return (
            False,
            "La cadena no contiene bloques.",
            [
                {
                    "indice": None,
                    "tipo": "estructura",
                    "mensaje": "No hay bloques registrados.",
                }
            ],
        )

    for posicion, bloque in enumerate(bloques):
        indice = bloque.get("indice", posicion)

        if bloque.get("indice") != posicion:
            incidencias.append(
                {
                    "indice": indice,
                    "tipo": "indice",
                    "mensaje": f"El bloque ocupa la posición {posicion}, pero tiene índice {indice}.",
                }
            )

        if posicion == 0:
            if bloque.get("hash_anterior") != "0" * 64:
                incidencias.append(
                    {
                        "indice": indice,
                        "tipo": "enlace",
                        "mensaje": "El bloque génesis tiene una referencia anterior incorrecta.",
                    }
                )
        elif bloque.get("hash_anterior") != bloques[posicion - 1].get("hash"):
            incidencias.append(
                {
                    "indice": indice,
                    "tipo": "enlace",
                    "mensaje": "El hash anterior no coincide con el hash almacenado del bloque previo.",
                }
            )

        try:
            calculado = RegistroBlockchain.calcular_hash(bloque)
        except Exception:
            logger.exception("Error recalculando SHA-256 del bloque %s", indice)
            incidencias.append(
                {
                    "indice": indice,
                    "tipo": "hash",
                    "mensaje": "No se pudo recalcular el hash de este bloque.",
                }
            )
            continue

        if bloque.get("hash") != calculado:
            incidencias.append(
                {
                    "indice": indice,
                    "tipo": "hash",
                    "mensaje": "El hash almacenado no coincide con el contenido del bloque.",
                }
            )

    if incidencias:
        return (
            False,
            f"Se detectaron {len(incidencias)} problemas de integridad en la cadena.",
            incidencias,
        )
    return True, "Todos los hashes y enlaces son correctos.", []


def _datos_publicos_bloque(bloque):
    datos = bloque.get("datos") if isinstance(bloque.get("datos"), dict) else {}
    permitidas = (
        "origen",
        "analisis_id",
        "sha256_entrada",
        "sha256_resultado",
        "registros",
        "demo_id",
    )
    return {
        k: datos[k]
        for k in permitidas
        if k in datos and isinstance(datos[k], (str, int, float, bool))
    }


def _serializar_bloque(block):
    return {
        "indice": block.get("indice"),
        "fecha": block.get("fecha"),
        "tipo": str(block.get("tipo", "desconocido")),
        "hash": str(block.get("hash", "")),
        "hash_anterior": str(block.get("hash_anterior", "")),
        "datos": _datos_publicos_bloque(block),
    }


def _huella_archivo_blockchain(ruta):
    huella = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for fragmento in iter(lambda: archivo.read(1024 * 1024), b""):
            huella.update(fragmento)
    return huella.hexdigest()


def _auditar_bloque_con_atlas(bloque, documentos):
    """Verifica el contenido original vinculado al hash del bloque."""
    datos = bloque.get("datos") or {}
    analisis_id = datos.get("analisis_id")
    indice = bloque.get("indice")
    if analisis_id is None:
        return {
            "indice": indice,
            "estado": "historico",
            "mensaje": "Bloque histórico sin identificador de análisis de Atlas.",
        }
    if not isinstance(analisis_id, str) or not ObjectId.is_valid(analisis_id):
        return {
            "indice": indice,
            "estado": "error",
            "mensaje": "Identificador de análisis malformado en el bloque.",
        }

    registro = documentos.get(analisis_id)
    if registro is None:
        return {
            "indice": indice,
            "estado": "error",
            "mensaje": "El análisis vinculado ya no existe en Atlas.",
        }

    if registro.indice_blockchain != indice or registro.hash_blockchain != bloque.get("hash"):
        return {
            "indice": indice,
            "estado": "error",
            "mensaje": "La referencia de Atlas no coincide con el bloque.",
        }

    if not datos.get("sha256_entrada") or registro.sha256_archivo != datos.get("sha256_entrada"):
        return {
            "indice": indice,
            "estado": "error",
            "mensaje": "El hash de entrada no coincide con Atlas.",
        }

    resultado = registro.resultados or {}
    esperado = resultado.get("sha256_resultado")
    if not esperado or esperado != datos.get("sha256_resultado"):
        return {
            "indice": indice,
            "estado": "error",
            "mensaje": "El hash del resultado no coincide con Atlas.",
        }

    if registro.tipo == Analisis.Tipo.PNL:
        texto = registro.texto_reporte or ""
        if hashlib.sha256(texto.encode("utf-8")).hexdigest() != registro.sha256_archivo:
            return {
                "indice": indice,
                "estado": "error",
                "mensaje": "El reporte original PNL fue modificado.",
            }
        contenido = json.dumps(
            {
                "categoria": resultado.get("categoria", ""),
                "resumen": registro.resumen_texto or "",
                "entidades": resultado.get("entidades", {}),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        actual = hashlib.sha256(contenido.encode("utf-8")).hexdigest()
    elif registro.tipo in (Analisis.Tipo.SOFI, Analisis.Tipo.DIGITAL_TWIN):
        raiz = Path(settings.MEDIA_ROOT).resolve()
        ruta = (raiz / str(registro.archivo_resultado or "")).resolve()
        if not ruta.is_relative_to(raiz) or ruta.suffix.lower() != ".csv" or not ruta.is_file():
            return {
                "indice": indice,
                "estado": "error",
                "mensaje": "El CSV de resultados falta o su ruta es inválida.",
            }
        actual = _huella_archivo_blockchain(ruta)
    else:
        return {
            "indice": indice,
            "estado": "error",
            "mensaje": "Tipo de análisis desconocido.",
        }

    if actual != esperado:
        return {
            "indice": indice,
            "estado": "error",
            "mensaje": "El resultado almacenado ya no coincide con SHA-256.",
        }

    return {
        "indice": indice,
        "estado": "integro",
        "mensaje": "Coinciden blockchain, Atlas y resultado original.",
    }


@require_GET
def obtener_estado_blockchain(request):
    try:
        with BLOQUEO_BLOCKCHAIN:
            _, bloques = _bloques_actuales()
            bloques = [_serializar_bloque(b) for b in bloques]
        return JsonResponse(
            {
                "total_bloques": len(bloques),
                "ultimo_hash": bloques[-1]["hash"] if bloques else None,
                "bloques": list(reversed(bloques)),
                "estado": "sin_verificar",
            }
        )
    except Exception:
        logger.exception("No fue posible consultar Blockchain")
        return JsonResponse({"error": "No se pudo leer la cadena de bloques."}, status=500)


@require_POST
def verificar_integridad_blockchain(request):
    try:
        # La verificación no agrega, corrige ni elimina bloques.
        with BLOQUEO_BLOCKCHAIN:
            _, bloques = _bloques_actuales()
            valida, mensaje, errores_cadena = _verificar_cadena_detallada(bloques)
            instantanea = [dict(b) for b in bloques]

        # No declarar íntegros los resultados si la cadena ya falló.
        if not valida:
            return JsonResponse(
                {
                    "cadena": {
                        "valida": False,
                        "mensaje": mensaje,
                        "errores": errores_cadena,
                    },
                    "auditoria": {
                        "verificados": 0,
                        "errores": 0,
                        "historicos": 0,
                        "resultados": [],
                    },
                }
            )

        ids = []
        for bloque in instantanea:
            datos = bloque.get("datos") or {}
            analisis_id = datos.get("analisis_id") if isinstance(datos, dict) else None
            if isinstance(analisis_id, str) and ObjectId.is_valid(analisis_id):
                ids.append(ObjectId(analisis_id))
        documentos = {str(r.pk): r for r in Analisis.objects.filter(pk__in=ids)} if ids else {}

        auditoria = []
        for bloque in instantanea:
            try:
                auditoria.append(_auditar_bloque_con_atlas(bloque, documentos))
            except Exception:
                logger.exception("Fallo auditando bloque %s", bloque.get("indice"))
                auditoria.append(
                    {
                        "indice": bloque.get("indice"),
                        "estado": "error",
                        "mensaje": "Error al comprobar el análisis vinculado.",
                    }
                )

        return JsonResponse(
            {
                "cadena": {"valida": True, "mensaje": mensaje, "errores": []},
                "auditoria": {
                    "verificados": sum(a["estado"] == "integro" for a in auditoria),
                    "errores": sum(a["estado"] == "error" for a in auditoria),
                    "historicos": sum(a["estado"] == "historico" for a in auditoria),
                    "resultados": auditoria,
                },
            }
        )
    except Exception:
        logger.exception("Error verificando blockchain")
        return JsonResponse(
            {"error": "No se pudo verificar la cadena. Revisa el registro de Django."},
            status=500,
        )


# ==================================================
# Fin de lógica blockchain
# ==================================================
