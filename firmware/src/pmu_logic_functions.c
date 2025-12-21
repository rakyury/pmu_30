/**
 ******************************************************************************
 * @file           : pmu_logic_functions.c
 * @brief          : Logic Functions Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_logic_functions.h"
#include "pmu_channel.h"
#include <string.h>
#include <stdlib.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_LogicFunction_t logic_functions[PMU_MAX_LOGIC_FUNCTIONS];
static uint16_t function_count = 0;
static uint16_t next_function_id = 1;

/* Private function prototypes -----------------------------------------------*/
static int32_t LogicFunc_ExecuteMath(PMU_LogicFunction_t* func);
static int32_t LogicFunc_ExecuteComparison(PMU_LogicFunction_t* func);
static int32_t LogicFunc_ExecuteLogic(PMU_LogicFunction_t* func);
static int32_t LogicFunc_ExecutePID(PMU_LogicFunction_t* func);
static int32_t LogicFunc_ExecuteHysteresis(PMU_LogicFunction_t* func);
static int32_t LogicFunc_ExecuteRateLimit(PMU_LogicFunction_t* func);
static int32_t LogicFunc_ExecuteDebounce(PMU_LogicFunction_t* func);
static int32_t LogicFunc_ExecuteTable1D(PMU_LogicFunction_t* func);
static int32_t LogicFunc_ExecuteMovingAvg(PMU_LogicFunction_t* func);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize logic functions module
 */
HAL_StatusTypeDef PMU_LogicFunctions_Init(void)
{
    memset(logic_functions, 0, sizeof(logic_functions));
    function_count = 0;
    next_function_id = 1;

    return HAL_OK;
}

/**
 * @brief Register a new logic function
 */
HAL_StatusTypeDef PMU_LogicFunctions_Register(PMU_LogicFunction_t* func)
{
    if (func == NULL || function_count >= PMU_MAX_LOGIC_FUNCTIONS) {
        return HAL_ERROR;
    }

    /* Assign function ID if not set */
    if (func->function_id == 0) {
        func->function_id = next_function_id++;
    }

    /* Copy function to registry */
    memcpy(&logic_functions[function_count], func, sizeof(PMU_LogicFunction_t));
    function_count++;

    return HAL_OK;
}

/**
 * @brief Unregister a logic function
 */
HAL_StatusTypeDef PMU_LogicFunctions_Unregister(uint16_t function_id)
{
    for (uint16_t i = 0; i < function_count; i++) {
        if (logic_functions[i].function_id == function_id) {
            /* Shift remaining functions down */
            for (uint16_t j = i; j < function_count - 1; j++) {
                memcpy(&logic_functions[j], &logic_functions[j + 1],
                       sizeof(PMU_LogicFunction_t));
            }
            function_count--;
            return HAL_OK;
        }
    }

    return HAL_ERROR;
}

/**
 * @brief Update all logic functions
 */
