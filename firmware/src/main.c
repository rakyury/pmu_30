/**
 ******************************************************************************
 * @file           : main.c
 * @brief          : Main program body for PMU-30
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This software is licensed under terms that can be found in the LICENSE file
 * in the root directory of this software component.
 * If no LICENSE file comes with this software, it is provided AS-IS.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "stm32h7xx_hal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"

/* Private includes ----------------------------------------------------------*/
#include "pmu_config.h"
#include "pmu_profet.h"
#include "pmu_hbridge.h"
#include "pmu_can.h"
#include "pmu_adc.h"
#include "pmu_protection.h"
#include "pmu_logic.h"
#include "pmu_logging.h"

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/
#define TASK_CONTROL_PRIORITY       (configMAX_PRIORITIES - 1)  /* Highest priority */
#define TASK_PROTECTION_PRIORITY    (configMAX_PRIORITIES - 2)
#define TASK_CAN_PRIORITY           (configMAX_PRIORITIES - 3)
#define TASK_LOGGING_PRIORITY       (tskIDLE_PRIORITY + 1)
#define TASK_UI_PRIORITY            (tskIDLE_PRIORITY + 2)

#define TASK_CONTROL_STACK_SIZE     (512)
#define TASK_PROTECTION_STACK_SIZE  (384)
#define TASK_CAN_STACK_SIZE         (512)
#define TASK_LOGGING_STACK_SIZE     (512)
#define TASK_UI_STACK_SIZE          (256)

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static TaskHandle_t xControlTaskHandle = NULL;
static TaskHandle_t xProtectionTaskHandle = NULL;
static TaskHandle_t xCANTaskHandle = NULL;
static TaskHandle_t xLoggingTaskHandle = NULL;
static TaskHandle_t xUITaskHandle = NULL;

/* Private function prototypes -----------------------------------------------*/
static void SystemClock_Config(void);
static void MPU_Config(void);
static void CPU_CACHE_Enable(void);
static void GPIO_Init(void);
static void Error_Handler(void);

/* FreeRTOS task functions */
static void vControlTask(void *pvParameters);
static void vProtectionTask(void *pvParameters);
static void vCANTask(void *pvParameters);
static void vLoggingTask(void *pvParameters);
static void vUITask(void *pvParameters);

/* Private user code ---------------------------------------------------------*/

/**
 * @brief  The application entry point.
 * @retval int
 */
int main(void)
{
    /* Configure the MPU */
    MPU_Config();

    /* Enable the CPU Cache */
    CPU_CACHE_Enable();

    /* MCU Configuration--------------------------------------------------------*/

    /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
    HAL_Init();

    /* Configure the system clock to 480 MHz */
    SystemClock_Config();

    /* Initialize all configured peripherals */
    GPIO_Init();

    /* Initialize PMU subsystems */
    PMU_Config_Init();
    PMU_PROFET_Init();
    PMU_HBridge_Init();
    PMU_CAN_Init();
    PMU_ADC_Init();
    PMU_Protection_Init();
    PMU_Logic_Init();
    PMU_Logging_Init();

    /* Create FreeRTOS tasks */

    /* Control task - 1kHz deterministic loop */
    xTaskCreate(vControlTask,
                "Control",
                TASK_CONTROL_STACK_SIZE,
                NULL,
                TASK_CONTROL_PRIORITY,
                &xControlTaskHandle);

    /* Protection task - fast fault detection */
    xTaskCreate(vProtectionTask,
                "Protection",
                TASK_PROTECTION_STACK_SIZE,
                NULL,
                TASK_PROTECTION_PRIORITY,
                &xProtectionTaskHandle);

    /* CAN communication task */
    xTaskCreate(vCANTask,
                "CAN",
                TASK_CAN_STACK_SIZE,
                NULL,
                TASK_CAN_PRIORITY,
                &xCANTaskHandle);

    /* Data logging task */
    xTaskCreate(vLoggingTask,
                "Logging",
                TASK_LOGGING_STACK_SIZE,
                NULL,
                TASK_LOGGING_PRIORITY,
                &xLoggingTaskHandle);

    /* UI/Status LED task */
    xTaskCreate(vUITask,
                "UI",
                TASK_UI_STACK_SIZE,
                NULL,
                TASK_UI_PRIORITY,
                &xUITaskHandle);

    /* Start scheduler */
    vTaskStartScheduler();

    /* We should never get here as control is now taken by the scheduler */
    while (1)
    {
        Error_Handler();
    }
}

