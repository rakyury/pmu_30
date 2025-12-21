/**
 ******************************************************************************
 * @file           : pmu_profet.c
 * @brief          : PROFET 2 (BTS7008-2EPA) Output Driver Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * PROFET 2 BTS7008-2EPA Intelligent High-Side Switch:
 * - 40A continuous current per channel
 * - 160A inrush current capability
 * - Integrated current sensing (kILIS factor)
 * - Overtemperature protection
 * - Overcurrent protection
 * - Short circuit detection
 * - Open load detection
 * - PWM capable (up to 1kHz)
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_profet.h"
#include "stm32h7xx_hal.h"
#include <string.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/
#define PROFET_KILIS_RATIO          4700    /* Current sense ratio (typical) */
#define PROFET_TEMP_COEFF_MV_C      2       /* Temperature coefficient mV/°C */
#define PROFET_FAULT_THRESHOLD      3       /* Consecutive faults before lockout */
#define PROFET_RETRY_DELAY_MS       100     /* Delay before retry after fault */

/* BTS7008-2EPA thresholds */
#define PROFET_OVERCURRENT_MA       42000   /* 105% of rated current */
#define PROFET_SHORT_CIRCUIT_MA     80000   /* Short circuit detection */
#define PROFET_OPEN_LOAD_MA         50      /* Minimum load current */
#define PROFET_OVERTEMP_THRESHOLD_C 145     /* Temperature warning */

/* Private macro -------------------------------------------------------------*/
#define IS_VALID_CHANNEL(ch)    ((ch) < PMU_NUM_OUTPUTS)

/* Private variables ---------------------------------------------------------*/
static PMU_PROFET_Channel_t channels[PMU_NUM_OUTPUTS];
static PMU_OutputConfig_t* channel_configs[PMU_NUM_OUTPUTS];
static TIM_HandleTypeDef* htim_pwm;
static ADC_HandleTypeDef* hadc_current;
static ADC_HandleTypeDef* hadc_status;

/* GPIO pin mapping for PROFET control (example - adjust to actual hardware) */
typedef struct {
    GPIO_TypeDef* port;
    uint16_t pin;
    uint32_t tim_channel;
} PROFET_GPIO_Map_t;

static const PROFET_GPIO_Map_t profet_gpio[PMU_NUM_OUTPUTS] = {
    /* OUT0-7: TIM1 channels on GPIOA */
    {GPIOA, GPIO_PIN_8,  TIM_CHANNEL_1},
    {GPIOA, GPIO_PIN_9,  TIM_CHANNEL_2},
    {GPIOA, GPIO_PIN_10, TIM_CHANNEL_3},
    {GPIOA, GPIO_PIN_11, TIM_CHANNEL_4},
    {GPIOB, GPIO_PIN_0,  TIM_CHANNEL_1},
    {GPIOB, GPIO_PIN_1,  TIM_CHANNEL_2},
    {GPIOB, GPIO_PIN_6,  TIM_CHANNEL_3},
    {GPIOB, GPIO_PIN_7,  TIM_CHANNEL_4},

    /* OUT8-15: TIM2 channels on GPIOB/GPIOC */
    {GPIOC, GPIO_PIN_6,  TIM_CHANNEL_1},
    {GPIOC, GPIO_PIN_7,  TIM_CHANNEL_2},
    {GPIOC, GPIO_PIN_8,  TIM_CHANNEL_3},
    {GPIOC, GPIO_PIN_9,  TIM_CHANNEL_4},
    {GPIOD, GPIO_PIN_12, TIM_CHANNEL_1},
    {GPIOD, GPIO_PIN_13, TIM_CHANNEL_2},
    {GPIOD, GPIO_PIN_14, TIM_CHANNEL_3},
    {GPIOD, GPIO_PIN_15, TIM_CHANNEL_4},

    /* OUT16-23: TIM3 channels */
    {GPIOE, GPIO_PIN_0,  TIM_CHANNEL_1},
    {GPIOE, GPIO_PIN_1,  TIM_CHANNEL_2},
    {GPIOE, GPIO_PIN_2,  TIM_CHANNEL_3},
    {GPIOE, GPIO_PIN_3,  TIM_CHANNEL_4},
    {GPIOE, GPIO_PIN_4,  TIM_CHANNEL_1},
    {GPIOE, GPIO_PIN_5,  TIM_CHANNEL_2},
    {GPIOE, GPIO_PIN_6,  TIM_CHANNEL_3},
    {GPIOE, GPIO_PIN_7,  TIM_CHANNEL_4},

    /* OUT24-29: TIM4 channels */
    {GPIOF, GPIO_PIN_0,  TIM_CHANNEL_1},
    {GPIOF, GPIO_PIN_1,  TIM_CHANNEL_2},
    {GPIOF, GPIO_PIN_2,  TIM_CHANNEL_3},
    {GPIOF, GPIO_PIN_3,  TIM_CHANNEL_4},
    {GPIOF, GPIO_PIN_4,  TIM_CHANNEL_1},
    {GPIOF, GPIO_PIN_5,  TIM_CHANNEL_2},
};

