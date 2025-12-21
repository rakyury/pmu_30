/**
 ******************************************************************************
 * @file           : pmu_logic.c
 * @brief          : Logic Engine Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * Logic Engine Features:
 * - 100 virtual functions with up to 10 operations each
 * - 256 virtual channels for inputs/outputs/intermediate values
 * - Full set of logical, comparison, and math operations
 * - Timers, counters, edge detection, hysteresis
 * - Execution @ 500Hz (called every 2ms from control task)
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_logic.h"
#include "pmu_profet.h"
#include "pmu_hbridge.h"
#include "pmu_adc.h"
#include "pmu_can.h"
#include "stm32h7xx_hal.h"
#include <string.h>
#include <math.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/
#define LOGIC_EPSILON   0.0001f     /* Floating point comparison tolerance */

/* Private macro -------------------------------------------------------------*/
#define IS_VALID_VCHAN(v)       ((v) < PMU_LOGIC_MAX_VCHANNELS)
#define IS_VALID_FUNCTION(f)    ((f) < PMU_LOGIC_MAX_FUNCTIONS)
#define FLOAT_EQUAL(a, b)       (fabsf((a) - (b)) < LOGIC_EPSILON)

/* Private variables ---------------------------------------------------------*/
static PMU_Logic_Function_t logic_functions[PMU_LOGIC_MAX_FUNCTIONS];
static PMU_VChannel_t vchannels[PMU_LOGIC_MAX_VCHANNELS];
static PMU_Logic_Timer_t timers[PMU_LOGIC_MAX_TIMERS];
static PMU_Logic_Counter_t counters[PMU_LOGIC_MAX_COUNTERS];
static PMU_Logic_Hysteresis_t hysteresis[PMU_LOGIC_MAX_HYSTERESIS];

static uint32_t operation_count = 0;
static float prev_values[PMU_LOGIC_MAX_VCHANNELS];  /* For edge detection */

/* Private function prototypes -----------------------------------------------*/
static float ExecuteOperation(PMU_Logic_Operation_t* op);
static float GetOperandValue(uint16_t vchan_index, float constant, uint8_t use_constant);
static float LogicAND(float a, float b);
static float LogicOR(float a, float b);
static float LogicNOT(float a);
static float LogicXOR(float a, float b);
static void UpdateTimers(void);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize logic engine
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logic_Init(void)
{
    /* Clear all structures */
    memset(logic_functions, 0, sizeof(logic_functions));
    memset(vchannels, 0, sizeof(vchannels));
    memset(timers, 0, sizeof(timers));
    memset(counters, 0, sizeof(counters));
    memset(hysteresis, 0, sizeof(hysteresis));
    memset(prev_values, 0, sizeof(prev_values));

    operation_count = 0;

    /* TODO: Load logic configuration from flash memory */
    /* TODO: Initialize predefined virtual channels */

    return HAL_OK;
}

/**
 * @brief Execute all logic functions @ 500Hz
 * @retval None
 */
void PMU_Logic_Execute(void)
{
    operation_count = 0;

    /* Update virtual channels from hardware */
    PMU_Logic_UpdateVChannels();

    /* Update timers */
    UpdateTimers();

    /* Execute all enabled functions */
    for (uint8_t func_idx = 0; func_idx < PMU_LOGIC_MAX_FUNCTIONS; func_idx++) {
        PMU_Logic_Function_t* func = &logic_functions[func_idx];

        if (!func->enabled) {
            continue;
        }

        /* Execute all operations in the function */
        for (uint8_t op_idx = 0; op_idx < func->operation_count; op_idx++) {
            PMU_Logic_Operation_t* op = &func->operations[op_idx];

            /* Safety: Check operation limit */
            if (operation_count >= PMU_LOGIC_MAX_OPERATIONS) {
                /* Too many operations - skip remaining */
                return;
            }

            /* Execute operation and store result */
            float result = ExecuteOperation(op);
            if (IS_VALID_VCHAN(op->output)) {
                vchannels[op->output].value = result;
                vchannels[op->output].updated = 1;
            }

            operation_count++;
        }
    }

    /* Apply outputs to hardware */
    PMU_Logic_ApplyOutputs();

    /* Save current values for edge detection */
    for (uint16_t i = 0; i < PMU_LOGIC_MAX_VCHANNELS; i++) {
        prev_values[i] = vchannels[i].value;
    }
}

