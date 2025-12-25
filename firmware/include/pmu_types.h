/**
 ******************************************************************************
 * @file           : pmu_types.h
 * @brief          : Common type definitions for PMU-30
 * @author         : R2 m-sport
 * @date           : 2025-12-23
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This header contains all common enums and types used across multiple
 * PMU-30 modules to avoid duplicate definitions.
 *
 ******************************************************************************
 */

#ifndef __PMU_TYPES_H
#define __PMU_TYPES_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

/* ============================================================================
 * Channel ID length constant
 * ============================================================================ */
#define PMU_CHANNEL_ID_LEN 32

/* ============================================================================
 * Channel Types (v2.0 unified architecture)
 * ============================================================================ */

/**
 * @brief Channel type enumeration
 */
typedef enum {
    PMU_CHANNEL_TYPE_DIGITAL_INPUT = 0,
    PMU_CHANNEL_TYPE_ANALOG_INPUT,
    PMU_CHANNEL_TYPE_POWER_OUTPUT,
    PMU_CHANNEL_TYPE_CAN_RX,
    PMU_CHANNEL_TYPE_CAN_TX,
    PMU_CHANNEL_TYPE_LIN_RX,
    PMU_CHANNEL_TYPE_LIN_TX,
    PMU_CHANNEL_TYPE_LOGIC,
    PMU_CHANNEL_TYPE_NUMBER,
    PMU_CHANNEL_TYPE_TABLE_2D,
    PMU_CHANNEL_TYPE_TABLE_3D,
    PMU_CHANNEL_TYPE_SWITCH,
    PMU_CHANNEL_TYPE_TIMER,
    PMU_CHANNEL_TYPE_FILTER,
    PMU_CHANNEL_TYPE_ENUM,
    PMU_CHANNEL_TYPE_LUA_SCRIPT,
    PMU_CHANNEL_TYPE_PID,
    PMU_CHANNEL_TYPE_BLINKMARINE_KEYPAD,
    PMU_CHANNEL_TYPE_HANDLER,
    PMU_CHANNEL_TYPE_COUNT
} PMU_ChannelType_t;

/* ============================================================================
 * CAN Message Types (Level 1)
 * ============================================================================ */

/**
 * @brief CAN Message type
 */
typedef enum {
    PMU_CAN_MSG_TYPE_NORMAL = 0,    /**< Normal single-frame message */
    PMU_CAN_MSG_TYPE_COMPOUND,      /**< Compound/multiplexed message */
    PMU_CAN_MSG_TYPE_PMU1_RX,       /**< PMU1 RX format */
    PMU_CAN_MSG_TYPE_PMU2_RX,       /**< PMU2 RX format */
    PMU_CAN_MSG_TYPE_PMU3_RX        /**< PMU3 RX format */
} PMU_CAN_MessageType_t;

/* Alias for compatibility */
typedef PMU_CAN_MessageType_t PMU_CanMessageType_t;

/* ============================================================================
 * CAN Data Types (Level 2)
 * ============================================================================ */

/**
 * @brief CAN Input timeout behavior
 */
typedef enum {
    PMU_CAN_TIMEOUT_USE_DEFAULT = 0,    /**< Use configured default value */
    PMU_CAN_TIMEOUT_HOLD_LAST,          /**< Hold last received value */
    PMU_CAN_TIMEOUT_SET_ZERO            /**< Set value to zero */
} PMU_CAN_TimeoutBehavior_t;

typedef PMU_CAN_TimeoutBehavior_t PMU_CanTimeoutBehavior_t;

/**
 * @brief CAN Input data type
 */
typedef enum {
    PMU_CAN_DATA_TYPE_UNSIGNED = 0,     /**< Unsigned integer */
    PMU_CAN_DATA_TYPE_SIGNED,           /**< Signed integer */
    PMU_CAN_DATA_TYPE_FLOAT             /**< IEEE 754 float */
} PMU_CAN_DataType_t;

typedef PMU_CAN_DataType_t PMU_CanDataType_t;

/**
 * @brief CAN Input data format
 */
