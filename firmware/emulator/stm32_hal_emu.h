/**
 ******************************************************************************
 * @file           : stm32_hal_emu.h
 * @brief          : STM32 HAL Emulation Layer for Native Platform
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This file provides STM32 HAL type definitions and function stubs
 * for running firmware on a native (PC) platform without real hardware.
 *
 ******************************************************************************
 */

#ifndef STM32_HAL_EMU_H
#define STM32_HAL_EMU_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief HAL Status Type
 */
typedef enum {
    HAL_OK       = 0x00U,
    HAL_ERROR    = 0x01U,
    HAL_BUSY     = 0x02U,
    HAL_TIMEOUT  = 0x03U
} HAL_StatusTypeDef;

/**
 * @brief HAL Lock Type
 */
typedef enum {
    HAL_UNLOCKED = 0x00U,
    HAL_LOCKED   = 0x01U
} HAL_LockTypeDef;

/* ============================================================================
 * GPIO Definitions
 * ============================================================================ */

typedef struct {
    uint32_t Pin;
    uint32_t Mode;
    uint32_t Pull;
    uint32_t Speed;
    uint32_t Alternate;
} GPIO_InitTypeDef;

typedef struct {
    uint32_t dummy;  /* Placeholder for GPIO registers */
} GPIO_TypeDef;

/* GPIO Pin definitions */
#define GPIO_PIN_0                 ((uint16_t)0x0001)
#define GPIO_PIN_1                 ((uint16_t)0x0002)
#define GPIO_PIN_2                 ((uint16_t)0x0004)
#define GPIO_PIN_3                 ((uint16_t)0x0008)
#define GPIO_PIN_4                 ((uint16_t)0x0010)
#define GPIO_PIN_5                 ((uint16_t)0x0020)
#define GPIO_PIN_6                 ((uint16_t)0x0040)
#define GPIO_PIN_7                 ((uint16_t)0x0080)
#define GPIO_PIN_8                 ((uint16_t)0x0100)
#define GPIO_PIN_9                 ((uint16_t)0x0200)
#define GPIO_PIN_10                ((uint16_t)0x0400)
#define GPIO_PIN_11                ((uint16_t)0x0800)
#define GPIO_PIN_12                ((uint16_t)0x1000)
#define GPIO_PIN_13                ((uint16_t)0x2000)
#define GPIO_PIN_14                ((uint16_t)0x4000)
#define GPIO_PIN_15                ((uint16_t)0x8000)
#define GPIO_PIN_All               ((uint16_t)0xFFFF)

/* GPIO Mode */
#define GPIO_MODE_INPUT            0x00000000U
#define GPIO_MODE_OUTPUT_PP        0x00000001U
#define GPIO_MODE_OUTPUT_OD        0x00000011U
#define GPIO_MODE_AF_PP            0x00000002U
#define GPIO_MODE_AF_OD            0x00000012U
#define GPIO_MODE_ANALOG           0x00000003U
#define GPIO_MODE_IT_RISING        0x10110000U
#define GPIO_MODE_IT_FALLING       0x10210000U
#define GPIO_MODE_IT_RISING_FALLING 0x10310000U

/* GPIO Pull */
#define GPIO_NOPULL                0x00000000U
#define GPIO_PULLUP                0x00000001U
#define GPIO_PULLDOWN              0x00000002U

/* GPIO Speed */
#define GPIO_SPEED_FREQ_LOW        0x00000000U
#define GPIO_SPEED_FREQ_MEDIUM     0x00000001U
#define GPIO_SPEED_FREQ_HIGH       0x00000002U
#define GPIO_SPEED_FREQ_VERY_HIGH  0x00000003U

/* GPIO Pin State */
#define GPIO_PIN_RESET             0
#define GPIO_PIN_SET               1

