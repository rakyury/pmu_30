/**
 ******************************************************************************
 * @file           : emu_ui.c
 * @brief          : Emulated UI with Console Visualization
 * @author         : R2 m-sport
 * @date           : 2025-12-23
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module provides console-based visualization for:
 * - 30 output channel states (LED indicators)
 * - System status LED
 * - Channel currents and faults
 * - Buzzer events
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "stm32_hal_emu.h"
#include "pmu_profet.h"
#include "pmu_protection.h"
#include <stdio.h>
#include <string.h>

/*
 * Note: We don't include pmu_ui.h directly because of enum conflicts
 * with pmu_can_stream.h. Instead we define the required types locally.
 */

/* LED colors (from pmu_ui.h) */
typedef enum {
    PMU_LED_OFF = 0,
    PMU_LED_GREEN,
    PMU_LED_RED,
    PMU_LED_ORANGE
} PMU_LED_Color_t;

/* LED patterns (from pmu_ui.h) */
typedef enum {
    PMU_LED_PATTERN_OFF = 0,
    PMU_LED_PATTERN_SOLID,
    PMU_LED_PATTERN_BLINK_SLOW,
    PMU_LED_PATTERN_BLINK_FAST,
    PMU_LED_PATTERN_PULSE,
    PMU_LED_PATTERN_FLASH
} PMU_LED_Pattern_t;

/* Status LED states (renamed to avoid conflict) */
typedef enum {
    EMU_STATUS_POWER_ON = 0,
    EMU_STATUS_RUNNING,
    EMU_STATUS_WARNING,
    EMU_STATUS_FAULT,
    EMU_STATUS_CRITICAL,
    EMU_STATUS_BOOTLOADER
} EMU_Status_LED_t;

/* Buzzer patterns (from pmu_ui.h) */
typedef enum {
    PMU_BUZZER_OFF = 0,
    PMU_BUZZER_BEEP_SHORT,
    PMU_BUZZER_BEEP_LONG,
    PMU_BUZZER_BEEP_DOUBLE,
    PMU_BUZZER_CONTINUOUS
} PMU_Buzzer_Pattern_t;

/* Button states (from pmu_ui.h) */
typedef enum {
    PMU_BUTTON_RELEASED = 0,
    PMU_BUTTON_PRESSED,
    PMU_BUTTON_HELD,
    PMU_BUTTON_LONG_PRESS
} PMU_Button_State_t;

#define PMU_UI_NUM_CHANNEL_LEDS     30

/* Only compile for emulator */
#ifdef PMU_EMULATOR

/* Private define ------------------------------------------------------------*/
#define EMU_UI_UPDATE_INTERVAL  20   /* Update every 20 calls (1 second at 20Hz) */
#define EMU_UI_COLUMNS          10   /* Channels per row */

/* ANSI color codes */
#define ANSI_RESET      "\033[0m"
#define ANSI_RED        "\033[31m"
#define ANSI_GREEN      "\033[32m"
#define ANSI_YELLOW     "\033[33m"
#define ANSI_BLUE       "\033[34m"
#define ANSI_MAGENTA    "\033[35m"
#define ANSI_CYAN       "\033[36m"
#define ANSI_WHITE      "\033[37m"
#define ANSI_BOLD       "\033[1m"
#define ANSI_DIM        "\033[2m"
#define ANSI_BLINK      "\033[5m"

/* LED symbols (ASCII for Windows console compatibility) */
#define LED_OFF_SYMBOL      "o"
#define LED_ON_GREEN        "O"
#define LED_ON_RED          "X"
#define LED_ON_ORANGE       "@"
#define LED_BLINK_SYMBOL    "*"

/* Private typedef -----------------------------------------------------------*/

typedef struct {
    PMU_LED_Color_t color;
    PMU_LED_Pattern_t pattern;
    uint8_t brightness;
    uint16_t phase;
} EMU_LED_State_t;

typedef struct {
    PMU_Button_State_t state;
    uint8_t raw_state;
} EMU_Button_t;

/* Private variables ---------------------------------------------------------*/
static EMU_LED_State_t channel_leds[PMU_UI_NUM_CHANNEL_LEDS];
static EMU_LED_State_t status_led;
static EMU_Button_t buttons[4];
static PMU_Buzzer_Pattern_t current_buzzer = PMU_BUZZER_OFF;
static uint32_t update_counter = 0;
static uint8_t initialized = 0;
static uint8_t visualization_enabled = 1;

