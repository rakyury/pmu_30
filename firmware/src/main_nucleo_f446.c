/**
 ******************************************************************************
 * @file           : main_nucleo_f446.c
 * @brief          : Main program for Nucleo-F446RE development board
 * @author         : R2 m-sport
 * @date           : 2025-12-27
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This is a debug version of PMU-30 firmware for Nucleo-F446RE.
 * Used for testing logic engine, CAN integration, and config parsing
 * without power output hardware.
 *
 * Features enabled:
 *   - Config parsing (JSON)
 *   - Channel abstraction (6 simulated outputs)
 *   - Logic engine
 *   - CAN communication (CAN1)
 *   - Debug output via UART (ST-LINK VCP)
 *   - ADC inputs (5 channels)
 *   - PWM outputs (6 channels for testing)
 *
 ******************************************************************************
 */

#ifdef NUCLEO_F446RE

/* Includes ------------------------------------------------------------------*/
#include "stm32f4xx_hal.h"

/* Re-enable FreeRTOS stubs - test if this is the culprit */
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"

#include <stdio.h>
#include <string.h>

/* PMU modules - TEST: Enable includes only, not function calls */
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
// No LUA for now

/* Private define ------------------------------------------------------------*/
/* (FreeRTOS defines disabled for minimal test) */

/* Pin definitions */
#define USER_LED_PIN        GPIO_PIN_5
#define USER_LED_PORT       GPIOA
#define USER_BTN_PIN        GPIO_PIN_13
#define USER_BTN_PORT       GPIOC

/* Minimal set of globals needed for minimal test */

/* Private variables ---------------------------------------------------------*/
/* Peripheral handles */
UART_HandleTypeDef huart2;
UART_HandleTypeDef huart1;  /* ESP32 WiFi bridge - Arduino D8(TX)/D2(RX) = PA9/PA10 */
CAN_HandleTypeDef hcan1;
ADC_HandleTypeDef hadc1;
TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim2;
TIM_HandleTypeDef htim3;
IWDG_HandleTypeDef hiwdg;

/* Debug counters */
static volatile uint32_t g_tick_count = 0;
static volatile uint32_t g_can_rx_count = 0;
static volatile uint32_t g_can_tx_count = 0;
static volatile uint32_t g_logic_exec_count = 0;

/* Software tick counter for bare-metal mode (SysTick disabled) */
static volatile uint32_t g_soft_tick_ms = 0;

/* Digital inputs storage */
uint8_t g_digital_inputs[8] = {0};

/* PWM output state */
static uint16_t output_duty[6] = {0};
static uint8_t output_state[6] = {0};

/* HAL_GetTick override */
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

/* Private function prototypes */
static void SystemClock_Config(void);
static void GPIO_Init(void);
static void USART2_Init(void);
static void USART1_Init(void);  /* ESP32 WiFi bridge - Arduino D8/D2 */
static void ADC1_Init(void);
static void TIM_PWM_Init(void);
static void IWDG_Init(void);
static void DigitalInputs_Read(void);
static void Debug_PrintChannelStates(void);
static void Debug_PrintStatus(void);

/* PMU_PROFET_Init is defined in pmu_stubs.c */
extern void PMU_PROFET_Init(void);

/* Main function -------------------------------------------------------------*/