/* GPIO Port instances (emulated) */
extern GPIO_TypeDef GPIOA_inst, GPIOB_inst, GPIOC_inst, GPIOD_inst;
extern GPIO_TypeDef GPIOE_inst, GPIOF_inst, GPIOG_inst, GPIOH_inst;
#define GPIOA (&GPIOA_inst)
#define GPIOB (&GPIOB_inst)
#define GPIOC (&GPIOC_inst)
#define GPIOD (&GPIOD_inst)
#define GPIOE (&GPIOE_inst)
#define GPIOF (&GPIOF_inst)
#define GPIOG (&GPIOG_inst)
#define GPIOH (&GPIOH_inst)

/* GPIO Clock Enable Macros (no-op in emulation) */
#define __HAL_RCC_GPIOA_CLK_ENABLE()  do { } while(0)
#define __HAL_RCC_GPIOB_CLK_ENABLE()  do { } while(0)
#define __HAL_RCC_GPIOC_CLK_ENABLE()  do { } while(0)
#define __HAL_RCC_GPIOD_CLK_ENABLE()  do { } while(0)
#define __HAL_RCC_GPIOE_CLK_ENABLE()  do { } while(0)
#define __HAL_RCC_GPIOF_CLK_ENABLE()  do { } while(0)
#define __HAL_RCC_GPIOG_CLK_ENABLE()  do { } while(0)
#define __HAL_RCC_GPIOH_CLK_ENABLE()  do { } while(0)

/* ============================================================================
 * ADC Definitions
 * ============================================================================ */

typedef struct {
    uint32_t dummy;  /* Placeholder for ADC registers */
} ADC_TypeDef;

typedef struct {
    uint32_t ClockPrescaler;
    uint32_t Resolution;
    uint32_t ScanConvMode;
    uint32_t EOCSelection;
    uint32_t LowPowerAutoWait;
    uint32_t ContinuousConvMode;
    uint32_t NbrOfConversion;
    uint32_t DiscontinuousConvMode;
    uint32_t ExternalTrigConv;
    uint32_t ExternalTrigConvEdge;
    uint32_t ConversionDataManagement;
    uint32_t Overrun;
    uint32_t LeftBitShift;
    uint32_t OversamplingMode;
} ADC_InitTypeDef;

typedef struct {
    ADC_TypeDef* Instance;
    ADC_InitTypeDef Init;
    HAL_LockTypeDef Lock;
    uint32_t State;
    uint32_t ErrorCode;
} ADC_HandleTypeDef;

typedef struct {
    uint32_t Channel;
    uint32_t Rank;
    uint32_t SamplingTime;
    uint32_t SingleDiff;
    uint32_t OffsetNumber;
    uint32_t Offset;
} ADC_ChannelConfTypeDef;

/* ADC Resolution */
#define ADC_RESOLUTION_16B         0x00000000U
#define ADC_RESOLUTION_14B         0x00000001U
#define ADC_RESOLUTION_12B         0x00000002U
#define ADC_RESOLUTION_10B         0x00000003U

/* ADC Clock Prescaler */
#define ADC_CLOCK_ASYNC_DIV1       0x00000000U
#define ADC_CLOCK_ASYNC_DIV2       0x00000001U
#define ADC_CLOCK_ASYNC_DIV4       0x00000002U

/* ADC Scan Mode */
#define ADC_SCAN_DISABLE           0x00000000U
#define ADC_SCAN_ENABLE            0x00000001U

/* ADC EOC Selection */
#define ADC_EOC_SINGLE_CONV        0x00000000U
#define ADC_EOC_SEQ_CONV           0x00000001U

/* ADC External Trigger */
#define ADC_SOFTWARE_START         0x00000000U
#define ADC_EXTERNALTRIGCONVEDGE_NONE 0x00000000U

/* ADC Data Management */
#define ADC_CONVERSIONDATA_DR      0x00000000U
#define ADC_CONVERSIONDATA_DMA_CIRCULAR 0x00000002U