/**
 * @brief Update virtual channels from hardware
 * @retval None
 */
void PMU_Logic_UpdateVChannels(void)
{
    /* Update all virtual channels from their sources */
    for (uint16_t i = 0; i < PMU_LOGIC_MAX_VCHANNELS; i++) {
        PMU_VChannel_t* vchan = &vchannels[i];

        switch (vchan->type) {
            case VCHAN_TYPE_ADC_INPUT:
                if (vchan->index < PMU30_NUM_ADC_INPUTS) {
                    vchan->value = PMU_ADC_GetScaledValue(vchan->index);
                }
                break;

            case VCHAN_TYPE_PROFET_CURRENT:
                if (vchan->index < PMU30_NUM_OUTPUTS) {
                    vchan->value = (float)PMU_PROFET_GetCurrent(vchan->index) / 1000.0f;  /* mA to A */
                }
                break;

            case VCHAN_TYPE_HBRIDGE_CURRENT:
                if (vchan->index < PMU30_NUM_HBRIDGES) {
                    vchan->value = (float)PMU_HBridge_GetCurrent(vchan->index) / 1000.0f;  /* mA to A */
                }
                break;

            case VCHAN_TYPE_SYSTEM_VOLTAGE:
                /* TODO: Read system voltage from ADC */
                vchan->value = 12.0f;  /* Placeholder */
                break;

            case VCHAN_TYPE_SYSTEM_TEMP:
                /* TODO: Read board temperature */
                vchan->value = 25.0f;  /* Placeholder */
                break;

            case VCHAN_TYPE_CAN_SIGNAL:
                /* TODO: Get CAN signal value */
                break;

            case VCHAN_TYPE_CONSTANT:
            case VCHAN_TYPE_VIRTUAL:
            default:
                /* These are set by logic operations */
                break;
        }
    }
}

/**
 * @brief Apply virtual channel outputs to hardware
 * @retval None
 */
void PMU_Logic_ApplyOutputs(void)
{
    /* Apply virtual channels to hardware outputs */
    for (uint16_t i = 0; i < PMU_LOGIC_MAX_VCHANNELS; i++) {
        PMU_VChannel_t* vchan = &vchannels[i];

        if (!vchan->updated) {
            continue;
        }

        switch (vchan->type) {
            case VCHAN_TYPE_PROFET_OUTPUT:
                if (vchan->index < PMU30_NUM_OUTPUTS) {
                    /* Set PROFET output state (0/1 or PWM duty 0-1000) */
                    uint16_t duty = (uint16_t)(vchan->value * 1000.0f);
                    if (duty > 0 && duty < 1000) {
                        PMU_PROFET_SetPWM(vchan->index, duty);
                    } else {
                        PMU_PROFET_SetState(vchan->index, (duty > 500) ? 1 : 0);
                    }
                }
                break;

            case VCHAN_TYPE_HBRIDGE_OUTPUT:
                if (vchan->index < PMU30_NUM_HBRIDGES) {
                    /* Set H-Bridge output */
                    uint16_t duty = (uint16_t)(fabsf(vchan->value) * 1000.0f);
                    PMU_HBridge_Mode_t mode = (vchan->value > 0) ?
                        PMU_HBRIDGE_MODE_FORWARD : PMU_HBRIDGE_MODE_REVERSE;
                    if (fabsf(vchan->value) < 0.01f) {
                        mode = PMU_HBRIDGE_MODE_COAST;
                    }
                    PMU_HBridge_SetMode(vchan->index, mode, duty);
                }
                break;

            default:
                /* Not an output type */
                break;
        }

        vchan->updated = 0;
    }
}

/**
 * @brief Get virtual channel value
 * @param vchan Virtual channel index
 * @retval Channel value
 */
float PMU_Logic_GetVChannel(uint16_t vchan)
{
    if (!IS_VALID_VCHAN(vchan)) {
        return 0.0f;
    }
    return vchannels[vchan].value;
}

