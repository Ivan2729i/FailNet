import re
import json
import ipaddress

# ==================================================
# 1. PATRONES DE IDENTIFICACIÓN
# ==================================================

# Direcciones IPv4
PATRON_IP = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")

# Dispositivos de red con identificadores habituales
PATRON_DISPOSITIVOS = re.compile(
    r"\b(?:"
    r"R\d+|"
    r"SW\d+|"
    r"RTR[-_]?\d+|"
    r"FW[-_]?\d+|"
    r"AP[-_]?\d+|"
    r"PC[-_]?\d+|"
    r"Router[-_][A-Za-z0-9_-]+|"
    r"Switch[-_][A-Za-z0-9_-]+"
    r")\b",
    re.IGNORECASE,
)

# Interfaces comunes de Cisco y Linux
PATRON_INTERFACES = re.compile(
    r"\b(?:"
    r"TenGigabitEthernet|"
    r"GigabitEthernet|"
    r"FastEthernet|"
    r"Ethernet|"
    r"Port-channel|"
    r"Loopback|"
    r"Vlan|"
    r"Gi|Fa|Te|Eth|Po|Lo"
    r")\s*\d+(?:/\d+){0,3}(?:\.\d+)?\b"
    r"|"
    r"\b(?:"
    r"eth\d+|"
    r"ens\d+|"
    r"enp\d+s\d+(?:f\d+)?|"
    r"wlan\d+"
    r")\b",
    re.IGNORECASE,
)

# Protocolos y servicios de red
PROTOCOLOS = [
    "HTTPS",
    "HTTP",
    "SSH",
    "SFTP",
    "FTP",
    "DNS",
    "DHCP",
    "ICMP",
    "TCP",
    "UDP",
    "SNMP",
    "NTP",
    "SMTP",
    "IMAP",
    "POP3",
    "OSPF",
    "BGP",
    "RIP",
    "ARP",
    "STP",
    "LLDP",
]

PATRON_PROTOCOLOS = re.compile(
    r"\b(?:" + "|".join(map(re.escape, PROTOCOLOS)) + r")\b", re.IGNORECASE
)


# ==================================================
# 2. ELIMINAR DUPLICADOS
# ==================================================


def valores_unicos(valores):

    resultado = []
    encontrados = set()

    for valor in valores:

        valor = valor.strip()
        clave = valor.lower()

        if clave not in encontrados:
            encontrados.add(clave)
            resultado.append(valor)

    return resultado


# ==================================================
# 3. EXTRAER DIRECCIONES IPv4
# ==================================================


def extraer_ips(texto):

    candidatos = PATRON_IP.findall(texto)

    ips_validas = []

    for candidato in candidatos:

        try:
            ipaddress.IPv4Address(candidato)
            ips_validas.append(candidato)

        except ipaddress.AddressValueError:
            pass

    return valores_unicos(ips_validas)


# ==================================================
# 4. EXTRAER DISPOSITIVOS
# ==================================================


def extraer_dispositivos(texto):

    encontrados = PATRON_DISPOSITIVOS.findall(texto)

    return valores_unicos(encontrados)


# ==================================================
# 5. EXTRAER INTERFACES
# ==================================================


def extraer_interfaces(texto):

    encontrados = [
        coincidencia.group() for coincidencia in PATRON_INTERFACES.finditer(texto)
    ]

    return valores_unicos(encontrados)


# ==================================================
# 6. EXTRAER PROTOCOLOS
# ==================================================


def extraer_protocolos(texto):

    encontrados = PATRON_PROTOCOLOS.findall(texto)

    encontrados = [protocolo.upper() for protocolo in encontrados]

    return valores_unicos(encontrados)


# ==================================================
# 7. FUNCIÓN PRINCIPAL
# ==================================================


def extraer_entidades(texto):

    if not isinstance(texto, str):
        raise TypeError("El reporte debe ser una cadena de texto.")

    return {
        "direcciones_ip": extraer_ips(texto),
        "dispositivos": extraer_dispositivos(texto),
        "interfaces": extraer_interfaces(texto),
        "protocolos": extraer_protocolos(texto),
    }


# ==================================================
# 8. PRUEBAS
# ==================================================

if __name__ == "__main__":

    reportes = [
        (
            "Se detectó pérdida de conectividad "
            "en el router R3 hacia la dirección "
            "192.168.1.10 mediante la interfaz "
            "GigabitEthernet0/1."
        ),
        (
            "El switch SW2 presenta errores en "
            "Fa0/10. El servidor 10.0.0.5 "
            "no responde a solicitudes ICMP."
        ),
        (
            "El router R1 reporta una falla DNS "
            "hacia 8.8.8.8 y problemas con "
            "el servicio HTTPS."
        ),
        (
            "La interfaz eth0 del servidor "
            "perdió conectividad. Se verificó "
            "la comunicación mediante SSH."
        ),
        (
            "El equipo reportó la dirección "
            "999.999.999.999, que no es una "
            "dirección IPv4 válida."
        ),
    ]

    print("=" * 65)
    print("EXTRACCIÓN DE ENTIDADES - NETINSIGHT AI")
    print("=" * 65)

    for numero, reporte in enumerate(reportes, start=1):

        print("\n" + "=" * 65)
        print(f"PRUEBA {numero}")
        print("=" * 65)

        print("\nREPORTE:")
        print(reporte)

        resultado = extraer_entidades(reporte)

        print("\nENTIDADES DETECTADAS:")

        print(json.dumps(resultado, indent=4, ensure_ascii=False))
