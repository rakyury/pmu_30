/**
 ******************************************************************************
 * @file           : pmu_ui.c
 * @brief          : User Interface Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module implements:
 * - 30x bicolor LED control (green/red)
 * - 1x system status LED
 * - Buzzer patterns
 * - Button input with debouncing
 * - Startup animation
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_ui.h"
#include "pmu_profet.h"
#include "pmu_protection.h"
#include "stm32h7xx_hal.h"
#include <string.h>

/* Private typedef -----------------------------------------------------------*/

/**
 * @brief LED state for one channel
 */
typedef struct {
    PMU_LED_Color_t color;          /* Current color */
    PMU_LED_Pattern_t pattern;      /* Pattern */
    uint8_t brightness;             /* 0-100% */
    uint16_t phase;                 /* Pattern phase counter */
} PMU_LED_State_t;

/**
 * @brief Button state tracking
 */
typedef struct {
    PMU_Button_State_t state;       /* Current state */
    uint8_t raw_state;              /* Raw GPIO state */
    uint8_t prev_state;             /* Previous state for edge detection */
    uint32_t press_time;            /* Press timestamp */
    uint32_t debounce_time;         /* Debounce timestamp */
} PMU_Button_Info_t;

/**
 * @brief Buzzer state
 */
typedef struct {
    PMU_Buzzer_Pattern_t pattern;   /* Current pattern */
    uint8_t active;                 /* Buzzer active flag */
    uint16_t timer;                 /* Pattern timer */
    uint16_t phase;                 /* Pattern phase */
} PMU_Buzzer_State_t;

/* Private define ------------------------------------------------------------*/

/* Update rate (20Hz = 50ms) */
#define UI_UPDATE_PERIOD_MS     50

/* Pattern speeds */
#define BLINK_SLOW_PERIOD       1000    /* 1s = 1Hz */
#define BLINK_FAST_PERIOD       250     /* 0.25s = 4Hz */
#define PULSE_PERIOD            2000    /* 2s */

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_LED_State_t channel_leds[PMU_UI_NUM_CHANNEL_LEDS];
static PMU_LED_State_t status_led;
static PMU_Button_Info_t buttons[4];  /* Up to 4 buttons */
static PMU_Buzzer_State_t buzzer;
static uint32_t tick_counter = 0;

/* Private function prototypes -----------------------------------------------*/
static void UI_UpdateLED(PMU_LED_State_t* led);
static void UI_SetLEDHardware(uint8_t channel, PMU_LED_Color_t color, uint8_t brightness);
static void UI_UpdateBuzzer(void);
static void UI_UpdateButtons(void);
static uint8_t UI_ReadButton(uint8_t button);

/* Private user code ---------------------------------------------------------*/

/**
 * @brief Initialize UI system
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_UI_Init(void)
{
    /* Clear states */
    memset(channel_leds, 0, sizeof(channel_leds));
    memset(&status_led, 0, sizeof(status_led));
    memset(buttons, 0, sizeof(buttons));
    memset(&buzzer, 0, sizeof(buzzer));

    /* Set default LED patterns */
    for (uint8_t i = 0; i < PMU_UI_NUM_CHANNEL_LEDS; i++) {
        channel_leds[i].color = PMU_LED_OFF;
        channel_leds[i].pattern = PMU_LED_PATTERN_OFF;
        channel_leds[i].brightness = 100;
    }

    /* Set status LED to power on */
    status_led.color = PMU_LED_GREEN;
    status_led.pattern = PMU_LED_PATTERN_SOLID;
    status_led.brightness = 100;

    /* TODO: Initialize GPIO for LEDs */
    /* This would configure 60 GPIO pins (30 channels × 2 colors) */

    /* TODO: Initialize PWM for buzzer */

    /* TODO: Initialize GPIO for buttons with pull-ups */

    /* Show startup animation */
    PMU_UI_StartupAnimation();

    return HAL_OK;
}

/**
 * @brief Update UI system (call at 20Hz)
 * @retval None
 */
void PMU_UI_Update(void)
{
    tick_counter++;

    /* Update status LED */
    UI_UpdateLED(&status_led);

    /* Update all channel LEDs */
    for (uint8_t i = 0; i < PMU_UI_NUM_CHANNEL_LEDS; i++) {
        UI_UpdateLED(&channel_leds[i]);
    }

    /* Update buzzer */
    UI_UpdateBuzzer();

    /* Update buttons */
    UI_UpdateButtons();

    /* Auto-update channel status from output states */
    PMU_UI_UpdateChannelStatus();
}

