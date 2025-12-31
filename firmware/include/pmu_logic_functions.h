/**
 ******************************************************************************
 * @file           : pmu_logic_functions.h
 * @brief          : Logic Functions for Virtual Channels
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * This module provides advanced logic functions that work with the
 * universal channel abstraction system. Functions can read from any
 * input channel and write to any output channel.
 *
 * Features:
 * - Mathematical operations (add, subtract, multiply, divide, min, max)
 * - Comparison operations (>, <, ==, !=, >=, <=)
 * - Logic operations (AND, OR, NOT, XOR)
 * - Lookup tables (1D and 2D interpolation)
 * - Filters (moving average, min/max window)
 * - PID controllers
 * - Hysteresis/Schmitt trigger
 * - Rate limiters
 *
 ******************************************************************************
 */

#ifndef PMU_LOGIC_FUNCTIONS_H
#define PMU_LOGIC_FUNCTIONS_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "pmu_hal.h"
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Function type identifier
 */
typedef enum {
    /* Mathematical Operations (0x00-0x1F) */
    PMU_FUNC_ADD = 0x00,           /**< Add two inputs */
    PMU_FUNC_SUBTRACT,             /**< Subtract: A - B */
    PMU_FUNC_MULTIPLY,             /**< Multiply: A * B */
    PMU_FUNC_DIVIDE,               /**< Divide: A / B */
    PMU_FUNC_MIN,                  /**< Minimum of N inputs */
    PMU_FUNC_MAX,                  /**< Maximum of N inputs */
    PMU_FUNC_AVERAGE,              /**< Average of N inputs */
    PMU_FUNC_ABS,                  /**< Absolute value */
    PMU_FUNC_SCALE,                /**< Scale: (input * scale) + offset */
    PMU_FUNC_CLAMP,                /**< Clamp to min/max range */

    /* Comparison Operations (0x20-0x3F) */
    PMU_FUNC_GREATER = 0x20,       /**< A > B ? 1 : 0 */
    PMU_FUNC_LESS,                 /**< A < B ? 1 : 0 */
    PMU_FUNC_EQUAL,                /**< A == B ? 1 : 0 */
    PMU_FUNC_NOT_EQUAL,            /**< A != B ? 1 : 0 */
    PMU_FUNC_GREATER_EQUAL,        /**< A >= B ? 1 : 0 */
    PMU_FUNC_LESS_EQUAL,           /**< A <= B ? 1 : 0 */
    PMU_FUNC_IN_RANGE,             /**< min <= A <= max ? 1 : 0 */

    /* Logic Operations (0x40-0x5F) */
    PMU_FUNC_AND = 0x40,           /**< Logical AND of N inputs */
    PMU_FUNC_OR,                   /**< Logical OR of N inputs */
    PMU_FUNC_NOT,                  /**< Logical NOT */
    PMU_FUNC_XOR,                  /**< Logical XOR */
    PMU_FUNC_NAND,                 /**< Logical NAND */
    PMU_FUNC_NOR,                  /**< Logical NOR */

    /* Tables (0x60-0x7F) */
    PMU_FUNC_TABLE_1D = 0x60,      /**< 1D lookup table with linear interpolation */
    PMU_FUNC_TABLE_2D,             /**< 2D lookup table (map) */

    /* Filters (0x80-0x9F) */
    PMU_FUNC_MOVING_AVG = 0x80,    /**< Moving average filter */
    PMU_FUNC_MIN_WINDOW,           /**< Minimum over time window */
    PMU_FUNC_MAX_WINDOW,           /**< Maximum over time window */
    PMU_FUNC_MEDIAN,               /**< Median filter */
    PMU_FUNC_LOW_PASS,             /**< Low-pass filter (RC) */

    /* Control (0xA0-0xBF) */
    PMU_FUNC_PID = 0xA0,           /**< PID controller */
    PMU_FUNC_HYSTERESIS,           /**< Hysteresis/Schmitt trigger */
    PMU_FUNC_RATE_LIMIT,           /**< Rate limiter */
    PMU_FUNC_DEBOUNCE,             /**< Digital debounce */

    /* Special (0xC0-0xFF) */
    PMU_FUNC_MUX = 0xC0,           /**< Multiplexer (select input based on selector) */
    PMU_FUNC_DEMUX,                /**< Demultiplexer */
    PMU_FUNC_CONDITIONAL,          /**< Conditional: condition ? true_val : false_val */
    PMU_FUNC_CUSTOM_LUA,           /**< Custom Lua function */
} PMU_FunctionType_t;

/**
 * @brief PID controller configuration
 */
typedef struct {
    float kp;                      /**< Proportional gain */
    float ki;                      /**< Integral gain */
    float kd;                      /**< Derivative gain */
    float setpoint;                /**< Target value */
    int32_t output_min;            /**< Minimum output */
    int32_t output_max;            /**< Maximum output */
    float integral;                /**< Integral accumulator (internal) */
    int32_t last_error;            /**< Last error (internal) */
    uint32_t last_update_ms;       /**< Last update time (internal) */
} PMU_PID_Config_t;

/**
 * @brief 1D lookup table
 */
typedef struct {
    uint16_t size;                 /**< Number of points */
    int32_t* x_values;             /**< X axis values */
    int32_t* y_values;             /**< Y axis values */
} PMU_Table1D_t;

/**
 * @brief 2D lookup table
 */
