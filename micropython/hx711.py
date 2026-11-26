# hx711.py - Driver HX711 para Raspberry Pi Pico 2 W (MicroPython)
# Proyecto 7 - Secador solar de cafe
#
# Comunicacion propia de 2 hilos:
#   DT  (DOUT): el HX711 lo pone en 0 cuando hay un dato listo
#   SCK (PD_SCK): la Pico genera 25 pulsos -> 24 bits de dato + 1 pulso
#                 que deja el canal A con ganancia 128 para la siguiente lectura
# Si SCK queda en alto mas de 60 us, el HX711 se apaga (power down);
# por eso desactivamos las interrupciones mientras se leen los bits.

import machine
import time
from machine import Pin

_PULSOS_GANANCIA = {128: 1, 64: 3, 32: 2}  # pulsos extra despues de los 24 bits


class HX711:
    def __init__(self, pin_dt, pin_sck, ganancia=128):
        self.dt = Pin(pin_dt, Pin.IN)
        self.sck = Pin(pin_sck, Pin.OUT, value=0)
        self.pulsos_extra = _PULSOS_GANANCIA[ganancia]
        self.offset = 0      # lectura cruda con la bandeja vacia (tara)
        self.escala = 1.0    # cuentas por gramo (sale de la calibracion)
        self.encender()
        self.leer_crudo()    # primera lectura: fija la ganancia

    # ---------- bajo nivel ----------
    def listo(self):
        return self.dt.value() == 0

    def esperar_listo(self, timeout_ms=1000):
        t0 = time.ticks_ms()
        while self.dt.value() == 1:
            if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
                raise OSError("HX711 no responde: revisa VCC, GND, DT y SCK")

    def leer_bits(self):
        """Solo los 25 pulsos (sin esperar). Es la parte que se medira en el reto C."""
        sck = self.sck
        dt = self.dt
        valor = 0
        irq = machine.disable_irq()
        try:
            for _ in range(24):
                sck.value(1)
                sck.value(0)
                valor = (valor << 1) | dt.value()
            for _ in range(self.pulsos_extra):
                sck.value(1)
                sck.value(0)
        finally:
            machine.enable_irq(irq)
        if valor & 0x800000:          # complemento a 2 de 24 bits
            valor -= 0x1000000
        return valor

    def leer_crudo(self):
        self.esperar_listo()
        return self.leer_bits()

    # ---------- utilidades ----------
    def promedio_crudo(self, n=10):
        total = 0
        for _ in range(n):
            total += self.leer_crudo()
        return total / n

    def tara(self, n=20):
        self.offset = self.promedio_crudo(n)
        return self.offset

    def calibrar(self, peso_conocido_g, n=20):
        """Con la tara ya hecha y el peso conocido sobre la bandeja."""
        cuentas = self.promedio_crudo(n) - self.offset
        if abs(cuentas) < 100:
            raise ValueError("Casi no cambia la lectura: revisa la celda (A+/A-) o el peso")
        self.escala = cuentas / peso_conocido_g
        return self.escala

    def peso_g(self, n=5):
        return (self.promedio_crudo(n) - self.offset) / self.escala

    def apagar(self):
        self.sck.value(0)
        self.sck.value(1)
        time.sleep_us(80)

    def encender(self):
        self.sck.value(0)
        time.sleep_ms(1)