/**
 * @brief Update single LED based on pattern
 * @param led LED state
 */
static void UI_UpdateLED(PMU_LED_State_t* led)
{
    uint8_t brightness = led->brightness;

    /* Update phase counter */
    led->phase++;

    /* Apply pattern */
    switch (led->pattern) {
        case PMU_LED_PATTERN_OFF:
            brightness = 0;
            break;

        case PMU_LED_PATTERN_SOLID:
            /* No change */
            break;

        case PMU_LED_PATTERN_BLINK_SLOW:
            /* 1Hz blink */
            if ((led->phase % (BLINK_SLOW_PERIOD / UI_UPDATE_PERIOD_MS)) <
                (BLINK_SLOW_PERIOD / UI_UPDATE_PERIOD_MS / 2)) {
                brightness = led->brightness;
            } else {
                brightness = 0;
            }
            break;

        case PMU_LED_PATTERN_BLINK_FAST:
            /* 4Hz blink */
            if ((led->phase % (BLINK_FAST_PERIOD / UI_UPDATE_PERIOD_MS)) <
                (BLINK_FAST_PERIOD / UI_UPDATE_PERIOD_MS / 2)) {
                brightness = led->brightness;
            } else {
                brightness = 0;
            }
            break;

        case PMU_LED_PATTERN_PULSE:
            /* Sinusoidal pulse */
            {
                uint16_t phase_in_period = led->phase % (PULSE_PERIOD / UI_UPDATE_PERIOD_MS);
                float angle = (float)phase_in_period / (PULSE_PERIOD / UI_UPDATE_PERIOD_MS) * 6.283f;  /* 2*PI */
                brightness = (uint8_t)(led->brightness * (0.5f + 0.5f * cosf(angle)));
            }
            break;

        case PMU_LED_PATTERN_FLASH:
            /* Quick flash then off */
            if (led->phase < 2) {
                brightness = led->brightness;
            } else {
                brightness = 0;
                led->pattern = PMU_LED_PATTERN_OFF;
                led->phase = 0;
            }
            break;
    }

    /* Set hardware */
    /* Note: channel index would be determined by LED pointer offset */
    /* For now, this is a placeholder */
}

/**
 * @brief Set hardware LED state
 * @param channel Channel number
 * @param color Color
 * @param brightness Brightness 0-100%
 */
static void UI_SetLEDHardware(uint8_t channel, PMU_LED_Color_t color, uint8_t brightness)
{
    /* TODO: Set GPIO pins for LED */
    /* Each channel has 2 pins: green and red */
    /* Color combinations:
     * OFF:    both LOW
     * GREEN:  green HIGH, red LOW
     * RED:    green LOW, red HIGH
     * ORANGE: both HIGH
     */

    /* Example GPIO control:
    GPIO_PinState green_state = GPIO_PIN_RESET;
    GPIO_PinState red_state = GPIO_PIN_RESET;

    if (brightness > 0) {
        switch (color) {
            case PMU_LED_GREEN:
                green_state = GPIO_PIN_SET;
                break;
            case PMU_LED_RED:
                red_state = GPIO_PIN_SET;
                break;
            case PMU_LED_ORANGE:
                green_state = GPIO_PIN_SET;
                red_state = GPIO_PIN_SET;
                break;
            default:
                break;
        }
    }

    // Set GPIOs (example - actual pins would be from mapping table)
    // HAL_GPIO_WritePin(LED_GREEN_GPIOx[channel], LED_GREEN_Pin[channel], green_state);
    // HAL_GPIO_WritePin(LED_RED_GPIOx[channel], LED_RED_Pin[channel], red_state);
    */
}

/**
 * @brief Set system status LED
 * @param status Status to display
 */
void PMU_UI_SetStatusLED(PMU_Status_LED_t status)
{
    switch (status) {
        case PMU_STATUS_POWER_ON:
            status_led.color = PMU_LED_GREEN;
            status_led.pattern = PMU_LED_PATTERN_SOLID;
            break;

        case PMU_STATUS_RUNNING:
            status_led.color = PMU_LED_GREEN;
            status_led.pattern = PMU_LED_PATTERN_PULSE;
            break;

        case PMU_STATUS_WARNING:
            status_led.color = PMU_LED_ORANGE;
            status_led.pattern = PMU_LED_PATTERN_BLINK_SLOW;
            break;

        case PMU_STATUS_FAULT:
            status_led.color = PMU_LED_RED;
            status_led.pattern = PMU_LED_PATTERN_BLINK_FAST;
            break;

        case PMU_STATUS_CRITICAL:
            status_led.color = PMU_LED_RED;
            status_led.pattern = PMU_LED_PATTERN_SOLID;
            break;

        case PMU_STATUS_BOOTLOADER:
            status_led.color = PMU_LED_ORANGE;
            status_led.pattern = PMU_LED_PATTERN_PULSE;
            break;
    }

    status_led.phase = 0;
}

