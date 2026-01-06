/**
 * Startup test for main_nucleo_f446.c debugging
 * Same includes and structure, but just blinks + UART
 */

#ifdef STARTUP_TEST_MODE

#include "stm32f4xx_hal.h"
#include <stdint.h>

/* Same FreeRTOS includes as main_nucleo_f446.c to catch any init issues */
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"

/* Peripheral handles - same as main_nucleo_f446.c */
UART_HandleTypeDef huart2;
IWDG_HandleTypeDef hiwdg;

/* Software tick counter (same as main) */
static volatile uint32_t g_soft_tick_ms = 0;

uint32_t HAL_GetTick(void)
{
    static uint32_t call_count = 0;
    if (g_soft_tick_ms == 0) {
        call_count++;
        if ((call_count & 0x1FF) == 0) {
            return call_count >> 9;
        }
    }
    return g_soft_tick_ms;
}

int main(void)
{
    /* Same early init as main_nucleo_f446.c */
    {
        /* Enable GPIOA clock */
        RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
        for (volatile int i = 0; i < 1000; i++);

        /* PA5 = Output for LED */
        GPIOA->MODER &= ~(3UL << (5 * 2));
        GPIOA->MODER |= (1UL << (5 * 2));

        /* Enable USART2 clock */
        RCC->APB1ENR |= RCC_APB1ENR_USART2EN;
        for (volatile int i = 0; i < 1000; i++);

        /* PA2 = AF7 (USART2 TX) */
        GPIOA->MODER &= ~(3UL << (2 * 2));
        GPIOA->MODER |= (2UL << (2 * 2));
        GPIOA->AFR[0] &= ~(0xFUL << (2 * 4));
        GPIOA->AFR[0] |= (7UL << (2 * 4));

        /* USART2: 115200 baud @ 16MHz HSI, BRR = 16M/115200 = 139 */
        USART2->CR1 = 0;
        USART2->BRR = 139;
        USART2->CR1 = USART_CR1_UE | USART_CR1_TE;
        for (volatile int i = 0; i < 100; i++);

        /* Send startup message */
        const char* msg = "STARTUP-TEST-OK\r\n";
        for (const char* p = msg; *p; p++) {
            while (!(USART2->SR & USART_SR_TXE));
            USART2->DR = *p;
        }
        while (!(USART2->SR & USART_SR_TC));
    }

    /* Main blink loop */
    uint32_t counter = 0;
    while (1) {
        /* Toggle LED */
        if (GPIOA->ODR & (1 << 5)) {
            GPIOA->BSRR = (1 << (5 + 16));  /* LED OFF */
        } else {
            GPIOA->BSRR = (1 << 5);          /* LED ON */
        }

        /* Print counter */
        char buf[32];
        int len = 0;
        buf[len++] = 'S';
        buf[len++] = 'T';
        buf[len++] = '=';

        uint32_t n = counter;
        char num[12];
        int ni = 0;
        do {
            num[ni++] = '0' + (n % 10);
            n /= 10;
        } while (n > 0);
        while (ni > 0) {
            buf[len++] = num[--ni];
        }
        buf[len++] = '\r';
        buf[len++] = '\n';

        for (int i = 0; i < len; i++) {
            while (!(USART2->SR & USART_SR_TXE));
            USART2->DR = buf[i];
        }
        while (!(USART2->SR & USART_SR_TC));

        counter++;

        /* Delay ~500ms at 16MHz */
        for (volatile uint32_t d = 0; d < 800000; d++);
    }
}

#endif /* STARTUP_TEST_MODE */