void PMU_LogicFunctions_Update(void)
{
    for (uint16_t i = 0; i < function_count; i++) {
        PMU_LogicFunction_t* func = &logic_functions[i];

        if (!func->enabled) {
            continue;
        }

        int32_t result = 0;

        /* Execute function based on type */
        switch (func->type) {
            /* Mathematical operations */
            case PMU_FUNC_ADD:
            case PMU_FUNC_SUBTRACT:
            case PMU_FUNC_MULTIPLY:
            case PMU_FUNC_DIVIDE:
            case PMU_FUNC_MIN:
            case PMU_FUNC_MAX:
            case PMU_FUNC_AVERAGE:
            case PMU_FUNC_ABS:
            case PMU_FUNC_SCALE:
            case PMU_FUNC_CLAMP:
                result = LogicFunc_ExecuteMath(func);
                break;

            /* Comparison operations */
            case PMU_FUNC_GREATER:
            case PMU_FUNC_LESS:
            case PMU_FUNC_EQUAL:
            case PMU_FUNC_NOT_EQUAL:
            case PMU_FUNC_GREATER_EQUAL:
            case PMU_FUNC_LESS_EQUAL:
            case PMU_FUNC_IN_RANGE:
                result = LogicFunc_ExecuteComparison(func);
                break;

            /* Logic operations */
            case PMU_FUNC_AND:
            case PMU_FUNC_OR:
            case PMU_FUNC_NOT:
            case PMU_FUNC_XOR:
            case PMU_FUNC_NAND:
            case PMU_FUNC_NOR:
                result = LogicFunc_ExecuteLogic(func);
                break;

            /* Tables */
            case PMU_FUNC_TABLE_1D:
                result = LogicFunc_ExecuteTable1D(func);
                break;

            /* Filters */
            case PMU_FUNC_MOVING_AVG:
                result = LogicFunc_ExecuteMovingAvg(func);
                break;

            /* Control */
            case PMU_FUNC_PID:
                result = LogicFunc_ExecutePID(func);
                break;

            case PMU_FUNC_HYSTERESIS:
                result = LogicFunc_ExecuteHysteresis(func);
                break;

            case PMU_FUNC_RATE_LIMIT:
                result = LogicFunc_ExecuteRateLimit(func);
                break;

            case PMU_FUNC_DEBOUNCE:
                result = LogicFunc_ExecuteDebounce(func);
                break;

            default:
                continue;
        }

        /* Write result to output channel */
        PMU_Channel_SetValue(func->output_channel, result);
    }
}

/**
 * @brief Get function by ID
 */
PMU_LogicFunction_t* PMU_LogicFunctions_GetByID(uint16_t function_id)
{
    for (uint16_t i = 0; i < function_count; i++) {
        if (logic_functions[i].function_id == function_id) {
            return &logic_functions[i];
        }
    }
    return NULL;
}

/**
 * @brief Enable/disable function
 */
HAL_StatusTypeDef PMU_LogicFunctions_SetEnabled(uint16_t function_id, bool enabled)
{
    PMU_LogicFunction_t* func = PMU_LogicFunctions_GetByID(function_id);
    if (func) {
        func->enabled = enabled ? 1 : 0;
        return HAL_OK;
    }
    return HAL_ERROR;
}

/**
 * @brief Create simple math function
 */
uint16_t PMU_LogicFunctions_CreateMath(PMU_FunctionType_t type,
                                        uint16_t output_ch,
                                        uint16_t input_a,
                                        uint16_t input_b)
{
    PMU_LogicFunction_t func = {0};
    func.type = type;
    func.output_channel = output_ch;
    func.input_channels[0] = input_a;
    func.input_channels[1] = input_b;
    func.input_count = 2;
    func.enabled = 1;

    if (PMU_LogicFunctions_Register(&func) == HAL_OK) {
        return func.function_id;
    }
    return 0;
}

/**
 * @brief Create comparison function
 */
uint16_t PMU_LogicFunctions_CreateComparison(PMU_FunctionType_t type,
                                              uint16_t output_ch,
                                              uint16_t input_a,
                                              uint16_t input_b)
{
    return PMU_LogicFunctions_CreateMath(type, output_ch, input_a, input_b);
}

/**
 * @brief Create PID controller
 */
uint16_t PMU_LogicFunctions_CreatePID(uint16_t output_ch,
                                       uint16_t input_ch,
                                       float setpoint,
                                       float kp,
                                       float ki,
                                       float kd)
{
    PMU_LogicFunction_t func = {0};
    func.type = PMU_FUNC_PID;
    func.output_channel = output_ch;
    func.input_channels[0] = input_ch;
    func.input_count = 1;
    func.enabled = 1;

    func.params.pid.kp = kp;
    func.params.pid.ki = ki;
    func.params.pid.kd = kd;
    func.params.pid.setpoint = setpoint;
    func.params.pid.output_min = 0;
    func.params.pid.output_max = 1000;
    func.params.pid.integral = 0.0f;
    func.params.pid.last_error = 0;
    func.params.pid.last_update_ms = 0;

    if (PMU_LogicFunctions_Register(&func) == HAL_OK) {
        return func.function_id;
    }
    return 0;
}

