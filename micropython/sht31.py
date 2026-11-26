# sht31.py - Driver SHT31 (temperatura y humedad) para Pico 2 W (MicroPython)
# Proyecto 7 - Secador solar de cafe
#
# Protocolo I2C. Direccion 0x44 (pin ADDR a GND o suelto) o 0x45 (ADDR a VCC).
# Cada medicion devuelve 6 bytes: T (2) + CRC (1) + HR (2) + CRC (1).
# Verificamos el CRC para saber que el dato llego sin errores por el bus.

import time

_CMD_MEDIR_ALTA = 0x2400   # alta repetibilidad, sin clock stretching (~15 ms)
_CMD_RESET = 0x30A2
_CMD_CALENTADOR_ON = 0x306D
_CMD_CALENTADOR_OFF = 0x3066


def _crc8(datos):
    crc = 0xFF
    for b in datos:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x31) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


class SHT31:
    def __init__(self, i2c, direccion=0x44):
        self.i2c = i2c
        self.dir = direccion
        self.reset()

    def _cmd(self, cmd):
        self.i2c.writeto(self.dir, bytes([cmd >> 8, cmd & 0xFF]))

    def reset(self):
        self._cmd(_CMD_RESET)
        time.sleep_ms(2)

    def leer(self, intentos=3):
        """Devuelve (temperatura_C, humedad_%). Reintenta si el bus falla."""
        error = None
        for _ in range(intentos):
            try:
                return self._leer_una_vez()
            except (OSError, ValueError) as e:
                error = e
                time.sleep_ms(50)
                try:
                    self.reset()      # reinicia el sensor por si quedo trabado
                except OSError:
                    pass
        raise OSError("SHT31 no responde tras %d intentos: %s" % (intentos, error))

    def _leer_una_vez(self):
        self._cmd(_CMD_MEDIR_ALTA)
        time.sleep_ms(16)
        d = self.i2c.readfrom(self.dir, 6)
        if _crc8(d[0:2]) != d[2] or _crc8(d[3:5]) != d[5]:
            raise ValueError("CRC incorrecto: revisa SDA/SCL y que no esten flojos")
        t_raw = (d[0] << 8) | d[1]
        h_raw = (d[3] << 8) | d[4]
        temperatura = -45 + 175 * t_raw / 65535
        humedad = 100 * h_raw / 65535
        return temperatura, humedad

    def calentador(self, encendido):
        """Calentador interno del sensor (solo para pruebas)."""
        self._cmd(_CMD_CALENTADOR_ON if encendido else _CMD_CALENTADOR_OFF)
