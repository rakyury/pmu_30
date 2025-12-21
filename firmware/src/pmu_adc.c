/**
 ******************************************************************************
 * @file           : pmu_adc.c
 * @brief          : Universal ADC Input Driver Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * 20 Universal Analog/Digital Inputs Implementation:
 * - Switch Active Low: Digital input with active low logic
 * - Switch Active High: Digital input with active high logic
 * - Rotary Switch: Multi-position switch with voltage divider
 * - Linear Analog: Linear voltage input (0-5V or 0-10V)
 * - Calibrated Analog: Analog input with custom calibration curve
 * - Frequency Input: Digital frequency measurement (RPM, speed, etc.)
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_adc.h"
#include "stm32h7xx_hal.h"
#include <string.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/
#define ADC_DMA_BUFFER_SIZE     20          /* 20 channels */
#define FREQUENCY_SAMPLE_TIME_MS 1000       /* 1 second for frequency measurement */

/* Private macro -------------------------------------------------------------*/
#define IS_VALID_INPUT(ch)      ((ch) < PMU30_NUM_ADC_INPUTS)
#define VOLTAGE_FROM_ADC(adc)   (((adc) * PMU_ADC_VREF_MV) / PMU_ADC_RESOLUTION)

/* Private variables ---------------------------------------------------------*/
static PMU_ADC_Input_t inputs[PMU30_NUM_ADC_INPUTS];
static PMU_InputConfig_t* input_configs[PMU30_NUM_ADC_INPUTS];
static uint16_t adc_dma_buffer[ADC_DMA_BUFFER_SIZE];
static ADC_HandleTypeDef* hadc_inputs;

/* Private function prototypes -----------------------------------------------*/
static void ADC_ProcessSwitchActiveLow(uint8_t channel);
static void ADC_ProcessSwitchActiveHigh(uint8_t channel);
static void ADC_ProcessRotarySwitch(uint8_t channel);
static void ADC_ProcessLinearAnalog(uint8_t channel);
static void ADC_ProcessCalibratedAnalog(uint8_t channel);
static void ADC_ProcessFrequencyInput(uint8_t channel);
static uint16_t ADC_ApplyFilter(uint8_t channel, uint16_t new_value);
static float ADC_ApplyCalibration(PMU_InputConfig_t* config, uint16_t raw);
static uint16_t ADC_ReadChannel(uint8_t channel);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize ADC driver
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_ADC_Init(void)
{
    HAL_StatusTypeDef status = HAL_OK;

    /* Clear all data */
    memset(inputs, 0, sizeof(inputs));
    memset(input_configs, 0, sizeof(input_configs));
    memset(adc_dma_buffer, 0, sizeof(adc_dma_buffer));

    /* Initialize all inputs */
    for (uint8_t i = 0; i < PMU30_NUM_ADC_INPUTS; i++) {
        inputs[i].raw_value = 0;
        inputs[i].scaled_value = 0.0f;
        inputs[i].digital_state = 0;
        inputs[i].frequency_hz = 0;
        inputs[i].debounce_counter = 0;
        inputs[i].filter_index = 0;
        inputs[i].last_edge_time = 0;
        inputs[i].edge_count = 0;
    }

    /* TODO: Initialize ADC1/ADC2/ADC3 with DMA for continuous conversion */
    /* TODO: Configure GPIO pins for analog inputs with protection */
    /* TODO: Configure external interrupt for frequency inputs */

    return status;
}

/**
 * @brief Update all ADC inputs - call at 1kHz
 * @retval None
 */
void PMU_ADC_Update(void)
{
    /* Read all ADC channels (would be automatic with DMA) */
    for (uint8_t i = 0; i < PMU30_NUM_ADC_INPUTS; i++) {
        /* Read and filter raw ADC value */
        uint16_t raw = ADC_ReadChannel(i);
        inputs[i].raw_value = ADC_ApplyFilter(i, raw);

        /* Process based on configured input type */
        if (input_configs[i] != NULL) {
            switch (input_configs[i]->type) {
                case PMU_INPUT_SWITCH_ACTIVE_LOW:
                    ADC_ProcessSwitchActiveLow(i);
                    break;

                case PMU_INPUT_SWITCH_ACTIVE_HIGH:
                    ADC_ProcessSwitchActiveHigh(i);
                    break;

                case PMU_INPUT_ROTARY_SWITCH:
                    ADC_ProcessRotarySwitch(i);
                    break;

                case PMU_INPUT_LINEAR_ANALOG:
                    ADC_ProcessLinearAnalog(i);
                    break;

                case PMU_INPUT_CALIBRATED_ANALOG:
                    ADC_ProcessCalibratedAnalog(i);
                    break;

                case PMU_INPUT_FREQUENCY:
                    ADC_ProcessFrequencyInput(i);
                    break;

                default:
                    /* Unknown type - treat as raw analog */
                    inputs[i].scaled_value = VOLTAGE_FROM_ADC(inputs[i].raw_value) / 1000.0f;
                    break;
            }
        }
    }
}

