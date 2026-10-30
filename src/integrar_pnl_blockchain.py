import json

from nlp.analizar_reporte import analizar_reporte
from blockchain.registro_blockchain import RegistroBlockchain

# ==================================================
# NETINSIGHT AI - INTEGRACIÓN PNL + BLOCKCHAIN
# ==================================================


def main():

    print("=" * 65)
    print("NETINSIGHT AI - PNL + BLOCKCHAIN")
    print("=" * 65)

    # ==============================================
    # 1. CARGAR BLOCKCHAIN
    # ==============================================

    blockchain = RegistroBlockchain()

    valido, mensaje = blockchain.verificar_cadena()

    print("\nESTADO DEL BLOCKCHAIN")
    print("Cadena válida:", valido)
    print("Resultado:", mensaje)
    print("Bloques existentes:", blockchain.obtener_total_bloques())

    if not valido:
        print("No se registrarán nuevos análisis.")
        return

    # ==============================================
    # 2. MODO INTERACTIVO
    # ==============================================

    print("\n" + "=" * 65)
    print("ANÁLISIS DE REPORTES TÉCNICOS")
    print("=" * 65)

    print("Introduce un reporte técnico de red.")
    print("Presiona ENTER sin escribir nada para salir.")

    while True:

        try:
            texto = input("\nReporte > ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nPrograma finalizado.")
            break

        if not texto:
            print("\nPrograma finalizado.")
            break

        # ==========================================
        # 3. EJECUTAR PNL
        # ==========================================

        try:
            resultado = analizar_reporte(texto)

        except (ValueError, TypeError) as error:
            print("Error en PNL:", error)
            continue

        print("\n" + "=" * 65)
        print("RESULTADO DEL ANÁLISIS PNL")
        print("=" * 65)

        print(json.dumps(resultado, indent=4, ensure_ascii=False))

        # ==========================================
        # 4. PREPARAR REGISTRO
        # ==========================================

        datos = {
            "origen": "entrada_usuario",
            "modelo": "nlp_clasificador.joblib",
            "categoria": resultado["categoria"],
            "reporte_original": (resultado["reporte_original"]),
            "entidades": resultado["entidades"],
            "resumen": resultado["resumen"],
        }

        # ==========================================
        # 5. GUARDAR EN BLOCKCHAIN
        # ==========================================

        try:
            bloque = blockchain.agregar_bloque(tipo="PNL", datos=datos)

        except (ValueError, TypeError, OSError) as error:
            print("\nNo se pudo registrar el análisis:", error)
            continue

        print("\n" + "=" * 65)
        print("REGISTRO BLOCKCHAIN")
        print("=" * 65)

        print("Bloque creado:", bloque["indice"])

        print("Tipo:", bloque["tipo"])

        print("Fecha:", bloque["fecha"])

        print("Hash SHA-256:", bloque["hash"])

        print("Hash anterior:", bloque["hash_anterior"])

        # ==========================================
        # 6. VERIFICAR INTEGRIDAD
        # ==========================================

        valido, mensaje = blockchain.verificar_cadena()

        print("\nVERIFICACIÓN FINAL")
        print("Cadena válida:", valido)
        print("Resultado:", mensaje)

        print("Total de bloques:", blockchain.obtener_total_bloques())

        if not valido:
            print("Se detectó un problema de integridad.")
            break


if __name__ == "__main__":
    main()