/* Previous states for change detection */
static PMU_PROFET_State_t prev_output_states[PMU_UI_NUM_CHANNEL_LEDS];
static EMU_Status_LED_t prev_status = EMU_STATUS_POWER_ON;

/* Private function prototypes -----------------------------------------------*/
static const char* UI_GetLEDSymbol(EMU_LED_State_t* led);
static const char* UI_GetColorCode(PMU_LED_Color_t color);
static const char* UI_GetStatusName(EMU_Status_LED_t status);
static void UI_PrintChannelGrid(void);
static void UI_PrintStatusBar(void);
static void UI_PrintOutputChange(uint8_t channel, PMU_PROFET_State_t old_state, PMU_PROFET_State_t new_state);

/* Public function prototypes */
HAL_StatusTypeDef PMU_UI_Init(void);
void PMU_UI_Update(void);
void PMU_UI_StartupAnimation(void);
void PMU_UI_UpdateChannelStatus(void);

/* Public functions ----------------------------------------------------------*/

/**
 * @brief Initialize UI system
 */
HAL_StatusTypeDef PMU_UI_Init(void)
{
    memset(channel_leds, 0, sizeof(channel_leds));
    memset(&status_led, 0, sizeof(status_led));
    memset(buttons, 0, sizeof(buttons));
    memset(prev_output_states, 0, sizeof(prev_output_states));

    /* Set default LED states */
    for (uint8_t i = 0; i < PMU_UI_NUM_CHANNEL_LEDS; i++) {
        channel_leds[i].color = PMU_LED_OFF;
        channel_leds[i].pattern = PMU_LED_PATTERN_OFF;
        channel_leds[i].brightness = 100;
    }

    status_led.color = PMU_LED_GREEN;
    status_led.pattern = PMU_LED_PATTERN_SOLID;

    initialized = 1;

    printf("\n");
    printf(ANSI_CYAN "+==================================================================+\n" ANSI_RESET);
    printf(ANSI_CYAN "|" ANSI_RESET ANSI_BOLD "           PMU-30 Emulator - Channel Visualization           " ANSI_RESET ANSI_CYAN "|\n" ANSI_RESET);
    printf(ANSI_CYAN "+==================================================================+\n" ANSI_RESET);
    printf("\n");

    PMU_UI_StartupAnimation();

    return HAL_OK;
}

/**
 * @brief Update UI system
 */
void PMU_UI_Update(void)
{
    if (!initialized) return;

    update_counter++;

    /* Update channel LEDs */
    for (uint8_t i = 0; i < PMU_UI_NUM_CHANNEL_LEDS; i++) {
        channel_leds[i].phase++;
    }
    status_led.phase++;

    /* Auto-update based on output states */
    PMU_UI_UpdateChannelStatus();

    /* Periodic full visualization (every second) */
    if (visualization_enabled && (update_counter % EMU_UI_UPDATE_INTERVAL) == 0) {
        UI_PrintStatusBar();
        UI_PrintChannelGrid();
    }
}

/**
 * @brief Set system status LED
 */
void EMU_UI_SetStatusLED(EMU_Status_LED_t status)
{
    if (status != prev_status) {
        printf(ANSI_CYAN "[UI] " ANSI_RESET "System status: %s%s%s\n",
               UI_GetColorCode(status_led.color),
               UI_GetStatusName(status),
               ANSI_RESET);
        prev_status = status;
    }

    switch (status) {
        case EMU_STATUS_POWER_ON:
            status_led.color = PMU_LED_GREEN;
            status_led.pattern = PMU_LED_PATTERN_SOLID;
            break;
        case EMU_STATUS_RUNNING:
            status_led.color = PMU_LED_GREEN;
            status_led.pattern = PMU_LED_PATTERN_PULSE;
            break;
        case EMU_STATUS_WARNING:
            status_led.color = PMU_LED_ORANGE;
            status_led.pattern = PMU_LED_PATTERN_BLINK_SLOW;
            break;
        case EMU_STATUS_FAULT:
            status_led.color = PMU_LED_RED;
            status_led.pattern = PMU_LED_PATTERN_BLINK_FAST;
            break;
        case EMU_STATUS_CRITICAL:
            status_led.color = PMU_LED_RED;
            status_led.pattern = PMU_LED_PATTERN_SOLID;
            break;
        case EMU_STATUS_BOOTLOADER:
            status_led.color = PMU_LED_ORANGE;
            status_led.pattern = PMU_LED_PATTERN_PULSE;
            break;
    }
    status_led.phase = 0;
}