/* Private function prototypes -----------------------------------------------*/
static void PROFET_UpdateCurrentSensing(uint8_t channel);
static void PROFET_UpdateDiagnostics(uint8_t channel);
static void PROFET_HandleFault(uint8_t channel, PMU_PROFET_Fault_t fault);
static uint16_t PROFET_ReadCurrentADC(uint8_t channel);
static uint16_t PROFET_ReadStatusADC(uint8_t channel);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize PROFET 2 driver
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PROFET_Init(void)
{
    HAL_StatusTypeDef status = HAL_OK;

    /* Clear all channel data */
    memset(channels, 0, sizeof(channels));
    memset(channel_configs, 0, sizeof(channel_configs));

    /* Initialize all channels to OFF state */
    for (uint8_t i = 0; i < PMU_NUM_OUTPUTS; i++) {
        channels[i].state = PMU_PROFET_STATE_OFF;
        channels[i].fault_flags = PMU_PROFET_FAULT_NONE;

        /* Set GPIO to LOW (PROFET off) */
        HAL_GPIO_WritePin(profet_gpio[i].port, profet_gpio[i].pin, GPIO_PIN_RESET);
    }

    /* TODO: Initialize timers for PWM (TIM1-4 @ 1kHz) */
    /* TODO: Initialize ADC for current sensing */
    /* TODO: Initialize ADC for status/diagnostic inputs */

    return status;
}

/**
 * @brief Update all PROFET 2 channels - call at 1kHz from control task
 * @retval None
 */
void PMU_PROFET_Update(void)
{
    static uint32_t tick_1khz = 0;
    tick_1khz++;

    for (uint8_t ch = 0; ch < PMU_NUM_OUTPUTS; ch++) {
        /* Update on-time counter */
        if (channels[ch].state == PMU_PROFET_STATE_ON ||
            channels[ch].state == PMU_PROFET_STATE_PWM) {
            channels[ch].on_time_ms++;
        }

        /* Update current sensing every cycle (1kHz) */
        PROFET_UpdateCurrentSensing(ch);

        /* Update diagnostics every 10ms (100Hz) */
        if ((tick_1khz % 10) == 0) {
            PROFET_UpdateDiagnostics(ch);
        }

        /* Apply configuration limits */
        if (channel_configs[ch] != NULL) {
            PMU_OutputConfig_t* cfg = channel_configs[ch];

            /* Check current limit */
            if (channels[ch].current_mA > cfg->current_limit_mA) {
                PROFET_HandleFault(ch, PMU_PROFET_FAULT_OVERCURRENT);
            }

            /* Check inrush duration */
            if (cfg->inrush_duration_ms > 0 &&
                channels[ch].on_time_ms < cfg->inrush_duration_ms) {
                /* Allow higher current during inrush */
                if (channels[ch].current_mA > cfg->inrush_current_mA) {
                    PROFET_HandleFault(ch, PMU_PROFET_FAULT_OVERCURRENT);
                }
            }
        }
    }
}

/**
 * @brief Set channel on/off
 * @param channel Channel number (0-29)
 * @param state 0=OFF, 1=ON
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PROFET_SetState(uint8_t channel, uint8_t state)
{
    if (!IS_VALID_CHANNEL(channel)) {
        return HAL_ERROR;
    }

    /* Don't allow state change if in fault */
    if (channels[channel].state == PMU_PROFET_STATE_FAULT &&
        channels[channel].fault_count >= PROFET_FAULT_THRESHOLD) {
        return HAL_ERROR;
    }

    if (state) {
        /* Turn ON */
        HAL_GPIO_WritePin(profet_gpio[channel].port,
                         profet_gpio[channel].pin,
                         GPIO_PIN_SET);
        channels[channel].state = PMU_PROFET_STATE_ON;
        channels[channel].pwm_duty = 1000; /* 100% */
    } else {
        /* Turn OFF */
        HAL_GPIO_WritePin(profet_gpio[channel].port,
                         profet_gpio[channel].pin,
                         GPIO_PIN_RESET);
        channels[channel].state = PMU_PROFET_STATE_OFF;
        channels[channel].pwm_duty = 0;
        channels[channel].on_time_ms = 0;
    }

    return HAL_OK;
}