int main(void)
{
    /*======== ULTRA-MINIMAL WITH HAL TEST ========*/
    /* Disable all interrupts */
    __disable_irq();
    SysTick->CTRL = 0;
    SysTick->VAL = 0;

    /* Enable GPIOA clock */
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    for (volatile int i = 0; i < 10000; i++);

    /* PA5 = Output (LED) */
    GPIOA->MODER &= ~(3UL << (5 * 2));
    GPIOA->MODER |= (1UL << (5 * 2));

    /* LED ON - immediate visual feedback */
    GPIOA->BSRR = (1 << 5);

    /* Enable USART2 clock */
    RCC->APB1ENR |= RCC_APB1ENR_USART2EN;
    for (volatile int i = 0; i < 10000; i++);

    /* PA2 = AF7 (USART2 TX) */
    GPIOA->MODER &= ~(3UL << (2 * 2));
    GPIOA->MODER |= (2UL << (2 * 2));
    GPIOA->AFR[0] &= ~(0xFUL << (2 * 4));
    GPIOA->AFR[0] |= (7UL << (2 * 4));

    /* USART2: 115200 baud @ 16MHz HSI */
    USART2->CR1 = 0;
    USART2->BRR = 139;
    USART2->CR1 = USART_CR1_UE | USART_CR1_TE;
    for (volatile int i = 0; i < 1000; i++);

    /* Send 'A' to confirm main() reached */
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'A';

    /* LED OFF after UART setup */
    GPIOA->BSRR = (1 << (5 + 16));

    /* Test: Call HAL_Init */
    HAL_Init();
    SysTick->CTRL = 0;
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'B';

    /* SystemClock_Config */
    SystemClock_Config();
    SysTick->CTRL = 0;
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'C';

    /* Peripheral initialization */
    GPIO_Init();
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'D';

    USART2_Init();
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'E';

    USART1_Init();  /* ESP32 WiFi bridge - Arduino D8/D2 */
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = '3';

    ADC1_Init();
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'F';

    TIM_PWM_Init();
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'G';

    /* IWDG (Independent Watchdog) - 2 second timeout */
    IWDG_Init();
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'H';

    /* PMU Module initialization with progress markers */
    PMU_Config_Init();
    HAL_IWDG_Refresh(&hiwdg);
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'I';

    PMU_CAN_Init();
    HAL_IWDG_Refresh(&hiwdg);
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'J';

    PMU_ADC_Init();
    PMU_Protection_Init();
    HAL_IWDG_Refresh(&hiwdg);
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'K';

    PMU_Channel_Init();
    PMU_PROFET_Init();
    HAL_IWDG_Refresh(&hiwdg);
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'L';

    /* Register digital input channels (channel_id 50-57) */
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
    HAL_IWDG_Refresh(&hiwdg);

    PMU_Logic_Init();
    PMU_ChannelExec_Init();
    HAL_IWDG_Refresh(&hiwdg);
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'M';

    PMU_LED_Init();
    PMU_Logging_Init();
    HAL_IWDG_Refresh(&hiwdg);
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'N';

    PMU_ST_Init();
    HAL_IWDG_Refresh(&hiwdg);
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'O';

    if (PMU_ST_LoadSavedConfig()) {
        /* Config loaded successfully */
    }
    HAL_IWDG_Refresh(&hiwdg);
    while (!(USART2->SR & USART_SR_TXE)); USART2->DR = 'P';

    /* Enable interrupts */
    __enable_irq();
    SysTick->CTRL = 0;

    /* VCP stabilization delay with IWDG refresh */
    for (volatile uint32_t i = 0; i < 2000000; i++) {
        if ((i & 0x3FFFF) == 0) HAL_IWDG_Refresh(&hiwdg);
    }
    HAL_IWDG_Refresh(&hiwdg);

    /* Send READY message */
    {
        const char* msg = "\r\nREADY\r\n";
        while (*msg) {
            while (!(USART2->SR & USART_SR_TXE));
            USART2->DR = *msg++;
        }
        while (!(USART2->SR & USART_SR_TC));
    }

    /* Signal successful startup */
    PMU_LED_SignalStartupOK();

    /* Main loop */
    while (1) {
        /* Poll UART RX */
        if (USART2->SR & USART_SR_RXNE) {
            uint8_t rx_byte = (uint8_t)(USART2->DR & 0xFF);
            PMU_ST_ProcessByte(rx_byte);
        }

        static uint32_t loop_count = 0;
        static uint32_t input_count = 0;
        loop_count++;

        /* 1kHz tasks */
        if (++input_count >= 200) {
            input_count = 0;
            g_soft_tick_ms++;
            DigitalInputs_Read();
            PMU_ADC_Update();
            PMU_ChannelExec_Update();

            if (output_state[1]) {
                GPIOA->ODR |= (1 << 5);
            } else {
                GPIOA->ODR &= ~(1 << 5);
                PMU_LED_Update();
            }
            g_logic_exec_count++;
        }

        /* Protocol update and IWDG refresh */
        if ((loop_count % 200) == 0) {
            PMU_ST_Update();
            HAL_IWDG_Refresh(&hiwdg);
        }

        /* DEBUG: Send test byte on USART1 TX every ~1 second */
        static uint32_t usart1_test_counter = 0;
        if (++usart1_test_counter >= 200000) {
            usart1_test_counter = 0;
            while (!(USART1->SR & USART_SR_TXE)) {}
            USART1->DR = 0x55;  /* Send 'U' pattern */
        }

    }
}

/* Static function implementations follow below */