/**
 * @brief Set virtual channel value
 * @param vchan Virtual channel index
 * @param value Value to set
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logic_SetVChannel(uint16_t vchan, float value)
{
    if (!IS_VALID_VCHAN(vchan)) {
        return HAL_ERROR;
    }

    vchannels[vchan].value = value;
    vchannels[vchan].updated = 1;

    return HAL_OK;
}

/**
 * @brief Add logic function
 * @param func_index Function index (0-99)
 * @param function Pointer to function structure
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logic_AddFunction(uint8_t func_index, PMU_Logic_Function_t* function)
{
    if (!IS_VALID_FUNCTION(func_index) || function == NULL) {
        return HAL_ERROR;
    }

    memcpy(&logic_functions[func_index], function, sizeof(PMU_Logic_Function_t));

    return HAL_OK;
}

/**
 * @brief Enable/disable logic function
 * @param func_index Function index (0-99)
 * @param enable Enable flag
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logic_EnableFunction(uint8_t func_index, uint8_t enable)
{
    if (!IS_VALID_FUNCTION(func_index)) {
        return HAL_ERROR;
    }

    logic_functions[func_index].enabled = enable;

    return HAL_OK;
}

/**
 * @brief Start timer
 * @param timer_index Timer index (0-31)
 * @param duration_ms Duration in milliseconds
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logic_StartTimer(uint8_t timer_index, uint32_t duration_ms)
{
    if (timer_index >= PMU_LOGIC_MAX_TIMERS) {
        return HAL_ERROR;
    }

    timers[timer_index].start_time = HAL_GetTick();
    timers[timer_index].duration_ms = duration_ms;
    timers[timer_index].active = 1;
    timers[timer_index].expired = 0;

    return HAL_OK;
}

/**
 * @brief Check if timer expired
 * @param timer_index Timer index (0-31)
 * @retval 1 if expired, 0 otherwise
 */
