/**
 ******************************************************************************
 * @file           : pmu_led.c
 * @brief          : Status LED Indication Module Implementation
 * @author         : R2 m-sport
 * @date           : 2026-01-01
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2026 R2 m-sport.
 * All rights reserved.
 *
 * Non-blocking LED state machine for system status indication.
 * Uses elapsed time to manage patterns without blocking.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_led.h"
#include "board_config.h"

/* Private typedef -----------------------------------------------------------*/

/**
 * @brief Pattern step definition
 */
typedef struct {
    uint8_t on;             /* 1 = LED on, 0 = LED off */
    uint16_t duration_ms;   /* Duration of this step */
} PatternStep_t;

/* Private define ------------------------------------------------------------*/

/* Maximum pattern steps */
#define MAX_PATTERN_STEPS   8

/* LED GPIO definitions - use board config or defaults */
#ifndef STATUS_LED_R_PIN
#define STATUS_LED_R_PIN    GPIO_PIN_6
#define STATUS_LED_R_PORT   GPIOC
#endif

#ifndef STATUS_LED_G_PIN
#define STATUS_LED_G_PIN    GPIO_PIN_7
#define STATUS_LED_G_PORT   GPIOC
#endif

#ifndef STATUS_LED_B_PIN
#define STATUS_LED_B_PIN    GPIO_PIN_8
#define STATUS_LED_B_PORT   GPIOC
#endif

/* Common cathode LED: HIGH = on, LOW = off */
/* Common anode LED: LOW = on, HIGH = off (define LED_COMMON_ANODE) */
#ifdef LED_COMMON_ANODE
#define LED_ON_STATE    GPIO_PIN_RESET
#define LED_OFF_STATE   GPIO_PIN_SET
#else
#define LED_ON_STATE    GPIO_PIN_SET
#define LED_OFF_STATE   GPIO_PIN_RESET
#endif

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/

static PMU_LED_Runtime_t led_runtime = {0};

/* Pattern definitions (ON/OFF sequences with durations) */

/* 1 blink pattern: ON-OFF */
static const PatternStep_t pattern_blink_1[] = {
    {1, PMU_LED_BLINK_ON_MS},
    {0, PMU_LED_BLINK_OFF_MS},
    {0, 0}  /* End marker */
};

/* 2 blinks pattern: ON-OFF-ON-OFF */
static const PatternStep_t pattern_blink_2[] = {
    {1, PMU_LED_BLINK_ON_MS},
    {0, PMU_LED_BLINK_OFF_MS},
    {1, PMU_LED_BLINK_ON_MS},
    {0, PMU_LED_BLINK_OFF_MS},
    {0, 0}  /* End marker */
};

/* 3 blinks pattern */
static const PatternStep_t pattern_blink_3[] = {
    {1, PMU_LED_BLINK_ON_MS},
    {0, PMU_LED_BLINK_OFF_MS},
    {1, PMU_LED_BLINK_ON_MS},
    {0, PMU_LED_BLINK_OFF_MS},
    {1, PMU_LED_BLINK_ON_MS},
    {0, PMU_LED_BLINK_OFF_MS},
    {0, 0}  /* End marker */
};

/* Fast blink pattern (loops) */
static const PatternStep_t pattern_fast_blink[] = {
    {1, PMU_LED_FAST_ON_MS},
    {0, PMU_LED_FAST_OFF_MS},
    {0xFF, 0}  /* Loop marker */
};

/* Slow blink pattern (loops) */
static const PatternStep_t pattern_slow_blink[] = {
    {1, PMU_LED_SLOW_ON_MS},
    {0, PMU_LED_SLOW_OFF_MS},
    {0xFF, 0}  /* Loop marker */
};

/* Heartbeat pattern (loops) */
static const PatternStep_t pattern_heartbeat[] = {
    {1, PMU_LED_HEARTBEAT_PULSE_MS},
    {0, PMU_LED_HEARTBEAT_GAP_MS},
    {1, PMU_LED_HEARTBEAT_PULSE_MS},
    {0, PMU_LED_HEARTBEAT_PAUSE_MS},
    {0xFF, 0}  /* Loop marker */
};