/* Dead code below - task implementations for later restoration */
#if 0
    /* unused */
    while (!(USART2->SR & USART_SR_TXE));
    USART2->DR = 'M';

    /* Load saved config from flash (if any) - after ST init */
    if (PMU_ST_LoadSavedConfig()) {
        /* Config loaded successfully - channels are ready */
    }
    HAL_IWDG_Refresh(&hiwdg);

    /* Send 'N' */
    while (!(USART2->SR & USART_SR_TXE));
    USART2->DR = 'N';

    /* Enable interrupts but keep SysTick disabled */
    __enable_irq();
    SysTick->CTRL = 0;

    /* Send 'O' (interrupts enabled) */
    while (!(USART2->SR & USART_SR_TXE));
    USART2->DR = 'O';

    /* Delay for ST-Link VCP to stabilize (~500ms)
     * The USB CDC-ACM interface needs time to enumerate before data can be received.
     * Without this delay, early UART transmissions may be lost.
     * Refresh IWDG during delay to prevent reset.
     */
    for (volatile uint32_t i = 0; i < 2000000; i++) {
        if ((i & 0x3FFFF) == 0) {  /* Every ~250K iterations (~60ms) */
            HAL_IWDG_Refresh(&hiwdg);
        }
    }
    HAL_IWDG_Refresh(&hiwdg);

    /* Send 'P' (after VCP delay) */
    while (!(USART2->SR & USART_SR_TXE));
    USART2->DR = 'P';

    /* Send newline and "READY" message */
    {
        const char* msg = "\r\nREADY\r\n";
        while (*msg) {
            while (!(USART2->SR & USART_SR_TXE));
            USART2->DR = *msg++;
        }
        while (!(USART2->SR & USART_SR_TC));
    }

    /* Signal successful startup with LED */
    PMU_LED_SignalStartupOK();

    SysTick->CTRL = 0;

    /* Main loop - poll UART RX and process MIN protocol */
    while (1) {
        /* Check if UART has received data (bare-metal polling)
         * MIN protocol handles TX/RX concurrency via its state machine.
         * No need to skip RX during TX - MIN's atomic TX and byte stuffing
         * ensure reliable framing even with concurrent operations.
         */
        if (USART2->SR & USART_SR_RXNE) {
            uint8_t rx_byte = (uint8_t)(USART2->DR & 0xFF);
            /* Pass to MIN protocol handler */
            PMU_ST_ProcessByte(rx_byte);
        }

        /* Counter-based timing since SysTick is disabled
         * At ~16MHz HSI, the loop runs approximately 200000 times/second
         * For 10Hz telemetry: call every ~20000 iterations
         */
        static uint32_t loop_count = 0;
        static uint32_t input_count = 0;
        loop_count++;

        /* Read digital inputs at ~1kHz (every 200 loops = ~1ms) */
        if (++input_count >= 200) {
            input_count = 0;
            g_soft_tick_ms++;  /* Increment software tick (~1ms resolution) */
            DigitalInputs_Read();
            PMU_ADC_Update();

            /* Channel Executor - processes all virtual channels (logic, timer, etc.) */
            PMU_ChannelExec_Update();

            /* LED (PA5) = state of power output 1 (priority over status LED) */
            if (output_state[1]) {
                GPIOA->ODR |= (1 << 5);
            } else {
                GPIOA->ODR &= ~(1 << 5);
                /* Only run status LED when output 1 is off */
                PMU_LED_Update();
            }

            g_logic_exec_count++;  /* Debug: count loop iterations */
        }

        /* MIN protocol update at ~1kHz (every 200 loops = ~1ms)
         * Handles retransmits, ACK timeouts, and telemetry streaming */
        if ((loop_count % 200) == 0) {
            PMU_ST_Update();

            /* Refresh IWDG watchdog (must be called within 2 seconds)
             * If main loop hangs, MCU will automatically reset */
            HAL_IWDG_Refresh(&hiwdg);
        }
    }
} /* end of old main() */
#endif /* disabled PMU init code */

/* All functions below are disabled for debugging - they use FreeRTOS and PMU modules */
#if 0

/* Task implementations ------------------------------------------------------*/

static void vControlTask(void *pvParameters)
{
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(1);  /* 1kHz */
    uint8_t logic_counter = 0;

    (void)pvParameters;

    for (;;) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        g_tick_count++;
        extern void PMU_SetCurrentTick(uint32_t);
        PMU_SetCurrentTick(g_tick_count);

        /* Read digital inputs */
        DigitalInputs_Read();

        /* Read ADC inputs */
        PMU_ADC_Update();

        /* Update channel abstraction */
        PMU_Channel_Update();

        /* Logic engine at 500Hz */
        if (++logic_counter >= 2) {
            logic_counter = 0;
            PMU_Logic_Execute();

            /* Channel Executor - handles all virtual channels (logic, timer, filter, etc.) */
            PMU_ChannelExec_Update();

            /* Update LED status patterns */
            PMU_LED_Update();

            g_logic_exec_count++;

#ifndef PMU_DISABLE_LUA
            PMU_Lua_Update();
#endif
        }

        /* Update protocol */
        PMU_Protocol_Update();

        /* Toggle LED every 500ms as heartbeat */
        if ((g_tick_count % 500) == 0) {
            LED_Toggle();
        }
    }
}

