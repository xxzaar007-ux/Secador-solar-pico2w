#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/sync.h"

#define PIN_DT   14
#define PIN_SCK  15
#define N        100


static int32_t hx711_leer(uint32_t *t_us) {
    while (gpio_get(PIN_DT)) tight_loop_contents();  

    uint32_t irq = save_and_disable_interrupts();    
    uint64_t t0 = time_us_64();
    uint32_t v = 0;
    for (int i = 0; i < 24; i++) {
        gpio_put(PIN_SCK, 1);
        busy_wait_us_32(1);                          
        v = (v << 1) | gpio_get(PIN_DT);
        gpio_put(PIN_SCK, 0);
        busy_wait_us_32(1);
    }
    gpio_put(PIN_SCK, 1); busy_wait_us_32(1);        
    gpio_put(PIN_SCK, 0); busy_wait_us_32(1);
    *t_us = (uint32_t)(time_us_64() - t0);
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

    printf("i,crudo,t_transfer_us,t_total_us\n");
    for (int i = 0; i < N; i++) {
        uint32_t tt;
        uint64_t t0 = time_us_64();
        int32_t c = hx711_leer(&tt);
        uint32_t total = (uint32_t)(time_us_64() - t0);
        printf("%d,%ld,%lu,%lu\n", i, (long)c, (unsigned long)tt, (unsigned long)total);
    }

    uint32_t n = 0, tt;
    uint64_t inicio = time_us_64();
    while (time_us_64() - inicio < 10000000ULL) { hx711_leer(&tt); n++; }
    printf("lecturas_10s,%lu\n", (unsigned long)n);

    while (true) sleep_ms(1000);
}