/**
 * @brief Set channel LED
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
 * @brief Update channel LEDs based on output states
 */
void PMU_UI_UpdateChannelStatus(void)
{
    for (uint8_t i = 0; i < PMU_UI_NUM_CHANNEL_LEDS; i++) {
        PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(i);

        if (ch == NULL) continue;

        /* Detect state changes and log them */
        if (ch->state != prev_output_states[i]) {
            UI_PrintOutputChange(i, prev_output_states[i], ch->state);
            prev_output_states[i] = ch->state;
        }

        /* Update LED based on channel state */
        if (ch->fault_flags != 0) {
            PMU_UI_SetChannelLED(i, PMU_LED_RED, PMU_LED_PATTERN_BLINK_FAST);
        } else if (ch->state == PMU_PROFET_STATE_ON) {
            PMU_UI_SetChannelLED(i, PMU_LED_GREEN, PMU_LED_PATTERN_SOLID);
        } else if (ch->state == PMU_PROFET_STATE_PWM) {
            PMU_UI_SetChannelLED(i, PMU_LED_GREEN, PMU_LED_PATTERN_BLINK_SLOW);
        } else {
            PMU_UI_SetChannelLED(i, PMU_LED_OFF, PMU_LED_PATTERN_OFF);
        }
    }

    /* Update status LED based on protection system */
    PMU_Protection_State_t* prot = PMU_Protection_GetState();
    if (prot != NULL) {
        if (prot->status == PMU_PROT_STATUS_CRITICAL) {
            EMU_UI_SetStatusLED(EMU_STATUS_CRITICAL);
        } else if (prot->status == PMU_PROT_STATUS_FAULT) {
            EMU_UI_SetStatusLED(EMU_STATUS_FAULT);
        } else if (prot->status == PMU_PROT_STATUS_WARNING) {
            EMU_UI_SetStatusLED(EMU_STATUS_WARNING);
        } else {
            EMU_UI_SetStatusLED(EMU_STATUS_RUNNING);
        }
    }
}

/**
 * @brief Play buzzer pattern
 */
void PMU_UI_PlayBuzzer(PMU_Buzzer_Pattern_t pattern)
{
    current_buzzer = pattern;

    const char* pattern_name = "Unknown";
    switch (pattern) {
        case PMU_BUZZER_OFF: pattern_name = "OFF"; break;
        case PMU_BUZZER_BEEP_SHORT: pattern_name = "BEEP (short)"; break;
        case PMU_BUZZER_BEEP_LONG: pattern_name = "BEEP (long)"; break;
        case PMU_BUZZER_BEEP_DOUBLE: pattern_name = "BEEP BEEP"; break;
        case PMU_BUZZER_CONTINUOUS: pattern_name = "ALARM!"; break;
    }

    if (pattern != PMU_BUZZER_OFF) {
        printf(ANSI_YELLOW "[BUZZER] %s" ANSI_RESET "\n", pattern_name);
    }
}

/**
 * @brief Stop buzzer
 */
void PMU_UI_StopBuzzer(void)
{
    current_buzzer = PMU_BUZZER_OFF;
}

/**
 * @brief Get button state
 */
PMU_Button_State_t PMU_UI_GetButtonState(uint8_t button)
{
    if (button >= 4) return PMU_BUTTON_RELEASED;
    return buttons[button].state;
}

/**
 * @brief Check if button pressed
 */
uint8_t PMU_UI_ButtonPressed(uint8_t button)
{
    return 0;  /* No physical buttons in emulator */
}

/**
 * @brief Check if button released
 */
uint8_t PMU_UI_ButtonReleased(uint8_t button)
{
    return 0;
}

/**
 * @brief Startup animation
 */