/**
 * @brief  Control task - Main 1kHz control loop
 * @param  pvParameters: Not used
 * @retval None
 */
static void vControlTask(void *pvParameters)
{
    TickType_t xLastWakeTime;
    const TickType_t xFrequency = pdMS_TO_TICKS(1);  /* 1ms = 1kHz */

    /* Initialize the xLastWakeTime variable with the current time */
    xLastWakeTime = xTaskGetTickCount();

    for (;;)
    {
        /* Wait for the next cycle */
        vTaskDelayUntil(&xLastWakeTime, xFrequency);

        /* Read all analog inputs */
        PMU_ADC_Update();

        /* Execute logic engine (500Hz, every 2nd cycle) */
        static uint8_t logic_counter = 0;
        if (++logic_counter >= 2) {
            logic_counter = 0;
            PMU_Logic_Execute();
        }

        /* Update output channels */
        PMU_PROFET_Update();
        PMU_HBridge_Update();

        /* Watchdog refresh */
        HAL_IWDG_Refresh(&hiwdg);
    }
}

/**
 * @brief  Protection task - Fast fault detection and response
 * @param  pvParameters: Not used
 * @retval None
 */
static void vProtectionTask(void *pvParameters)
{
    TickType_t xLastWakeTime;
    const TickType_t xFrequency = pdMS_TO_TICKS(1);  /* 1ms */

    xLastWakeTime = xTaskGetTickCount();

    for (;;)
    {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);

        /* Check all protection systems */
        PMU_Protection_Check();

        /* Handle any faults */
        PMU_Protection_HandleFaults();
    }
}

/**
 * @brief  CAN communication task
 * @param  pvParameters: Not used
 * @retval None
 */
static void vCANTask(void *pvParameters)
{
    for (;;)
    {
        /* Process CAN messages (blocking with timeout) */
        PMU_CAN_ProcessMessages(10);  /* 10ms timeout */

        /* Transmit periodic messages */
        PMU_CAN_TransmitPeriodic();
    }
}

/**
 * @brief  Data logging task
 * @param  pvParameters: Not used
 * @retval None
 */
static void vLoggingTask(void *pvParameters)
{
    TickType_t xLastWakeTime;
    const TickType_t xFrequency = pdMS_TO_TICKS(2);  /* 2ms = 500Hz */

    xLastWakeTime = xTaskGetTickCount();

    for (;;)
    {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);

        /* Log data at 500Hz */
        PMU_Logging_LogData();
    }
}

/**
 * @brief  UI/Status LED update task
 * @param  pvParameters: Not used
 * @retval None
 */
static void vUITask(void *pvParameters)
{
    TickType_t xLastWakeTime;
    const TickType_t xFrequency = pdMS_TO_TICKS(50);  /* 50ms = 20Hz */

    xLastWakeTime = xTaskGetTickCount();

    for (;;)
    {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);

        /* Update status LEDs */
        PMU_UI_UpdateLEDs();

        /* Handle button inputs (if any) */
        PMU_UI_ProcessInputs();
    }
}

/**
 * @brief  System Clock Configuration
 *         The system Clock is configured as follow :
 *            System Clock source            = PLL (HSE)
 *            SYSCLK(Hz)                     = 480000000 (480 MHz)
 *            HCLK(Hz)                       = 240000000 (240 MHz)
 *            AHB Prescaler                  = 2
 *            APB1 Prescaler                 = 2
 *            APB2 Prescaler                 = 2
 *            APB3 Prescaler                 = 2
 *            APB4 Prescaler                 = 2
 *            HSE Frequency(Hz)              = 25000000
 *            PLL_M                          = 5
 *            PLL_N                          = 192
 *            PLL_P                          = 2
 *            PLL_Q                          = 4
 *            PLL_R                          = 2
 *            VDD(V)                         = 3.3
 *            Flash Latency(WS)              = 4
 * @param  None
 * @retval None
 */
