# ventilador.py - Control PWM del extractor 12 V con modulo MOSFET HW-042 (AOD4184)
# Proyecto 7 - Secador solar de cafe (Pico 2 W, MicroPython)
#
# La Pico NO alimenta el ventilador: solo envia la senal PWM (3.3 V) al MOSFET,
# y el MOSFET conecta/desconecta los 12 V de la fuente muy rapido.
# % de velocidad = % del tiempo que el MOSFET esta encendido (duty cycle).

import time
from machine import Pin, PWM


class Ventilador:
    def __init__(self, pin, freq=1000, minimo=25):
        self.pin = pin
        self.pwm = PWM(Pin(pin))
        self.pwm.freq(freq)
        self.minimo = minimo     # % por debajo del cual el ventilador se detiene
        self.porcentaje = 0
        self.apagar()

    def _duty(self, porcentaje):
        self.pwm.duty_u16(int(porcentaje * 65535 / 100))

    def velocidad(self, porcentaje):
        """0 = apagado, 100 = maximo. Si arranca desde 0, da un impulso al 100 %."""
        porcentaje = max(0, min(100, porcentaje))
        if 0 < porcentaje < self.minimo:
            porcentaje = self.minimo
        if self.porcentaje == 0 and porcentaje > 0:
            self._duty(100)          # impulso de arranque
            time.sleep_ms(500)
        self._duty(porcentaje)
        self.porcentaje = porcentaje

    def apagar(self):
        self._duty(0)
        self.porcentaje = 0

    def frecuencia(self, freq):
        self.pwm.freq(freq)
        self._duty(self.porcentaje)

    def liberar(self):
        self.apagar()
        self.pwm.deinit()
        Pin(self.pin, Pin.OUT, value=0)   # pin firme en 0 V: MOSFET apagado
