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
#include "pmu_spi.h"
#include "stm32h7xx_hal.h"
#include <string.h>
#include <stdbool.h>
#ifdef _WIN32
#include <stdio.h>
#endif

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
#define IS_VALID_CHANNEL(ch)    ((ch) < PMU30_NUM_OUTPUTS)

/* Private variables ---------------------------------------------------------*/
static PMU_PROFET_Channel_t channels[PMU30_NUM_OUTPUTS];
static PMU_OutputConfig_t* channel_configs[PMU30_NUM_OUTPUTS];
static TIM_HandleTypeDef* htim_pwm;
static ADC_HandleTypeDef* hadc_current;
static ADC_HandleTypeDef* hadc_status;
static uint8_t spi_diag_enabled = 0;  /* SPI diagnostics enabled flag */
static uint8_t manual_override[PMU30_NUM_OUTPUTS];  /* Manual override flags (prevents logic from overwriting) */

/* GPIO pin mapping for PROFET control (example - adjust to actual hardware) */
typedef struct {
    GPIO_TypeDef* port;
    uint16_t pin;
    uint32_t tim_channel;
} PROFET_GPIO_Map_t;

static const PROFET_GPIO_Map_t profet_gpio[PMU30_NUM_OUTPUTS] = {
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
static void PROFET_UpdateCurrentSensingSPI(uint8_t channel);
static void PROFET_UpdateDiagnostics(uint8_t channel);
static void PROFET_HandleFault(uint8_t channel, PMU_PROFET_Fault_t fault);
static uint16_t PROFET_ReadCurrentADC(uint8_t channel);
static uint16_t PROFET_ReadStatusADC(uint8_t channel);
static inline bool PROFET_IsInFaultState(PMU_PROFET_State_t state);

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
    for (uint8_t i = 0; i < PMU30_NUM_OUTPUTS; i++) {
        channels[i].state = PMU_PROFET_STATE_OFF;
        channels[i].fault_flags = PMU_PROFET_FAULT_NONE;

        /* Set GPIO to LOW (PROFET off) */
        HAL_GPIO_WritePin(profet_gpio[i].port, profet_gpio[i].pin, GPIO_PIN_RESET);
    }

    /* Initialize timers for PWM (TIM1-4 @ 1kHz)
     * 30 PROFET channels require multiple timers
     * Distribution:
     * - TIM1 (advanced): CH1-4 (4 channels) - Outputs 0-3
     * - TIM2 (GP 32-bit): CH1-4 (4 channels) - Outputs 4-7
     * - TIM3 (GP 16-bit): CH1-4 (4 channels) - Outputs 8-11
     * - TIM4 (GP 16-bit): CH1-4 (4 channels) - Outputs 12-15
     * - TIM5 (GP 32-bit): CH1-4 (4 channels) - Outputs 16-19
     * - TIM8 (advanced): CH1-4 (4 channels) - Outputs 20-23
     * - TIM12 (GP): CH1-2 (2 channels) - Outputs 24-25
     * - TIM13/14: 4 channels - Outputs 26-29
     *
     * PWM Configuration:
     * - Frequency: 1 kHz (1ms period)
     * - Resolution: 1000 steps (1000 Hz / 1000 = 1 Hz step)
     * - Prescaler: Calculated from APB timer clock
     */

#ifndef UNIT_TEST
    extern TIM_HandleTypeDef htim1, htim2, htim3, htim4, htim5, htim8;

    /* Configure TIM1-4 for PWM @ 1kHz
     * ARR = 1000 for 1000 steps (0.1% resolution)
     * Prescaler depends on APB clock (typically 200MHz for STM32H7)
     * Timer clock after prescaler should be 1MHz
     * Formula: Prescaler = (TIM_CLK / (ARR * PWM_FREQ)) - 1
     *         = (200MHz / (1000 * 1000Hz)) - 1 = 199
     */

    TIM_OC_InitTypeDef sConfigOC = {0};

    /* TIM1: Advanced timer (APB2 = 200MHz) */
    htim1.Instance = TIM1;
    htim1.Init.Prescaler = 199;  /* 200MHz / 200 = 1MHz */
    htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim1.Init.Period = 999;  /* 1MHz / 1000 = 1kHz */
    htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim1.Init.RepetitionCounter = 0;
    htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;

    if (HAL_TIM_PWM_Init(&htim1) != HAL_OK) {
        return HAL_ERROR;
    }

    /* Configure PWM channels for TIM1 */
    sConfigOC.OCMode = TIM_OCMODE_PWM1;
    sConfigOC.Pulse = 0;  /* Initial duty cycle = 0% */
    sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
    sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;

    for (uint32_t ch = TIM_CHANNEL_1; ch <= TIM_CHANNEL_4; ch <<= 1) {
        if (HAL_TIM_PWM_ConfigChannel(&htim1, &sConfigOC, ch) != HAL_OK) {
            return HAL_ERROR;
        }
        HAL_TIM_PWM_Start(&htim1, ch);
    }

    /* TIM2-5 and TIM8 would be configured similarly
     * For brevity, showing structure - full implementation would repeat for each timer
     *
     * TODO: Implement remaining timers (TIM2-5, TIM8, TIM12-14) following same pattern
     * Each timer handles 4 channels except TIM12-14 which handle fewer channels
     */

    /* Initialize ADC for current sensing (IS pins)
     * Each PROFET has a current sense output (kILIS ratio)
     * 30 channels require dedicated ADC channels or multiplexing
     *
     * Option 1: Dedicated ADC channels (requires 30 ADC pins)
     * Option 2: Analog multiplexer (CD4067 or similar) to reduce pin count
     *
     * For now, assuming dedicated ADC channels distributed across ADC1/2/3
     * ADC configuration would be done in PMU_ADC_Init() and MX_GPIO_Init()
     */

    /* Initialize ADC for status/diagnostic (ST pins)
     * PROFET ST pins provide temperature information
     * Similar to current sense, needs 30 ADC channels or multiplexing
     */
#endif /* UNIT_TEST */

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

    /* Update SPI diagnostics if enabled (at 100Hz rate) */
    if (spi_diag_enabled && (tick_1khz % 10) == 0) {
        PMU_SPI_Update();
    }

    for (uint8_t ch = 0; ch < PMU30_NUM_OUTPUTS; ch++) {
        /* Update on-time counter */
        if (channels[ch].state == PMU_PROFET_STATE_ON ||
            channels[ch].state == PMU_PROFET_STATE_PWM) {
            channels[ch].on_time_ms++;
        }

        /* Update current sensing every cycle (1kHz) */
        if (spi_diag_enabled) {
            /* Use high-precision SPI-based current sensing */
            PROFET_UpdateCurrentSensingSPI(ch);
        } else {
            /* Use internal ADC current sensing */
            PROFET_UpdateCurrentSensing(ch);
        }

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

            /* Check inrush duration (soft-start period) */
            if (cfg->soft_start_ms > 0 &&
                channels[ch].on_time_ms < cfg->soft_start_ms) {
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

    /* Don't allow state change if in fault lockout */
    if (PROFET_IsInFaultState(channels[channel].state) &&
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
        channels[channel].on_time_ms = 0;  /* Reset grace period for fault detection */
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
 * @brief Set channel state with manual override (prevents logic from overwriting)
 * @param channel Channel number (0-29)
 * @param state 0=OFF, 1=ON
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PROFET_SetStateManual(uint8_t channel, uint8_t state)
{
#ifdef _WIN32
    printf("[PROFET] SetStateManual: ch=%d, state=%d\n", channel, state);
#endif
    HAL_StatusTypeDef result = PMU_PROFET_SetState(channel, state);
    if (result == HAL_OK) {
        manual_override[channel] = 1;
#ifdef _WIN32
        printf("[PROFET] Manual override SET for ch=%d, new_state=%d\n", channel, channels[channel].state);
#endif
    }
    return result;
}

/**
 * @brief Check if channel has manual override set
 * @param channel Channel number (0-29)
 * @retval 1 if override set, 0 otherwise
 */
uint8_t PMU_PROFET_HasManualOverride(uint8_t channel)
{
    if (!IS_VALID_CHANNEL(channel)) {
        return 0;
    }
    return manual_override[channel];
}

/**
 * @brief Clear manual override for channel
 * @param channel Channel number (0-29)
 * @retval None
 */
void PMU_PROFET_ClearManualOverride(uint8_t channel)
{
    if (IS_VALID_CHANNEL(channel)) {
        manual_override[channel] = 0;
    }
}

/**
 * @brief Clear all manual overrides
 * @retval None
 */
void PMU_PROFET_ClearAllManualOverrides(void)
{
    memset(manual_override, 0, sizeof(manual_override));
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

    /* Don't allow PWM if in fault lockout */
    if (PROFET_IsInFaultState(channels[channel].state) &&
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

#ifndef UNIT_TEST
        /* Configure timer PWM duty cycle
         * duty is in range 0-1000 (PMU_PROFET_PWM_RESOLUTION)
         * Timer ARR = 999, so pulse = (duty * 1000) / 1000 = duty
         *
         * Channel to timer mapping:
         * 0-3: TIM1_CH1-4, 4-7: TIM2_CH1-4, etc.
         */

        extern TIM_HandleTypeDef htim1, htim2, htim3, htim4, htim5, htim8;

        TIM_HandleTypeDef* htim = NULL;
        uint32_t tim_channel = 0;

        /* Map channel to timer and channel */
        if (channel < 4) {
            htim = &htim1;
            tim_channel = TIM_CHANNEL_1 << (channel % 4);
        } else if (channel < 8) {
            htim = &htim2;
            tim_channel = TIM_CHANNEL_1 << (channel % 4);
        } else if (channel < 12) {
            htim = &htim3;
            tim_channel = TIM_CHANNEL_1 << (channel % 4);
        } else if (channel < 16) {
            htim = &htim4;
            tim_channel = TIM_CHANNEL_1 << (channel % 4);
        } else if (channel < 20) {
            htim = &htim5;
            tim_channel = TIM_CHANNEL_1 << (channel % 4);
        } else if (channel < 24) {
            htim = &htim8;
            tim_channel = TIM_CHANNEL_1 << (channel % 4);
        }
        /* Channels 24-29 would use TIM12-14 */

        if (htim != NULL) {
            /* Set PWM pulse width (duty * ARR / 1000) */
            __HAL_TIM_SET_COMPARE(htim, tim_channel, duty);
        }
#endif
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
 * @brief Check if channel is in a fault state
 * @param state Channel state
 * @retval true if in fault state
 */
static inline bool PROFET_IsInFaultState(PMU_PROFET_State_t state)
{
    return (state == PMU_PROFET_STATE_OC ||
            state == PMU_PROFET_STATE_OT ||
            state == PMU_PROFET_STATE_SC ||
            state == PMU_PROFET_STATE_OL);
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

    /* If channel was in any fault state, move to OFF */
    if (PROFET_IsInFaultState(channels[channel].state)) {
        channels[channel].state = PMU_PROFET_STATE_OFF;
    }

    return HAL_OK;
}

/**
 * @brief Inject fault into channel (for emulator/testing)
 * @param channel Channel number (0-29)
 * @param fault Fault flags to inject
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PROFET_InjectFault(uint8_t channel, uint8_t fault)
{
    if (!IS_VALID_CHANNEL(channel)) {
        return HAL_ERROR;
    }

    channels[channel].fault_flags |= fault;
    channels[channel].fault_count++;

    /* Map fault type to specific ECUMaster-compatible state */
    PMU_PROFET_State_t fault_state;
    if (fault & PMU_PROFET_FAULT_SHORT_CIRCUIT) {
        fault_state = PMU_PROFET_STATE_SC;
    } else if (fault & PMU_PROFET_FAULT_OVERTEMP) {
        fault_state = PMU_PROFET_STATE_OT;
    } else if (fault & PMU_PROFET_FAULT_OPEN_LOAD) {
        fault_state = PMU_PROFET_STATE_OL;
    } else {
        fault_state = PMU_PROFET_STATE_OC;  /* Default to OC */
    }

    /* Set channel to fault state and turn off */
    channels[channel].state = fault_state;
    HAL_GPIO_WritePin(profet_gpio[channel].port,
                     profet_gpio[channel].pin,
                     GPIO_PIN_RESET);

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
    PMU_PROFET_State_t state = channels[channel].state;

    /* Only check diagnostics when channel is ON or PWM (active states) */
    if (state != PMU_PROFET_STATE_ON && state != PMU_PROFET_STATE_PWM) {
        return;
    }

    /* Short circuit detection (>80A) - check immediately */
    if (current > PROFET_SHORT_CIRCUIT_MA) {
        PROFET_HandleFault(channel, PMU_PROFET_FAULT_SHORT_CIRCUIT);
        return;
    }

    /* Overcurrent detection (>42A sustained) - check immediately */
    if (current > PROFET_OVERCURRENT_MA) {
        PROFET_HandleFault(channel, PMU_PROFET_FAULT_OVERCURRENT);
        return;
    }

    /* Open load detection (<50mA when ON)
     * Only check after channel has been on for a while (500ms grace period)
     * This allows current sensing to stabilize after turn-on
     * Skip if manual override is set (WebUI controlled) */
    if (!manual_override[channel] &&
        channels[channel].on_time_ms > 500 &&
        channels[channel].pwm_duty > 500 &&
        current < PROFET_OPEN_LOAD_MA) {
        /* Only flag open load if PWM > 50% and channel has been on long enough */
        PROFET_HandleFault(channel, PMU_PROFET_FAULT_OPEN_LOAD);
    }

    /* Temperature monitoring via status pin */
    uint16_t status_adc = PROFET_ReadStatusADC(channel);
    uint32_t status_mv = (status_adc * 3300UL) / 4095;

#ifdef _WIN32
    /* Emulator mode: Use temperature directly from emulator state
     * The SPI stub returns temperature from emulator, not ADC-derived
     */
    int16_t temp_C = PMU_SPI_GetTemperature(channel);
#else
    /* Estimate temperature from status voltage
     * STATUS pin voltage decreases with temperature
     * Typical: 5V @ 25°C, decreases ~2mV/°C
     */
    int16_t temp_C = 25 + (int16_t)((5000 - status_mv) / PROFET_TEMP_COEFF_MV_C);
#endif
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

    /* Map fault type to specific ECUMaster-compatible state */
    PMU_PROFET_State_t fault_state;
    switch (fault) {
        case PMU_PROFET_FAULT_OVERCURRENT:
            fault_state = PMU_PROFET_STATE_OC;
            break;
        case PMU_PROFET_FAULT_OVERTEMP:
            fault_state = PMU_PROFET_STATE_OT;
            break;
        case PMU_PROFET_FAULT_SHORT_CIRCUIT:
            fault_state = PMU_PROFET_STATE_SC;
            break;
        case PMU_PROFET_FAULT_OPEN_LOAD:
            fault_state = PMU_PROFET_STATE_OL;
            break;
        default:
            fault_state = PMU_PROFET_STATE_OC;  /* Default to OC for unknown faults */
            break;
    }

    /* Immediate shutdown for critical faults */
    if (fault == PMU_PROFET_FAULT_SHORT_CIRCUIT ||
        fault == PMU_PROFET_FAULT_OVERTEMP) {

        /* Turn off channel immediately */
        HAL_GPIO_WritePin(profet_gpio[channel].port,
                         profet_gpio[channel].pin,
                         GPIO_PIN_RESET);
        channels[channel].state = fault_state;
    }

    /* Lockout after too many faults */
    if (channels[channel].fault_count >= PROFET_FAULT_THRESHOLD) {
        channels[channel].state = fault_state;
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
#ifdef UNIT_TEST
    /* For unit tests, return dummy value (no current) */
    return 0;
#else
    /* Read current sense (IS) from ADC
     * Each PROFET has a current sense output with kILIS ratio (typically 1:1000 to 1:10000)
     * For BTS7002/BTS7008: kILIS = 1:1400 (1.4mA IS current per 1A load)
     *
     * Connection example:
     * - IS pins connected to ADC channels through resistor (e.g., 1kΩ to GND)
     * - Voltage = IS_current × R = (I_load / kILIS) × R
     * - For 10A load with kILIS=1400: IS = 7.14mA, V_sense = 7.14mV @ 1kΩ
     *
     * ADC channels: Distributed across ADC1/2/3
     * Channels 0-9:   ADC2 channels 0-9
     * Channels 10-19: ADC2 channels 10-19
     * Channels 20-29: ADC3 channels 0-9 (if available)
     *
     * For now, using dedicated buffer or multiplexed ADC read
     */

    /* Map to ADC channel - this depends on actual hardware layout
     * Would typically be configured in ADC DMA buffer
     */
    extern ADC_HandleTypeDef hadc2, hadc3;
    extern uint16_t profet_current_adc_buffer[30];  /* DMA buffer for current sense */

    /* Read from DMA buffer (automatically updated in background) */
    if (channel < 30) {
        return profet_current_adc_buffer[channel];
    }

    return 0;
#endif
}

/**
 * @brief Read status ADC for a channel (for temperature sensing)
 * @param channel Channel number
 * @retval ADC value (12-bit)
 */
static uint16_t PROFET_ReadStatusADC(uint8_t channel)
{
#ifdef UNIT_TEST
    /* For unit tests, return dummy value representing 25°C */
    return (uint16_t)((1500 * 4095UL) / 3300); /* ~1.5V = 25°C typical */
#else
    /* Read status (ST) from ADC for temperature sensing
     * PROFET ST pin provides proportional voltage output related to chip temperature:
     * - V_ST ≈ 1.0V at 25°C (typical)
     * - Temperature coefficient: ~6mV/°C
     * - Range: 0.5V (-50°C) to 2.5V (+150°C)
     *
     * Formula: Temp(°C) = (V_ST - 1.0V) / 0.006V + 25°C
     *
     * ADC channels: Distributed across ADC1/2/3
     * Channels 0-29 status pins mapped to dedicated ADC channels
     */

    extern uint16_t profet_status_adc_buffer[30];  /* DMA buffer for status sense */

    /* Read from DMA buffer (automatically updated in background) */
    if (channel < 30) {
        return profet_status_adc_buffer[channel];
    }

    return (uint16_t)((1000 * 4095UL) / 3300);  /* Default 1.0V = 25°C */
#endif
}

/**
 * @brief Enable SPI-based diagnostics (high precision mode)
 * @param enable 1=enable, 0=disable
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PROFET_EnableSPIDiag(uint8_t enable)
{
    if (enable && !spi_diag_enabled) {
        /* Initialize SPI diagnostic interface */
        if (PMU_SPI_Init() != HAL_OK) {
            return HAL_ERROR;
        }
        spi_diag_enabled = 1;
    } else if (!enable && spi_diag_enabled) {
        /* Deinitialize SPI diagnostic interface */
        PMU_SPI_DeInit();
        spi_diag_enabled = 0;
    }

    return HAL_OK;
}

/**
 * @brief Get SPI diagnostic data for all channels
 * @retval Pointer to SPI diagnostic data
 */
PMU_SPI_DiagData_t* PMU_PROFET_GetSPIDiagData(void)
{
    if (!spi_diag_enabled) {
        return NULL;
    }
    return PMU_SPI_GetDiagData();
}

/**
 * @brief Calibrate current sensing (zero offset)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_PROFET_CalibrateCurrent(void)
{
    if (!spi_diag_enabled) {
        return HAL_ERROR;
    }

    /* Turn off all outputs for calibration */
    for (uint8_t ch = 0; ch < PMU30_NUM_OUTPUTS; ch++) {
        if (channels[ch].state != PMU_PROFET_STATE_OFF) {
            /* Cannot calibrate while outputs are active */
            return HAL_ERROR;
        }
    }

    /* Calibrate SPI ADC offset */
    HAL_StatusTypeDef status;

    status = PMU_SPI_CalibrateOffset(PMU_SPI_DEV_ADC_CURRENT);
    if (status != HAL_OK) {
        return status;
    }

    status = PMU_SPI_CalibrateOffset(PMU_SPI_DEV_ADC_STATUS);
    if (status != HAL_OK) {
        return status;
    }

    return HAL_OK;
}

/**
 * @brief Update current sensing for a channel using SPI ADC
 * @param channel Channel number
 * @retval None
 */
static void PROFET_UpdateCurrentSensingSPI(uint8_t channel)
{
    /* Get current from SPI diagnostic interface */
    uint32_t current_mA = PMU_SPI_GetCurrent(channel);

    /* Apply moving average filter (4 samples) */
    channels[channel].current_mA = (uint16_t)((channels[channel].current_mA * 3 + current_mA) / 4);

    /* Get temperature from SPI diagnostic interface */
    channels[channel].temperature_C = PMU_SPI_GetTemperature(channel);
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