/* ADC Overrun */
#define ADC_OVR_DATA_PRESERVED     0x00000000U
#define ADC_OVR_DATA_OVERWRITTEN   0x00000001U

/* ADC Left Bit Shift */
#define ADC_LEFTBITSHIFT_NONE      0x00000000U

/* ADC Channels */
#define ADC_CHANNEL_0              0x00000000U
#define ADC_CHANNEL_1              0x00000001U
#define ADC_CHANNEL_2              0x00000002U
#define ADC_CHANNEL_3              0x00000003U
#define ADC_CHANNEL_4              0x00000004U
#define ADC_CHANNEL_5              0x00000005U
#define ADC_CHANNEL_6              0x00000006U
#define ADC_CHANNEL_7              0x00000007U
#define ADC_CHANNEL_8              0x00000008U
#define ADC_CHANNEL_9              0x00000009U
#define ADC_CHANNEL_10             0x0000000AU
#define ADC_CHANNEL_11             0x0000000BU
#define ADC_CHANNEL_12             0x0000000CU
#define ADC_CHANNEL_13             0x0000000DU
#define ADC_CHANNEL_14             0x0000000EU
#define ADC_CHANNEL_15             0x0000000FU

/* ADC Rank */
#define ADC_REGULAR_RANK_1         0x00000001U
#define ADC_REGULAR_RANK_2         0x00000002U
#define ADC_REGULAR_RANK_3         0x00000003U
#define ADC_REGULAR_RANK_4         0x00000004U
#define ADC_REGULAR_RANK_5         0x00000005U
#define ADC_REGULAR_RANK_6         0x00000006U
#define ADC_REGULAR_RANK_7         0x00000007U
#define ADC_REGULAR_RANK_8         0x00000008U

/* ADC Sampling Time */
#define ADC_SAMPLETIME_1CYCLE_5    0x00000000U
#define ADC_SAMPLETIME_2CYCLES_5   0x00000001U
#define ADC_SAMPLETIME_8CYCLES_5   0x00000002U
#define ADC_SAMPLETIME_16CYCLES_5  0x00000003U
#define ADC_SAMPLETIME_32CYCLES_5  0x00000004U
#define ADC_SAMPLETIME_64CYCLES_5  0x00000005U

/* ADC Single/Differential */
#define ADC_SINGLE_ENDED           0x00000000U
#define ADC_DIFFERENTIAL_ENDED     0x00000001U

/* ADC Offset */
#define ADC_OFFSET_NONE            0x00000000U

/* ADC Instances */
extern ADC_TypeDef ADC1_inst, ADC2_inst, ADC3_inst;
#define ADC1 (&ADC1_inst)
#define ADC2 (&ADC2_inst)
#define ADC3 (&ADC3_inst)

/* ============================================================================
 * Timer Definitions
 * ============================================================================ */

typedef struct {
    uint32_t dummy;  /* Placeholder for timer registers */
} TIM_TypeDef;

typedef struct {
    uint32_t Prescaler;
    uint32_t CounterMode;
    uint32_t Period;
    uint32_t ClockDivision;
    uint32_t RepetitionCounter;
    uint32_t AutoReloadPreload;
} TIM_Base_InitTypeDef;

typedef struct {
    uint32_t OCMode;
    uint32_t Pulse;
    uint32_t OCPolarity;
    uint32_t OCNPolarity;
    uint32_t OCFastMode;
    uint32_t OCIdleState;
    uint32_t OCNIdleState;
} TIM_OC_InitTypeDef;

typedef struct {
    TIM_TypeDef* Instance;
    TIM_Base_InitTypeDef Init;
    HAL_LockTypeDef Lock;
    uint32_t State;
} TIM_HandleTypeDef;

/* Timer Modes */
#define TIM_COUNTERMODE_UP         0x00000000U
#define TIM_COUNTERMODE_DOWN       0x00000010U
#define TIM_COUNTERMODE_CENTERALIGNED1 0x00000020U