typedef struct {
    uint16_t x_size;               /**< X axis size */
    uint16_t y_size;               /**< Y axis size */
    int32_t* x_values;             /**< X axis values */
    int32_t* y_values;             /**< Y axis values */
    int32_t* z_values;             /**< Z values (x_size * y_size) */
} PMU_Table2D_t;

/**
 * @brief Moving average filter
 */
typedef struct {
    uint16_t window_size;          /**< Window size */
    uint16_t index;                /**< Current index (internal) */
    int32_t* buffer;               /**< Sample buffer */
    int64_t sum;                   /**< Running sum (internal) */
} PMU_MovingAvg_t;

/**
 * @brief Logic function configuration
 */
typedef struct {
    uint16_t function_id;          /**< Unique function ID */
    PMU_FunctionType_t type;       /**< Function type */
    uint16_t output_channel;       /**< Output channel ID */
    uint16_t input_channels[8];    /**< Input channel IDs (up to 8) */
    uint8_t input_count;           /**< Number of inputs */
    uint8_t enabled;               /**< Enable flag */

    /* Type-specific parameters */
    union {
        struct {
            int32_t scale;         /**< Scale factor (x1000 for fixed-point) */
            int32_t offset;        /**< Offset value */
        } scale;

        struct {
            int32_t min;           /**< Minimum value */
            int32_t max;           /**< Maximum value */
        } clamp;

        PMU_PID_Config_t pid;      /**< PID configuration */
        PMU_Table1D_t table_1d;    /**< 1D table */
        PMU_Table2D_t table_2d;    /**< 2D table */
        PMU_MovingAvg_t moving_avg; /**< Moving average */

        struct {
            int32_t threshold_on;  /**< Hysteresis ON threshold */
            int32_t threshold_off; /**< Hysteresis OFF threshold */
            uint8_t state;         /**< Current state (internal) */
        } hysteresis;

        struct {
            int32_t max_rate;      /**< Maximum rate of change per second */
            int32_t last_value;    /**< Last output value (internal) */
            uint32_t last_update_ms; /**< Last update time (internal) */
        } rate_limit;

        struct {
            uint32_t debounce_ms;  /**< Debounce time in ms */
            uint8_t state;         /**< Current stable state (internal) */
            uint32_t last_change_ms; /**< Last state change time (internal) */
        } debounce;

        uint8_t custom_params[64]; /**< Custom parameters for Lua/user functions */
    } params;
} PMU_LogicFunction_t;

/* Exported constants --------------------------------------------------------*/

#define PMU_MAX_LOGIC_FUNCTIONS     64  /**< Maximum logic functions */

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize logic functions module
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_LogicFunctions_Init(void);

/**
 * @brief Register a new logic function
 * @param func Function configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_LogicFunctions_Register(PMU_LogicFunction_t* func);

/**
 * @brief Unregister a logic function
 * @param function_id Function ID
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_LogicFunctions_Unregister(uint16_t function_id);

/**
 * @brief Update all logic functions (call periodically)
 * @retval None
 */
void PMU_LogicFunctions_Update(void);

/**
 * @brief Get function by ID
 * @param function_id Function ID
 * @retval Pointer to function or NULL
 */
PMU_LogicFunction_t* PMU_LogicFunctions_GetByID(uint16_t function_id);

/**
 * @brief Enable/disable function
 * @param function_id Function ID
 * @param enabled Enable flag
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_LogicFunctions_SetEnabled(uint16_t function_id, bool enabled);

/**
 * @brief Create simple math function (add, subtract, multiply, divide)
 * @param type Function type
 * @param output_ch Output channel
 * @param input_a Input A channel
 * @param input_b Input B channel
 * @retval Function ID or 0 on error
 */
uint16_t PMU_LogicFunctions_CreateMath(PMU_FunctionType_t type,
                                        uint16_t output_ch,
                                        uint16_t input_a,
                                        uint16_t input_b);

/**
 * @brief Create comparison function
 * @param type Comparison type
 * @param output_ch Output channel
 * @param input_a Input A channel
 * @param input_b Input B channel
 * @retval Function ID or 0 on error
 */
uint16_t PMU_LogicFunctions_CreateComparison(PMU_FunctionType_t type,
                                              uint16_t output_ch,
                                              uint16_t input_a,
                                              uint16_t input_b);

/**
 * @brief Create PID controller
 * @param output_ch Output channel
 * @param input_ch Input (process variable) channel
 * @param setpoint Target setpoint
 * @param kp Proportional gain
 * @param ki Integral gain
 * @param kd Derivative gain
 * @retval Function ID or 0 on error
 */
uint16_t PMU_LogicFunctions_CreatePID(uint16_t output_ch,
                                       uint16_t input_ch,
                                       float setpoint,
                                       float kp,
                                       float ki,
                                       float kd);

/**
 * @brief Create hysteresis function
 * @param output_ch Output channel
 * @param input_ch Input channel
 * @param threshold_on ON threshold
 * @param threshold_off OFF threshold
 * @retval Function ID or 0 on error
 */
uint16_t PMU_LogicFunctions_CreateHysteresis(uint16_t output_ch,
                                              uint16_t input_ch,
                                              int32_t threshold_on,
                                              int32_t threshold_off);

#ifdef __cplusplus
}
#endif

#endif /* PMU_LOGIC_FUNCTIONS_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