/**
 * @brief Set channel PWM duty cycle
 * @param channel Channel number (0-29)
 * @param duty Duty cycle (0-1000 = 0-100.0%)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PROFET_SetPWM(uint8_t channel, uint16_t duty)
{
    if (!IS_VALID_CHANNEL(channel)) {
        return HAL_ERROR;
    }

    /* Clamp duty cycle */
    if (duty > PMU_PROFET_PWM_RESOLUTION) {
        duty = PMU_PROFET_PWM_RESOLUTION;
    }

    /* Don't allow PWM if in fault */
    if (channels[channel].state == PMU_PROFET_STATE_FAULT &&
        channels[channel].fault_count >= PROFET_FAULT_THRESHOLD) {
        return HAL_ERROR;
    }

    channels[channel].pwm_duty = duty;

    if (duty == 0) {
        /* Fully OFF */
        channels[channel].state = PMU_PROFET_STATE_OFF;
        HAL_GPIO_WritePin(profet_gpio[channel].port,
                         profet_gpio[channel].pin,
                         GPIO_PIN_RESET);
    } else if (duty == PMU_PROFET_PWM_RESOLUTION) {
        /* Fully ON */
        channels[channel].state = PMU_PROFET_STATE_ON;
        HAL_GPIO_WritePin(profet_gpio[channel].port,
                         profet_gpio[channel].pin,
                         GPIO_PIN_SET);
    } else {
        /* PWM mode */
        channels[channel].state = PMU_PROFET_STATE_PWM;

        /* TODO: Configure timer PWM duty cycle */
        /* TIM_OC_InitTypeDef sConfigOC;
        sConfigOC.Pulse = (duty * TIM_ARR) / 1000;
        HAL_TIM_PWM_ConfigChannel(htim_pwm, &sConfigOC, profet_gpio[channel].tim_channel);
        HAL_TIM_PWM_Start(htim_pwm, profet_gpio[channel].tim_channel); */
    }

    return HAL_OK;
}

/**
 * @brief Get channel current
 * @param channel Channel number (0-29)
 * @retval Current in mA
 */
uint16_t PMU_PROFET_GetCurrent(uint8_t channel)
{
    if (!IS_VALID_CHANNEL(channel)) {
        return 0;
    }
    return channels[channel].current_mA;
}

/**
 * @brief Get channel temperature
 * @param channel Channel number (0-29)
 * @retval Temperature in °C
 */
int16_t PMU_PROFET_GetTemperature(uint8_t channel)
{
    if (!IS_VALID_CHANNEL(channel)) {
        return 0;
    }
    return channels[channel].temperature_C;
}

/**
 * @brief Get channel fault status
 * @param channel Channel number (0-29)
 * @retval Fault flags
 */
uint8_t PMU_PROFET_GetFaults(uint8_t channel)
{
    if (!IS_VALID_CHANNEL(channel)) {
        return 0;
    }
    return channels[channel].fault_flags;
}

/**
 * @brief Clear channel faults
 * @param channel Channel number (0-29)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PROFET_ClearFaults(uint8_t channel)
{
    if (!IS_VALID_CHANNEL(channel)) {
        return HAL_ERROR;
    }

    channels[channel].fault_flags = PMU_PROFET_FAULT_NONE;
    channels[channel].fault_count = 0;

    /* If channel was in fault state, move to OFF */
    if (channels[channel].state == PMU_PROFET_STATE_FAULT) {
        channels[channel].state = PMU_PROFET_STATE_OFF;
    }

    return HAL_OK;
}

/**
 * @brief Get channel runtime data
 * @param channel Channel number (0-29)
 * @retval Pointer to channel data
 */