/* Pattern lookup table */
static const PatternStep_t* const patterns[] = {
    NULL,                   /* PMU_LED_PATTERN_OFF */
    NULL,                   /* PMU_LED_PATTERN_SOLID */
    pattern_blink_1,        /* PMU_LED_PATTERN_BLINK_1 */
    pattern_blink_2,        /* PMU_LED_PATTERN_BLINK_2 */
    pattern_blink_3,        /* PMU_LED_PATTERN_BLINK_3 */
    pattern_fast_blink,     /* PMU_LED_PATTERN_FAST_BLINK */
    pattern_slow_blink,     /* PMU_LED_PATTERN_SLOW_BLINK */
    pattern_heartbeat       /* PMU_LED_PATTERN_HEARTBEAT */
};

/* Private function prototypes -----------------------------------------------*/
static void LED_SetHardware(PMU_LED_Color_t color);
static void LED_GPIO_Init(void);
static uint32_t LED_GetTick(void);

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Get current tick count (ms)
 * @note HAL_GetTick() is available both on real hardware and in emulator
 */
static uint32_t LED_GetTick(void)
{
    return HAL_GetTick();
}

/**
 * @brief Initialize LED GPIO pins
 */
static void LED_GPIO_Init(void)
{
#ifndef PMU_EMULATOR
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* Enable GPIO clocks */
    __HAL_RCC_GPIOC_CLK_ENABLE();

    /* Configure GPIO pins for RGB LED */
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;

    /* Red LED */
    GPIO_InitStruct.Pin = STATUS_LED_R_PIN;
    HAL_GPIO_Init(STATUS_LED_R_PORT, &GPIO_InitStruct);
    HAL_GPIO_WritePin(STATUS_LED_R_PORT, STATUS_LED_R_PIN, LED_OFF_STATE);

    /* Green LED */
    GPIO_InitStruct.Pin = STATUS_LED_G_PIN;
    HAL_GPIO_Init(STATUS_LED_G_PORT, &GPIO_InitStruct);
    HAL_GPIO_WritePin(STATUS_LED_G_PORT, STATUS_LED_G_PIN, LED_OFF_STATE);

    /* Blue LED */
    GPIO_InitStruct.Pin = STATUS_LED_B_PIN;
    HAL_GPIO_Init(STATUS_LED_B_PORT, &GPIO_InitStruct);
    HAL_GPIO_WritePin(STATUS_LED_B_PORT, STATUS_LED_B_PIN, LED_OFF_STATE);
#endif
}

/**
 * @brief Set LED hardware state
 * @param color Color to display
 */
static void LED_SetHardware(PMU_LED_Color_t color)
{
#ifndef PMU_EMULATOR
    /* Turn all off first */
    HAL_GPIO_WritePin(STATUS_LED_R_PORT, STATUS_LED_R_PIN, LED_OFF_STATE);
    HAL_GPIO_WritePin(STATUS_LED_G_PORT, STATUS_LED_G_PIN, LED_OFF_STATE);
    HAL_GPIO_WritePin(STATUS_LED_B_PORT, STATUS_LED_B_PIN, LED_OFF_STATE);

    /* Set color */
    switch (color) {
        case PMU_LED_COLOR_RED:
            HAL_GPIO_WritePin(STATUS_LED_R_PORT, STATUS_LED_R_PIN, LED_ON_STATE);
            break;
        case PMU_LED_COLOR_GREEN:
            HAL_GPIO_WritePin(STATUS_LED_G_PORT, STATUS_LED_G_PIN, LED_ON_STATE);
            break;
        case PMU_LED_COLOR_BLUE:
            HAL_GPIO_WritePin(STATUS_LED_B_PORT, STATUS_LED_B_PIN, LED_ON_STATE);
            break;
        case PMU_LED_COLOR_YELLOW:
            HAL_GPIO_WritePin(STATUS_LED_R_PORT, STATUS_LED_R_PIN, LED_ON_STATE);
            HAL_GPIO_WritePin(STATUS_LED_G_PORT, STATUS_LED_G_PIN, LED_ON_STATE);
            break;
        case PMU_LED_COLOR_CYAN:
            HAL_GPIO_WritePin(STATUS_LED_G_PORT, STATUS_LED_G_PIN, LED_ON_STATE);
            HAL_GPIO_WritePin(STATUS_LED_B_PORT, STATUS_LED_B_PIN, LED_ON_STATE);
            break;
        case PMU_LED_COLOR_MAGENTA:
            HAL_GPIO_WritePin(STATUS_LED_R_PORT, STATUS_LED_R_PIN, LED_ON_STATE);
            HAL_GPIO_WritePin(STATUS_LED_B_PORT, STATUS_LED_B_PIN, LED_ON_STATE);
            break;
        case PMU_LED_COLOR_WHITE:
            HAL_GPIO_WritePin(STATUS_LED_R_PORT, STATUS_LED_R_PIN, LED_ON_STATE);
            HAL_GPIO_WritePin(STATUS_LED_G_PORT, STATUS_LED_G_PIN, LED_ON_STATE);
            HAL_GPIO_WritePin(STATUS_LED_B_PORT, STATUS_LED_B_PIN, LED_ON_STATE);
            break;
        case PMU_LED_COLOR_OFF:
        default:
            /* All already off */
            break;
    }
#else
    /* Emulator: just store state */
    (void)color;
#endif
}

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize LED module
 */