void PMU_UI_StartupAnimation(void)
{
    printf(ANSI_GREEN "[OK] UI initialized with %d channels\n" ANSI_RESET, PMU_UI_NUM_CHANNEL_LEDS);
    printf("\n");

    /* Print initial grid */
    UI_PrintChannelGrid();
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Get LED symbol based on state
 */
static const char* UI_GetLEDSymbol(EMU_LED_State_t* led)
{
    if (led->pattern == PMU_LED_PATTERN_OFF || led->color == PMU_LED_OFF) {
        return LED_OFF_SYMBOL;
    }

    if (led->pattern == PMU_LED_PATTERN_BLINK_SLOW ||
        led->pattern == PMU_LED_PATTERN_BLINK_FAST) {
        /* Blinking - alternate symbol */
        if ((led->phase / 5) % 2 == 0) {
            return LED_BLINK_SYMBOL;
        }
    }

    switch (led->color) {
        case PMU_LED_GREEN:  return LED_ON_GREEN;
        case PMU_LED_RED:    return LED_ON_RED;
        case PMU_LED_ORANGE: return LED_ON_ORANGE;
        default:             return LED_OFF_SYMBOL;
    }
}

/**
 * @brief Get ANSI color code
 */
static const char* UI_GetColorCode(PMU_LED_Color_t color)
{
    switch (color) {
        case PMU_LED_GREEN:  return ANSI_GREEN;
        case PMU_LED_RED:    return ANSI_RED;
        case PMU_LED_ORANGE: return ANSI_YELLOW;
        default:             return ANSI_DIM;
    }
}

/**
 * @brief Get status name string
 */
static const char* UI_GetStatusName(EMU_Status_LED_t status)
{
    switch (status) {
        case EMU_STATUS_POWER_ON:   return "POWER ON";
        case EMU_STATUS_RUNNING:    return "RUNNING";
        case EMU_STATUS_WARNING:    return "WARNING";
        case EMU_STATUS_FAULT:      return "FAULT";
        case EMU_STATUS_CRITICAL:   return "CRITICAL";
        case EMU_STATUS_BOOTLOADER: return "BOOTLOADER";
        default:                    return "UNKNOWN";
    }
}

/**
 * @brief Print channel visualization grid
 */
static void UI_PrintChannelGrid(void)
{
    printf("\n" ANSI_CYAN "+---------------------------------------------------------+\n" ANSI_RESET);
    printf(ANSI_CYAN "|" ANSI_RESET "                   CHANNEL STATUS                        " ANSI_CYAN "|\n" ANSI_RESET);
    printf(ANSI_CYAN "+---------------------------------------------------------+\n" ANSI_RESET);

    /* Print channels in rows */
    for (uint8_t row = 0; row < 3; row++) {
        printf(ANSI_CYAN "| " ANSI_RESET);

        /* Channel numbers */
        for (uint8_t col = 0; col < EMU_UI_COLUMNS; col++) {
            uint8_t ch = row * EMU_UI_COLUMNS + col;
            if (ch < PMU_UI_NUM_CHANNEL_LEDS) {
                printf("%s%2d%s ", ANSI_DIM, ch, ANSI_RESET);
            } else {
                printf("   ");
            }
        }
        printf("    " ANSI_CYAN "|\n" ANSI_RESET);

        /* LED symbols */
        printf(ANSI_CYAN "| " ANSI_RESET);
        for (uint8_t col = 0; col < EMU_UI_COLUMNS; col++) {
            uint8_t ch = row * EMU_UI_COLUMNS + col;
            if (ch < PMU_UI_NUM_CHANNEL_LEDS) {
                printf("%s %s %s",
                       UI_GetColorCode(channel_leds[ch].color),
                       UI_GetLEDSymbol(&channel_leds[ch]),
                       ANSI_RESET);
            } else {
                printf("   ");
            }
        }
        printf("    " ANSI_CYAN "|\n" ANSI_RESET);

        if (row < 2) {
            printf(ANSI_CYAN "|" ANSI_RESET "                                                         " ANSI_CYAN "|\n" ANSI_RESET);
        }
    }

    printf(ANSI_CYAN "+---------------------------------------------------------+\n" ANSI_RESET);

    /* Legend */
    printf(ANSI_DIM "  Legend: " ANSI_RESET);
    printf(ANSI_DIM "%s" ANSI_RESET "=OFF  ", LED_OFF_SYMBOL);
    printf(ANSI_GREEN "%s" ANSI_RESET "=ON  ", LED_ON_GREEN);
    printf(ANSI_GREEN "%s" ANSI_RESET "=PWM  ", LED_BLINK_SYMBOL);
    printf(ANSI_RED "%s" ANSI_RESET "=FAULT\n", LED_ON_RED);
    printf("\n");
}

/**
 * @brief Print status bar
 */
static void UI_PrintStatusBar(void)
{
    /* Count active channels */
    uint8_t on_count = 0;
    uint8_t pwm_count = 0;
    uint8_t fault_count = 0;

    for (uint8_t i = 0; i < PMU_UI_NUM_CHANNEL_LEDS; i++) {
        PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(i);
        if (ch) {
            if (ch->fault_flags != 0) fault_count++;
            else if (ch->state == PMU_PROFET_STATE_ON) on_count++;
            else if (ch->state == PMU_PROFET_STATE_PWM) pwm_count++;
        }
    }

    printf(ANSI_CYAN "-----------------------------------------------------------\n" ANSI_RESET);
    printf("  Status: %s%s%s  |  ",
           UI_GetColorCode(status_led.color),
           UI_GetStatusName(prev_status),
           ANSI_RESET);
    printf(ANSI_GREEN "ON: %d" ANSI_RESET "  |  ", on_count);
    printf(ANSI_YELLOW "PWM: %d" ANSI_RESET "  |  ", pwm_count);
    printf(ANSI_RED "FAULT: %d" ANSI_RESET "\n", fault_count);
}

/**
 * @brief Print output state change
 */
static void UI_PrintOutputChange(uint8_t channel, PMU_PROFET_State_t old_state, PMU_PROFET_State_t new_state)
{
    const char* old_name = "OFF";
    const char* new_name = "OFF";
    const char* new_color = ANSI_DIM;

    switch (old_state) {
        case PMU_PROFET_STATE_OFF:   old_name = "OFF"; break;
        case PMU_PROFET_STATE_ON:    old_name = "ON"; break;
        case PMU_PROFET_STATE_PWM:   old_name = "PWM"; break;
        case PMU_PROFET_STATE_FAULT: old_name = "FAULT"; break;
    }

    switch (new_state) {
        case PMU_PROFET_STATE_OFF:
            new_name = "OFF";
            new_color = ANSI_DIM;
            break;
        case PMU_PROFET_STATE_ON:
            new_name = "ON";
            new_color = ANSI_GREEN;
            break;
        case PMU_PROFET_STATE_PWM:
            new_name = "PWM";
            new_color = ANSI_YELLOW;
            break;
        case PMU_PROFET_STATE_FAULT:
            new_name = "FAULT";
            new_color = ANSI_RED;
            break;
    }

    printf(ANSI_BLUE "[OUT %02d] " ANSI_RESET "%s → %s%s%s\n",
           channel, old_name, new_color, new_name, ANSI_RESET);
}

/* ========================================================================== */
/* Emulator-specific functions                                                 */
/* ========================================================================== */

/**
 * @brief Enable/disable visualization output
 */
void EMU_UI_SetVisualization(uint8_t enabled)
{
    visualization_enabled = enabled;
    if (enabled) {
        printf(ANSI_GREEN "[EMU_UI] Visualization enabled\n" ANSI_RESET);
    } else {
        printf(ANSI_DIM "[EMU_UI] Visualization disabled\n" ANSI_RESET);
    }
}

/**
 * @brief Force print current state
 */
void EMU_UI_PrintState(void)
{
    UI_PrintStatusBar();
    UI_PrintChannelGrid();
}

/**
 * @brief Print detailed channel info
 */
void EMU_UI_PrintChannelDetails(uint8_t channel)
{
    if (channel >= PMU_UI_NUM_CHANNEL_LEDS) {
        printf(ANSI_RED "Invalid channel: %d\n" ANSI_RESET, channel);
        return;
    }

    PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(channel);
    if (!ch) {
        printf(ANSI_RED "No data for channel %d\n" ANSI_RESET, channel);
        return;
    }

    printf("\n" ANSI_CYAN "=== Channel %d Details ===\n" ANSI_RESET, channel);
    printf("  State:       ");
    switch (ch->state) {
        case PMU_PROFET_STATE_OFF:   printf(ANSI_DIM "OFF\n" ANSI_RESET); break;
        case PMU_PROFET_STATE_ON:    printf(ANSI_GREEN "ON\n" ANSI_RESET); break;
        case PMU_PROFET_STATE_PWM:   printf(ANSI_YELLOW "PWM (%d.%d%%)\n" ANSI_RESET,
                                            ch->pwm_duty / 10, ch->pwm_duty % 10); break;
        case PMU_PROFET_STATE_FAULT: printf(ANSI_RED "FAULT\n" ANSI_RESET); break;
    }
    printf("  Current:     %d mA\n", ch->current_mA);
    printf("  Temperature: %d °C\n", ch->temperature_C);
    printf("  On time:     %lu ms\n", (unsigned long)ch->on_time_ms);
    printf("  Faults:      0x%02X (%d total)\n", ch->fault_flags, ch->fault_count);
    printf("\n");
}

#endif /* PMU_EMULATOR */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
