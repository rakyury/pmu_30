/**
 ******************************************************************************
 * @file           : main_nucleo.c
 * @brief          : Main program for Nucleo-H743ZI development board
 * @author         : R2 m-sport
 * @date           : 2025-12-27
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This is a minimal version of the PMU-30 firmware for testing on Nucleo board.
 * Hardware features like PROFET outputs, H-Bridge, WiFi are disabled.
 *
 * Enabled features:
 *   - Config parsing (JSON)
 *   - Channel abstraction
 *   - Logic engine
 *   - Telemetry via UART
 *   - CAN communication
 *   - UI via LEDs and UART
 *
 ******************************************************************************
 */

#ifdef PMU_NUCLEO_BOARD

/* Includes ------------------------------------------------------------------*/
#include "stm32h7xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"

/* PMU modules */
#include "pmu_config.h"
#include "pmu_can.h"
#include "pmu_adc.h"
#include "pmu_protection.h"
#include "pmu_logic.h"
#include "pmu_logging.h"
#include "pmu_lua.h"
#include "pmu_protocol.h"
#include "pmu_config_json.h"
#include "pmu_channel.h"
#include "pmu_logic_functions.h"
#include "pmu_can_stream.h"

#ifndef PMU_DISABLE_PROFET
#include "pmu_profet.h"
#endif

#ifndef PMU_DISABLE_HBRIDGE
#include "pmu_hbridge.h"
#endif

/* Private define ------------------------------------------------------------*/
#define TASK_CONTROL_PRIORITY       (configMAX_PRIORITIES - 1)
#define TASK_PROTECTION_PRIORITY    (configMAX_PRIORITIES - 2)
#define TASK_CAN_PRIORITY           (configMAX_PRIORITIES - 3)
#define TASK_UI_PRIORITY            (tskIDLE_PRIORITY + 2)

#define TASK_CONTROL_STACK_SIZE     (512)
#define TASK_PROTECTION_STACK_SIZE  (384)
#define TASK_CAN_STACK_SIZE         (512)
#define TASK_UI_STACK_SIZE          (256)

/* Nucleo-H743ZI LED pins */
#define LED_GREEN_PIN       GPIO_PIN_0
#define LED_GREEN_PORT      GPIOB
#define LED_YELLOW_PIN      GPIO_PIN_1
#define LED_YELLOW_PORT     GPIOE
#define LED_RED_PIN         GPIO_PIN_14
#define LED_RED_PORT        GPIOB

/* User button */
#define USER_BTN_PIN        GPIO_PIN_13
#define USER_BTN_PORT       GPIOC

/* Private variables ---------------------------------------------------------*/
static TaskHandle_t xControlTaskHandle = NULL;
static TaskHandle_t xProtectionTaskHandle = NULL;
static TaskHandle_t xCANTaskHandle = NULL;
static TaskHandle_t xUITaskHandle = NULL;

/* UART handle for debug/protocol */
UART_HandleTypeDef huart3;

/* Private function prototypes -----------------------------------------------*/
static void SystemClock_Config(void);
static void MPU_Config(void);
static void CPU_CACHE_Enable(void);
static void GPIO_Init(void);
static void UART3_Init(void);

static void vControlTask(void *pvParameters);
static void vProtectionTask(void *pvParameters);
static void vCANTask(void *pvParameters);
static void vUITask(void *pvParameters);

static void LED_SetStatus(uint8_t status);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief  The application entry point for Nucleo board
 */
