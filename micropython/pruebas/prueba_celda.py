# prueba_celda.py - Prueba individual de la celda de carga 5 kg + HX711
# Proyecto 7 - Secador solar de cafe (Pico 2 W, MicroPython)
#
# Ejecutar desde Thonny con hx711.py ya guardado en la Pico.
# Cableado:
#   HX711 VCC (y VDD si tiene) -> 3V3(OUT)  pin fisico 36
#   HX711 GND                  -> GND       pin fisico 38
#   HX711 DT                   -> GP14      pin fisico 19
#   HX711 SCK                  -> GP15      pin fisico 20
#   Celda: rojo E+, negro E-, blanco A-, verde A+

import time
import json
from hx711 import HX711

PIN_DT = 14
PIN_SCK = 15
ARCHIVO_CALIB = "calib_celda.json"


def linea(titulo):
    print("\n" + "=" * 50)
    print(titulo)
    print("=" * 50)


def desviacion(datos):
    m = sum(datos) / len(datos)
    return (sum((x - m) ** 2 for x in datos) / (len(datos) - 1)) ** 0.5, m


# ---------------- PRUEBA 1: comunicacion ----------------
linea("PRUEBA 1 - Comunicacion con el HX711")
try:
    celda = HX711(PIN_DT, PIN_SCK)
except OSError as e:
    print("FALLO:", e)
    raise SystemExit

crudos = [celda.leer_crudo() for _ in range(10)]
for v in crudos:
    print("  crudo:", v)

if all(v == crudos[0] for v in crudos):
    print("FALLO: todas las lecturas son iguales -> revisa DT/SCK")
elif any(v in (8388607, -8388608) for v in crudos):
    print("FALLO: valor saturado -> revisa cables de la celda (E+/E-/A+/A-)")
else:
    print("OK: el HX711 responde y los valores varian un poco (normal)")

# ---------------- PRUEBA 2: tara ----------------
linea("PRUEBA 2 - Tara (bandeja vacia)")
input("Deja la bandeja VACIA y presiona Enter...")
print("offset =", celda.tara(20))

# ---------------- PRUEBA 3: calibracion ----------------
linea("PRUEBA 3 - Calibracion con peso conocido")
peso = float(input("Peso conocido en gramos (ej. 500): "))
input("Pon el peso en el CENTRO de la bandeja y presiona Enter...")
escala = celda.calibrar(peso, 20)
print("escala = %.4f cuentas/g" % escala)
if escala < 0:
    print("Aviso: escala negativa. Funciona igual, pero si quieres positiva intercambia A+ y A-.")

with open(ARCHIVO_CALIB, "w") as f:
    json.dump({"offset": celda.offset, "escala": escala}, f)
print("Guardado en", ARCHIVO_CALIB)

# ---------------- PRUEBA 4: validacion ----------------
linea("PRUEBA 4 - Validacion con otros pesos")
print("Pon objetos de peso conocido (distintos al de calibracion). Escribe 'f' para terminar.")
while True:
    r = input("Peso real en g (o 'f'): ")
    if r.strip().lower() == "f":
        break
    real = float(r)
    medido = celda.peso_g(10)
    err = medido - real
    print("  medido = %.1f g | error = %+.1f g (%.2f %%)" % (medido, err, 100 * err / real if real else 0))

# ---------------- PRUEBA 5: estabilidad y tiempos (linea base del reto) ----------------
linea("PRUEBA 5 - Estabilidad y tiempos (MicroPython = ANTES)")
input("Deja UN peso fijo en la bandeja y presiona Enter (tarda ~10-15 s)...")

pesos = []
tiempos_us = []
for _ in range(100):
    celda.esperar_listo()
    t0 = time.ticks_us()
    v = celda.leer_bits()
    tiempos_us.append(time.ticks_diff(time.ticks_us(), t0))
    pesos.append((v - celda.offset) / celda.escala)

sd, media = desviacion(pesos)
print("Peso medio          : %.2f g" % media)
print("Desviacion estandar : %.2f g" % sd)
print("Tiempo por lectura  : %.1f us (solo los 25 pulsos)" % (sum(tiempos_us) / len(tiempos_us)))

n = 0
t0 = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), t0) < 10000:
    celda.leer_crudo()
    n += 1
print("Lecturas por segundo: %.1f" % (n / 10))

# ---------------- Lectura continua ----------------
linea("Lectura continua (Ctrl+C para salir)")
try:
    while True:
        print("Peso: %8.1f g" % celda.peso_g(5))
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Fin de la prueba")
