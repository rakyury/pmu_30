/**
 ******************************************************************************
 * @file           : pmu_led.h
 * @brief          : Status LED Indication Module
 * @author         : R2 m-sport
 * @date           : 2026-01-01
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2026 R2 m-sport.
 * All rights reserved.
 *
 * Status LED provides visual feedback for system state:
 * - Green: System OK
 * - Red: System fault
 * - Blue: Communication active (WiFi/BT)
 *
 * Patterns:
 * - 1 blink: System initialized successfully
 * - 2 blinks: Configuration loaded
 * - Fast blink: Error state
 * - Off: Normal operation
 *
 ******************************************************************************
 */

#ifndef __PMU_LED_H
#define __PMU_LED_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief LED color enumeration
 */
typedef enum {
    PMU_LED_COLOR_OFF = 0,
    PMU_LED_COLOR_GREEN,
    PMU_LED_COLOR_RED,
    PMU_LED_COLOR_BLUE,
    PMU_LED_COLOR_YELLOW,    /* Red + Green */
    PMU_LED_COLOR_CYAN,      /* Green + Blue */
    PMU_LED_COLOR_MAGENTA,   /* Red + Blue */
    PMU_LED_COLOR_WHITE      /* All on */
} PMU_LED_Color_t;

/**
 * @brief LED pattern enumeration
 */
typedef enum {
    PMU_LED_PATTERN_OFF = 0,        /* LED off */
    PMU_LED_PATTERN_SOLID,          /* Constant on */
    PMU_LED_PATTERN_BLINK_1,        /* 1 blink then off */
    PMU_LED_PATTERN_BLINK_2,        /* 2 blinks then off */
    PMU_LED_PATTERN_BLINK_3,        /* 3 blinks then off */
    PMU_LED_PATTERN_FAST_BLINK,     /* Continuous fast blinking (error) */
    PMU_LED_PATTERN_SLOW_BLINK,     /* Continuous slow blinking */
    PMU_LED_PATTERN_HEARTBEAT       /* Double pulse heartbeat */
} PMU_LED_Pattern_t;

/**
 * @brief System state for LED indication
 */
typedef enum {
    PMU_LED_STATE_STARTUP,          /* System starting */
    PMU_LED_STATE_STARTUP_OK,       /* Startup successful (1 blink green) */
    PMU_LED_STATE_STARTUP_ERROR,    /* Startup failed (fast red) */
    PMU_LED_STATE_CONFIG_LOADED,    /* Config loaded (2 blinks green) */
    PMU_LED_STATE_CONFIG_ERROR,     /* Config error (fast red) */
    PMU_LED_STATE_NORMAL,           /* Normal operation (off) */
    PMU_LED_STATE_WARNING,          /* Warning state (slow yellow blink) */
    PMU_LED_STATE_FAULT,            /* Fault state (fast red) */
    PMU_LED_STATE_COMM_ACTIVE       /* Communication active (blue pulse) */
} PMU_LED_State_t;

/**
 * @brief LED runtime state (internal)
 */
typedef struct {
    PMU_LED_State_t current_state;
    PMU_LED_Color_t current_color;
    PMU_LED_Pattern_t current_pattern;
    uint32_t pattern_start_ms;
    uint8_t pattern_step;
    bool pattern_active;
    bool comm_indicator_active;
    uint32_t comm_indicator_timeout;
} PMU_LED_Runtime_t;

/* Exported constants --------------------------------------------------------*/

/* Timing constants (ms) */
#define PMU_LED_BLINK_ON_MS         500     /* Single blink ON duration */
#define PMU_LED_BLINK_OFF_MS        400     /* Pause between blinks */
#define PMU_LED_FAST_ON_MS          100     /* Fast blink ON duration */
#define PMU_LED_FAST_OFF_MS         100     /* Fast blink OFF duration */
#define PMU_LED_SLOW_ON_MS          500     /* Slow blink ON duration */
#define PMU_LED_SLOW_OFF_MS         500     /* Slow blink OFF duration */
#define PMU_LED_HEARTBEAT_PULSE_MS  100     /* Heartbeat pulse duration */
#define PMU_LED_HEARTBEAT_GAP_MS    100     /* Gap between heartbeat pulses */
#define PMU_LED_HEARTBEAT_PAUSE_MS  600     /* Pause after heartbeat */
#define PMU_LED_COMM_TIMEOUT_MS     100     /* Communication indicator timeout */

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize LED module
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_LED_Init(void);

/**
 * @brief Update LED state machine (call at 20-50Hz from UI task)
 * @retval None
 * @note Non-blocking function, uses elapsed time for pattern timing
 */
void PMU_LED_Update(void);

/**
 * @brief Set LED system state
 * @param state System state for indication
 * @retval None
 */
void PMU_LED_SetState(PMU_LED_State_t state);

/**
 * @brief Get current LED state
 * @retval Current state
 */
PMU_LED_State_t PMU_LED_GetState(void);

/**
 * @brief Set LED color directly (overrides pattern)
 * @param color LED color
 * @retval None
 */
void PMU_LED_SetColor(PMU_LED_Color_t color);

/**
 * @brief Set LED pattern
 * @param pattern LED pattern
 * @param color Pattern color
 * @retval None
 */
void PMU_LED_SetPattern(PMU_LED_Pattern_t pattern, PMU_LED_Color_t color);

/**
 * @brief Trigger communication activity indicator
 * @retval None
 * @note Brief blue flash to indicate CAN/WiFi/BT activity
 */
void PMU_LED_TriggerCommActivity(void);

/**
 * @brief Signal startup success (1 green blink)
 * @retval None
 */
void PMU_LED_SignalStartupOK(void);

/**
 * @brief Signal startup error (fast red blink)
 * @retval None
 */
void PMU_LED_SignalStartupError(void);

/**
 * @brief Signal config loaded (2 green blinks)
 * @retval None
 */
void PMU_LED_SignalConfigLoaded(void);

/**
 * @brief Signal config error (fast red blink)
 * @retval None
 */
void PMU_LED_SignalConfigError(void);

/**
 * @brief Turn off LED (normal operation)
 * @retval None
 */
void PMU_LED_Off(void);

/**
 * @brief Check if LED is currently in error state
 * @retval true if showing error pattern
 */
bool PMU_LED_IsError(void);

/**
 * @brief Get LED runtime state for debugging
 * @retval Pointer to runtime state
 */
const PMU_LED_Runtime_t* PMU_LED_GetRuntime(void);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_LED_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
