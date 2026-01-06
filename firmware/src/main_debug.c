/**
 * Debug version of main_nucleo_f446.c
 * Same structure and includes, but PMU modules disabled
 */

#ifdef DEBUG_MAIN_ONLY

/* Same includes as main_nucleo_f446.c */
#include "stm32f4xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"

#include <stdio.h>
#include <string.h>

/* PMU modules - SAME includes as main_nucleo_f446.c */
#include "pmu_config.h"
#include "pmu_can.h"
#include "pmu_adc.h"
#include "pmu_protection.h"
#include "pmu_logic.h"
#include "pmu_logging.h"
#include "pmu_protocol.h"
#include "pmu_channel.h"
#include "pmu_can_stream.h"
#include "pmu_channel_exec.h"
#include "pmu_led.h"
#include "pmu_serial_transfer_port.h"

#ifndef PMU_DISABLE_LUA
#include "pmu_lua.h"
#endif

/* Same defines and variables as main_nucleo_f446.c */
#define TASK_CONTROL_PRIORITY       (configMAX_PRIORITIES - 1)
#define TASK_PROTECTION_PRIORITY    (configMAX_PRIORITIES - 2)
#define TASK_CAN_PRIORITY           (configMAX_PRIORITIES - 3)
#define TASK_DEBUG_PRIORITY         (tskIDLE_PRIORITY + 2)

#define TASK_CONTROL_STACK_SIZE     (128)
#define TASK_PROTECTION_STACK_SIZE  (96)
#define TASK_CAN_STACK_SIZE         (128)
#define TASK_DEBUG_STACK_SIZE       (128)

#define USER_LED_PIN        GPIO_PIN_5
#define USER_LED_PORT       GPIOA
#define USER_BTN_PIN        GPIO_PIN_13
#define USER_BTN_PORT       GPIOC

static TaskHandle_t xControlTaskHandle = NULL;
static TaskHandle_t xProtectionTaskHandle = NULL;
static TaskHandle_t xCANTaskHandle = NULL;
static TaskHandle_t xDebugTaskHandle = NULL;

UART_HandleTypeDef huart2;
CAN_HandleTypeDef hcan1;
ADC_HandleTypeDef hadc1;
TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim2;
TIM_HandleTypeDef htim3;
IWDG_HandleTypeDef hiwdg;

static volatile uint32_t g_tick_count = 0;
static volatile uint32_t g_can_rx_count = 0;
static volatile uint32_t g_can_tx_count = 0;
static volatile uint32_t g_logic_exec_count = 0;
static volatile uint32_t g_soft_tick_ms = 0;

uint8_t g_digital_inputs[8] = {0};
static uint16_t output_duty[6] = {0};
static uint8_t output_state[6] = {0};

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

/* NucleoOutput functions - same as main_nucleo_f446.c */
void NucleoOutput_SetPWM(uint8_t channel, uint16_t duty)
{
    if (channel >= 6) return;
    if (duty > 1000) duty = 1000;
    output_duty[channel] = duty;
    switch (channel) {
        case 0: __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, duty); break;
        case 1: __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_2, duty); break;
        case 4: __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, duty); break;
        case 5: __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_2, duty); break;
        default: break;
    }
}

void NucleoOutput_SetState(uint8_t channel, uint8_t state)
{
    if (channel >= 6) return;
    output_state[channel] = state;
    if (state) {
        NucleoOutput_SetPWM(channel, 1000);
    } else {
        NucleoOutput_SetPWM(channel, 0);
    }
}

void NucleoOutput_Reset(void)
{
    for (uint8_t i = 0; i < 6; i++) {
        output_state[i] = 0;
        output_duty[i] = 0;
        NucleoOutput_SetPWM(i, 0);
    }
}

static void SystemClock_Config(void);
static void GPIO_Init(void);
static void USART2_Init(void);
static void IWDG_Init(void);
static void ADC1_Init(void);
static void TIM_PWM_Init(void);

