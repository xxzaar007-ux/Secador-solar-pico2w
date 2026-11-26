# main.py - SECADOR SOLAR DE CAFE: sistema completo (corre solo al encender la Pico)
# Proyecto 7 - Arquitectura del Computador I (Pico 2 W, MicroPython)
#
# Tareas concurrentes con asyncio:
#   tarea_peso      -> balanza (HX711): detecta la muestra y el punto optimo
#   tarea_ambiente  -> temperatura y humedad del aire (SHT31, I2C)
#   tarea_control   -> extractor por PWM (automatico o manual desde el celular)
#   tarea_red       -> Wi-Fi + MQTT con Adafruit IO, con reconexion automatica
#   tarea_led       -> estado con el LED de la Pico
#   tarea_pantalla  -> estado en la consola (si hay laptop conectada)
#
# Archivos necesarios en la Pico:
#   hx711.py, sht31.py, ventilador.py, wifi.py, mqtt_simple.py, config.py, calib_celda.json

import asyncio
import json
import time
import machine
import ubinascii
from machine import Pin, I2C
from hx711 import HX711
from sht31 import SHT31
from ventilador import Ventilador
from mqtt_simple import MQTTClient
import wifi
import config

# ---------------- Configuracion ----------------
PIN_DT, PIN_SCK = 14, 15          # HX711
PIN_SDA, PIN_SCL = 4, 5           # SHT31 (I2C0)
PIN_FAN = 16                      # PWM al MOSFET
I2C_FREQ = 20000
FAN_FREQ = 1000

H0 = 0.45          # humedad inicial del cafe (40-50 %)
HF = 0.12          # humedad final buscada (11-12 %)
TEMP_MAX = 40.0    # no pasar de 40 C en cafe pergamino

HR_ENCENDER = 50.0
HR_MAXIMA = 80.0
FAN_MIN = 30

PESO_MIN_MUESTRA = 50.0
PESO_VACIO = 20.0
ARCHIVO_CALIB = "calib_celda.json"

# Adafruit IO (plan gratis: max 10 feeds y 30 datos por minuto)
# Feeds usados (los que ya existen en la cuenta):
#   peso, temperatura, humedad-aire, humedad-grano, listo  -> la Pico publica cada 20 s
#   alertas   -> la Pico publica mensajes cuando pasa algo (muestra, listo, alerta T)
#   extractor -> la Pico ESCUCHA: 0 = automatico, 1-100 = velocidad manual desde el celular
AIO_SERVER = "io.adafruit.com"
PUBLICAR_CADA_S = 20              # 5 feeds cada 20 s = 15 datos/min
FEED = lambda nombre: "%s/feeds/%s" % (config.AIO_USER, nombre)

# ---------------- Estado compartido ----------------
estado = {
    "fase": "ESPERANDO",
    "peso": 0.0, "w0": None, "wobj": None,
    "temp": None, "hr": None,
    "fan": 0,
    "alerta_temp": False,
    "auto": True,          # extractor automatico (toggle del dashboard)
    "manual": 50,          # velocidad manual (slider del dashboard)
    "wifi": False, "nube": False,
    "errores": 0,
    "eventos": [],         # mensajes pendientes para el feed "alertas"
}


def avisar(msg):
    print("\n>>> %s\n" % msg)
    estado["eventos"].append(msg)
    estado["eventos"] = estado["eventos"][-5:]

celda = None
sensor = None
fan = None
i2c = None


# ---------------- Inicializacion ----------------
def iniciar_sht31():
    global sensor
    dirs = i2c.scan()
    for d in (0x44, 0x45):
        if d in dirs:
            sensor = SHT31(i2c, d)
            print("SHT31 listo en", hex(d))
            return True
    sensor = None
    print("SHT31 no encontrado (se reintentara)")
    return False


def iniciar():
    global celda, fan, i2c
    fan = Ventilador(PIN_FAN, freq=FAN_FREQ, minimo=FAN_MIN)
    fan.apagar()

    with open(ARCHIVO_CALIB) as f:
        calib = json.load(f)
    celda = HX711(PIN_DT, PIN_SCK)
    celda.escala = calib["escala"]
    print("Tara: deja la bandeja VACIA (5 s)...")
    led = Pin("LED", Pin.OUT)
    for _ in range(10):                 # LED encendido fijo = haciendo tara
        led.on()
        time.sleep_ms(500)
    celda.tara(20)
    led.off()
    print("Tara lista.")

    i2c = I2C(0, sda=Pin(PIN_SDA), scl=Pin(PIN_SCL), freq=I2C_FREQ)
    iniciar_sht31()


# ---------------- Balanza ----------------
async def leer_peso_async(n=5):
    total = 0
    for _ in range(n):
        t0 = time.ticks_ms()
        while not celda.listo():
            if time.ticks_diff(time.ticks_ms(), t0) > 1000:
                raise OSError("HX711 no responde")
            await asyncio.sleep_ms(5)
        total += celda.leer_bits()
    return (total / n - celda.offset) / celda.escala