static void vProtectionTask(void *pvParameters)
{
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(1);

    (void)pvParameters;

    for (;;) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        PMU_Protection_Update();
    }
}

static void vCANTask(void *pvParameters)
{
    (void)pvParameters;

    for (;;) {
        PMU_CAN_Update();
        PMU_CanStream_Update();
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

static void vDebugTask(void *pvParameters)
{
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(1000);  /* 1Hz status output */

    (void)pvParameters;

    for (;;) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);

        /* Print periodic status */
        Debug_PrintStatus();
    }
}
#endif /* disabled FreeRTOS tasks */

/* Debug output functions ----------------------------------------------------*/

/* Debug output disabled - USART2 is shared with protocol communication */
/* If you need debug output, use a different UART or only enable before protocol init */
#define DEBUG_OUTPUT_ENABLED 0

static void Debug_Print(const char* msg)
{
#if DEBUG_OUTPUT_ENABLED
    HAL_UART_Transmit(&huart2, (uint8_t*)msg, strlen(msg), 100);
#else
    (void)msg; /* Suppress unused warning */
#endif
}

static void Debug_PrintStatus(void)
{
    char buf[128];

    snprintf(buf, sizeof(buf),
             "[%lu] Ticks: %lu | Logic: %lu | CAN RX: %lu TX: %lu\r\n",
             HAL_GetTick() / 1000,
             g_tick_count,
             g_logic_exec_count,
             g_can_rx_count,
             g_can_tx_count);
    Debug_Print(buf);

    /* Print channel states */
    Debug_PrintChannelStates();
}

static void Debug_PrintChannelStates(void)
{
    char buf[64];

#ifndef PMU_DISABLE_PROFET
    Debug_Print("  Outputs:  ");
    for (uint8_t i = 0; i < 6; i++) {
        PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(i);
        if (ch) {
            const char* state_str = "?";
            switch (ch->state) {
                case PMU_PROFET_STATE_OFF:   state_str = "OFF"; break;
                case PMU_PROFET_STATE_ON:    state_str = "ON"; break;
                case PMU_PROFET_STATE_PWM:   state_str = "PWM"; break;
                case PMU_PROFET_STATE_FAULT: state_str = "FLT"; break;
            }
            snprintf(buf, sizeof(buf), "[%d:%s] ", i, state_str);
            Debug_Print(buf);
        }
    }
    Debug_Print("\r\n");
#else
    Debug_Print("  Outputs: (PROFET disabled)\r\n");
#endif

    /* Print digital inputs */
    Debug_Print("  DIN:      ");
    for (uint8_t i = 0; i < 8; i++) {
        snprintf(buf, sizeof(buf), "[%d:%c] ", i, g_digital_inputs[i] ? '1' : '0');
        Debug_Print(buf);
    }
    Debug_Print("\r\n");
}

/* PWM Output control --------------------------------------------------------*/
/* Nucleo-F446RE PWM mapping:
 * Output 0 -> TIM1_CH1 (PA8)
 * Output 1 -> TIM1_CH2 (PA9)
 * Output 2 -> (not connected)
 * Output 3 -> (not connected)
 * Output 4 -> TIM3_CH1 (PB4)
 * Output 5 -> TIM3_CH2 (PB5)
 */
/* Note: output_duty[] and output_state[] declared at top of file */

/**
 * @brief Set PWM duty cycle for output channel
 * @param channel Output channel (0-5)
 * @param duty Duty cycle (0-1000 = 0-100%)
 */
void NucleoOutput_SetPWM(uint8_t channel, uint16_t duty)
{
    if (channel >= 6) return;
    if (duty > 1000) duty = 1000;

    output_duty[channel] = duty;

    /* Apply to hardware */
    switch (channel) {
        case 0: __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_1, duty); break;
        case 1: __HAL_TIM_SET_COMPARE(&htim1, TIM_CHANNEL_2, duty); break;
        case 4: __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_1, duty); break;
        case 5: __HAL_TIM_SET_COMPARE(&htim3, TIM_CHANNEL_2, duty); break;
        default: break;  /* Channels 2, 3 not connected */
    }
}

/**
 * @brief Set output state (ON/OFF)
 * @param channel Output channel (0-5)
 * @param state 0=OFF, 1=ON (100% duty)
 */