int main(void)
{
    /* ABSOLUTE FIRST - LED blink test at 115200 baud */
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
        const char* msg = "DBG-MAIN-START\r\n";
        for (const char* p = msg; *p; p++) {
            while (!(USART2->SR & USART_SR_TXE));
            USART2->DR = *p;
        }
        while (!(USART2->SR & USART_SR_TC));

        /* Blink LED 3 times at startup */
        for (int i = 0; i < 3; i++) {
            GPIOA->BSRR = (1 << 5);  /* LED ON */
            for (volatile uint32_t d = 0; d < 400000; d++);
            GPIOA->BSRR = (1 << (5 + 16));  /* LED OFF */
            for (volatile uint32_t d = 0; d < 400000; d++);
        }
    }

    /* Disable SysTick and interrupts */
    __disable_irq();
    SysTick->CTRL = 0;

    /* HAL_Init */
    HAL_Init();
    SysTick->CTRL = 0;

    /* SystemClock_Config */
    SystemClock_Config();
    SysTick->CTRL = 0;

    /* Peripheral initialization */
    GPIO_Init();
    USART2_Init();

    /* After HAL USART init - send confirmation at 115200 */
    {
        const char* debug_msg = "DBG:HAL-OK\r\n";
        while (*debug_msg) {
            while (!(USART2->SR & USART_SR_TXE));
            USART2->DR = *debug_msg++;
        }
        while (!(USART2->SR & USART_SR_TC));
    }

    ADC1_Init();
    TIM_PWM_Init();
    IWDG_Init();

    /* PMU modules - same as main_nucleo_f446.c */
    PMU_Config_Init();
    /* PMU_CAN_Init(); - stubbed */
    /* PMU_ADC_Init(); - stubbed */
    PMU_Protection_Init();
    PMU_Channel_Init();
    PMU_PROFET_Init();

    /* Register digital input channels (channel_id 50-57) - same as main */
    for (uint8_t i = 0; i < 8; i++) {
        PMU_Channel_t din_channel = {0};
        din_channel.channel_id = 50 + i;
        snprintf(din_channel.name, sizeof(din_channel.name), "DIN%d", i);
        din_channel.hw_class = PMU_CHANNEL_CLASS_INPUT_SWITCH;
        din_channel.min_value = 0;
        din_channel.max_value = 1;
        din_channel.physical_index = i;
        din_channel.flags = PMU_CHANNEL_FLAG_ENABLED;
        PMU_Channel_Register(&din_channel);
    }

    PMU_Logic_Init();
    PMU_ChannelExec_Init();
    PMU_LED_Init();
    PMU_Logging_Init();
    PMU_ST_Init();

    HAL_IWDG_Refresh(&hiwdg);

    /* Load saved config from flash (if any) - same as main */
    if (PMU_ST_LoadSavedConfig()) {
        /* Config loaded successfully */
    }

    /* Enable interrupts but keep SysTick disabled */
    __enable_irq();
    SysTick->CTRL = 0;

    /* Delay for ST-Link VCP to stabilize */
    for (volatile uint32_t i = 0; i < 2000000; i++);

    /* Send ready message */
    {
        const char* msg = "DBG-MAIN-READY\r\n";
        while (*msg) {
            while (!(USART2->SR & USART_SR_TXE));
            USART2->DR = *msg++;
        }
        while (!(USART2->SR & USART_SR_TC));
    }

    /* Signal successful startup with LED - SKIP for debugging */
    /* PMU_LED_SignalStartupOK(); */

    SysTick->CTRL = 0;

    /* Main loop - SIMPLIFIED for debugging */
    static uint32_t counter = 0;
    while (1) {
        /* Check if UART has received data */
        if (USART2->SR & USART_SR_RXNE) {
            uint8_t rx_byte = (uint8_t)(USART2->DR & 0xFF);
            PMU_ST_ProcessByte(rx_byte);
        }

        static uint32_t loop_count = 0;
        static uint32_t input_count = 0;
        loop_count++;

        if (++input_count >= 200) {
            input_count = 0;
            g_soft_tick_ms++;

            /* Read digital inputs */
            g_digital_inputs[0] = !HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13);
            for (uint8_t i = 0; i < 8; i++) {
                PMU_Channel_UpdateValue(50 + i, g_digital_inputs[i]);
            }

            PMU_ADC_Update();
            PMU_ChannelExec_Update();

            /* LED control - same as main_nucleo_f446.c */
            if (output_state[1]) {
                GPIOA->ODR |= (1 << 5);
            } else {
                GPIOA->ODR &= ~(1 << 5);
                PMU_LED_Update();
            }

            g_logic_exec_count++;

            /* Debug output every second */
            if (g_soft_tick_ms % 1000 == 0) {
                GPIOA->ODR ^= (1 << 5);  /* Toggle LED */

                /* Print counter */
                char buf[32];
                int len = 0;
                buf[len++] = 'L';
                buf[len++] = 'P';
                buf[len++] = '=';
                uint32_t n = counter++;
                char num[12];
                int ni = 0;
                do { num[ni++] = '0' + (n % 10); n /= 10; } while (n > 0);
                while (ni > 0) buf[len++] = num[--ni];
                buf[len++] = '\r';
                buf[len++] = '\n';

                for (int i = 0; i < len; i++) {
                    while (!(USART2->SR & USART_SR_TXE));
                    USART2->DR = buf[i];
                }
                while (!(USART2->SR & USART_SR_TC));
            }
        }

        /* MIN protocol update and watchdog refresh */
        if ((loop_count % 200) == 0) {
            PMU_ST_Update();
            HAL_IWDG_Refresh(&hiwdg);
        }
    }
}