typedef enum {
    PMU_CAN_DATA_FORMAT_8BIT = 0,       /**< 8-bit value */
    PMU_CAN_DATA_FORMAT_16BIT,          /**< 16-bit value */
    PMU_CAN_DATA_FORMAT_32BIT,          /**< 32-bit value */
    PMU_CAN_DATA_FORMAT_CUSTOM          /**< Custom bit field */
} PMU_CAN_DataFormat_t;

typedef PMU_CAN_DataFormat_t PMU_CanDataFormat_t;

/**
 * @brief CAN frame type
 */
typedef enum {
    PMU_CAN_FRAME_CLASSIC = 0,  /**< CAN 2.0 frame */
    PMU_CAN_FRAME_FD            /**< CAN FD frame */
} PMU_CAN_FrameType_t;

/**
 * @brief CAN ID type
 */
typedef enum {
    PMU_CAN_ID_STANDARD = 0,    /**< 11-bit standard ID */
    PMU_CAN_ID_EXTENDED         /**< 29-bit extended ID */
} PMU_CAN_IdType_t;

/**
 * @brief CAN bus identifier
 */
typedef enum {
    PMU_CAN_BUS_1 = 0,      /**< CAN FD 1 */
    PMU_CAN_BUS_2,          /**< CAN FD 2 */
    PMU_CAN_BUS_3,          /**< CAN 2.0 A/B */
    PMU_CAN_BUS_4,          /**< CAN 2.0 A/B */
    PMU_CAN_BUS_COUNT
} PMU_CAN_Bus_t;

/* ============================================================================
 * Input Types
 * ============================================================================ */

/**
 * @brief Input channel type
 */
typedef enum {
    PMU_INPUT_TYPE_ANALOG = 0,      /**< Analog voltage input */
    PMU_INPUT_TYPE_DIGITAL,         /**< Digital on/off input */
    PMU_INPUT_TYPE_FREQUENCY,       /**< Frequency input */
    PMU_INPUT_TYPE_ROTARY,          /**< Rotary switch */
    PMU_INPUT_TYPE_RESISTIVE,       /**< Resistive sensor */
    PMU_INPUT_TYPE_THERMISTOR,      /**< Temperature sensor */
    PMU_INPUT_TYPE_COUNT
} PMU_InputType_t;

/* ============================================================================
 * Output Types
 * ============================================================================ */

/**
 * @brief Output channel type
 */
typedef enum {
    PMU_OUTPUT_TYPE_PROFET = 0,     /**< PROFET high-side switch */
    PMU_OUTPUT_TYPE_HBRIDGE,        /**< H-Bridge motor driver */
    PMU_OUTPUT_TYPE_GENERIC,        /**< General purpose output */
    PMU_OUTPUT_TYPE_COUNT
} PMU_OutputType_t;

/**
 * @brief Output state
 */
typedef enum {
    PMU_OUTPUT_STATE_OFF = 0,
    PMU_OUTPUT_STATE_ON,
    PMU_OUTPUT_STATE_PWM,
    PMU_OUTPUT_STATE_FAULT
} PMU_OutputState_t;

/* ============================================================================
 * Button Function Modes (ECUMaster compatible)
 * ============================================================================ */

/**
 * @brief Button function mode
 */
typedef enum {
    PMU_BUTTON_MODE_DIRECT = 0,         /**< Direct input passthrough */
    PMU_BUTTON_MODE_MOMENTARY,          /**< Output only while pressed */
    PMU_BUTTON_MODE_TOGGLE,             /**< Toggle output on press */
    PMU_BUTTON_MODE_LATCHING,           /**< Stay on until reset channel */
    PMU_BUTTON_MODE_LONG_PRESS,         /**< Separate short/long actions */
    PMU_BUTTON_MODE_DOUBLE_CLICK,       /**< Detect double clicks */
    PMU_BUTTON_MODE_PRESS_AND_HOLD,     /**< Progressive action with timer */
    PMU_BUTTON_MODE_COUNT
} PMU_ButtonMode_t;

/* ============================================================================
 * Marker to indicate types are defined
 * ============================================================================ */
#define PMU_TYPES_DEFINED 1

#ifdef __cplusplus
}
#endif

#endif /* __PMU_TYPES_H */
