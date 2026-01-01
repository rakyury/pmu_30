/**
 * @file timer.h
 * @brief Logic Engine - Timer Functions (Stateful but Pure)
 *
 * Timer state is passed as parameter - function has no internal state.
 * This allows the same timer logic to work in firmware, tests, or simulation.
 *
 * @version 1.0
 * @date January 2026
 */

#ifndef ENGINE_TIMER_H
#define ENGINE_TIMER_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Timer Mode Types
 *============================================================================*/

typedef enum {
    TIMER_MODE_DELAY_ON    = 0x00,  /**< Delay before output goes ON */
    TIMER_MODE_DELAY_OFF   = 0x01,  /**< Delay before output goes OFF */
    TIMER_MODE_PULSE       = 0x02,  /**< Output ON for duration, then OFF */
    TIMER_MODE_BLINK       = 0x03,  /**< Toggle at interval */
    TIMER_MODE_ONESHOT     = 0x04,  /**< Single pulse, requires reset */
    TIMER_MODE_RETRIGGERABLE = 0x05, /**< Restarts on each trigger */
    TIMER_MODE_MONOSTABLE  = 0x06,  /**< Like oneshot but auto-resets */
} TimerMode_t;

/*============================================================================
 * Timer State (passed by pointer, modified by function)
 *============================================================================*/

typedef enum {
    TIMER_STATE_IDLE      = 0,  /**< Waiting for trigger */
    TIMER_STATE_RUNNING   = 1,  /**< Timer is counting */
    TIMER_STATE_EXPIRED   = 2,  /**< Timer has finished */
    TIMER_STATE_PAUSED    = 3,  /**< Timer is paused */
} TimerStateEnum_t;

typedef struct {
    uint8_t  state;             /**< Current state (TimerStateEnum_t) */
    uint8_t  output;            /**< Current output value (0 or 1) */
    uint8_t  last_trigger;      /**< Last trigger input state (for edge detect) */
    uint8_t  blink_phase;       /**< Blink phase (0 or 1) */
    uint32_t start_time_ms;     /**< Time when timer started */
    uint32_t elapsed_ms;        /**< Elapsed time since start */
    uint32_t pause_time_ms;     /**< Time when paused (for resume) */
} Timer_State_t;

/*============================================================================
 * Timer Configuration
 *============================================================================*/

typedef struct {
    uint8_t  mode;              /**< Timer mode (TimerMode_t) */
    uint8_t  start_edge;        /**< 0=level, 1=rising, 2=falling, 3=both */
    uint8_t  auto_reset;        /**< Auto-reset after expire */
    uint8_t  reserved;
    uint32_t duration_ms;       /**< Timer duration in milliseconds */
    uint32_t blink_on_ms;       /**< Blink ON time (for BLINK mode) */
    uint32_t blink_off_ms;      /**< Blink OFF time (for BLINK mode) */
} Timer_Config_t;

/*============================================================================
 * Timer Functions
 *============================================================================*/

/**
 * Initialize timer state.
 *
 * @param state Timer state to initialize
 */
void Timer_Init(Timer_State_t* state);

/**
 * Reset timer to idle state.
 *
 * @param state Timer state
 */
void Timer_Reset(Timer_State_t* state);

/**
 * Update timer and get output value.
 *
 * This is the main timer function. Call it every loop iteration.
 *
 * @param state Timer state (modified)
 * @param config Timer configuration (read-only)
 * @param trigger Trigger input value
 * @param now_ms Current time in milliseconds
 * @return Output value (0 or 1)
 */
int32_t Timer_Update(Timer_State_t* state, const Timer_Config_t* config,
                     int32_t trigger, uint32_t now_ms);

/**
 * Pause timer (freezes elapsed time).
 */
void Timer_Pause(Timer_State_t* state, uint32_t now_ms);

/**
 * Resume paused timer.
 */
void Timer_Resume(Timer_State_t* state, uint32_t now_ms);

/**
 * Get remaining time in milliseconds.
 *
 * @param state Timer state
 * @param config Timer configuration
 * @return Remaining time, or 0 if expired/idle
 */
uint32_t Timer_GetRemaining(const Timer_State_t* state, const Timer_Config_t* config);

/**
 * Get elapsed time in milliseconds.
 */
uint32_t Timer_GetElapsed(const Timer_State_t* state);

/**
 * Check if timer is running.
 */
bool Timer_IsRunning(const Timer_State_t* state);

/**
 * Check if timer has expired.
 */
bool Timer_IsExpired(const Timer_State_t* state);

#ifdef __cplusplus
}
#endif

#endif /* ENGINE_TIMER_H */