HAL_StatusTypeDef PMU_LED_Init(void)
{
    /* Initialize GPIO */
    LED_GPIO_Init();

    /* Initialize runtime state */
    led_runtime.current_state = PMU_LED_STATE_STARTUP;
    led_runtime.current_color = PMU_LED_COLOR_OFF;
    led_runtime.current_pattern = PMU_LED_PATTERN_OFF;
    led_runtime.pattern_start_ms = LED_GetTick();
    led_runtime.pattern_step = 0;
    led_runtime.pattern_active = false;
    led_runtime.comm_indicator_active = false;
    led_runtime.comm_indicator_timeout = 0;

    /* All LEDs off initially */
    LED_SetHardware(PMU_LED_COLOR_OFF);

    return HAL_OK;
}

/**
 * @brief Update LED state machine
 */
void PMU_LED_Update(void)
{
    uint32_t now = LED_GetTick();
    const PatternStep_t* pattern;
    uint32_t elapsed;

    /* Handle communication indicator (brief blue flash overlay) */
    if (led_runtime.comm_indicator_active) {
        if (now >= led_runtime.comm_indicator_timeout) {
            led_runtime.comm_indicator_active = false;
            /* Restore pattern state */
        } else {
            LED_SetHardware(PMU_LED_COLOR_BLUE);
            return;
        }
    }

    /* Handle solid color (no pattern) */
    if (led_runtime.current_pattern == PMU_LED_PATTERN_SOLID) {
        LED_SetHardware(led_runtime.current_color);
        return;
    }

    /* Handle off state */
    if (led_runtime.current_pattern == PMU_LED_PATTERN_OFF) {
        LED_SetHardware(PMU_LED_COLOR_OFF);
        return;
    }

    /* Handle patterns */
    if (!led_runtime.pattern_active) {
        LED_SetHardware(PMU_LED_COLOR_OFF);
        return;
    }

    pattern = patterns[led_runtime.current_pattern];
    if (pattern == NULL) {
        LED_SetHardware(PMU_LED_COLOR_OFF);
        return;
    }

    /* Calculate elapsed time in current step */
    elapsed = now - led_runtime.pattern_start_ms;

    /* Check if current step duration elapsed */
    if (elapsed >= pattern[led_runtime.pattern_step].duration_ms) {
        /* Move to next step */
        led_runtime.pattern_step++;
        led_runtime.pattern_start_ms = now;

        /* Check for end marker (duration = 0) */
        if (pattern[led_runtime.pattern_step].duration_ms == 0) {
            if (pattern[led_runtime.pattern_step].on == 0xFF) {
                /* Loop marker - restart pattern */
                led_runtime.pattern_step = 0;
            } else {
                /* End marker - pattern complete */
                led_runtime.pattern_active = false;
                led_runtime.current_pattern = PMU_LED_PATTERN_OFF;
                LED_SetHardware(PMU_LED_COLOR_OFF);

                /* If completing startup/config patterns, go to normal state */
                if (led_runtime.current_state == PMU_LED_STATE_STARTUP_OK ||
                    led_runtime.current_state == PMU_LED_STATE_CONFIG_LOADED) {
                    led_runtime.current_state = PMU_LED_STATE_NORMAL;
                }
                return;
            }
        }
    }

    /* Set LED state based on current step */
    if (pattern[led_runtime.pattern_step].on) {
        LED_SetHardware(led_runtime.current_color);
    } else {
        LED_SetHardware(PMU_LED_COLOR_OFF);
    }
}

/**
 * @brief Set LED system state
 */
