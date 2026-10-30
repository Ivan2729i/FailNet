from pathlib import Path
import csv

# ==========================================
# CONFIGURACIÓN
# ==========================================

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "raw" / "nlp"

DATA.mkdir(parents=True, exist_ok=True)

# Reportes simulados para el prototipo inicial.
# Ampliaremos este conjunto antes de la
# evaluación definitiva.

reportes = {
    "conectividad": [
        "El router R1 no responde a las solicitudes de ping.",
        "Se perdió comunicación con la IP 192.168.1.10.",
        "El switch SW2 presenta pérdida de paquetes.",
        "No existe conectividad entre dos segmentos de red.",
        "El equipo no puede alcanzar la puerta de enlace.",
        "Se presentan respuestas intermitentes en ICMP.",
        "La estación de trabajo perdió acceso a la red.",
        "El router R3 muestra destinos inalcanzables.",
        "Se interrumpió la comunicación entre las VLAN.",
        "El servidor 10.0.0.5 dejó de responder a ping.",
        "Los paquetes no llegan al dispositivo remoto.",
        "Se detectan errores de comunicación entre nodos.",
        "La ruta hacia la subred destino no está disponible.",
        "Un dispositivo de red responde de forma intermitente.",
        "No se puede establecer comunicación con la red externa.",
    ],
    "rendimiento": [
        "La red presenta tiempos de respuesta elevados.",
        "Se observa un aumento considerable de latencia.",
        "El tráfico de datos se encuentra por encima de lo habitual.",
        "La transferencia de archivos es demasiado lenta.",
        "El ancho de banda disponible ha disminuido.",
        "Se detectaron picos de utilización de la red.",
        "Los usuarios reportan lentitud durante las conexiones.",
        "Se observa tráfico intenso durante varios minutos.",
        "La velocidad de transmisión ha disminuido.",
        "El tiempo de respuesta entre nodos aumentó.",
        "El rendimiento de la red es inferior al esperado.",
        "La utilización del enlace permanece elevada.",
        "Existen variaciones importantes en la velocidad.",
        "Se reporta congestión durante la transmisión.",
        "La comunicación presenta retrasos frecuentes.",
    ],
    "interfaces": [
        "La interfaz GigabitEthernet0/1 cambió a estado down.",
        "El puerto Ethernet1/0 dejó de estar activo.",
        "Se detectó una interfaz de red desconectada.",
        "El enlace físico del switch SW1 está inactivo.",
        "La interfaz Gi0/2 presenta cambios de estado.",
        "El puerto del router permanece administrativamente down.",
        "La interfaz eth0 no tiene enlace físico.",
        "Se detectaron errores de entrada en un puerto.",
        "El puerto GigabitEthernet0/3 registra descartes.",
        "La interfaz de salida presenta errores de transmisión.",
        "El enlace entre los switches cambió de estado.",
        "El puerto Fa0/10 dejó de operar.",
        "Una interfaz presenta numerosas colisiones.",
        "Se registraron errores CRC en un puerto Ethernet.",
        "La interfaz TenGigabitEthernet1/0/1 está inactiva.",
    ],
    "servicios": [
        "El servidor DNS no resuelve los nombres solicitados.",
        "Los equipos no reciben direcciones mediante DHCP.",
        "El servicio HTTP dejó de responder.",
        "No se puede establecer una sesión SSH con el servidor.",
        "El servidor web devuelve un error de servicio.",
        "La consulta DNS no obtiene una respuesta válida.",
        "El servicio DHCP no asigna una dirección IP.",
        "El puerto del servicio HTTPS no acepta conexiones.",
        "El servidor FTP rechaza las solicitudes de acceso.",
        "El servicio de nombres presenta errores.",
        "Se registró una interrupción del servicio NTP.",
        "La aplicación web responde con error 503.",
        "El servidor de autenticación no atiende solicitudes.",
        "El servicio SSH finaliza las sesiones inesperadamente.",
        "Los clientes reportan problemas con el servicio DNS.",
    ],
}

# ==========================================
# CREAR CSV
# ==========================================

ruta = DATA / "reportes_red.csv"

with ruta.open("w", newline="", encoding="utf-8-sig") as archivo:

    writer = csv.writer(archivo)

    writer.writerow(["id", "texto", "categoria", "origen"])

    identificador = 1

    for categoria, textos in reportes.items():

        for texto in textos:

            writer.writerow([identificador, texto, categoria, "simulado"])

            identificador += 1

# ==========================================
# RESUMEN
# ==========================================

print("=" * 60)
print("DATASET INICIAL DE PNL - NETINSIGHT AI")
print("=" * 60)

for categoria, textos in reportes.items():
    print(f"{categoria}: {len(textos)} reportes")

print("\nTotal:", identificador - 1)
print("Archivo generado:", ruta)
print("\nDataset inicial creado correctamente.")
