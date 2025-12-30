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

#define TASK_CONTROL_STACK_SIZE     (256)
#define TASK_PROTECTION_STACK_SIZE  (192)
#define TASK_CAN_STACK_SIZE         (256)
#define TASK_DEBUG_STACK_SIZE       (256)

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

/* Main function -------------------------------------------------------------*/

int main(void)
{
    /* MCU Configuration */
    HAL_Init();
    SystemClock_Config();

    /* Initialize peripherals */
    GPIO_Init();
    USART2_Init();

    /* Print startup banner */
    Debug_Print("\r\n");
    Debug_Print("╔═══════════════════════════════════════════════════════════════╗\r\n");
    Debug_Print("║       PMU-30 Debug Firmware - Nucleo-F446RE                   ║\r\n");
    Debug_Print("║                 R2 m-sport (c) 2025                           ║\r\n");
    Debug_Print("╠═══════════════════════════════════════════════════════════════╣\r\n");
    Debug_Print("║  MCU:              STM32F446RE @ 180 MHz                      ║\r\n");
    Debug_Print("║  Config Parsing:   ENABLED                                    ║\r\n");
    Debug_Print("║  Outputs:          6 (PWM on GPIO)                            ║\r\n");
    Debug_Print("║  Analog Inputs:    5 (ADC)                                    ║\r\n");
    Debug_Print("║  Digital Inputs:   8 (GPIO)                                   ║\r\n");
    Debug_Print("║  Logic Engine:     ENABLED                                    ║\r\n");
    Debug_Print("║  CAN:              CAN1 (PA11/PA12) @ 500kbit                 ║\r\n");
    Debug_Print("║  Debug UART:       USART2 (115200 baud)                       ║\r\n");
    Debug_Print("╚═══════════════════════════════════════════════════════════════╝\r\n");
    Debug_Print("\r\n");

    /* LED blink to indicate startup */
    for (int i = 0; i < 3; i++) {
        LED_Set(1);
        HAL_Delay(100);
        LED_Set(0);
        HAL_Delay(100);
    }

    /* Initialize more peripherals */
    Debug_Print("[INIT] CAN1_Init...\r\n");
    CAN1_Init();

    Debug_Print("[INIT] ADC1_Init...\r\n");
    ADC1_Init();

    Debug_Print("[INIT] TIM_PWM_Init...\r\n");
    TIM_PWM_Init();

    /* Initialize PMU subsystems */
    Debug_Print("[INIT] PMU_Config_Init...\r\n");
    PMU_Config_Init();

    Debug_Print("[INIT] PMU_CAN_Init...\r\n");
    PMU_CAN_Init();

    Debug_Print("[INIT] PMU_ADC_Init...\r\n");
    PMU_ADC_Init();

    Debug_Print("[INIT] PMU_Protection_Init...\r\n");
    PMU_Protection_Init();

    Debug_Print("[INIT] PMU_Channel_Init...\r\n");
    PMU_Channel_Init();

    Debug_Print("[INIT] PMU_LogicFunctions_Init...\r\n");
    PMU_LogicFunctions_Init();

    Debug_Print("[INIT] PMU_Logic_Init...\r\n");
    PMU_Logic_Init();

    Debug_Print("[INIT] PMU_Logging_Init...\r\n");
    PMU_Logging_Init();

#ifndef PMU_DISABLE_LUA
    Debug_Print("[INIT] PMU_Lua_Init...\r\n");
    PMU_Lua_Init();
#endif

    Debug_Print("[INIT] PMU_JSON_Init...\r\n");
    PMU_JSON_Init();

    Debug_Print("[INIT] PMU_Protocol_Init (UART)...\r\n");
    PMU_Protocol_Init(PMU_TRANSPORT_UART);

    /* Initialize CAN Stream */
    PMU_CanStreamConfig_t stream_config = {
        .enabled = true,
        .can_bus = 0,           /* CAN1 */
        .base_id = 0x600,
        .is_extended = false,
        .include_extended = true
    };
    Debug_Print("[INIT] PMU_CanStream_Init...\r\n");
    PMU_CanStream_Init(&stream_config);

    Debug_Print("\r\n");
    Debug_Print("═══════════════════════════════════════════════════════════════\r\n");
    Debug_Print("  All subsystems initialized. Starting FreeRTOS...\r\n");
    Debug_Print("═══════════════════════════════════════════════════════════════\r\n");
    Debug_Print("\r\n");

    /* Create FreeRTOS tasks */
    xTaskCreate(vControlTask, "Control", TASK_CONTROL_STACK_SIZE,
                NULL, TASK_CONTROL_PRIORITY, &xControlTaskHandle);

    xTaskCreate(vProtectionTask, "Protection", TASK_PROTECTION_STACK_SIZE,
                NULL, TASK_PROTECTION_PRIORITY, &xProtectionTaskHandle);

    xTaskCreate(vCANTask, "CAN", TASK_CAN_STACK_SIZE,
                NULL, TASK_CAN_PRIORITY, &xCANTaskHandle);

    xTaskCreate(vDebugTask, "Debug", TASK_DEBUG_STACK_SIZE,
                NULL, TASK_DEBUG_PRIORITY, &xDebugTaskHandle);

    /* Start scheduler */
    vTaskStartScheduler();

    /* Should never reach here */
    while (1) {
        LED_Toggle();
        HAL_Delay(50);
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

static void Debug_Print(const char* msg)
{
    HAL_UART_Transmit(&huart2, (uint8_t*)msg, strlen(msg), 100);
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

/* Digital input reading */
static uint8_t g_digital_inputs[8] = {0};

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
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /* Configure power supply */
    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    /* Configure HSE and PLL for 180 MHz */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_BYPASS;  /* 8MHz from ST-LINK */
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = 4;
    RCC_OscInitStruct.PLL.PLLN = 180;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
    RCC_OscInitStruct.PLL.PLLQ = 4;
    RCC_OscInitStruct.PLL.PLLR = 2;

    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
        while (1);
    }

    /* Activate Over-Drive mode for 180 MHz */
    if (HAL_PWREx_EnableOverDrive() != HAL_OK) {
        while (1);
    }

    /* Configure clocks */
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                                  RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV4;  /* 45 MHz */
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV2;  /* 90 MHz */

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_5) != HAL_OK) {
        while (1);
    }
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

#endif /* NUCLEO_F446RE */