async def tarea_peso():
    hist = []
    while True:
        try:
            p = await leer_peso_async(5)
            estado["peso"] = p
            hist.append(p)
            hist = hist[-5:]
            fase = estado["fase"]
            if fase == "ESPERANDO":
                if len(hist) == 5 and min(hist) > PESO_MIN_MUESTRA and max(hist) - min(hist) < 5:
                    w0 = sum(hist) / 5
                    estado["w0"] = w0
                    estado["wobj"] = w0 * (1 - H0) / (1 - HF)
                    estado["fase"] = "SECANDO"
                    avisar("Muestra detectada: %.0f g, avisa al llegar a %.0f g" % (w0, estado["wobj"]))
            elif p < PESO_VACIO:
                estado.update(fase="ESPERANDO", w0=None, wobj=None)
                avisar("Bandeja vacia: esperando nueva muestra")
            elif fase == "SECANDO" and len(hist) >= 3 and max(hist[-3:]) <= estado["wobj"]:
                estado["fase"] = "LISTO"
                avisar("CAFE LISTO: llego a %.0f g (humedad ~%d %%)" % (p, int(HF * 100)))
        except OSError as e:
            estado["errores"] += 1
            print("[peso] error:", e)
        await asyncio.sleep_ms(300)


# ---------------- Ambiente ----------------
async def tarea_ambiente():
    fallos = 0
    while True:
        if sensor is None:
            try:
                iniciar_sht31()
            except OSError:
                pass
            await asyncio.sleep(5)
            continue
        try:
            t, h = sensor.leer()
            fallos = 0
            estado["temp"] = t
            estado["hr"] = h
            alerta = t > TEMP_MAX
            if alerta and not estado["alerta_temp"]:
                avisar("ALERTA: temperatura %.1f C supera %.0f C" % (t, TEMP_MAX))
            elif not alerta and estado["alerta_temp"]:
                avisar("Temperatura de vuelta bajo %.0f C" % TEMP_MAX)
            estado["alerta_temp"] = alerta
        except OSError as e:
            estado["errores"] += 1
            fallos += 1
            print("[ambiente] error:", e)
            if fallos >= 3:
                estado["temp"] = None
                estado["hr"] = None
        await asyncio.sleep(2)


# ---------------- Extractor ----------------
def velocidad_por_humedad(hr):
    if hr < HR_ENCENDER:
        return 0
    if hr >= HR_MAXIMA:
        return 100
    return FAN_MIN + (hr - HR_ENCENDER) / (HR_MAXIMA - HR_ENCENDER) * (100 - FAN_MIN)


async def tarea_control():
    while True:
        t, hr = estado["temp"], estado["hr"]
        if t is not None and t > TEMP_MAX:
            v = 100                                   # seguridad: siempre enfria
        elif not estado["auto"]:
            v = estado["manual"]                      # control desde el celular
        elif estado["fase"] == "SECANDO" and hr is not None:
            v = int(velocidad_por_humedad(hr))
        else:
            v = 0
        if v <= 0:
            if fan.porcentaje != 0:
                fan.apagar()
        elif fan.porcentaje == 0 or abs(v - fan.porcentaje) >= 5:
            fan.velocidad(v)
        estado["fan"] = fan.porcentaje
        await asyncio.sleep(1)


# ---------------- Nube (Adafruit IO) ----------------
def al_recibir(topic, msg):
    """Feed 'extractor': 0 = automatico, 1-100 = velocidad manual (ON/OFF tambien sirve)."""
    if not topic.decode().endswith("/extractor"):
        return
    texto = msg.decode().strip().upper()
    if texto == "ON":
        estado["auto"], estado["manual"] = False, 100
    elif texto == "OFF":
        estado["auto"] = True
    else:
        try:
            v = max(0, min(100, int(float(texto))))
        except ValueError:
            return
        if v == 0:
            estado["auto"] = True
        else:
            estado["auto"], estado["manual"] = False, v
    print("[nube] extractor:", "AUTOMATICO" if estado["auto"] else "MANUAL %d %%" % estado["manual"])


def publicar_todo(cliente):
    e = estado
    cliente.publish(FEED("peso"), "%.1f" % e["peso"])
    cliente.publish(FEED("listo"), "1" if e["fase"] == "LISTO" else "0")
    if e["temp"] is not None:
        cliente.publish(FEED("temperatura"), "%.1f" % e["temp"])
        cliente.publish(FEED("humedad-aire"), "%.1f" % e["hr"])
    if e["w0"] is not None and e["peso"] > 0:
        h_grano = max(0, (1 - e["w0"] * (1 - H0) / e["peso"]) * 100)
        cliente.publish(FEED("humedad-grano"), "%.1f" % h_grano)