void PMU_LED_SetState(PMU_LED_State_t state)
{
    led_runtime.current_state = state;

    switch (state) {
        case PMU_LED_STATE_STARTUP:
            PMU_LED_SetPattern(PMU_LED_PATTERN_FAST_BLINK, PMU_LED_COLOR_YELLOW);
            break;

        case PMU_LED_STATE_STARTUP_OK:
            PMU_LED_SetPattern(PMU_LED_PATTERN_BLINK_1, PMU_LED_COLOR_GREEN);
            break;

        case PMU_LED_STATE_STARTUP_ERROR:
            PMU_LED_SetPattern(PMU_LED_PATTERN_FAST_BLINK, PMU_LED_COLOR_RED);
            break;

        case PMU_LED_STATE_CONFIG_LOADED:
            PMU_LED_SetPattern(PMU_LED_PATTERN_BLINK_2, PMU_LED_COLOR_GREEN);
            break;

        case PMU_LED_STATE_CONFIG_ERROR:
            PMU_LED_SetPattern(PMU_LED_PATTERN_FAST_BLINK, PMU_LED_COLOR_RED);
            break;

        case PMU_LED_STATE_NORMAL:
            PMU_LED_SetPattern(PMU_LED_PATTERN_OFF, PMU_LED_COLOR_OFF);
            break;

        case PMU_LED_STATE_WARNING:
            PMU_LED_SetPattern(PMU_LED_PATTERN_SLOW_BLINK, PMU_LED_COLOR_YELLOW);
            break;

        case PMU_LED_STATE_FAULT:
            PMU_LED_SetPattern(PMU_LED_PATTERN_FAST_BLINK, PMU_LED_COLOR_RED);
            break;

        case PMU_LED_STATE_COMM_ACTIVE:
            PMU_LED_SetPattern(PMU_LED_PATTERN_HEARTBEAT, PMU_LED_COLOR_BLUE);
            break;

        default:
            PMU_LED_SetPattern(PMU_LED_PATTERN_OFF, PMU_LED_COLOR_OFF);
            break;
    }
}

/**
 * @brief Get current LED state
 */
PMU_LED_State_t PMU_LED_GetState(void)
{
    return led_runtime.current_state;
}

/**
 * @brief Set LED color directly
 */
void PMU_LED_SetColor(PMU_LED_Color_t color)
{
    led_runtime.current_color = color;
    led_runtime.current_pattern = PMU_LED_PATTERN_SOLID;
    led_runtime.pattern_active = false;
    LED_SetHardware(color);
}

/**
 * @brief Set LED pattern
 */
void PMU_LED_SetPattern(PMU_LED_Pattern_t pattern, PMU_LED_Color_t color)
{
    led_runtime.current_pattern = pattern;
    led_runtime.current_color = color;
    led_runtime.pattern_step = 0;
    led_runtime.pattern_start_ms = LED_GetTick();
    led_runtime.pattern_active = (pattern != PMU_LED_PATTERN_OFF &&
                                   pattern != PMU_LED_PATTERN_SOLID);
}

/**
 * @brief Trigger communication activity indicator
 */
void PMU_LED_TriggerCommActivity(void)
{
    led_runtime.comm_indicator_active = true;
    led_runtime.comm_indicator_timeout = LED_GetTick() + PMU_LED_COMM_TIMEOUT_MS;
}

/**
 * @brief Signal startup success
 */
void PMU_LED_SignalStartupOK(void)
{
    PMU_LED_SetState(PMU_LED_STATE_STARTUP_OK);
}

/**
 * @brief Signal startup error
 */
void PMU_LED_SignalStartupError(void)
{
    PMU_LED_SetState(PMU_LED_STATE_STARTUP_ERROR);
}

/**
 * @brief Signal config loaded
 */
void PMU_LED_SignalConfigLoaded(void)
{
    PMU_LED_SetState(PMU_LED_STATE_CONFIG_LOADED);
}

/**
 * @brief Signal config error
 */
void PMU_LED_SignalConfigError(void)
{
    PMU_LED_SetState(PMU_LED_STATE_CONFIG_ERROR);
}

/**
 * @brief Turn off LED
 */
void PMU_LED_Off(void)
{
    PMU_LED_SetState(PMU_LED_STATE_NORMAL);
}

/**
 * @brief Check if LED is in error state
 */
bool PMU_LED_IsError(void)
{
    return (led_runtime.current_state == PMU_LED_STATE_STARTUP_ERROR ||
            led_runtime.current_state == PMU_LED_STATE_CONFIG_ERROR ||
            led_runtime.current_state == PMU_LED_STATE_FAULT);
}

/**
 * @brief Get LED runtime state
 */
const PMU_LED_Runtime_t* PMU_LED_GetRuntime(void)
{
    return &led_runtime;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