void NucleoOutput_SetState(uint8_t channel, uint8_t state)
{
    if (channel >= 6) return;

    output_state[channel] = state;

    if (state) {
        NucleoOutput_SetPWM(channel, 1000);  /* 100% duty */
    } else {
        NucleoOutput_SetPWM(channel, 0);     /* 0% duty */
    }
}

/**
 * @brief Get output state
 * @param channel Output channel (0-5)
 * @return 0=OFF, 1=ON
 */
uint8_t NucleoOutput_GetState(uint8_t channel)
{
    if (channel >= 6) return 0;
    return output_state[channel];
}

/**
 * @brief Get output duty cycle
 * @param channel Output channel (0-5)
 * @return Duty cycle (0-1000)
 */
uint16_t NucleoOutput_GetDuty(uint8_t channel)
{
    if (channel >= 6) return 0;
    return output_duty[channel];
}

/**
 * @brief Reset all outputs to OFF (for config reload)
 */
void NucleoOutput_Reset(void)
{
    for (uint8_t i = 0; i < 6; i++) {
        output_state[i] = 0;
        output_duty[i] = 0;
        NucleoOutput_SetPWM(i, 0);
    }
}

/* LED control ---------------------------------------------------------------*/

static void LED_Toggle(void)
{
    HAL_GPIO_TogglePin(USER_LED_PORT, USER_LED_PIN);
}

static void LED_Set(uint8_t state)
{
    HAL_GPIO_WritePin(USER_LED_PORT, USER_LED_PIN,
                      state ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

/* Peripheral initialization -------------------------------------------------*/

static void GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* Enable GPIO clocks */
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    /* User LED (PA5) */
    HAL_GPIO_WritePin(USER_LED_PORT, USER_LED_PIN, GPIO_PIN_RESET);
    GPIO_InitStruct.Pin = USER_LED_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(USER_LED_PORT, &GPIO_InitStruct);

    /* Digital inputs configuration */
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_PULLDOWN;  /* Pull-down for active-high inputs */
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;

    /* DIN0: PC13 - User Button (active-low, no pull needed) */
    GPIO_InitStruct.Pin = GPIO_PIN_13;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

    /* DIN1: PB1 (relocated from PC6 - now used for UART3 TX to ESP32) */
    /* DIN2: PC12 */
    GPIO_InitStruct.Pin = GPIO_PIN_12;
    GPIO_InitStruct.Pull = GPIO_PULLDOWN;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

    /* DIN1, DIN3-DIN7: PB1, PB2, PB12, PB13, PB14, PB15 */
    GPIO_InitStruct.Pin = GPIO_PIN_1 | GPIO_PIN_2 | GPIO_PIN_12 | GPIO_PIN_13 | GPIO_PIN_14 | GPIO_PIN_15;
    GPIO_InitStruct.Pull = GPIO_PULLDOWN;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
}

/* Digital input reading (g_digital_inputs declared at top of file) */

/* Debug counter for channel 50 updates */
static volatile uint32_t g_ch50_update_ok = 0;
static volatile uint32_t g_ch50_update_fail = 0;
uint32_t Debug_GetCh50UpdateOk(void) { return g_ch50_update_ok; }
uint32_t Debug_GetCh50UpdateFail(void) { return g_ch50_update_fail; }

static void DigitalInputs_Read(void)
{
    /* Read all digital inputs */
    g_digital_inputs[0] = !HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13);  /* Button active-low */
    g_digital_inputs[1] = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_1);    /* DIN1: PB1 (PC6 used for UART3 TX) */
    g_digital_inputs[2] = HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_12);
    g_digital_inputs[3] = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_2);
    g_digital_inputs[4] = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_15);
    g_digital_inputs[5] = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_14);
    g_digital_inputs[6] = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_13);
    g_digital_inputs[7] = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_12);

    /* Sync to channel system for source_channel linking
     * Digital inputs use channel_id 50-57 (50 + pin) */
    for (uint8_t i = 0; i < 8; i++) {
        HAL_StatusTypeDef result = PMU_Channel_UpdateValue(50 + i, g_digital_inputs[i]);
        /* Track channel 50 updates */
        if (i == 0) {
            if (result == HAL_OK) g_ch50_update_ok++;
            else g_ch50_update_fail++;
        }
    }
}

uint8_t DigitalInput_Get(uint8_t channel)
{
    if (channel >= 8) return 0;
    return g_digital_inputs[channel];
}