/* Timer Clock Division */
#define TIM_CLOCKDIVISION_DIV1     0x00000000U
#define TIM_CLOCKDIVISION_DIV2     0x00000100U
#define TIM_CLOCKDIVISION_DIV4     0x00000200U

/* Timer OC Mode */
#define TIM_OCMODE_TIMING          0x00000000U
#define TIM_OCMODE_ACTIVE          0x00000010U
#define TIM_OCMODE_INACTIVE        0x00000020U
#define TIM_OCMODE_TOGGLE          0x00000030U
#define TIM_OCMODE_PWM1            0x00000060U
#define TIM_OCMODE_PWM2            0x00000070U

/* Timer OC Polarity */
#define TIM_OCPOLARITY_HIGH        0x00000000U
#define TIM_OCPOLARITY_LOW         0x00000002U

/* Timer Channels */
#define TIM_CHANNEL_1              0x00000000U
#define TIM_CHANNEL_2              0x00000004U
#define TIM_CHANNEL_3              0x00000008U
#define TIM_CHANNEL_4              0x0000000CU
#define TIM_CHANNEL_5              0x00000010U
#define TIM_CHANNEL_6              0x00000014U

/* Timer Instances */
extern TIM_TypeDef TIM1_inst, TIM2_inst, TIM3_inst, TIM4_inst;
extern TIM_TypeDef TIM5_inst, TIM6_inst, TIM7_inst, TIM8_inst;
extern TIM_TypeDef TIM15_inst, TIM16_inst, TIM17_inst;
#define TIM1  (&TIM1_inst)
#define TIM2  (&TIM2_inst)
#define TIM3  (&TIM3_inst)
#define TIM4  (&TIM4_inst)
#define TIM5  (&TIM5_inst)
#define TIM6  (&TIM6_inst)
#define TIM7  (&TIM7_inst)
#define TIM8  (&TIM8_inst)
#define TIM15 (&TIM15_inst)
#define TIM16 (&TIM16_inst)
#define TIM17 (&TIM17_inst)

/* ============================================================================
 * SPI Definitions
 * ============================================================================ */

typedef struct {
    uint32_t dummy;  /* Placeholder for SPI registers */
} SPI_TypeDef;

typedef struct {
    uint32_t Mode;
    uint32_t Direction;
    uint32_t DataSize;
    uint32_t CLKPolarity;
    uint32_t CLKPhase;
    uint32_t NSS;
    uint32_t BaudRatePrescaler;
    uint32_t FirstBit;
    uint32_t TIMode;
    uint32_t CRCCalculation;
    uint32_t CRCPolynomial;
} SPI_InitTypeDef;

typedef struct {
    SPI_TypeDef* Instance;
    SPI_InitTypeDef Init;
    HAL_LockTypeDef Lock;
    uint32_t State;
    uint32_t ErrorCode;
} SPI_HandleTypeDef;

/* SPI Mode */
#define SPI_MODE_SLAVE             0x00000000U
#define SPI_MODE_MASTER            0x00000104U

/* SPI Instances */
extern SPI_TypeDef SPI1_inst, SPI2_inst, SPI3_inst;
#define SPI1 (&SPI1_inst)
#define SPI2 (&SPI2_inst)
#define SPI3 (&SPI3_inst)

/* ============================================================================
 * UART Definitions
 * ============================================================================ */

typedef struct {
    uint32_t dummy;  /* Placeholder for UART registers */
} USART_TypeDef;

typedef struct {
    uint32_t BaudRate;
    uint32_t WordLength;
    uint32_t StopBits;
    uint32_t Parity;
    uint32_t Mode;
    uint32_t HwFlowCtl;
    uint32_t OverSampling;
} UART_InitTypeDef;

typedef struct {
    USART_TypeDef* Instance;
    UART_InitTypeDef Init;
    HAL_LockTypeDef Lock;
    uint32_t State;
    uint32_t ErrorCode;
} UART_HandleTypeDef;