/**
 * @brief Set channel LED
 * @param channel Channel number
 * @param color Color
 * @param pattern Pattern
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_UI_SetChannelLED(uint8_t channel, PMU_LED_Color_t color,
                                        PMU_LED_Pattern_t pattern)
{
    if (channel >= PMU_UI_NUM_CHANNEL_LEDS) {
        return HAL_ERROR;
    }

    channel_leds[channel].color = color;
    channel_leds[channel].pattern = pattern;
    channel_leds[channel].phase = 0;

    return HAL_OK;
}

/**
 * @brief Set all channel LEDs
 * @param color Color
 * @param pattern Pattern
 */
void PMU_UI_SetAllChannelLEDs(PMU_LED_Color_t color, PMU_LED_Pattern_t pattern)
{
    for (uint8_t i = 0; i < PMU_UI_NUM_CHANNEL_LEDS; i++) {
        channel_leds[i].color = color;
        channel_leds[i].pattern = pattern;
        channel_leds[i].phase = 0;
    }
}

/**
 * @brief Update channel status LEDs based on outputs
 */
void PMU_UI_UpdateChannelStatus(void)
{
    for (uint8_t i = 0; i < PMU_UI_NUM_CHANNEL_LEDS; i++) {
        PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(i);

        if (ch == NULL) {
            continue;
        }

        /* Set LED based on channel state */
        if (ch->fault_flags != 0) {
            /* Fault - red blinking */
            PMU_UI_SetChannelLED(i, PMU_LED_RED, PMU_LED_PATTERN_BLINK_FAST);
        } else if (ch->state == PMU_PROFET_STATE_ON) {
            /* On - green solid */
            PMU_UI_SetChannelLED(i, PMU_LED_GREEN, PMU_LED_PATTERN_SOLID);
        } else if (ch->state == PMU_PROFET_STATE_PWM) {
            /* PWM - green blinking */
            PMU_UI_SetChannelLED(i, PMU_LED_GREEN, PMU_LED_PATTERN_BLINK_SLOW);
        } else {
            /* Off */
            PMU_UI_SetChannelLED(i, PMU_LED_OFF, PMU_LED_PATTERN_OFF);
        }
    }

    /* Update status LED based on protection system */
    PMU_Protection_State_t* prot = PMU_Protection_GetState();
    if (prot != NULL) {
        if (prot->status == PMU_PROT_STATUS_CRITICAL) {
            PMU_UI_SetStatusLED(PMU_STATUS_CRITICAL);
        } else if (prot->status == PMU_PROT_STATUS_FAULT) {
            PMU_UI_SetStatusLED(PMU_STATUS_FAULT);
        } else if (prot->status == PMU_PROT_STATUS_WARNING) {
            PMU_UI_SetStatusLED(PMU_STATUS_WARNING);
        } else {
            PMU_UI_SetStatusLED(PMU_STATUS_RUNNING);
        }
    }
}

/**
 * @brief Play buzzer pattern
 * @param pattern Pattern to play
 */
void PMU_UI_PlayBuzzer(PMU_Buzzer_Pattern_t pattern)
{
    buzzer.pattern = pattern;
    buzzer.active = 1;
    buzzer.timer = 0;
    buzzer.phase = 0;
}

/**
 * @brief Stop buzzer
 */
void PMU_UI_StopBuzzer(void)
{
    buzzer.active = 0;
    /* TODO: Turn off buzzer GPIO/PWM */
}

/**
 * @brief Update buzzer pattern
 */