static void USART2_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* Enable clocks */
    __HAL_RCC_USART2_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();

    /* USART2 GPIO: PA2=TX, PA3=RX */
    GPIO_InitStruct.Pin = GPIO_PIN_2 | GPIO_PIN_3;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF7_USART2;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    /* USART2 configuration */
    huart2.Instance = USART2;
    huart2.Init.BaudRate = 115200;
    huart2.Init.WordLength = UART_WORDLENGTH_8B;
    huart2.Init.StopBits = UART_STOPBITS_1;
    huart2.Init.Parity = UART_PARITY_NONE;
    huart2.Init.Mode = UART_MODE_TX_RX;
    huart2.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart2.Init.OverSampling = UART_OVERSAMPLING_16;

    HAL_UART_Init(&huart2);

    /* USART2 interrupt disabled - using bare-metal polling instead */
    // HAL_NVIC_SetPriority(USART2_IRQn, 5, 0);
    // HAL_NVIC_EnableIRQ(USART2_IRQn);
}

/**
 * @brief USART1 Initialization for ESP32 WiFi bridge
 * @note  PA9=TX (D8), PA10=RX (D2) - Arduino connector
 *        Same SerialTransfer protocol as USB, enables WiFi connectivity
 */
static void USART1_Init(void)
{
    /* Enable clocks */
    __HAL_RCC_USART1_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();

    /* USART1 GPIO: PA9=TX (D8), PA10=RX (D2) - Arduino connector
     * Direct register access to ensure correct AF7 configuration */

    /* PA9: MODER = 10 (AF mode) */
    GPIOA->MODER &= ~(3UL << (9 * 2));
    GPIOA->MODER |= (2UL << (9 * 2));
    /* PA9: OSPEEDR = 11 (very high speed) */
    GPIOA->OSPEEDR |= (3UL << (9 * 2));
    /* PA9: PUPDR = 01 (pull-up) */
    GPIOA->PUPDR &= ~(3UL << (9 * 2));
    GPIOA->PUPDR |= (1UL << (9 * 2));
    /* PA9: AFR[1] bit 4-7 = 0111 (AF7 = USART1) */
    GPIOA->AFR[1] &= ~(0xFUL << ((9 - 8) * 4));
    GPIOA->AFR[1] |= (7UL << ((9 - 8) * 4));

    /* PA10: MODER = 10 (AF mode) */
    GPIOA->MODER &= ~(3UL << (10 * 2));
    GPIOA->MODER |= (2UL << (10 * 2));
    /* PA10: OSPEEDR = 11 (very high speed) */
    GPIOA->OSPEEDR |= (3UL << (10 * 2));
    /* PA10: PUPDR = 01 (pull-up) */
    GPIOA->PUPDR &= ~(3UL << (10 * 2));
    GPIOA->PUPDR |= (1UL << (10 * 2));
    /* PA10: AFR[1] bit 8-11 = 0111 (AF7 = USART1) */
    GPIOA->AFR[1] &= ~(0xFUL << ((10 - 8) * 4));
    GPIOA->AFR[1] |= (7UL << ((10 - 8) * 4));

    /* USART1: 115200 baud @ 16MHz HSI */
    USART1->CR1 = 0;
    USART1->BRR = 139;  /* 16MHz / 115200 = 138.89 */
    USART1->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;
}

static void CAN1_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    CAN_FilterTypeDef sFilterConfig;

    /* Enable clocks */
    __HAL_RCC_CAN1_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();

    /* CAN1 GPIO: PA11=RX, PA12=TX */
    GPIO_InitStruct.Pin = GPIO_PIN_11 | GPIO_PIN_12;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF9_CAN1;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    /* CAN1 configuration - 500 kbit/s @ 45 MHz APB1 */
    hcan1.Instance = CAN1;
    hcan1.Init.Prescaler = 5;
    hcan1.Init.Mode = CAN_MODE_NORMAL;
    hcan1.Init.SyncJumpWidth = CAN_SJW_1TQ;
    hcan1.Init.TimeSeg1 = CAN_BS1_15TQ;
    hcan1.Init.TimeSeg2 = CAN_BS2_2TQ;
    hcan1.Init.TimeTriggeredMode = DISABLE;
    hcan1.Init.AutoBusOff = ENABLE;
    hcan1.Init.AutoWakeUp = DISABLE;
    hcan1.Init.AutoRetransmission = ENABLE;
    hcan1.Init.ReceiveFifoLocked = DISABLE;
    hcan1.Init.TransmitFifoPriority = DISABLE;

    if (HAL_CAN_Init(&hcan1) != HAL_OK) {
        Debug_Print("[ERROR] CAN1 init failed!\r\n");
        return;
    }

    /* Configure filter to accept all messages */
    sFilterConfig.FilterBank = 0;
    sFilterConfig.FilterMode = CAN_FILTERMODE_IDMASK;
    sFilterConfig.FilterScale = CAN_FILTERSCALE_32BIT;
    sFilterConfig.FilterIdHigh = 0x0000;
    sFilterConfig.FilterIdLow = 0x0000;
    sFilterConfig.FilterMaskIdHigh = 0x0000;
    sFilterConfig.FilterMaskIdLow = 0x0000;
    sFilterConfig.FilterFIFOAssignment = CAN_FILTER_FIFO0;
    sFilterConfig.FilterActivation = ENABLE;

    if (HAL_CAN_ConfigFilter(&hcan1, &sFilterConfig) != HAL_OK) {
        Debug_Print("[ERROR] CAN1 filter config failed!\r\n");
        return;
    }

    /* Start CAN */
    if (HAL_CAN_Start(&hcan1) != HAL_OK) {
        Debug_Print("[ERROR] CAN1 start failed!\r\n");
        return;
    }

    Debug_Print("[OK] CAN1 initialized @ 500 kbit/s\r\n");
}