/**
 * @brief Get raw ADC value
 * @param channel Input channel (0-19)
 * @retval Raw ADC value (0-1023)
 */
uint16_t PMU_ADC_GetRawValue(uint8_t channel)
{
    if (!IS_VALID_INPUT(channel)) {
        return 0;
    }
    return inputs[channel].raw_value;
}

/**
 * @brief Get scaled value with calibration applied
 * @param channel Input channel (0-19)
 * @retval Scaled value in configured units
 */
float PMU_ADC_GetScaledValue(uint8_t channel)
{
    if (!IS_VALID_INPUT(channel)) {
        return 0.0f;
    }
    return inputs[channel].scaled_value;
}

/**
 * @brief Get digital state (for switch inputs)
 * @param channel Input channel (0-19)
 * @retval Digital state (0 or 1)
 */
uint8_t PMU_ADC_GetDigitalState(uint8_t channel)
{
    if (!IS_VALID_INPUT(channel)) {
        return 0;
    }
    return inputs[channel].digital_state;
}

/**
 * @brief Get frequency (for frequency inputs)
 * @param channel Input channel (0-19)
 * @retval Frequency in Hz
 */
uint32_t PMU_ADC_GetFrequency(uint8_t channel)
{
    if (!IS_VALID_INPUT(channel)) {
        return 0;
    }
    return inputs[channel].frequency_hz;
}

/**
 * @brief Get input runtime data
 * @param channel Input channel (0-19)
 * @retval Pointer to input data
 */
PMU_ADC_Input_t* PMU_ADC_GetInputData(uint8_t channel)
{
    if (!IS_VALID_INPUT(channel)) {
        return NULL;
    }
    return &inputs[channel];
}

/**
 * @brief Set input configuration
 * @param channel Input channel (0-19)
 * @param config Pointer to configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_ADC_SetConfig(uint8_t channel, PMU_InputConfig_t* config)
{
    if (!IS_VALID_INPUT(channel) || config == NULL) {
        return HAL_ERROR;
    }

    input_configs[channel] = config;

    /* Clear filter buffer when config changes */
    memset(inputs[channel].filter_buffer, 0, sizeof(inputs[channel].filter_buffer));
    inputs[channel].filter_index = 0;

    return HAL_OK;
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Process Switch Active Low input
 * @param channel Input channel
 * @retval None
 */
static void ADC_ProcessSwitchActiveLow(uint8_t channel)
{
    PMU_InputConfig_t* cfg = input_configs[channel];
    uint16_t voltage_mv = VOLTAGE_FROM_ADC(inputs[channel].raw_value);

    /* Active low: LOW = pressed (1), HIGH = released (0) */
    uint8_t new_state = (voltage_mv < cfg->threshold_low_mv) ? 1 : 0;

    /* Debouncing */
    if (new_state != inputs[channel].digital_state) {
        inputs[channel].debounce_counter++;
        if (inputs[channel].debounce_counter >= cfg->debounce_ms) {
            inputs[channel].digital_state = new_state;
            inputs[channel].debounce_counter = 0;
        }
    } else {
        inputs[channel].debounce_counter = 0;
    }

    inputs[channel].scaled_value = (float)inputs[channel].digital_state;
}

/**
 * @brief Process Switch Active High input
 * @param channel Input channel
 * @retval None
 */
static void ADC_ProcessSwitchActiveHigh(uint8_t channel)
{
    PMU_InputConfig_t* cfg = input_configs[channel];
    uint16_t voltage_mv = VOLTAGE_FROM_ADC(inputs[channel].raw_value);

    /* Active high: HIGH = pressed (1), LOW = released (0) */
    uint8_t new_state = (voltage_mv > cfg->threshold_high_mv) ? 1 : 0;

    /* Debouncing */
    if (new_state != inputs[channel].digital_state) {
        inputs[channel].debounce_counter++;
        if (inputs[channel].debounce_counter >= cfg->debounce_ms) {
            inputs[channel].digital_state = new_state;
            inputs[channel].debounce_counter = 0;
        }
    } else {
        inputs[channel].debounce_counter = 0;
    }

    inputs[channel].scaled_value = (float)inputs[channel].digital_state;
}

/**
 * @brief Process Rotary Switch input (multi-position with voltage divider)
 * @param channel Input channel
 * @retval None
 */
static void ADC_ProcessRotarySwitch(uint8_t channel)
{
    PMU_InputConfig_t* cfg = input_configs[channel];
    uint16_t voltage_mv = VOLTAGE_FROM_ADC(inputs[channel].raw_value);

    /* Determine switch position based on voltage ranges
     * Example for 8-position switch:
     * Pos 0: 0.00V, Pos 1: 0.71V, Pos 2: 1.43V, Pos 3: 2.14V
     * Pos 4: 2.86V, Pos 5: 3.57V, Pos 6: 4.29V, Pos 7: 5.00V
     */

    /* Calculate position (0-7 for 8-position switch) */
    uint8_t position = 0;
    uint16_t step_mv = 5000 / 8; /* Assuming 8 positions and 5V range */

    for (uint8_t i = 0; i < 8; i++) {
        uint16_t pos_voltage = i * step_mv;
        if (voltage_mv < (pos_voltage + step_mv / 2)) {
            position = i;
            break;
        }
    }

    inputs[channel].digital_state = position;
    inputs[channel].scaled_value = (float)position;
}