/**
 * @brief Create hysteresis function
 */
uint16_t PMU_LogicFunctions_CreateHysteresis(uint16_t output_ch,
                                              uint16_t input_ch,
                                              int32_t threshold_on,
                                              int32_t threshold_off)
{
    PMU_LogicFunction_t func = {0};
    func.type = PMU_FUNC_HYSTERESIS;
    func.output_channel = output_ch;
    func.input_channels[0] = input_ch;
    func.input_count = 1;
    func.enabled = 1;

    func.params.hysteresis.threshold_on = threshold_on;
    func.params.hysteresis.threshold_off = threshold_off;
    func.params.hysteresis.state = 0;

    if (PMU_LogicFunctions_Register(&func) == HAL_OK) {
        return func.function_id;
    }
    return 0;
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Execute mathematical operation
 */
static int32_t LogicFunc_ExecuteMath(PMU_LogicFunction_t* func)
{
    int32_t a = (func->input_count > 0) ? PMU_Channel_GetValue(func->input_channels[0]) : 0;
    int32_t b = (func->input_count > 1) ? PMU_Channel_GetValue(func->input_channels[1]) : 0;

    switch (func->type) {
        case PMU_FUNC_ADD:
            return a + b;

        case PMU_FUNC_SUBTRACT:
            return a - b;

        case PMU_FUNC_MULTIPLY:
            return (int32_t)(((int64_t)a * b) / 1000);  /* Fixed-point */

        case PMU_FUNC_DIVIDE:
            return (b != 0) ? ((int64_t)a * 1000 / b) : 0;

        case PMU_FUNC_MIN: {
            int32_t min = a;
            for (uint8_t i = 1; i < func->input_count; i++) {
                int32_t val = PMU_Channel_GetValue(func->input_channels[i]);
                if (val < min) min = val;
            }
            return min;
        }

        case PMU_FUNC_MAX: {
            int32_t max = a;
            for (uint8_t i = 1; i < func->input_count; i++) {
                int32_t val = PMU_Channel_GetValue(func->input_channels[i]);
                if (val > max) max = val;
            }
            return max;
        }

        case PMU_FUNC_AVERAGE: {
            int64_t sum = 0;
            for (uint8_t i = 0; i < func->input_count; i++) {
                sum += PMU_Channel_GetValue(func->input_channels[i]);
            }
            return (int32_t)(sum / func->input_count);
        }

        case PMU_FUNC_ABS:
            return (a < 0) ? -a : a;

        case PMU_FUNC_SCALE:
            return (int32_t)(((int64_t)a * func->params.scale.scale) / 1000 + func->params.scale.offset);

        case PMU_FUNC_CLAMP:
            if (a < func->params.clamp.min) return func->params.clamp.min;
            if (a > func->params.clamp.max) return func->params.clamp.max;
            return a;

        default:
            return 0;
    }
}

/**
 * @brief Execute comparison operation
 */
static int32_t LogicFunc_ExecuteComparison(PMU_LogicFunction_t* func)
{
    int32_t a = PMU_Channel_GetValue(func->input_channels[0]);
    int32_t b = (func->input_count > 1) ? PMU_Channel_GetValue(func->input_channels[1]) : 0;

    switch (func->type) {
        case PMU_FUNC_GREATER:
            return (a > b) ? 1 : 0;

        case PMU_FUNC_LESS:
            return (a < b) ? 1 : 0;

        case PMU_FUNC_EQUAL:
            return (a == b) ? 1 : 0;

        case PMU_FUNC_NOT_EQUAL:
            return (a != b) ? 1 : 0;

        case PMU_FUNC_GREATER_EQUAL:
            return (a >= b) ? 1 : 0;

        case PMU_FUNC_LESS_EQUAL:
            return (a <= b) ? 1 : 0;

        case PMU_FUNC_IN_RANGE:
            return (a >= func->params.clamp.min && a <= func->params.clamp.max) ? 1 : 0;

        default:
            return 0;
    }
}

/**
 * @brief Execute logic operation
 */
static int32_t LogicFunc_ExecuteLogic(PMU_LogicFunction_t* func)
{
    switch (func->type) {
        case PMU_FUNC_AND: {
            for (uint8_t i = 0; i < func->input_count; i++) {
                if (PMU_Channel_GetValue(func->input_channels[i]) == 0) {
                    return 0;
                }
            }
            return 1;
        }

        case PMU_FUNC_OR: {
            for (uint8_t i = 0; i < func->input_count; i++) {
                if (PMU_Channel_GetValue(func->input_channels[i]) != 0) {
                    return 1;
                }
            }
            return 0;
        }

        case PMU_FUNC_NOT:
            return (PMU_Channel_GetValue(func->input_channels[0]) == 0) ? 1 : 0;

        case PMU_FUNC_XOR: {
            int count = 0;
            for (uint8_t i = 0; i < func->input_count; i++) {
                if (PMU_Channel_GetValue(func->input_channels[i]) != 0) {
                    count++;
                }
            }
            return (count % 2 == 1) ? 1 : 0;
        }

        case PMU_FUNC_NAND: {
            for (uint8_t i = 0; i < func->input_count; i++) {
                if (PMU_Channel_GetValue(func->input_channels[i]) == 0) {
                    return 1;
                }
            }
            return 0;
        }

        case PMU_FUNC_NOR: {
            for (uint8_t i = 0; i < func->input_count; i++) {
                if (PMU_Channel_GetValue(func->input_channels[i]) != 0) {
                    return 0;
                }
            }
            return 1;
        }

        default:
            return 0;
    }
}

/**
 * @brief Execute PID controller
 */
static int32_t LogicFunc_ExecutePID(PMU_LogicFunction_t* func)
{
    uint32_t now_ms = HAL_GetTick();
    int32_t process_var = PMU_Channel_GetValue(func->input_channels[0]);

    /* Calculate time delta */
    float dt;
    if (func->params.pid.last_update_ms == 0) {
        dt = 0.001f;  /* First run */
    } else {
        dt = (now_ms - func->params.pid.last_update_ms) / 1000.0f;
    }
    func->params.pid.last_update_ms = now_ms;

    /* Calculate error */
    float error = func->params.pid.setpoint - process_var;

    /* Proportional term */
    float p_term = func->params.pid.kp * error;

    /* Integral term */
    func->params.pid.integral += error * dt;
    float i_term = func->params.pid.ki * func->params.pid.integral;

    /* Derivative term */
    float d_term = 0.0f;
    if (dt > 0) {
        d_term = func->params.pid.kd * (error - func->params.pid.last_error) / dt;
    }
    func->params.pid.last_error = (int32_t)error;

    /* Calculate output */
    float output = p_term + i_term + d_term;

    /* Clamp output */
    if (output < func->params.pid.output_min) output = func->params.pid.output_min;
    if (output > func->params.pid.output_max) output = func->params.pid.output_max;

    return (int32_t)output;
}

/**
 * @brief Execute hysteresis
 */
static int32_t LogicFunc_ExecuteHysteresis(PMU_LogicFunction_t* func)
{
    int32_t input = PMU_Channel_GetValue(func->input_channels[0]);

    if (input >= func->params.hysteresis.threshold_on) {
        func->params.hysteresis.state = 1;
    } else if (input <= func->params.hysteresis.threshold_off) {
        func->params.hysteresis.state = 0;
    }

    return func->params.hysteresis.state;
}

/**
 * @brief Execute rate limiter
 */
static int32_t LogicFunc_ExecuteRateLimit(PMU_LogicFunction_t* func)
{
    uint32_t now_ms = HAL_GetTick();
    int32_t input = PMU_Channel_GetValue(func->input_channels[0]);

    if (func->params.rate_limit.last_update_ms == 0) {
        func->params.rate_limit.last_value = input;
        func->params.rate_limit.last_update_ms = now_ms;
        return input;
    }

    /* Calculate time delta */
    float dt = (now_ms - func->params.rate_limit.last_update_ms) / 1000.0f;
    func->params.rate_limit.last_update_ms = now_ms;

    /* Calculate maximum allowed change */
    int32_t max_change = (int32_t)(func->params.rate_limit.max_rate * dt);

    /* Limit rate of change */
    int32_t diff = input - func->params.rate_limit.last_value;
    if (diff > max_change) {
        func->params.rate_limit.last_value += max_change;
    } else if (diff < -max_change) {
        func->params.rate_limit.last_value -= max_change;
    } else {
        func->params.rate_limit.last_value = input;
    }

    return func->params.rate_limit.last_value;
}

/**
 * @brief Execute debounce
 */
static int32_t LogicFunc_ExecuteDebounce(PMU_LogicFunction_t* func)
{
    uint32_t now_ms = HAL_GetTick();
    int32_t input = PMU_Channel_GetValue(func->input_channels[0]);
    uint8_t input_bool = (input != 0) ? 1 : 0;

    /* Check if state changed */
    if (input_bool != func->params.debounce.state) {
        /* Start debounce timer */
        if (func->params.debounce.last_change_ms == 0) {
            func->params.debounce.last_change_ms = now_ms;
        } else {
            /* Check if debounce time elapsed */
            if (now_ms - func->params.debounce.last_change_ms >= func->params.debounce.debounce_ms) {
                func->params.debounce.state = input_bool;
                func->params.debounce.last_change_ms = 0;
            }
        }
    } else {
        /* Reset debounce timer */
        func->params.debounce.last_change_ms = 0;
    }

    return func->params.debounce.state;
}

/**
 * @brief Execute 1D lookup table with linear interpolation
 */
static int32_t LogicFunc_ExecuteTable1D(PMU_LogicFunction_t* func)
{
    int32_t input = PMU_Channel_GetValue(func->input_channels[0]);
    PMU_Table1D_t* table = &func->params.table_1d;

    if (table->size == 0 || table->x_values == NULL || table->y_values == NULL) {
        return 0;
    }

    /* Handle out of range */
    if (input <= table->x_values[0]) {
        return table->y_values[0];
    }
    if (input >= table->x_values[table->size - 1]) {
        return table->y_values[table->size - 1];
    }

    /* Find interpolation points */
    for (uint16_t i = 0; i < table->size - 1; i++) {
        if (input >= table->x_values[i] && input <= table->x_values[i + 1]) {
            /* Linear interpolation */
            int32_t x0 = table->x_values[i];
            int32_t x1 = table->x_values[i + 1];
            int32_t y0 = table->y_values[i];
            int32_t y1 = table->y_values[i + 1];

            if (x1 == x0) {
                return y0;
            }

            return y0 + (int32_t)(((int64_t)(input - x0) * (y1 - y0)) / (x1 - x0));
        }
    }

    return 0;
}

/**
 * @brief Execute moving average filter
 */
static int32_t LogicFunc_ExecuteMovingAvg(PMU_LogicFunction_t* func)
{
    int32_t input = PMU_Channel_GetValue(func->input_channels[0]);
    PMU_MovingAvg_t* avg = &func->params.moving_avg;

    if (avg->window_size == 0 || avg->buffer == NULL) {
        return input;
    }

    /* Subtract old value from sum */
    avg->sum -= avg->buffer[avg->index];

    /* Add new value */
    avg->buffer[avg->index] = input;
    avg->sum += input;

    /* Advance index */
    avg->index++;
    if (avg->index >= avg->window_size) {
        avg->index = 0;
    }

    /* Return average */
    return (int32_t)(avg->sum / avg->window_size);
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
