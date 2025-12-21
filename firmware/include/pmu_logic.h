/**
 ******************************************************************************
 * @file           : pmu_logic.h
 * @brief          : Logic Engine Header
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * Logic Engine Features:
 * - 100 virtual functions @ 500Hz execution
 * - 250 operations per cycle maximum
 * - Virtual channels (inputs from CAN, ADC, outputs, etc.)
 * - Logical operations: AND, OR, NOT, XOR
 * - Comparison: >, <, ==, !=, >=, <=
 * - Math: +, -, *, /, %, min, max, abs, clamp
 * - Timers, counters, edge detection
 * - Hysteresis, filters
 *
 ******************************************************************************
 */

#ifndef __PMU_LOGIC_H
#define __PMU_LOGIC_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "pmu_config.h"

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Logic operation types
 */
typedef enum {
    /* Logical operations */
    LOGIC_OP_AND = 0,
    LOGIC_OP_OR,
    LOGIC_OP_NOT,
    LOGIC_OP_XOR,

    /* Comparison operations */
    LOGIC_OP_GREATER,
    LOGIC_OP_LESS,
    LOGIC_OP_EQUAL,
    LOGIC_OP_NOT_EQUAL,
    LOGIC_OP_GREATER_EQUAL,
    LOGIC_OP_LESS_EQUAL,

    /* Math operations */
    LOGIC_OP_ADD,
    LOGIC_OP_SUBTRACT,
    LOGIC_OP_MULTIPLY,
    LOGIC_OP_DIVIDE,
    LOGIC_OP_MODULO,
    LOGIC_OP_MIN,
    LOGIC_OP_MAX,
    LOGIC_OP_ABS,
    LOGIC_OP_CLAMP,

    /* Special operations */
    LOGIC_OP_TIMER,
    LOGIC_OP_COUNTER,
    LOGIC_OP_EDGE_RISING,
    LOGIC_OP_EDGE_FALLING,
    LOGIC_OP_HYSTERESIS,
    LOGIC_OP_FILTER,
    LOGIC_OP_TOGGLE,

    /* Assignment */
    LOGIC_OP_SET,
    LOGIC_OP_RESET,

    LOGIC_OP_COUNT
} PMU_Logic_Op_t;

/**
 * @brief Virtual channel types
 */
typedef enum {
    VCHAN_TYPE_CONSTANT = 0,
    VCHAN_TYPE_ADC_INPUT,
    VCHAN_TYPE_PROFET_OUTPUT,
    VCHAN_TYPE_PROFET_CURRENT,
    VCHAN_TYPE_HBRIDGE_OUTPUT,
    VCHAN_TYPE_HBRIDGE_CURRENT,
    VCHAN_TYPE_CAN_SIGNAL,
    VCHAN_TYPE_SYSTEM_VOLTAGE,
    VCHAN_TYPE_SYSTEM_TEMP,
    VCHAN_TYPE_VIRTUAL,
    VCHAN_TYPE_COUNT
} PMU_VChan_Type_t;

/**
 * @brief Virtual channel structure
 */
typedef struct {
    PMU_VChan_Type_t type;
    uint16_t index;             /* Index into source array */
    float value;                /* Current value */
    uint8_t updated;            /* Update flag */
} PMU_VChannel_t;

/**
 * @brief Logic operation structure
 */
typedef struct {
    PMU_Logic_Op_t operation;
    uint16_t input_a;           /* Virtual channel index */
    uint16_t input_b;           /* Virtual channel index */
    uint16_t input_c;           /* Virtual channel index (for clamp, etc.) */
    uint16_t output;            /* Virtual channel index for result */
    float constant_a;           /* Constant value for input_a */
    float constant_b;           /* Constant value for input_b */
    float constant_c;           /* Constant value for input_c */
    uint8_t use_constant_a;     /* Use constant instead of vchannel */
    uint8_t use_constant_b;
    uint8_t use_constant_c;
} PMU_Logic_Operation_t;

/**
 * @brief Logic function structure
 */
typedef struct {
    uint8_t enabled;
    uint8_t operation_count;
    PMU_Logic_Operation_t operations[10];  /* Max 10 operations per function */
    char name[32];
} PMU_Logic_Function_t;

/**
 * @brief Timer structure
 */
typedef struct {
    uint32_t start_time;
    uint32_t duration_ms;
    uint8_t active;
    uint8_t expired;
} PMU_Logic_Timer_t;

/**
 * @brief Counter structure
 */
typedef struct {
    uint32_t count;
    uint32_t limit;
    uint8_t reset_on_limit;
} PMU_Logic_Counter_t;

/**
 * @brief Hysteresis structure
 */
typedef struct {
    float threshold_high;
    float threshold_low;
    uint8_t state;
} PMU_Logic_Hysteresis_t;

/* Exported constants --------------------------------------------------------*/

#define PMU_LOGIC_MAX_FUNCTIONS     100
#define PMU_LOGIC_MAX_OPERATIONS    250
#define PMU_LOGIC_MAX_VCHANNELS     256
#define PMU_LOGIC_MAX_TIMERS        32
#define PMU_LOGIC_MAX_COUNTERS      32
#define PMU_LOGIC_MAX_HYSTERESIS    32

/* Exported macro ------------------------------------------------------------*/

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize logic engine
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logic_Init(void);

/**
 * @brief Execute all logic functions @ 500Hz
 * @retval None
 */
void PMU_Logic_Execute(void);

/**
 * @brief Update virtual channels from hardware
 * @retval None
 */
void PMU_Logic_UpdateVChannels(void);

/**
 * @brief Apply virtual channel outputs to hardware
 * @retval None
 */
void PMU_Logic_ApplyOutputs(void);

/**
 * @brief Get virtual channel value
 * @param vchan Virtual channel index
 * @retval Channel value
 */
float PMU_Logic_GetVChannel(uint16_t vchan);

/**
 * @brief Set virtual channel value
 * @param vchan Virtual channel index
 * @param value Value to set
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logic_SetVChannel(uint16_t vchan, float value);

/**
 * @brief Add logic function
 * @param func_index Function index (0-99)
 * @param function Pointer to function structure
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logic_AddFunction(uint8_t func_index, PMU_Logic_Function_t* function);

/**
 * @brief Enable/disable logic function
 * @param func_index Function index (0-99)
 * @param enable Enable flag
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logic_EnableFunction(uint8_t func_index, uint8_t enable);

/**
 * @brief Start timer
 * @param timer_index Timer index (0-31)
 * @param duration_ms Duration in milliseconds
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logic_StartTimer(uint8_t timer_index, uint32_t duration_ms);

/**
 * @brief Check if timer expired
 * @param timer_index Timer index (0-31)
 * @retval 1 if expired, 0 otherwise
 */
uint8_t PMU_Logic_TimerExpired(uint8_t timer_index);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_LOGIC_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
