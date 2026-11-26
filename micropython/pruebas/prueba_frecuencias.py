# prueba_frecuencias.py - Compara frecuencias PWM del extractor
# Para cada frecuencia: 100 % -> 50 % -> 30 %. Anota en cual el ventilador
# cambia mejor de velocidad y hace menos ruido.
# Necesita ventilador.py en la Pico. Fuente de 12 V enchufada.

import time
from ventilador import Ventilador

FRECUENCIAS = (100, 200, 500, 1000, 25000)

fan = Ventilador(16, freq=FRECUENCIAS[0], minimo=0)
try:
    for f in FRECUENCIAS:
        fan.apagar()
        fan.frecuencia(f)
        print("\n=== %d Hz ===" % f)
        for p in (100, 50, 30):
            fan.velocidad(p)
            print("  %3d %%" % p)
            time.sleep(3)
        fan.apagar()
        input("  Anota ruido y si bajo la velocidad. Enter para seguir...")
finally:
    fan.liberar()
    print("Ventilador apagado.")