/**
 * @brief Process Linear Analog input
 * @param channel Input channel
 * @retval None
 */
static void ADC_ProcessLinearAnalog(uint8_t channel)
{
    PMU_InputConfig_t* cfg = input_configs[channel];

    /* Apply linear scaling: Result = (Raw × Multiplier / Divider) + Offset */
    float voltage_v = VOLTAGE_FROM_ADC(inputs[channel].raw_value) / 1000.0f;
    inputs[channel].scaled_value = (voltage_v * cfg->multiplier) + cfg->offset;
}

/**
 * @brief Process Calibrated Analog input with custom curve
 * @param channel Input channel
 * @retval None
 */
static void ADC_ProcessCalibratedAnalog(uint8_t channel)
{
    PMU_InputConfig_t* cfg = input_configs[channel];

    /* Apply calibration curve if available */
    inputs[channel].scaled_value = ADC_ApplyCalibration(cfg, inputs[channel].raw_value);
}

/**
 * @brief Process Frequency Input (for RPM, speed sensors, etc.)
 * @param channel Input channel
 * @retval None
 */
static void ADC_ProcessFrequencyInput(uint8_t channel)
{
    /* Frequency measurement using edge counting
     * This would typically use an external interrupt or timer input capture
     * For now, calculate based on edge count over sample period
     */

    static uint32_t last_freq_update[PMU30_NUM_ADC_INPUTS] = {0};
    uint32_t current_time = HAL_GetTick();

    /* Update frequency every second */
    if ((current_time - last_freq_update[channel]) >= FREQUENCY_SAMPLE_TIME_MS) {
        /* Calculate frequency from edge count */
        inputs[channel].frequency_hz = inputs[channel].edge_count;
        inputs[channel].edge_count = 0;
        last_freq_update[channel] = current_time;
    }

    /* Apply multiplier for RPM calculation (e.g., pulses per revolution) */
    PMU_InputConfig_t* cfg = input_configs[channel];
    if (cfg != NULL) {
        inputs[channel].scaled_value = inputs[channel].frequency_hz * cfg->multiplier;
    } else {
        inputs[channel].scaled_value = (float)inputs[channel].frequency_hz;
    }
}

/**
 * @brief Apply moving average filter
 * @param channel Input channel
 * @param new_value New raw value
 * @retval Filtered value
 */
static uint16_t ADC_ApplyFilter(uint8_t channel, uint16_t new_value)
{
    /* Get filter size from config, default to 4 samples */
    uint8_t filter_size = 4;
    if (input_configs[channel] != NULL && input_configs[channel]->filter_samples > 0) {
        filter_size = input_configs[channel]->filter_samples;
        if (filter_size > 8) filter_size = 8;
    }

    /* Add to circular buffer */
    inputs[channel].filter_buffer[inputs[channel].filter_index] = new_value;
    inputs[channel].filter_index = (inputs[channel].filter_index + 1) % filter_size;

    /* Calculate average */
    uint32_t sum = 0;
    for (uint8_t i = 0; i < filter_size; i++) {
        sum += inputs[channel].filter_buffer[i];
    }

    return (uint16_t)(sum / filter_size);
}

/**
 * @brief Apply calibration curve to raw value
 * @param config Input configuration
 * @param raw Raw ADC value
 * @retval Calibrated value
 */
static float ADC_ApplyCalibration(PMU_InputConfig_t* config, uint16_t raw)
{
    /* For now, use simple linear calibration
     * In full implementation, this could use lookup table with interpolation
     * for non-linear sensors (temp sensors, pressure sensors, etc.)
     */

    float voltage_v = VOLTAGE_FROM_ADC(raw) / 1000.0f;
    return (voltage_v * config->multiplier) + config->offset;
}

/**
 * @brief Read ADC channel value
 * @param channel Input channel
 * @retval Raw ADC value (0-1023)
 */
static uint16_t ADC_ReadChannel(uint8_t channel)
{
    /* With DMA, this would just read from DMA buffer */
    if (channel < ADC_DMA_BUFFER_SIZE) {
        /* STM32H7 has 16-bit ADC, scale to 10-bit */
        return adc_dma_buffer[channel] >> 6;
    }

    /* TODO: For real hardware, implement actual ADC reading */
    /* For now, return dummy value */
    return 512; /* Mid-scale */
}

/**
 * @brief EXTI callback for frequency input edge detection
 * @param GPIO_Pin Pin number
 * @retval None
 */
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    /* Determine which input channel triggered the interrupt */
    for (uint8_t i = 0; i < PMU30_NUM_ADC_INPUTS; i++) {
        if (input_configs[i] != NULL &&
            input_configs[i]->type == PMU_INPUT_FREQUENCY) {

            /* Increment edge counter */
            inputs[i].edge_count++;
            inputs[i].last_edge_time = HAL_GetTick();
            break;
        }
    }
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
