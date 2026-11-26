# prueba_rapida_ventilador.py - Hace girar solo el ventilador (no necesita otros archivos)
# PWM: GP16 (pin 21) -> 220 ohm -> borne verde PWM del MOSFET
# GND: pin 23 -> riel negativo -> borne verde GND del MOSFET

import time
from machine import Pin, PWM

fan = PWM(Pin(16))
fan.freq(1000)


def velocidad(p):
    fan.duty_u16(int(p * 65535 / 100))
    print("Velocidad: %d %%" % p)


try:
    velocidad(100)
    time.sleep(3)
    velocidad(60)
    time.sleep(3)
    velocidad(35)
    time.sleep(3)
    velocidad(100)
    time.sleep(2)
finally:
    fan.duty_u16(0)
    fan.deinit()
    Pin(16, Pin.OUT, value=0)   # deja el pin firme en 0 V (MOSFET apagado)
    print("Ventilador apagado")
