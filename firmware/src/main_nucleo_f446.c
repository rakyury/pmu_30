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
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"

#include <stdio.h>
#include <string.h>

/* PMU modules */
#include "pmu_config.h"
#include "pmu_can.h"
#include "pmu_adc.h"
#include "pmu_protection.h"
#include "pmu_logic.h"
#include "pmu_logging.h"
#include "pmu_protocol.h"
#include "pmu_config_json.h"
#include "pmu_channel.h"
#include "pmu_logic_functions.h"
#include "pmu_can_stream.h"

#ifndef PMU_DISABLE_LUA
#include "pmu_lua.h"
#endif

/* Private define ------------------------------------------------------------*/
#define TASK_CONTROL_PRIORITY       (configMAX_PRIORITIES - 1)
#define TASK_PROTECTION_PRIORITY    (configMAX_PRIORITIES - 2)
#define TASK_CAN_PRIORITY           (configMAX_PRIORITIES - 3)
#define TASK_DEBUG_PRIORITY         (tskIDLE_PRIORITY + 2)

/* Reduced stack sizes for F446RE (128KB RAM) */
#define TASK_CONTROL_STACK_SIZE     (128)
#define TASK_PROTECTION_STACK_SIZE  (96)
#define TASK_CAN_STACK_SIZE         (128)
#define TASK_DEBUG_STACK_SIZE       (128)

/* Pin definitions */
#define USER_LED_PIN        GPIO_PIN_5
#define USER_LED_PORT       GPIOA
#define USER_BTN_PIN        GPIO_PIN_13
#define USER_BTN_PORT       GPIOC

/* Private variables ---------------------------------------------------------*/
static TaskHandle_t xControlTaskHandle = NULL;
static TaskHandle_t xProtectionTaskHandle = NULL;
static TaskHandle_t xCANTaskHandle = NULL;
static TaskHandle_t xDebugTaskHandle = NULL;

/* Peripheral handles */
UART_HandleTypeDef huart2;
CAN_HandleTypeDef hcan1;
ADC_HandleTypeDef hadc1;
TIM_HandleTypeDef htim1;
TIM_HandleTypeDef htim2;
TIM_HandleTypeDef htim3;

/* Debug counters */
static volatile uint32_t g_tick_count = 0;
static volatile uint32_t g_can_rx_count = 0;
static volatile uint32_t g_can_tx_count = 0;
static volatile uint32_t g_logic_exec_count = 0;

/* Private function prototypes -----------------------------------------------*/
static void SystemClock_Config(void);
static void GPIO_Init(void);
static void USART2_Init(void);
static void CAN1_Init(void);
static void ADC1_Init(void);
static void TIM_PWM_Init(void);

static void vControlTask(void *pvParameters);
static void vProtectionTask(void *pvParameters);
static void vCANTask(void *pvParameters);
static void vDebugTask(void *pvParameters);

static void Debug_Print(const char* msg);
static void Debug_PrintStatus(void);
static void Debug_PrintChannelStates(void);
static void LED_Toggle(void);
static void LED_Set(uint8_t state);
static void DigitalInputs_Read(void);
uint8_t DigitalInput_Get(uint8_t channel);

/* Digital inputs storage */
static uint8_t g_digital_inputs[8] = {0};

/* Main function -------------------------------------------------------------*/