async def conectar_wifi_async():
    w = wifi.wlan
    w.active(True)
    try:
        w.config(pm=0xA11140)
    except Exception:
        pass
    try:
        w.disconnect()
    except Exception:
        pass
    print("[red] conectando a", config.WIFI_SSID)
    w.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    for _ in range(100):                       # hasta 20 s sin bloquear lo demas
        if w.isconnected():
            print("[red] Wi-Fi OK, IP", wifi.ip())
            return True
        await asyncio.sleep_ms(200)
    print("[red] sin Wi-Fi:", wifi.ESTADOS.get(w.status(), w.status()))
    return False


async def tarea_red():
    cliente = None
    ultimo_envio = time.ticks_ms() - PUBLICAR_CADA_S * 1000
    ultimo_ping = time.ticks_ms()
    client_id = "secador-" + ubinascii.hexlify(machine.unique_id()).decode()

    while True:
        # 1) Wi-Fi
        if not wifi.conectado():
            estado["wifi"] = False
            estado["nube"] = False
            if cliente:
                cliente.disconnect()
                cliente = None
            if not await conectar_wifi_async():
                await asyncio.sleep(5)
                continue
        estado["wifi"] = True

        # 2) MQTT
        if cliente is None:
            try:
                cliente = MQTTClient(client_id, AIO_SERVER, user=config.AIO_USER,
                                     password=config.AIO_KEY, keepalive=60)
                cliente.set_callback(al_recibir)
                cliente.connect()
                cliente.subscribe(FEED("extractor"))
                cliente.publish(FEED("extractor") + "/get", "")    # pide el ultimo valor
                estado["nube"] = True
                print("[nube] conectado a Adafruit IO")
            except Exception as e:
                print("[nube] no se pudo conectar:", e)
                if cliente:
                    cliente.disconnect()
                cliente = None
                estado["nube"] = False
                await asyncio.sleep(5)
                continue

        # 3) Recibir, publicar y mantener viva la conexion
        try:
            cliente.check_msg()
            ahora = time.ticks_ms()
            if time.ticks_diff(ahora, ultimo_envio) >= PUBLICAR_CADA_S * 1000:
                publicar_todo(cliente)
                ultimo_envio = ultimo_ping = ahora
            elif estado["eventos"]:                      # avisos: al instante
                cliente.publish(FEED("alertas"), estado["eventos"].pop(0))
                ultimo_ping = ahora
            elif time.ticks_diff(ahora, ultimo_ping) >= 30000:
                cliente.ping()
                ultimo_ping = ahora
        except Exception as e:
            print("[nube] conexion perdida:", e)
            cliente.disconnect()
            cliente = None
            estado["nube"] = False
        await asyncio.sleep_ms(500)


# ---------------- LED y consola ----------------
async def tarea_led():
    led = Pin("LED", Pin.OUT)
    while True:
        if estado["fase"] == "LISTO" or estado["alerta_temp"]:
            led.toggle()                               # rapido: listo o alerta
            await asyncio.sleep_ms(150)
        else:
            n = 1 if estado["nube"] else 2             # 1 = en la nube, 2 = sin nube
            for _ in range(n):
                led.on()
                await asyncio.sleep_ms(100)
                led.off()
                await asyncio.sleep_ms(200)
            await asyncio.sleep_ms(1700)


def _f(valor, formato, vacio="--"):
    return vacio if valor is None else formato % valor


async def tarea_pantalla():
    while True:
        e = estado
        print("[%-9s] Peso %7.1f g | Obj %s | T %s | HR %s | Fan %3d%% %s | WiFi %s | Nube %s"
              % (e["fase"], e["peso"], _f(e["wobj"], "%.1f"), _f(e["temp"], "%.1f"),
                 _f(e["hr"], "%.1f"), e["fan"], "AUTO" if e["auto"] else "MANUAL",
                 "OK" if e["wifi"] else "--", "OK" if e["nube"] else "--"))
        await asyncio.sleep(2)


# ---------------- Programa principal ----------------
async def main():
    iniciar()
    print("\nSecador iniciado.\n")
    asyncio.create_task(tarea_peso())
    asyncio.create_task(tarea_ambiente())
    asyncio.create_task(tarea_control())
    asyncio.create_task(tarea_red())
    asyncio.create_task(tarea_led())
    await tarea_pantalla()


try:
    asyncio.run(main())
except KeyboardInterrupt:
    if fan is not None:
        fan.liberar()
    print("Secador detenido desde Thonny.")
except Exception as e:
    if fan is not None:
        fan.liberar()
    try:
        with open("error_log.txt", "a") as f:
            f.write("%d ms: %s\n" % (time.ticks_ms(), e))
    except OSError:
        pass
    print("ERROR:", e, "-> reinicio en 10 s")
    time.sleep(10)
    machine.reset()