PMU_PROFET_Channel_t* PMU_PROFET_GetChannelData(uint8_t channel)
{
    if (!IS_VALID_CHANNEL(channel)) {
        return NULL;
    }
    return &channels[channel];
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Update current sensing for a channel
 * @param channel Channel number
 * @retval None
 */
static void PROFET_UpdateCurrentSensing(uint8_t channel)
{
    /* Read current sense ADC (IS pin) */
    uint16_t adc_value = PROFET_ReadCurrentADC(channel);

    /* Convert ADC to current using kILIS ratio
     * PROFET 2 BTS7008-2EPA typical kILIS = 4700 (1:4700 current mirror)
     * IS current = Load current / kILIS
     * IS voltage = IS current × RS (sense resistor, typically 1kΩ)
     *
     * For 40A load: IS = 40A / 4700 = 8.5mA
     * Voltage across 1kΩ: V = 8.5mA × 1kΩ = 8.5V
     *
     * ADC reading (12-bit, 3.3V ref): ADC = (V / 3.3V) × 4095
     * Current (mA) = (ADC × 3300mV / 4095) / 1kΩ × kILIS
     */

    uint32_t voltage_mv = (adc_value * 3300UL) / 4095;
    uint32_t current_ma = (voltage_mv * PROFET_KILIS_RATIO) / 1000;

    /* Apply moving average filter (4 samples) */
    channels[channel].current_mA = (uint16_t)((channels[channel].current_mA * 3 + current_ma) / 4);
}

/**
 * @brief Update diagnostics for a channel
 * @param channel Channel number
 * @retval None
 */
static void PROFET_UpdateDiagnostics(uint8_t channel)
{
    uint16_t current = channels[channel].current_mA;

    /* Only check diagnostics when channel is supposed to be ON */
    if (channels[channel].state == PMU_PROFET_STATE_OFF) {
        return;
    }

    /* Short circuit detection (>80A) */
    if (current > PROFET_SHORT_CIRCUIT_MA) {
        PROFET_HandleFault(channel, PMU_PROFET_FAULT_SHORT_CIRCUIT);
        return;
    }

    /* Overcurrent detection (>42A sustained) */
    if (current > PROFET_OVERCURRENT_MA) {
        PROFET_HandleFault(channel, PMU_PROFET_FAULT_OVERCURRENT);
        return;
    }

    /* Open load detection (<50mA when ON) */
    if (channels[channel].pwm_duty > 500 && current < PROFET_OPEN_LOAD_MA) {
        /* Only flag open load if PWM > 50% */
        PROFET_HandleFault(channel, PMU_PROFET_FAULT_OPEN_LOAD);
    }

    /* Temperature monitoring via status pin */
    uint16_t status_adc = PROFET_ReadStatusADC(channel);
    uint32_t status_mv = (status_adc * 3300UL) / 4095;

    /* Estimate temperature from status voltage
     * STATUS pin voltage decreases with temperature
     * Typical: 5V @ 25°C, decreases ~2mV/°C
     */
    int16_t temp_C = 25 + (int16_t)((5000 - status_mv) / PROFET_TEMP_COEFF_MV_C);
    channels[channel].temperature_C = temp_C;

    /* Overtemperature detection */
    if (temp_C > PROFET_OVERTEMP_THRESHOLD_C) {
        PROFET_HandleFault(channel, PMU_PROFET_FAULT_OVERTEMP);
    }
}

/**
 * @brief Handle fault condition
 * @param channel Channel number
 * @param fault Fault type
 * @retval None
 */
static void PROFET_HandleFault(uint8_t channel, PMU_PROFET_Fault_t fault)
{
    /* Set fault flag */
    channels[channel].fault_flags |= fault;
    channels[channel].fault_count++;

    /* Immediate shutdown for critical faults */
    if (fault == PMU_PROFET_FAULT_SHORT_CIRCUIT ||
        fault == PMU_PROFET_FAULT_OVERTEMP) {

        /* Turn off channel immediately */
        HAL_GPIO_WritePin(profet_gpio[channel].port,
                         profet_gpio[channel].pin,
                         GPIO_PIN_RESET);
        channels[channel].state = PMU_PROFET_STATE_FAULT;
    }

    /* Lockout after too many faults */
    if (channels[channel].fault_count >= PROFET_FAULT_THRESHOLD) {
        channels[channel].state = PMU_PROFET_STATE_FAULT;
        HAL_GPIO_WritePin(profet_gpio[channel].port,
                         profet_gpio[channel].pin,
                         GPIO_PIN_RESET);
    }
}

/**
 * @brief Read current sense ADC for a channel
 * @param channel Channel number
 * @retval ADC value (12-bit)
 */
static uint16_t PROFET_ReadCurrentADC(uint8_t channel)
{
    /* TODO: Implement ADC reading from current sense inputs
     * This would use ADC1/ADC2/ADC3 with DMA for all 30 channels
     * For now, return dummy value */
    return 0;
}

/**
 * @brief Read status ADC for a channel (for temperature sensing)
 * @param channel Channel number
 * @retval ADC value (12-bit)
 */
static uint16_t PROFET_ReadStatusADC(uint8_t channel)
{
    /* TODO: Implement ADC reading from status inputs
     * For now, return dummy value representing 25°C */
    return (uint16_t)((5000 * 4095UL) / 3300); /* 5V = 25°C */
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