int main(void)
{
    /* ================================================================== */
    /* DIAGNOSTIC INIT - Find where crash happens                          */
    /* ================================================================== */

    /* Disable SysTick and interrupts */
    __disable_irq();
    SysTick->CTRL = 0;

    /* Bare-metal LED setup for diagnostics */
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN;
    for (volatile int i = 0; i < 1000; i++);
    GPIOA->MODER &= ~(3 << (5 * 2));
    GPIOA->MODER |= (1 << (5 * 2));

    /* Blink 1 = Start */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* HAL_Init */
    HAL_Init();
    SysTick->CTRL = 0;

    /* Blink 2 = HAL OK */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* SystemClock_Config */
    SystemClock_Config();
    SysTick->CTRL = 0;

    /* Blink 3 = Clock OK */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* GPIO_Init */
    GPIO_Init();

    /* Blink 4 = GPIO OK */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* USART2_Init */
    USART2_Init();

    /* Blink 5 = UART OK */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* ===== STEP-BY-STEP DIAGNOSTIC INIT ===== */
    /* Each blink means one more step passed */

    /* Skip CAN1_Init for now */
    /* Blink 6 = (CAN skipped) */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* ADC1_Init */
    ADC1_Init();
    /* Blink 7 = ADC OK */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* TIM_PWM_Init */
    TIM_PWM_Init();
    /* Blink 8 = PWM OK */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* PMU_Config_Init */
    PMU_Config_Init();
    /* Blink 9 = Config OK */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* PMU_CAN_Init (stub) */
    PMU_CAN_Init();
    /* Blink 9a = PMU_CAN OK */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 150000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 150000; d++);

    /* PMU_ADC_Init (stub) */
    PMU_ADC_Init();
    /* Blink 9b = PMU_ADC OK */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 150000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 150000; d++);

    /* PMU_Protection_Init */
    PMU_Protection_Init();
    /* Blink 10 = Protection OK */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* PMU_Channel_Init */
    PMU_Channel_Init();
    /* Blink 11 = Channel OK */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* PMU_LogicFunctions_Init */
    PMU_LogicFunctions_Init();

    /* PMU_Logic_Init */
    PMU_Logic_Init();
    /* Blink 12 = Logic OK */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* PMU_Logging_Init */
    PMU_Logging_Init();

    /* PMU_JSON_Init */
    PMU_JSON_Init();

    /* PMU_Protocol_Init */
    PMU_Protocol_Init(PMU_TRANSPORT_UART);
    /* Blink 13 = Protocol OK */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* Blink 14 = Ready for main loop */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* Enable interrupts but keep SysTick disabled */
    __enable_irq();
    SysTick->CTRL = 0;  /* Re-disable SysTick after enable_irq */

    /* TEST: Send "READY" to verify UART TX works (bare-metal, no HAL timeout) */
    {
        const char* msg = "PMU30-READY\r\n";
        while (*msg) {
            while (!(USART2->SR & USART_SR_TXE));  /* Wait for TX empty */
            USART2->DR = *msg++;
        }
        while (!(USART2->SR & USART_SR_TC));  /* Wait for transmission complete */
    }

    /* Start UART reception for protocol (without HAL_Delay) */
    /* NOTE: Using bare-metal polling in main loop instead of interrupt RX
     * because SysTick is disabled and HAL_UART_Receive_IT may not work properly.
     */
    // extern void Protocol_StartUartReception(void);
    // Protocol_StartUartReception();

    /* Make sure SysTick stays off */
    SysTick->CTRL = 0;

    /* ===== ALL INIT DONE - FAST BLINK 5x ===== */
    for (int i = 0; i < 5; i++) {
        GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 100000; d++);
        GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 100000; d++);
    }

    /* Blink 15 = Entering main loop */
    GPIOA->ODR |= (1 << 5); for (volatile int d = 0; d < 300000; d++);
    GPIOA->ODR &= ~(1 << 5); for (volatile int d = 0; d < 300000; d++);

    /* Main loop - poll UART RX and process protocol */
    while (1) {
        /* Check if UART has received data (bare-metal polling) */
        if (USART2->SR & USART_SR_RXNE) {
            uint8_t rx_byte = (uint8_t)(USART2->DR & 0xFF);

            /* Pass to protocol handler (NO echo - would break protocol!) */
            PMU_Protocol_ProcessData(&rx_byte, 1);
        }

        /* Slow blink every ~1s to show main loop running */
        static uint32_t loop_count = 0;
        if (++loop_count >= 200000) {
            loop_count = 0;
            GPIOA->ODR ^= (1 << 5);
        }
    }
}

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
            PMU_LogicFunctions_Update();
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

    /* DIN1-DIN2: PC10, PC12 */
    GPIO_InitStruct.Pin = GPIO_PIN_10 | GPIO_PIN_12;
    GPIO_InitStruct.Pull = GPIO_PULLDOWN;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

    /* DIN3-DIN7: PB2, PB12, PB13, PB14, PB15 */
    GPIO_InitStruct.Pin = GPIO_PIN_2 | GPIO_PIN_12 | GPIO_PIN_13 | GPIO_PIN_14 | GPIO_PIN_15;
    GPIO_InitStruct.Pull = GPIO_PULLDOWN;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
}

/* Digital input reading (g_digital_inputs declared at top of file) */

static void DigitalInputs_Read(void)
{
    /* Read all digital inputs */
    g_digital_inputs[0] = !HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_13);  /* Button active-low */
    g_digital_inputs[1] = HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_10);
    g_digital_inputs[2] = HAL_GPIO_ReadPin(GPIOC, GPIO_PIN_12);
    g_digital_inputs[3] = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_2);
    g_digital_inputs[4] = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_15);
    g_digital_inputs[5] = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_14);
    g_digital_inputs[6] = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_13);
    g_digital_inputs[7] = HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_12);
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

    /* TIM1: PA8 (CH1), PA9 (CH2) - outputs 0, 1 */
    GPIO_InitStruct.Pin = GPIO_PIN_8 | GPIO_PIN_9;
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

/* UART interrupt handlers ---------------------------------------------------*/

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

#endif /* NUCLEO_F446RE */