int main(void)
{
    /* Configure MPU and caches */
    MPU_Config();
    CPU_CACHE_Enable();

    /* HAL initialization */
    HAL_Init();
    SystemClock_Config();

    /* Initialize GPIO and UART */
    GPIO_Init();
    UART3_Init();

    /* Print startup message */
    const char* banner =
        "\r\n"
        "╔═══════════════════════════════════════════════════════╗\r\n"
        "║       PMU-30 Firmware - Nucleo-H743ZI Test Build      ║\r\n"
        "║                 R2 m-sport (c) 2025                   ║\r\n"
        "╠═══════════════════════════════════════════════════════╣\r\n"
        "║  Config Parsing:    ENABLED                           ║\r\n"
        "║  Channels:          ENABLED                           ║\r\n"
        "║  Logic Engine:      ENABLED                           ║\r\n"
        "║  CAN Telemetry:     ENABLED                           ║\r\n"
        "║  PROFET Outputs:    DISABLED (no hardware)            ║\r\n"
        "║  H-Bridge:          DISABLED (no hardware)            ║\r\n"
        "║  WiFi/Bluetooth:    DISABLED                          ║\r\n"
        "╚═══════════════════════════════════════════════════════╝\r\n"
        "\r\n";
    HAL_UART_Transmit(&huart3, (uint8_t*)banner, strlen(banner), 1000);

    /* Blink all LEDs to indicate startup */
    LED_SetStatus(0x07);  /* All on */
    HAL_Delay(200);
    LED_SetStatus(0x00);  /* All off */
    HAL_Delay(200);
    LED_SetStatus(0x01);  /* Green only */

    /* Initialize PMU subsystems */
    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_Config_Init...\r\n", 27, 100);
    PMU_Config_Init();

    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_CAN_Init...\r\n", 24, 100);
    PMU_CAN_Init();

    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_ADC_Init...\r\n", 24, 100);
    PMU_ADC_Init();

    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_Protection_Init...\r\n", 31, 100);
    PMU_Protection_Init();

    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_Channel_Init...\r\n", 28, 100);
    PMU_Channel_Init();

    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_LogicFunctions_Init...\r\n", 35, 100);
    PMU_LogicFunctions_Init();

    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_Logic_Init...\r\n", 26, 100);
    PMU_Logic_Init();

    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_Logging_Init...\r\n", 28, 100);
    PMU_Logging_Init();

#ifndef PMU_DISABLE_PROFET
    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_PROFET_Init...\r\n", 27, 100);
    PMU_PROFET_Init();
#endif

#ifndef PMU_DISABLE_HBRIDGE
    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_HBridge_Init...\r\n", 28, 100);
    PMU_HBridge_Init();
#endif

    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_Lua_Init...\r\n", 24, 100);
    PMU_Lua_Init();

    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_JSON_Init...\r\n", 25, 100);
    PMU_JSON_Init();

#ifdef PMU_PROTOCOL_UART
    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_Protocol_Init(UART)...\r\n", 35, 100);
    PMU_Protocol_Init(PMU_TRANSPORT_UART);
#else
    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_Protocol_Init(USB)...\r\n", 34, 100);
    PMU_Protocol_Init(PMU_TRANSPORT_USB);
#endif

    /* Initialize CAN Stream */
    PMU_CanStreamConfig_t stream_config = {
        .enabled = true,
        .can_bus = 0,
        .base_id = 0x600,
        .is_extended = false,
        .include_extended = true
    };
    HAL_UART_Transmit(&huart3, (uint8_t*)"[INIT] PMU_CanStream_Init...\r\n", 30, 100);
    PMU_CanStream_Init(&stream_config);

    HAL_UART_Transmit(&huart3, (uint8_t*)"\r\n[READY] All subsystems initialized.\r\n", 39, 100);
    HAL_UART_Transmit(&huart3, (uint8_t*)"[READY] Starting FreeRTOS scheduler...\r\n\r\n", 42, 100);

    /* Create FreeRTOS tasks */
    xTaskCreate(vControlTask, "Control", TASK_CONTROL_STACK_SIZE,
                NULL, TASK_CONTROL_PRIORITY, &xControlTaskHandle);

    xTaskCreate(vProtectionTask, "Protection", TASK_PROTECTION_STACK_SIZE,
                NULL, TASK_PROTECTION_PRIORITY, &xProtectionTaskHandle);

    xTaskCreate(vCANTask, "CAN", TASK_CAN_STACK_SIZE,
                NULL, TASK_CAN_PRIORITY, &xCANTaskHandle);

    xTaskCreate(vUITask, "UI", TASK_UI_STACK_SIZE,
                NULL, TASK_UI_PRIORITY, &xUITaskHandle);

    /* Start scheduler */
    vTaskStartScheduler();

    /* Should never reach here */
    while (1) {
        LED_SetStatus(0x04);  /* Red = error */
        HAL_Delay(100);
        LED_SetStatus(0x00);
        HAL_Delay(100);
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

        /* Read analog inputs */
        PMU_ADC_Update();

        /* Update channel abstraction */
        PMU_Channel_Update();

        /* Logic engine at 500Hz */
        if (++logic_counter >= 2) {
            logic_counter = 0;
            PMU_Logic_Execute();
            PMU_LogicFunctions_Update();
            PMU_Lua_Update();
        }

#ifndef PMU_DISABLE_PROFET
        PMU_PROFET_Update();
#endif

#ifndef PMU_DISABLE_HBRIDGE
        PMU_HBridge_Update();
#endif

        PMU_Protocol_Update();
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

static void vUITask(void *pvParameters)
{
    TickType_t xLastWakeTime = xTaskGetTickCount();
    const TickType_t xFrequency = pdMS_TO_TICKS(50);  /* 20Hz */
    static uint32_t blink_counter = 0;

    (void)pvParameters;

    for (;;) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);

        /* Get protection status */
        PMU_Protection_State_t* prot = PMU_Protection_GetState();

        /* Update LEDs based on system status */
        if (prot && prot->status == PMU_PROT_STATUS_CRITICAL) {
            /* Critical - blink red fast */
            LED_SetStatus((blink_counter & 1) ? 0x04 : 0x00);
        } else if (prot && prot->status == PMU_PROT_STATUS_FAULT) {
            /* Fault - solid red */
            LED_SetStatus(0x04);
        } else if (prot && prot->status == PMU_PROT_STATUS_WARNING) {
            /* Warning - yellow */
            LED_SetStatus(0x02);
        } else {
            /* Normal - blink green slowly */
            LED_SetStatus((blink_counter & 0x04) ? 0x01 : 0x00);
        }

        blink_counter++;
    }
}

/* LED control ---------------------------------------------------------------*/