/* UART Instances */
extern USART_TypeDef USART1_inst, USART2_inst, USART3_inst;
extern USART_TypeDef UART4_inst, UART5_inst;
#define USART1 (&USART1_inst)
#define USART2 (&USART2_inst)
#define USART3 (&USART3_inst)
#define UART4  (&UART4_inst)
#define UART5  (&UART5_inst)

/* ============================================================================
 * FDCAN Definitions
 * ============================================================================ */

typedef struct {
    uint32_t dummy;  /* Placeholder for FDCAN registers */
} FDCAN_GlobalTypeDef;

typedef struct {
    uint32_t ClockDivider;
    uint32_t FrameFormat;
    uint32_t Mode;
    uint32_t AutoRetransmission;
    uint32_t TransmitPause;
    uint32_t ProtocolException;
    uint32_t NominalPrescaler;
    uint32_t NominalSyncJumpWidth;
    uint32_t NominalTimeSeg1;
    uint32_t NominalTimeSeg2;
    uint32_t DataPrescaler;
    uint32_t DataSyncJumpWidth;
    uint32_t DataTimeSeg1;
    uint32_t DataTimeSeg2;
    uint32_t StdFiltersNbr;
    uint32_t ExtFiltersNbr;
    uint32_t TxFifoQueueMode;
} FDCAN_InitTypeDef;

typedef struct {
    FDCAN_GlobalTypeDef* Instance;
    FDCAN_InitTypeDef Init;
    HAL_LockTypeDef Lock;
    uint32_t State;
    uint32_t ErrorCode;
} FDCAN_HandleTypeDef;

typedef struct {
    uint32_t Identifier;
    uint32_t IdType;
    uint32_t TxFrameType;
    uint32_t DataLength;
    uint32_t ErrorStateIndicator;
    uint32_t BitRateSwitch;
    uint32_t FDFormat;
    uint32_t TxEventFifoControl;
    uint32_t MessageMarker;
} FDCAN_TxHeaderTypeDef;

typedef struct {
    uint32_t Identifier;
    uint32_t IdType;
    uint32_t RxFrameType;
    uint32_t DataLength;
    uint32_t ErrorStateIndicator;
    uint32_t BitRateSwitch;
    uint32_t FDFormat;
    uint32_t RxTimestamp;
    uint32_t FilterIndex;
    uint32_t IsFilterMatchingFrame;
} FDCAN_RxHeaderTypeDef;

typedef struct {
    uint32_t IdType;
    uint32_t FilterIndex;
    uint32_t FilterType;
    uint32_t FilterConfig;
    uint32_t FilterID1;
    uint32_t FilterID2;
} FDCAN_FilterTypeDef;

/* FDCAN Frame Format */
#define FDCAN_FRAME_CLASSIC        0x00000000U
#define FDCAN_FRAME_FD_NO_BRS      0x00100000U
#define FDCAN_FRAME_FD_BRS         0x00300000U

/* FDCAN Mode */
#define FDCAN_MODE_NORMAL          0x00000000U
#define FDCAN_MODE_RESTRICTED_OPERATION 0x00000001U
#define FDCAN_MODE_BUS_MONITORING  0x00000002U
#define FDCAN_MODE_INTERNAL_LOOPBACK 0x00000003U
#define FDCAN_MODE_EXTERNAL_LOOPBACK 0x00000004U

/* FDCAN ID Type */
#define FDCAN_STANDARD_ID          0x00000000U
#define FDCAN_EXTENDED_ID          0x40000000U

/* FDCAN Frame Type */
#define FDCAN_DATA_FRAME           0x00000000U
#define FDCAN_REMOTE_FRAME         0x00100000U