static void ADC1_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    ADC_ChannelConfTypeDef sConfig = {0};

    /* Enable clocks */
    __HAL_RCC_ADC1_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    /* Configure ADC GPIO pins */
    /* PA0 (A0), PA1 (A1), PA4 (A2) */
    GPIO_InitStruct.Pin = GPIO_PIN_0 | GPIO_PIN_1 | GPIO_PIN_4;
    GPIO_InitStruct.Mode = GPIO_MODE_ANALOG;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    /* PB0 (A3) */
    GPIO_InitStruct.Pin = GPIO_PIN_0;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    /* PC1 (A4) */
    GPIO_InitStruct.Pin = GPIO_PIN_1;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

    /* ADC1 configuration */
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

    if (HAL_ADC_Init(&hadc1) != HAL_OK) {
        Debug_Print("[ERROR] ADC1 init failed!\r\n");
        return;
    }

    /* Configure channel 0 as default */
    sConfig.Channel = ADC_CHANNEL_0;
    sConfig.Rank = 1;
    sConfig.SamplingTime = ADC_SAMPLETIME_56CYCLES;

    if (HAL_ADC_ConfigChannel(&hadc1, &sConfig) != HAL_OK) {
        Debug_Print("[ERROR] ADC1 channel config failed!\r\n");
        return;
    }

    Debug_Print("[OK] ADC1 initialized (5 channels)\r\n");
}

static void TIM_PWM_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    TIM_OC_InitTypeDef sConfigOC = {0};

    /* Enable clocks */
    __HAL_RCC_TIM1_CLK_ENABLE();
    __HAL_RCC_TIM2_CLK_ENABLE();
    __HAL_RCC_TIM3_CLK_ENABLE();

    /* TIM1: PA8 (CH1) - output 0
     * NOTE: PA9 (CH2) removed - used for USART1 TX (ESP32 WiFi bridge) */
    GPIO_InitStruct.Pin = GPIO_PIN_8;  /* Only PA8, not PA9! */
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF1_TIM1;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    /* TIM3: PB4 (CH1), PB5 (CH2) - outputs 4, 5 */
    GPIO_InitStruct.Pin = GPIO_PIN_4 | GPIO_PIN_5;
    GPIO_InitStruct.Alternate = GPIO_AF2_TIM3;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    /* TIM1 configuration @ 1kHz PWM */
    htim1.Instance = TIM1;
    htim1.Init.Prescaler = 179;  /* 180MHz / 180 = 1MHz */
    htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim1.Init.Period = 999;     /* 1MHz / 1000 = 1kHz */
    htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim1.Init.RepetitionCounter = 0;
    htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;

    if (HAL_TIM_PWM_Init(&htim1) != HAL_OK) {
        Debug_Print("[ERROR] TIM1 init failed!\r\n");
        return;
    }

    /* PWM configuration */
    sConfigOC.OCMode = TIM_OCMODE_PWM1;
    sConfigOC.Pulse = 0;
    sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
    sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;

    HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, TIM_CHANNEL_1);
    HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, TIM_CHANNEL_2);
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1);
    HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_2);

    /* TIM3 configuration */
    htim3.Instance = TIM3;
    htim3.Init.Prescaler = 89;   /* 90MHz / 90 = 1MHz (APB1) */
    htim3.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim3.Init.Period = 999;
    htim3.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;

    if (HAL_TIM_PWM_Init(&htim3) != HAL_OK) {
        Debug_Print("[ERROR] TIM3 init failed!\r\n");
        return;
    }

    HAL_TIM_PWM_ConfigChannel(&htim3, &sConfigOC, TIM_CHANNEL_1);
    HAL_TIM_PWM_ConfigChannel(&htim3, &sConfigOC, TIM_CHANNEL_2);
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_2);

    Debug_Print("[OK] PWM timers initialized (6 channels @ 1kHz)\r\n");
}