/* Copied from main_nucleo_f446.c */
static void SystemClock_Config(void)
{
    RCC->APB1ENR |= RCC_APB1ENR_PWREN;
    PWR->CR |= PWR_CR_VOS;
    RCC->CFGR &= ~RCC_CFGR_SW;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_HSI);
    RCC->CFGR &= ~(RCC_CFGR_PPRE1 | RCC_CFGR_PPRE2 | RCC_CFGR_HPRE);
    SystemCoreClock = 16000000;
}

static void GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    /* LED on PA5 */
    GPIO_InitStruct.Pin = GPIO_PIN_5;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    /* User button PC13 */
    GPIO_InitStruct.Pin = GPIO_PIN_13;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);
}

static void USART2_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_USART2_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();

    GPIO_InitStruct.Pin = GPIO_PIN_2 | GPIO_PIN_3;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF7_USART2;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    huart2.Instance = USART2;
    huart2.Init.BaudRate = 115200;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;
    HAL_UART_Init(&huart2);
}

static void IWDG_Init(void)
{
    hiwdg.Instance = IWDG;
    hiwdg.Init.Prescaler = IWDG_PRESCALER_64;
    hiwdg.Init.Reload = 1000;
    HAL_IWDG_Init(&hiwdg);
}

static void ADC1_Init(void)
{
    __HAL_RCC_ADC1_CLK_ENABLE();
    hadc1.Instance = ADC1;
    hadc1.Init.ClockPrescaler = ADC_CLOCK_SYNC_PCLK_DIV4;
    hadc1.Init.Resolution = ADC_RESOLUTION_12B;
    hadc1.Init.ScanConvMode = DISABLE;
    hadc1.Init.ContinuousConvMode = DISABLE;
    hadc1.Init.DiscontinuousConvMode = DISABLE;
    hadc1.Init.ExternalTrigConvEdge = ADC_EXTERNALTRIGCONVEDGE_NONE;
    hadc1.Init.ExternalTrigConv = ADC_SOFTWARE_START;
    hadc1.Init.DataAlign = ADC_DATAALIGN_RIGHT;
    hadc1.Init.NbrOfConversion = 1;
    hadc1.Init.DMAContinuousRequests = DISABLE;
    hadc1.Init.EOCSelection = ADC_EOC_SINGLE_CONV;
    HAL_ADC_Init(&hadc1);
}

static void TIM_PWM_Init(void)
{
    __HAL_RCC_TIM2_CLK_ENABLE();
    htim2.Instance = TIM2;
    htim2.Init.Prescaler = 15;
    htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim2.Init.Period = 1000;
    htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    HAL_TIM_PWM_Init(&htim2);
}

void Error_Handler(void)
{
    __disable_irq();
    while (1) {
        GPIOA->ODR ^= (1 << 5);
        for (volatile int i = 0; i < 500000; i++);
    }
}

void HardFault_Handler(void)
{
    while (1) {
        GPIOA->BSRR = (1 << 5);
    }
}

#endif /* DEBUG_MAIN_ONLY */