static void LED_SetStatus(uint8_t status)
{
    /* Green LED (LD1) - bit 0 */
    HAL_GPIO_WritePin(LED_GREEN_PORT, LED_GREEN_PIN,
                      (status & 0x01) ? GPIO_PIN_SET : GPIO_PIN_RESET);

    /* Yellow LED (LD2) - bit 1 */
    HAL_GPIO_WritePin(LED_YELLOW_PORT, LED_YELLOW_PIN,
                      (status & 0x02) ? GPIO_PIN_SET : GPIO_PIN_RESET);

    /* Red LED (LD3) - bit 2 */
    HAL_GPIO_WritePin(LED_RED_PORT, LED_RED_PIN,
                      (status & 0x04) ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

/* Hardware initialization ---------------------------------------------------*/

static void GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* Enable GPIO clocks */
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOE_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    /* Configure LED pins as outputs */
    HAL_GPIO_WritePin(LED_GREEN_PORT, LED_GREEN_PIN, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(LED_RED_PORT, LED_RED_PIN, GPIO_PIN_RESET);

    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;

    GPIO_InitStruct.Pin = LED_GREEN_PIN | LED_RED_PIN;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    HAL_GPIO_WritePin(LED_YELLOW_PORT, LED_YELLOW_PIN, GPIO_PIN_RESET);
    GPIO_InitStruct.Pin = LED_YELLOW_PIN;
    HAL_GPIO_Init(LED_YELLOW_PORT, &GPIO_InitStruct);

    /* Configure user button as input */
    GPIO_InitStruct.Pin = USER_BTN_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(USER_BTN_PORT, &GPIO_InitStruct);
}

static void UART3_Init(void)
{
    /* USART3 is connected to ST-LINK VCP */
    __HAL_RCC_USART3_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* USART3 GPIO: PD8=TX, PD9=RX */
    GPIO_InitStruct.Pin = GPIO_PIN_8 | GPIO_PIN_9;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF7_USART3;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);

    huart3.Instance = USART3;
    huart3.Init.BaudRate = 115200;
    huart3.Init.WordLength = UART_WORDLENGTH_8B;
    huart3.Init.StopBits = UART_STOPBITS_1;
    huart3.Init.Parity = UART_PARITY_NONE;
    huart3.Init.Mode = UART_MODE_TX_RX;
    huart3.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart3.Init.OverSampling = UART_OVERSAMPLING_16;

    HAL_UART_Init(&huart3);
}

static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /* Supply configuration */
    HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    while (!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {}

    /* HSE oscillator (8MHz on Nucleo) */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_BYPASS;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = 1;
    RCC_OscInitStruct.PLL.PLLN = 120;
    RCC_OscInitStruct.PLL.PLLP = 2;
    RCC_OscInitStruct.PLL.PLLQ = 4;
    RCC_OscInitStruct.PLL.PLLR = 2;
    RCC_OscInitStruct.PLL.PLLRGE = RCC_PLL1VCIRANGE_3;
    RCC_OscInitStruct.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
    RCC_OscInitStruct.PLL.PLLFRACN = 0;

    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
        while (1);
    }

    /* CPU, AHB, APB clocks */
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                                  RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2 |
                                  RCC_CLOCKTYPE_D3PCLK1 | RCC_CLOCKTYPE_D1PCLK1;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_HCLK_DIV2;
    RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV2;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV2;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV2;
    RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV2;

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_4) != HAL_OK) {
        while (1);
    }
}

static void MPU_Config(void)
{
    MPU_Region_InitTypeDef MPU_InitStruct = {0};

    HAL_MPU_Disable();

    /* Configure the MPU as Strongly ordered for not defined regions */
    MPU_InitStruct.Enable = MPU_REGION_ENABLE;
    MPU_InitStruct.BaseAddress = 0x00;
    MPU_InitStruct.Size = MPU_REGION_SIZE_4GB;
    MPU_InitStruct.AccessPermission = MPU_REGION_NO_ACCESS;
    MPU_InitStruct.IsBufferable = MPU_ACCESS_NOT_BUFFERABLE;
    MPU_InitStruct.IsCacheable = MPU_ACCESS_NOT_CACHEABLE;
    MPU_InitStruct.IsShareable = MPU_ACCESS_SHAREABLE;
    MPU_InitStruct.Number = MPU_REGION_NUMBER0;
    MPU_InitStruct.TypeExtField = MPU_TEX_LEVEL0;
    MPU_InitStruct.SubRegionDisable = 0x87;
    MPU_InitStruct.DisableExec = MPU_INSTRUCTION_ACCESS_DISABLE;

    HAL_MPU_ConfigRegion(&MPU_InitStruct);

    HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);
}

static void CPU_CACHE_Enable(void)
{
    SCB_EnableICache();
    SCB_EnableDCache();
}

/* Error handlers ------------------------------------------------------------*/

void Error_Handler(void)
{
    __disable_irq();
    LED_SetStatus(0x04);  /* Red LED */
    while (1);
}

void HardFault_Handler(void)
{
    LED_SetStatus(0x06);  /* Red + Yellow */
    while (1);
}

#endif /* PMU_NUCLEO_BOARD */