/**
 * @brief IWDG Independent Watchdog initialization
 *
 * Configures ~2 second timeout. If HAL_IWDG_Refresh() is not called
 * within this time, MCU will automatically reset.
 *
 * LSI oscillator: ~32kHz (can vary 17-47kHz)
 * Prescaler: 64 -> counter clock = 32000/64 = 500 Hz
 * Reload: 1000 -> timeout = 1000/500 = 2 seconds
 */
static void IWDG_Init(void)
{
    hiwdg.Instance = IWDG;
    hiwdg.Init.Prescaler = IWDG_PRESCALER_64;   /* LSI / 64 = ~500Hz */
    hiwdg.Init.Reload = 1000;                    /* 1000 / 500 = 2 sec timeout */

    if (HAL_IWDG_Init(&hiwdg) != HAL_OK) {
        /* IWDG init failed - blink LED rapidly */
        for (int i = 0; i < 10; i++) {
            GPIOA->ODR ^= (1 << 5);
            for (volatile int d = 0; d < 100000; d++);
        }
    }
}

static void SystemClock_Config(void)
{
    /* SIMPLE CONFIG: Just use HSI @ 16 MHz - no PLL, no waiting */
    /* HAL functions need SysTick for timeouts, but we disabled it */
    /* So we configure clocks directly via registers */

    /* Enable power interface clock */
    RCC->APB1ENR |= RCC_APB1ENR_PWREN;

    /* Set voltage scaling to Scale 1 (required for high freq, but ok for 16MHz too) */
    PWR->CR |= PWR_CR_VOS;

    /* HSI is already on by default after reset */
    /* Just make sure SYSCLK = HSI (should already be default) */
    RCC->CFGR &= ~RCC_CFGR_SW;  /* SW = 00 = HSI */

    /* Wait for HSI to be used as system clock */
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_HSI);

    /* Configure APB1 = HCLK/1 = 16 MHz, APB2 = HCLK/1 = 16 MHz */
    RCC->CFGR &= ~(RCC_CFGR_PPRE1 | RCC_CFGR_PPRE2 | RCC_CFGR_HPRE);

    /* Update SystemCoreClock variable */
    SystemCoreClock = 16000000;
}

/* Error handlers ------------------------------------------------------------*/

void Error_Handler(void)
{
    __disable_irq();
    while (1) {
        LED_Toggle();
        for (volatile int i = 0; i < 500000; i++);
    }
}

void HardFault_Handler(void)
{
    while (1) {
        LED_Set(1);
    }
}

/* UART interrupt handlers - disabled for bare-metal polling mode */
#if 0

/**
 * @brief USART2 IRQ handler
 */
void USART2_IRQHandler(void)
{
    HAL_UART_IRQHandler(&huart2);
}

/* Protocol RX buffer for interrupt reception */
static uint8_t uart_rx_byte;

/* Debug counters for protocol diagnostics */
volatile uint32_t g_uart_rx_count = 0;
volatile uint8_t g_last_rx_byte = 0;

/**
 * @brief UART RX complete callback - called when a byte is received
 */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART2) {
        /* Debug: count received bytes and toggle LED */
        g_uart_rx_count++;
        g_last_rx_byte = uart_rx_byte;

        /* Toggle LED on EVERY byte to show activity */
        HAL_GPIO_TogglePin(USER_LED_PORT, USER_LED_PIN);

        /* Pass received byte to protocol handler */
        PMU_Protocol_ProcessData(&uart_rx_byte, 1);

        /* Re-enable RX interrupt for next byte */
        HAL_UART_Receive_IT(&huart2, &uart_rx_byte, 1);
    }
}

/**
 * @brief Start protocol UART reception (called after protocol init)
 */
void Protocol_StartUartReception(void)
{
    /* Start interrupt-driven reception */
    HAL_StatusTypeDef status = HAL_UART_Receive_IT(&huart2, &uart_rx_byte, 1);

    /* If failed, blink LED rapidly (bare-metal, no HAL_Delay) */
    if (status != HAL_OK) {
        for (int i = 0; i < 20; i++) {
            GPIOA->ODR ^= (1 << 5);
            for (volatile int d = 0; d < 50000; d++);
        }
    }
}

#endif /* disabled functions for debugging */

#endif /* NUCLEO_F446RE */