static void UI_UpdateBuzzer(void)
{
    if (!buzzer.active) {
        return;
    }

    buzzer.timer++;

    switch (buzzer.pattern) {
        case PMU_BUZZER_BEEP_SHORT:
            if (buzzer.timer < 2) {  /* 100ms at 20Hz */
                /* Buzzer ON */
            } else {
                PMU_UI_StopBuzzer();
            }
            break;

        case PMU_BUZZER_BEEP_LONG:
            if (buzzer.timer < 10) {  /* 500ms */
                /* Buzzer ON */
            } else {
                PMU_UI_StopBuzzer();
            }
            break;

        case PMU_BUZZER_BEEP_DOUBLE:
            if (buzzer.timer < 2 || (buzzer.timer >= 4 && buzzer.timer < 6)) {
                /* Buzzer ON */
            } else if (buzzer.timer >= 8) {
                PMU_UI_StopBuzzer();
            }
            break;

        case PMU_BUZZER_CONTINUOUS:
            /* Buzzer ON continuously */
            break;

        default:
            PMU_UI_StopBuzzer();
            break;
    }
}

/**
 * @brief Update button states
 */
static void UI_UpdateButtons(void)
{
    for (uint8_t i = 0; i < 4; i++) {
        /* Read raw button state */
        uint8_t raw = UI_ReadButton(i);

        /* Debounce */
        if (raw != buttons[i].raw_state) {
            buttons[i].debounce_time = tick_counter;
            buttons[i].raw_state = raw;
        }

        /* Check debounce time */
        if ((tick_counter - buttons[i].debounce_time) * UI_UPDATE_PERIOD_MS >= PMU_UI_DEBOUNCE_MS) {
            /* Update state */
            if (raw && !buttons[i].prev_state) {
                /* Button pressed */
                buttons[i].state = PMU_BUTTON_PRESSED;
                buttons[i].press_time = tick_counter;
            } else if (!raw && buttons[i].prev_state) {
                /* Button released */
                buttons[i].state = PMU_BUTTON_RELEASED;
            } else if (raw && buttons[i].prev_state) {
                /* Button held */
                uint32_t held_time = (tick_counter - buttons[i].press_time) * UI_UPDATE_PERIOD_MS;

                if (held_time >= PMU_UI_LONG_PRESS_MS) {
                    buttons[i].state = PMU_BUTTON_LONG_PRESS;
                } else if (held_time >= PMU_UI_HOLD_TIME_MS) {
                    buttons[i].state = PMU_BUTTON_HELD;
                } else {
                    buttons[i].state = PMU_BUTTON_PRESSED;
                }
            }

            buttons[i].prev_state = raw;
        }
    }
}

/**
 * @brief Read button hardware state
 * @param button Button index
 * @retval 1 if pressed, 0 if released
 */
static uint8_t UI_ReadButton(uint8_t button)
{
    /* TODO: Read GPIO pin */
    /* Return 1 if button pressed (active low with pull-up) */
    return 0;
}

/**
 * @brief Get button state
 * @param button Button index
 * @retval Button state
 */
PMU_Button_State_t PMU_UI_GetButtonState(uint8_t button)
{
    if (button >= 4) {
        return PMU_BUTTON_RELEASED;
    }

    return buttons[button].state;
}

/**
 * @brief Check if button just pressed
 * @param button Button index
 * @retval 1 if just pressed
 */
uint8_t PMU_UI_ButtonPressed(uint8_t button)
{
    if (button >= 4) {
        return 0;
    }

    return (buttons[button].state == PMU_BUTTON_PRESSED &&
            !buttons[button].prev_state) ? 1 : 0;
}

/**
 * @brief Check if button just released
 * @param button Button index
 * @retval 1 if just released
 */
uint8_t PMU_UI_ButtonReleased(uint8_t button)
{
    if (button >= 4) {
        return 0;
    }

    return (buttons[button].state == PMU_BUTTON_RELEASED &&
            buttons[button].prev_state) ? 1 : 0;
}

/**
 * @brief Startup animation
 */
void PMU_UI_StartupAnimation(void)
{
    /* Sequential LED sweep */
    for (uint8_t i = 0; i < PMU_UI_NUM_CHANNEL_LEDS; i++) {
        PMU_UI_SetChannelLED(i, PMU_LED_GREEN, PMU_LED_PATTERN_SOLID);
        HAL_Delay(20);
        PMU_UI_SetChannelLED(i, PMU_LED_OFF, PMU_LED_PATTERN_OFF);
    }

    /* Flash all */
    PMU_UI_SetAllChannelLEDs(PMU_LED_GREEN, PMU_LED_PATTERN_SOLID);
    HAL_Delay(100);
    PMU_UI_SetAllChannelLEDs(PMU_LED_OFF, PMU_LED_PATTERN_OFF);

    /* Beep */
    PMU_UI_PlayBuzzer(PMU_BUZZER_BEEP_SHORT);
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