/* FDCAN Data Length */
#define FDCAN_DLC_BYTES_0          0x00000000U
#define FDCAN_DLC_BYTES_1          0x00010000U
#define FDCAN_DLC_BYTES_2          0x00020000U
#define FDCAN_DLC_BYTES_3          0x00030000U
#define FDCAN_DLC_BYTES_4          0x00040000U
#define FDCAN_DLC_BYTES_5          0x00050000U
#define FDCAN_DLC_BYTES_6          0x00060000U
#define FDCAN_DLC_BYTES_7          0x00070000U
#define FDCAN_DLC_BYTES_8          0x00080000U
#define FDCAN_DLC_BYTES_12         0x00090000U
#define FDCAN_DLC_BYTES_16         0x000A0000U
#define FDCAN_DLC_BYTES_20         0x000B0000U
#define FDCAN_DLC_BYTES_24         0x000C0000U
#define FDCAN_DLC_BYTES_32         0x000D0000U
#define FDCAN_DLC_BYTES_48         0x000E0000U
#define FDCAN_DLC_BYTES_64         0x000F0000U

/* FDCAN RX FIFO */
#define FDCAN_RX_FIFO0             0x00000000U
#define FDCAN_RX_FIFO1             0x00000001U

/* FDCAN Filter Type */
#define FDCAN_FILTER_RANGE         0x00000000U
#define FDCAN_FILTER_DUAL          0x00000001U
#define FDCAN_FILTER_MASK          0x00000002U

/* FDCAN Filter Config */
#define FDCAN_FILTER_DISABLE       0x00000000U
#define FDCAN_FILTER_TO_RXFIFO0    0x00000001U
#define FDCAN_FILTER_TO_RXFIFO1    0x00000002U
#define FDCAN_FILTER_REJECT        0x00000003U

/* FDCAN Instances */
extern FDCAN_GlobalTypeDef FDCAN1_inst, FDCAN2_inst, FDCAN3_inst;
#define FDCAN1 (&FDCAN1_inst)
#define FDCAN2 (&FDCAN2_inst)
#define FDCAN3 (&FDCAN3_inst)

/* ============================================================================
 * IWDG (Watchdog) Definitions
 * ============================================================================ */

typedef struct {
    uint32_t dummy;
} IWDG_TypeDef;

typedef struct {
    uint32_t Prescaler;
    uint32_t Reload;
    uint32_t Window;
} IWDG_InitTypeDef;

typedef struct {
    IWDG_TypeDef* Instance;
    IWDG_InitTypeDef Init;
} IWDG_HandleTypeDef;

extern IWDG_TypeDef IWDG_inst;
#define IWDG (&IWDG_inst)

/* ============================================================================
 * DMA Definitions
 * ============================================================================ */

typedef struct {
    uint32_t dummy;
} DMA_Stream_TypeDef;

typedef struct {
    uint32_t Request;
    uint32_t Direction;
    uint32_t PeriphInc;
    uint32_t MemInc;
    uint32_t PeriphDataAlignment;
    uint32_t MemDataAlignment;
    uint32_t Mode;
    uint32_t Priority;
    uint32_t FIFOMode;
    uint32_t FIFOThreshold;
    uint32_t MemBurst;
    uint32_t PeriphBurst;
} DMA_InitTypeDef;

typedef struct {
    DMA_Stream_TypeDef* Instance;
    DMA_InitTypeDef Init;
    HAL_LockTypeDef Lock;
    uint32_t State;
    uint32_t ErrorCode;
} DMA_HandleTypeDef;

/* ============================================================================
 * NVIC Definitions
 * ============================================================================ */

