# wifi.py - Conexion Wi-Fi de la Pico 2 W con reconexion
# Proyecto 7 - Secador solar de cafe (MicroPython)
# Se reutiliza despues para MQTT (Adafruit IO).

import time
import network

try:
    network.country("PE")
except Exception:
    try:
        import rp2
        rp2.country("PE")
    except Exception:
        pass
try:
    network.hostname("secador-cafe")     # nombre que se ve en el hotspot
except Exception:
    pass

GOT_IP = getattr(network, "STAT_GOT_IP", 3)
WRONG_PASSWORD = getattr(network, "STAT_WRONG_PASSWORD", -3)
NO_AP_FOUND = getattr(network, "STAT_NO_AP_FOUND", -2)
CONNECT_FAIL = getattr(network, "STAT_CONNECT_FAIL", -1)

ESTADOS = {
    0: "inactivo",
    1: "conectando",
    2: "sin IP todavia",
    GOT_IP: "conectado",
    CONNECT_FAIL: "fallo de conexion",
    NO_AP_FOUND: "no encuentra la red (nombre o banda 5 GHz)",
    WRONG_PASSWORD: "contrasena incorrecta",
}

wlan = network.WLAN(network.STA_IF)


def conectar(ssid, password, timeout_s=20, al_esperar=None):
    """Intenta conectar. Devuelve (ok, texto_del_estado)."""
    wlan.active(True)
    try:
        wlan.config(pm=0xA11140)   # sin ahorro de energia: conexion mas estable
    except Exception:
        pass
    if wlan.isconnected():
        return True, "conectado"
    try:
        wlan.disconnect()
    except Exception:
        pass
    wlan.connect(ssid, password)
    t0 = time.ticks_ms()
    estado = wlan.status()
    while time.ticks_diff(time.ticks_ms(), t0) < timeout_s * 1000:
        estado = wlan.status()
        if estado == GOT_IP:
            return True, "conectado"
        if estado in (WRONG_PASSWORD, NO_AP_FOUND, CONNECT_FAIL):
            break
        if al_esperar:
            al_esperar()
        else:
            time.sleep_ms(200)
    texto = ESTADOS.get(estado, "estado %s" % estado)
    if estado == 1:
        texto = "tiempo agotado (sigue 'conectando')"
    try:
        wlan.disconnect()
    except Exception:
        pass
    return False, texto


def conectado():
    return wlan.isconnected()


def ip():
    return wlan.ifconfig()[0]


def senal_dbm():
    try:
        return wlan.status("rssi")
    except Exception:
        return None


def hay_internet(host="io.adafruit.com", puerto=1883, timeout=5):
    """Prueba de verdad: abre una conexion TCP al servidor MQTT de Adafruit IO."""
    import socket
    try:
        addr = socket.getaddrinfo(host, puerto)[0][-1]
        s = socket.socket()
        s.settimeout(timeout)
        try:
            s.connect(addr)
        finally:
            s.close()
        return True
    except OSError:
        return False
