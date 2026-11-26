# prueba_sht31.py - Prueba individual del sensor SHT31
# Proyecto 7 - Secador solar de cafe (Pico 2 W, MicroPython)
#
# Ejecutar desde Thonny con sht31.py ya guardado en la Pico.
# Cableado:
#   SHT31 VIN -> 3V3(OUT)  pin fisico 36  (fila 5 derecha, hueco libre)
#   SHT31 GND -> GND       pin fisico 38  (fila 3 derecha, hueco libre)
#   SHT31 SDA -> GP4       pin fisico 6   (fila 6 izquierda, hueco a6)
#   SHT31 SCL -> GP5       pin fisico 7   (fila 7 izquierda, hueco a7)

import time
from machine import I2C, Pin
from sht31 import SHT31

TEMP_MAX = 40.0   # limite recomendado para secar cafe en pergamino


def linea(titulo):
    print("\n" + "=" * 50)
    print(titulo)
    print("=" * 50)


def desviacion(datos):
    m = sum(datos) / len(datos)
    return (sum((x - m) ** 2 for x in datos) / (len(datos) - 1)) ** 0.5, m


# ---------------- PRUEBA 1: bus I2C ----------------
linea("PRUEBA 1 - Buscar el sensor en el bus I2C")
i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=100000)
encontrados = i2c.scan()
print("Direcciones encontradas:", [hex(d) for d in encontrados])

if 0x44 in encontrados:
    direccion = 0x44
elif 0x45 in encontrados:
    direccion = 0x45
else:
    print("FALLO: no aparece 0x44 ni 0x45.")
    print("Revisa VIN, GND y que SDA vaya a GP4 y SCL a GP5 (no invertidos).")
    raise SystemExit
print("OK: SHT31 encontrado en", hex(direccion))

sensor = SHT31(i2c, direccion)

# ---------------- PRUEBA 2: lecturas ----------------
linea("PRUEBA 2 - 10 lecturas (1 por segundo)")
for i in range(10):
    t, h = sensor.leer()
    print("  %2d) Temp: %5.2f C   Humedad: %5.1f %%" % (i + 1, t, h))
    time.sleep(1)
print("Compara con un termometro o el clima de tu celular (diferencia normal: 1-2 C)")

# ---------------- PRUEBA 3: estabilidad ----------------
linea("PRUEBA 3 - Estabilidad (30 lecturas, no toques el sensor)")
ts, hs = [], []
for _ in range(30):
    t, h = sensor.leer()
    ts.append(t)
    hs.append(h)
    time.sleep_ms(300)
sd_t, m_t = desviacion(ts)
sd_h, m_h = desviacion(hs)
print("Temperatura: media %.2f C, desviacion %.3f C" % (m_t, sd_t))
print("Humedad    : media %.1f %%, desviacion %.3f %%" % (m_h, sd_h))

# ---------------- PRUEBA 4: respuesta ----------------
linea("PRUEBA 4 - Respuesta del sensor")
print("Durante 20 s: SOPLA cerca del sensor (sube la humedad)")
print("y luego tocalo con los dedos (sube la temperatura).")
input("Presiona Enter para empezar...")
t0, h0 = sensor.leer()
for _ in range(20):
    t, h = sensor.leer()
    print("  Temp: %5.2f C (%+.2f)   Humedad: %5.1f %% (%+.1f)" % (t, t - t0, h, h - h0))
    time.sleep(1)
print("Si la humedad subio varios % y la temperatura algunas decimas o mas: OK")

# ---------------- Lectura continua ----------------
linea("Lectura continua (Ctrl+C o STOP para salir)")
try:
    while True:
        t, h = sensor.leer()
        aviso = "  <-- ALERTA: supera 40 C" if t > TEMP_MAX else ""
        print("Temp: %5.2f C   Humedad: %5.1f %%%s" % (t, h, aviso))
        time.sleep(2)
except KeyboardInterrupt:
    print("Fin de la prueba")
