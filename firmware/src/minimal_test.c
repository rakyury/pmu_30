/**
 * Minimal Blink + UART Test for Nucleo-F446RE
 * Tests: LED (PA5), UART TX (PA2 @ 115200)
 *
 * To build: Replace main_nucleo_f446.c with this file in platformio.ini
 * Or add -D MINIMAL_TEST_MODE to build_flags
 */

#ifdef MINIMAL_TEST_MODE

#include "stm32f4xx_hal.h"
#include <stdint.h>

/* Minimal init - no FreeRTOS, no HAL beyond basics */
int main(void)
{
    /* Disable all interrupts */
    __disable_irq();

    /* Reset SysTick */
    SysTick->CTRL = 0;
    SysTick->VAL = 0;

    /*--------------------- LED Setup (PA5) ---------------------*/
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;  /* Enable GPIOA clock */

    /* Brief delay for clock to stabilize */
    for (volatile int i = 0; i < 10000; i++);

    /* PA5 = Output, Push-Pull */
    GPIOA->MODER &= ~(3UL << (5 * 2));   /* Clear mode bits */
    GPIOA->MODER |= (1UL << (5 * 2));    /* Output mode */
    GPIOA->OTYPER &= ~(1UL << 5);        /* Push-pull */
    GPIOA->OSPEEDR |= (3UL << (5 * 2));  /* High speed */
    GPIOA->PUPDR &= ~(3UL << (5 * 2));   /* No pull */

    /* LED ON - immediate visual feedback */
    GPIOA->BSRR = (1 << 5);

    /*--------------------- UART Setup (PA2 TX) ---------------------*/
    RCC->APB1ENR |= RCC_APB1ENR_USART2EN;  /* Enable USART2 clock */

    /* Delay for clock to stabilize */
    for (volatile int i = 0; i < 10000; i++);

    /* PA2 = AF7 (USART2_TX) */
    GPIOA->MODER &= ~(3UL << (2 * 2));
    GPIOA->MODER |= (2UL << (2 * 2));     /* Alternate function */
    GPIOA->OTYPER &= ~(1UL << 2);         /* Push-pull */
    GPIOA->OSPEEDR |= (3UL << (2 * 2));   /* High speed */
    GPIOA->AFR[0] &= ~(0xFUL << (2 * 4)); /* Clear AF bits */
    GPIOA->AFR[0] |= (7UL << (2 * 4));    /* AF7 = USART2 */

    /* USART2 config: 115200 baud @ 16MHz HSI
     * BRR = f_clk / baud = 16000000 / 115200 = 138.89 ≈ 139
     * With oversampling by 16: BRR = 139 = 0x8B */
    USART2->CR1 = 0;                       /* Disable USART */
    USART2->CR2 = 0;                       /* 1 stop bit */
    USART2->CR3 = 0;                       /* No flow control */
    USART2->BRR = 139;                     /* 115200 baud */
    USART2->CR1 = USART_CR1_UE | USART_CR1_TE;  /* Enable USART + TX */

    /* Wait for TX enable */
    for (volatile int i = 0; i < 1000; i++);

    /* LED OFF after UART setup */
    GPIOA->BSRR = (1 << (5 + 16));

    /*--------------------- Send startup message ---------------------*/
    const char* msg = "\r\n*** MINIMAL TEST OK ***\r\n";
    for (const char* p = msg; *p; p++) {
        while (!(USART2->SR & USART_SR_TXE));  /* Wait for TX empty */
        USART2->DR = *p;
    }
    while (!(USART2->SR & USART_SR_TC));  /* Wait for TX complete */

    /*--------------------- Main loop: Blink + print ---------------------*/
    uint32_t counter = 0;
    while (1) {
        /* Toggle LED */
        if (GPIOA->ODR & (1 << 5)) {
            GPIOA->BSRR = (1 << (5 + 16));  /* LED OFF */
        } else {
            GPIOA->BSRR = (1 << 5);          /* LED ON */
        }

        /* Print counter every blink */
        char buf[32];
        int len = 0;
        buf[len++] = 'C';
        buf[len++] = 'N';
        buf[len++] = 'T';
        buf[len++] = '=';

        /* Simple number to string */
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

#endif /* MINIMAL_TEST_MODE */
