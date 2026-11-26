# mqtt_simple.py - Cliente MQTT 3.1.1 minimo (publicar y suscribirse, QoS 0)
# Proyecto 7 - Secador solar de cafe. Basado en la logica de umqtt.simple,
# incluido aqui para no depender de librerias externas.

import socket
import struct


def _largo(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _texto(s):
    if isinstance(s, str):
        s = s.encode()
    return struct.pack("!H", len(s)) + s


class MQTTClient:
    def __init__(self, client_id, server, port=1883, user=None, password=None,
                 keepalive=60, timeout=10):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.user = user
        self.password = password
        self.keepalive = keepalive
        self.timeout = timeout
        self.sock = None
        self.cb = None
        self.pid = 0
        self.suback = False

    def set_callback(self, cb):
        self.cb = cb

    def _leer(self, n):
        buf = b""
        while len(buf) < n:
            parte = self.sock.read(n - len(buf))
            if not parte:
                raise OSError("MQTT: conexion cerrada")
            buf += parte
        return buf

    def _leer_largo(self):
        n = 0
        sh = 0
        while True:
            b = self._leer(1)[0]
            n |= (b & 0x7F) << sh
            if not b & 0x80:
                return n
            sh += 7

    def connect(self):
        addr = socket.getaddrinfo(self.server, self.port)[0][-1]
        self.sock = socket.socket()
        self.sock.settimeout(self.timeout)
        self.sock.connect(addr)
        flags = 0x02                       # clean session
        payload = _texto(self.client_id)
        if self.user:
            flags |= 0xC0
            payload += _texto(self.user) + _texto(self.password)
        cuerpo = b"\x00\x04MQTT\x04" + bytes([flags]) + struct.pack("!H", self.keepalive) + payload
        self.sock.write(b"\x10" + _largo(len(cuerpo)) + cuerpo)
        resp = self._leer(4)
        if resp[0] != 0x20:
            raise OSError("MQTT: respuesta invalida")
        if resp[3] != 0:
            raise OSError("MQTT rechazado (codigo %d): revisa usuario y clave" % resp[3])

    def disconnect(self):
        try:
            self.sock.write(b"\xE0\x00")
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass
        self.sock = None

    def ping(self):
        self.sock.write(b"\xC0\x00")

    def publish(self, topic, msg, retain=False):
        if isinstance(msg, str):
            msg = msg.encode()
        datos = _texto(topic) + msg
        self.sock.write(bytes([0x30 | (1 if retain else 0)]) + _largo(len(datos)) + datos)

    def subscribe(self, topic):
        self.pid = (self.pid % 65535) + 1
        datos = struct.pack("!H", self.pid) + _texto(topic) + b"\x00"
        self.sock.write(b"\x82" + _largo(len(datos)) + datos)
        self.suback = False
        while not self.suback:
            self.wait_msg()

    def wait_msg(self):
        res = self.sock.read(1)
        self.sock.settimeout(self.timeout)
        if res is None:
            return None                    # no habia nada (modo no bloqueante)
        if res == b"":
            raise OSError("MQTT: conexion cerrada")
        op = res[0]
        if op == 0xD0:                     # PINGRESP
            self._leer(1)
            return None
        sz = self._leer_largo()
        if op == 0x90:                     # SUBACK
            self._leer(sz)
            self.suback = True
            return None
        if op & 0xF0 == 0x30:              # PUBLISH recibido
            tlen = struct.unpack("!H", self._leer(2))[0]
            topic = self._leer(tlen)
            sz -= tlen + 2
            if op & 0x06:
                self._leer(2)
                sz -= 2
            msg = self._leer(sz)
            if self.cb:
                self.cb(topic, msg)
            return op
        self._leer(sz)                     # otro paquete: se descarta
        return None

    def check_msg(self):
        """Revisa si llego algo, sin quedarse esperando."""
        self.sock.setblocking(False)
        return self.wait_msg()