typedef enum {
    NonMaskableInt_IRQn         = -14,
    HardFault_IRQn              = -13,
    MemoryManagement_IRQn       = -12,
    BusFault_IRQn               = -11,
    UsageFault_IRQn             = -10,
    SVCall_IRQn                 = -5,
    DebugMonitor_IRQn           = -4,
    PendSV_IRQn                 = -2,
    SysTick_IRQn                = -1,
    WWDG_IRQn                   = 0,
    EXTI0_IRQn                  = 6,
    EXTI1_IRQn                  = 7,
    EXTI2_IRQn                  = 8,
    EXTI3_IRQn                  = 9,
    EXTI4_IRQn                  = 10,
    TIM1_UP_IRQn                = 25,
    TIM2_IRQn                   = 28,
    TIM3_IRQn                   = 29,
    TIM4_IRQn                   = 30,
    FDCAN1_IT0_IRQn             = 19,
    FDCAN1_IT1_IRQn             = 21,
    FDCAN2_IT0_IRQn             = 63,
    FDCAN2_IT1_IRQn             = 64,
} IRQn_Type;

/* ============================================================================
 * Emulated HAL Functions
 * ============================================================================ */

/* Tick & Timing */
uint32_t HAL_GetTick(void);
void HAL_Delay(uint32_t Delay);
void HAL_IncTick(void);

/* Initialization */
HAL_StatusTypeDef HAL_Init(void);
HAL_StatusTypeDef HAL_DeInit(void);

/* GPIO Functions */
HAL_StatusTypeDef HAL_GPIO_Init(GPIO_TypeDef* GPIOx, GPIO_InitTypeDef* GPIO_Init);
void HAL_GPIO_DeInit(GPIO_TypeDef* GPIOx, uint32_t GPIO_Pin);
int HAL_GPIO_ReadPin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin);
void HAL_GPIO_WritePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin, int PinState);
void HAL_GPIO_TogglePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin);
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin);

/* ADC Functions */
HAL_StatusTypeDef HAL_ADC_Init(ADC_HandleTypeDef* hadc);
HAL_StatusTypeDef HAL_ADC_DeInit(ADC_HandleTypeDef* hadc);
HAL_StatusTypeDef HAL_ADC_Start(ADC_HandleTypeDef* hadc);
HAL_StatusTypeDef HAL_ADC_Stop(ADC_HandleTypeDef* hadc);
HAL_StatusTypeDef HAL_ADC_Start_DMA(ADC_HandleTypeDef* hadc, uint32_t* pData, uint32_t Length);
HAL_StatusTypeDef HAL_ADC_Stop_DMA(ADC_HandleTypeDef* hadc);
HAL_StatusTypeDef HAL_ADC_ConfigChannel(ADC_HandleTypeDef* hadc, ADC_ChannelConfTypeDef* sConfig);
uint32_t HAL_ADC_GetValue(ADC_HandleTypeDef* hadc);
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc);

/* Timer Functions */
HAL_StatusTypeDef HAL_TIM_Base_Init(TIM_HandleTypeDef* htim);
HAL_StatusTypeDef HAL_TIM_Base_DeInit(TIM_HandleTypeDef* htim);
HAL_StatusTypeDef HAL_TIM_Base_Start(TIM_HandleTypeDef* htim);
HAL_StatusTypeDef HAL_TIM_Base_Stop(TIM_HandleTypeDef* htim);
HAL_StatusTypeDef HAL_TIM_PWM_Init(TIM_HandleTypeDef* htim);
HAL_StatusTypeDef HAL_TIM_PWM_Start(TIM_HandleTypeDef* htim, uint32_t Channel);
HAL_StatusTypeDef HAL_TIM_PWM_Stop(TIM_HandleTypeDef* htim, uint32_t Channel);
HAL_StatusTypeDef HAL_TIM_PWM_ConfigChannel(TIM_HandleTypeDef* htim, TIM_OC_InitTypeDef* sConfig, uint32_t Channel);
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef* htim);

/* Macro to set PWM compare value */
#define __HAL_TIM_SET_COMPARE(htim, channel, compare) do { } while(0)
#define __HAL_TIM_GET_COMPARE(htim, channel) (0)

