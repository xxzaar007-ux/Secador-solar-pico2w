#include <stdio.h>
#include <math.h>
#include "pico/stdlib.h"
#include "hardware/sync.h"

#define PIN_DT        14
#define PIN_SCK       15
#define N             100
#define ESCALA        450.71668f
#define CICLOS_PULSO  40

static inline void pausa_pulso(void) {
    busy_wait_at_least_cycles(CICLOS_PULSO);
}

static bool hx711_esperar(uint32_t timeout_ms) {
    absolute_time_t limite = make_timeout_time_ms(timeout_ms);
    while (gpio_get(PIN_DT)) {
        if (time_reached(limite)) return false;
        tight_loop_contents();
    }
    return true;
}

static int32_t hx711_bits(void) {
    uint32_t irq = save_and_disable_interrupts();
    uint32_t v = 0;
    for (int i = 0; i < 24; i++) {
        gpio_put(PIN_SCK, 1);
        pausa_pulso();
        v = (v << 1) | gpio_get(PIN_DT);
        gpio_put(PIN_SCK, 0);
        pausa_pulso();
    }
    gpio_put(PIN_SCK, 1); pausa_pulso();
    gpio_put(PIN_SCK, 0); pausa_pulso();
    restore_interrupts(irq);

    if (v & 0x800000) v |= 0xFF000000;
    return (int32_t)v;
}

int main(void) {
    stdio_init_all();
    gpio_init(PIN_DT);  gpio_set_dir(PIN_DT, GPIO_IN);
    gpio_init(PIN_SCK); gpio_set_dir(PIN_SCK, GPIO_OUT); gpio_put(PIN_SCK, 0);

    while (!stdio_usb_connected()) sleep_ms(100);
    sleep_ms(500);

    static int32_t crudos[N];
    static uint32_t tiempos[N];

    printf("\n=== HX711 en C (Pico SDK) ===\n");
    printf("i,crudo,t_transfer_us\n");
    for (int i = 0; i < N; i++) {
        if (!hx711_esperar(1000)) {
            printf("ERROR: HX711 no responde (revisa DT, SCK, VCC, GND)\n");
            while (true) sleep_ms(1000);
        }
        uint64_t t0 = time_us_64();
        crudos[i] = hx711_bits();
        tiempos[i] = (uint32_t)(time_us_64() - t0);
        printf("%d,%ld,%lu\n", i, (long)crudos[i], (unsigned long)tiempos[i]);
    }

    uint32_t n = 0;
    uint64_t inicio = time_us_64();
    while (time_us_64() - inicio < 10000000ULL) {
        if (hx711_esperar(1000)) { hx711_bits(); n++; }
    }

    double suma_t = 0, suma_c = 0;
    uint32_t t_min = tiempos[0], t_max = tiempos[0];
    for (int i = 0; i < N; i++) {
        suma_t += tiempos[i];
        suma_c += crudos[i];
        if (tiempos[i] < t_min) t_min = tiempos[i];
        if (tiempos[i] > t_max) t_max = tiempos[i];
    }
    double media_t = suma_t / N;
    double media_c = suma_c / N;
    double var = 0;
    for (int i = 0; i < N; i++) var += (crudos[i] - media_c) * (crudos[i] - media_c);
    double desv_c = sqrt(var / (N - 1));

    printf("\n----- RESUMEN C (Pico SDK) -----\n");
    printf("Tiempo de transferencia: media %.1f us (min %lu, max %lu)\n",
           media_t, (unsigned long)t_min, (unsigned long)t_max);
    printf("CPU ocupada por lectura : %.3f %% (a 10 lecturas/s)\n", media_t / 100000.0 * 100.0);
    printf("Desviacion estandar     : %.1f cuentas\n", desv_c);
    if (ESCALA != 0.0f)
        printf("Desviacion estandar     : %.2f g\n", desv_c / fabs(ESCALA));
    printf("Lecturas en 10 s        : %lu (%.1f por segundo)\n", (unsigned long)n, n / 10.0);

    while (true) sleep_ms(1000);
}