static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    /** Supply configuration update enable
     */
    HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);

    /** Configure the main internal regulator output voltage
     */
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE0);

    while (!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {}

    /** Initializes the RCC Oscillators according to the specified parameters
     * in the RCC_OscInitTypeDef structure.
     */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = 5;
    RCC_OscInitStruct.PLL.PLLN = 192;
    RCC_OscInitStruct.PLL.PLLP = 2;
    RCC_OscInitStruct.PLL.PLLQ = 4;
    RCC_OscInitStruct.PLL.PLLR = 2;
    RCC_OscInitStruct.PLL.PLLRGE = RCC_PLL1VCIRANGE_2;
    RCC_OscInitStruct.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
    RCC_OscInitStruct.PLL.PLLFRACN = 0;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
    {
        Error_Handler();
    }

    /** Initializes the CPU, AHB and APB buses clocks
     */
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

    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_4) != HAL_OK)
    {
        Error_Handler();
    }
}

/**
 * @brief  Configure the MPU attributes
 * @param  None
 * @retval None
 */
static void MPU_Config(void)
{
    MPU_Region_InitTypeDef MPU_InitStruct;

    /* Disable the MPU */
    HAL_MPU_Disable();

    /* Configure the MPU attributes for SRAM */
    MPU_InitStruct.Enable = MPU_REGION_ENABLE;
    MPU_InitStruct.BaseAddress = 0x24000000;
    MPU_InitStruct.Size = MPU_REGION_SIZE_512KB;
    MPU_InitStruct.AccessPermission = MPU_REGION_FULL_ACCESS;
    MPU_InitStruct.IsBufferable = MPU_ACCESS_NOT_BUFFERABLE;
    MPU_InitStruct.IsCacheable = MPU_ACCESS_CACHEABLE;
    MPU_InitStruct.IsShareable = MPU_ACCESS_NOT_SHAREABLE;
    MPU_InitStruct.Number = MPU_REGION_NUMBER0;
    MPU_InitStruct.TypeExtField = MPU_TEX_LEVEL0;
    MPU_InitStruct.SubRegionDisable = 0x00;
    MPU_InitStruct.DisableExec = MPU_INSTRUCTION_ACCESS_ENABLE;

    HAL_MPU_ConfigRegion(&MPU_InitStruct);

    /* Enable the MPU */
    HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);
}

/**
 * @brief  CPU L1-Cache enable.
 * @param  None
 * @retval None
 */
static void CPU_CACHE_Enable(void)
{
    /* Enable I-Cache */
    SCB_EnableICache();

    /* Enable D-Cache */
    SCB_EnableDCache();
}

/**
 * @brief GPIO Initialization Function
 * @param None
 * @retval None
 */
static void GPIO_Init(void)
{
    /* GPIO Ports Clock Enable */
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();
    __HAL_RCC_GPIOE_CLK_ENABLE();
    __HAL_RCC_GPIOF_CLK_ENABLE();
    __HAL_RCC_GPIOG_CLK_ENABLE();
    __HAL_RCC_GPIOH_CLK_ENABLE();
}

/**
 * @brief  This function is executed in case of error occurrence.
 * @retval None
 */
static void Error_Handler(void)
{
    /* User can add his own implementation to report the HAL error return state */
    __disable_irq();
    while (1)
    {
        /* Blink error LED or halt */
    }
}

#ifdef USE_FULL_ASSERT
/**
 * @brief  Reports the name of the source file and the source line number
 *         where the assert_param error has occurred.
 * @param  file: pointer to the source file name
 * @param  line: assert_param error line source number
 * @retval None
 */
void assert_failed(uint8_t *file, uint32_t line)
{
    /* User can add his own implementation to report the file name and line number,
       ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
}
#endif /* USE_FULL_ASSERT */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
