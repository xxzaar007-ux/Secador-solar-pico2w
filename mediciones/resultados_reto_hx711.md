# Resultados del reto: HX711 en C vs MicroPython

Mismo circuito (DT GP14, SCK GP15), celda de 5 kg. Escala: 300.5 cuentas = 0.67 g (≈ 448.5 cuentas/g).

| Qué medimos | MicroPython | C (Pico SDK) | Mejora |
|---|---|---|---|
| Tiempo por lectura (µs) | 371.2 (mín 364, máx 388) | 15.9 (mín 15, máx 22) | 23.3× más rápido |
| CPU ocupada a 10 lecturas/s | 0.371 % | 0.016 % | 23× menos |
| Precisión (desv. estándar, mismo peso) | 0.84 g (n = 31) | 0.67 g (n = 100) | 20 % menor |
| Lecturas por segundo | 11.7 | 11.7 | Igual (lo limita el HX711) |

## Archivos
- `reto_hx711_c.txt`: salida serial de la versión en C (`c_sdk/hx711_bench`).
- `reto_hx711_micropython.txt`: salida de la versión en MicroPython.
- `figura5_reto_hx711.png` y `figura5_reto_hx711.py`: figura del paper y el script que la genera.

## Nota sobre la precisión en MicroPython
Durante la corrida de MicroPython se puso y se quitó el peso, por eso el resumen automático del archivo (163.57 g) no es válido. Se usó el tramo estable i = 54–84 (31 lecturas, media ≈ 385 314 cuentas), con el mismo peso que la prueba en C (media ≈ 383 366). Sin carga (i = 0–49) la desviación fue 0.20 g. Los tiempos de transferencia usan las 100 lecturas.