uint8_t PMU_Logic_TimerExpired(uint8_t timer_index)
{
    if (timer_index >= PMU_LOGIC_MAX_TIMERS) {
        return 0;
    }

    return timers[timer_index].expired;
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Execute a single logic operation
 * @param op Pointer to operation structure
 * @retval Operation result
 */
static float ExecuteOperation(PMU_Logic_Operation_t* op)
{
    float a = GetOperandValue(op->input_a, op->constant_a, op->use_constant_a);
    float b = GetOperandValue(op->input_b, op->constant_b, op->use_constant_b);
    float c = GetOperandValue(op->input_c, op->constant_c, op->use_constant_c);
    float result = 0.0f;

    switch (op->operation) {
        /* Logical operations */
        case LOGIC_OP_AND:
            result = LogicAND(a, b);
            break;

        case LOGIC_OP_OR:
            result = LogicOR(a, b);
            break;

        case LOGIC_OP_NOT:
            result = LogicNOT(a);
            break;

        case LOGIC_OP_XOR:
            result = LogicXOR(a, b);
            break;

        /* Comparison operations */
        case LOGIC_OP_GREATER:
            result = (a > b) ? 1.0f : 0.0f;
            break;

        case LOGIC_OP_LESS:
            result = (a < b) ? 1.0f : 0.0f;
            break;

        case LOGIC_OP_EQUAL:
            result = FLOAT_EQUAL(a, b) ? 1.0f : 0.0f;
            break;

        case LOGIC_OP_NOT_EQUAL:
            result = !FLOAT_EQUAL(a, b) ? 1.0f : 0.0f;
            break;

        case LOGIC_OP_GREATER_EQUAL:
            result = (a >= b || FLOAT_EQUAL(a, b)) ? 1.0f : 0.0f;
            break;

        case LOGIC_OP_LESS_EQUAL:
            result = (a <= b || FLOAT_EQUAL(a, b)) ? 1.0f : 0.0f;
            break;

        /* Math operations */
        case LOGIC_OP_ADD:
            result = a + b;
            break;

        case LOGIC_OP_SUBTRACT:
            result = a - b;
            break;

        case LOGIC_OP_MULTIPLY:
            result = a * b;
            break;

        case LOGIC_OP_DIVIDE:
            result = (fabsf(b) > LOGIC_EPSILON) ? (a / b) : 0.0f;  /* Prevent division by zero */
            break;

        case LOGIC_OP_MODULO:
            result = (int32_t)a % (int32_t)b;  /* Integer modulo */
            break;

        case LOGIC_OP_MIN:
            result = (a < b) ? a : b;
            break;

        case LOGIC_OP_MAX:
            result = (a > b) ? a : b;
            break;

        case LOGIC_OP_ABS:
            result = fabsf(a);
            break;

        case LOGIC_OP_CLAMP:
            /* Clamp a between b (min) and c (max) */
            result = (a < b) ? b : ((a > c) ? c : a);
            break;

        /* Special operations */
        case LOGIC_OP_EDGE_RISING:
            /* Rising edge: previous was 0, current is 1 */
            result = (prev_values[op->input_a] < 0.5f && a >= 0.5f) ? 1.0f : 0.0f;
            break;

        case LOGIC_OP_EDGE_FALLING:
            /* Falling edge: previous was 1, current is 0 */
            result = (prev_values[op->input_a] >= 0.5f && a < 0.5f) ? 1.0f : 0.0f;
            break;

        case LOGIC_OP_HYSTERESIS:
            /* Hysteresis: b = low threshold, c = high threshold */
            {
                uint8_t hyst_idx = (uint8_t)op->input_a % PMU_LOGIC_MAX_HYSTERESIS;
                if (a > c) {
                    hysteresis[hyst_idx].state = 1;
                } else if (a < b) {
                    hysteresis[hyst_idx].state = 0;
                }
                result = hysteresis[hyst_idx].state ? 1.0f : 0.0f;
            }
            break;

        case LOGIC_OP_TOGGLE:
            /* Toggle output on rising edge of input */
            if (prev_values[op->input_a] < 0.5f && a >= 0.5f) {
                result = (vchannels[op->output].value < 0.5f) ? 1.0f : 0.0f;
            } else {
                result = vchannels[op->output].value;  /* Keep current state */
            }
            break;

        case LOGIC_OP_SET:
            result = 1.0f;
            break;

        case LOGIC_OP_RESET:
            result = 0.0f;
            break;

        default:
            result = 0.0f;
            break;
    }

    return result;
}

/**
 * @brief Get operand value (from vchannel or constant)
 * @param vchan_index Virtual channel index
 * @param constant Constant value
 * @param use_constant Flag to use constant instead of vchannel
 * @retval Operand value
 */
static float GetOperandValue(uint16_t vchan_index, float constant, uint8_t use_constant)
{
    if (use_constant) {
        return constant;
    }

    if (IS_VALID_VCHAN(vchan_index)) {
        return vchannels[vchan_index].value;
    }

    return 0.0f;
}

/**
 * @brief Logical AND operation
 * @param a First operand
 * @param b Second operand
 * @retval 1.0f if both non-zero, 0.0f otherwise
 */
static float LogicAND(float a, float b)
{
    return ((a > 0.5f) && (b > 0.5f)) ? 1.0f : 0.0f;
}

/**
 * @brief Logical OR operation
 * @param a First operand
 * @param b Second operand
 * @retval 1.0f if any non-zero, 0.0f otherwise
 */
static float LogicOR(float a, float b)
{
    return ((a > 0.5f) || (b > 0.5f)) ? 1.0f : 0.0f;
}

/**
 * @brief Logical NOT operation
 * @param a Operand
 * @retval 1.0f if zero, 0.0f if non-zero
 */
static float LogicNOT(float a)
{
    return (a < 0.5f) ? 1.0f : 0.0f;
}

/**
 * @brief Logical XOR operation
 * @param a First operand
 * @param b Second operand
 * @retval 1.0f if exactly one is non-zero, 0.0f otherwise
 */
static float LogicXOR(float a, float b)
{
    uint8_t a_bool = (a > 0.5f);
    uint8_t b_bool = (b > 0.5f);
    return (a_bool ^ b_bool) ? 1.0f : 0.0f;
}

/**
 * @brief Update all timers
 * @retval None
 */
static void UpdateTimers(void)
{
    uint32_t current_time = HAL_GetTick();

    for (uint8_t i = 0; i < PMU_LOGIC_MAX_TIMERS; i++) {
        if (!timers[i].active) {
            continue;
        }

        uint32_t elapsed = current_time - timers[i].start_time;

        if (elapsed >= timers[i].duration_ms) {
            timers[i].expired = 1;
            timers[i].active = 0;
        }
    }
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