/* SPI Functions */
HAL_StatusTypeDef HAL_SPI_Init(SPI_HandleTypeDef* hspi);
HAL_StatusTypeDef HAL_SPI_DeInit(SPI_HandleTypeDef* hspi);
HAL_StatusTypeDef HAL_SPI_Transmit(SPI_HandleTypeDef* hspi, uint8_t* pData, uint16_t Size, uint32_t Timeout);
HAL_StatusTypeDef HAL_SPI_Receive(SPI_HandleTypeDef* hspi, uint8_t* pData, uint16_t Size, uint32_t Timeout);
HAL_StatusTypeDef HAL_SPI_TransmitReceive(SPI_HandleTypeDef* hspi, uint8_t* pTxData, uint8_t* pRxData, uint16_t Size, uint32_t Timeout);

/* UART Functions */
HAL_StatusTypeDef HAL_UART_Init(UART_HandleTypeDef* huart);
HAL_StatusTypeDef HAL_UART_DeInit(UART_HandleTypeDef* huart);
HAL_StatusTypeDef HAL_UART_Transmit(UART_HandleTypeDef* huart, uint8_t* pData, uint16_t Size, uint32_t Timeout);
HAL_StatusTypeDef HAL_UART_Receive(UART_HandleTypeDef* huart, uint8_t* pData, uint16_t Size, uint32_t Timeout);

/* FDCAN Functions */
HAL_StatusTypeDef HAL_FDCAN_Init(FDCAN_HandleTypeDef* hfdcan);
HAL_StatusTypeDef HAL_FDCAN_DeInit(FDCAN_HandleTypeDef* hfdcan);
HAL_StatusTypeDef HAL_FDCAN_Start(FDCAN_HandleTypeDef* hfdcan);
HAL_StatusTypeDef HAL_FDCAN_Stop(FDCAN_HandleTypeDef* hfdcan);
HAL_StatusTypeDef HAL_FDCAN_ConfigFilter(FDCAN_HandleTypeDef* hfdcan, FDCAN_FilterTypeDef* sFilterConfig);
HAL_StatusTypeDef HAL_FDCAN_AddMessageToTxFifoQ(FDCAN_HandleTypeDef* hfdcan, FDCAN_TxHeaderTypeDef* pTxHeader, uint8_t* pTxData);
HAL_StatusTypeDef HAL_FDCAN_GetRxMessage(FDCAN_HandleTypeDef* hfdcan, uint32_t RxLocation, FDCAN_RxHeaderTypeDef* pRxHeader, uint8_t* pRxData);
uint32_t HAL_FDCAN_GetRxFifoFillLevel(FDCAN_HandleTypeDef* hfdcan, uint32_t RxFifo);
HAL_StatusTypeDef HAL_FDCAN_ActivateNotification(FDCAN_HandleTypeDef* hfdcan, uint32_t ActiveITs, uint32_t BufferIndexes);
void HAL_FDCAN_RxFifo0Callback(FDCAN_HandleTypeDef* hfdcan, uint32_t RxFifo0ITs);

/* IWDG Functions */
HAL_StatusTypeDef HAL_IWDG_Init(IWDG_HandleTypeDef* hiwdg);
HAL_StatusTypeDef HAL_IWDG_Refresh(IWDG_HandleTypeDef* hiwdg);

/* NVIC Functions */
void HAL_NVIC_SetPriority(IRQn_Type IRQn, uint32_t PreemptPriority, uint32_t SubPriority);
void HAL_NVIC_EnableIRQ(IRQn_Type IRQn);
void HAL_NVIC_DisableIRQ(IRQn_Type IRQn);

/* System Functions */
void SystemClock_Config(void);
void Error_Handler(void);

/* Critical Section */
#define __disable_irq() do { } while(0)
#define __enable_irq()  do { } while(0)

/* Memory Barrier */
#define __DSB() do { } while(0)
#define __ISB() do { } while(0)
#define __DMB() do { } while(0)

#ifdef __cplusplus
}
#endif

#endif /* STM32_HAL_EMU_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
