# prueba_ventilador.py - Prueba individual del extractor 12 V + MOSFET HW-042
# Proyecto 7 - Secador solar de cafe (Pico 2 W, MicroPython)
#
# Ejecutar desde Thonny con ventilador.py ya guardado en la Pico.
# Cableado:
#   GP16 (pin 21, fila 20 derecha) -> resistencia 220 ohm -> PWM/TRIG del modulo
#   GND  (pin 23, fila 18 derecha) -> GND del modulo (tierra comun)
#   Fuente 12 V (+) -> VIN+    Fuente 12 V (-) -> VIN-
#   Ventilador rojo -> OUT+    Ventilador negro -> OUT-

import time
from ventilador import Ventilador

PIN_PWM = 16
fan = Ventilador(PIN_PWM, freq=1000)


def linea(titulo):
    print("\n" + "=" * 50)
    print(titulo)
    print("=" * 50)


try:
    # ---------------- PRUEBA 1: encendido / apagado ----------------
    linea("PRUEBA 1 - Encendido y apagado")
    input("Fuente de 12 V encendida? Presiona Enter...")
    print("Ventilador al 100 % por 4 s...")
    fan.velocidad(100)
    time.sleep(4)
    fan.apagar()
    print("Apagado. Debio girar fuerte y luego detenerse.")
    time.sleep(3)

    # ---------------- PRUEBA 2: escalones de velocidad ----------------
    linea("PRUEBA 2 - Escalones de velocidad")
    print("Escucha y observa: cada escalon debe girar mas lento que el anterior.")
    for p in (100, 80, 60, 40, 30):
        fan.minimo = 0
        fan.velocidad(p)
        print("  Velocidad: %3d %%" % p)
        time.sleep(4)
    fan.apagar()
    time.sleep(2)

    # ---------------- PRUEBA 3: velocidad minima ----------------
    linea("PRUEBA 3 - Buscar la velocidad minima")
    print("Bajamos de 5 en 5. Responde 's' si GIRA o 'n' si se DETUVO.")
    fan.velocidad(100)
    time.sleep(1)
    minimo = 0
    for p in range(50, 0, -5):
        fan._duty(p)
        fan.porcentaje = p
        time.sleep(3)
        r = input("  %2d %% -> gira? (s/n): " % p).strip().lower()
        if r == "n":
            minimo = p + 5
            break
    fan.apagar()
    print("Velocidad minima util: %d %%  (anotala para el programa final)" % minimo)
    fan.minimo = minimo

    # ---------------- PRUEBA 4: control manual ----------------
    linea("PRUEBA 4 - Control manual")
    print("Escribe un % (0-100) y Enter. 'f' para terminar.")
    while True:
        r = input("  Velocidad %: ").strip().lower()
        if r == "f":
            break
        try:
            fan.velocidad(int(r))
            print("  -> %d %%" % fan.porcentaje)
        except ValueError:
            print("  Escribe un numero entre 0 y 100")

except KeyboardInterrupt:
    pass
finally:
    fan.liberar()
    print("\nVentilador apagado. Fin de la prueba.")
