/**
 ******************************************************************************
 * @file           : pmu_ui.h
 * @brief          : User Interface (LEDs, Buzzer, Buttons) Header
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 ******************************************************************************
 */

#ifndef __PMU_UI_H
#define __PMU_UI_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Exported types ------------------------------------------------------------*/

/**
 * @brief LED colors (bicolor LEDs)
 */
typedef enum {
    PMU_LED_OFF = 0,
    PMU_LED_GREEN,
    PMU_LED_RED,
    PMU_LED_ORANGE      /* Both green and red */
} PMU_LED_Color_t;

/**
 * @brief LED pattern for status indication
 */
typedef enum {
    PMU_LED_PATTERN_OFF = 0,
    PMU_LED_PATTERN_SOLID,
    PMU_LED_PATTERN_BLINK_SLOW,     /* 1Hz */
    PMU_LED_PATTERN_BLINK_FAST,     /* 4Hz */
    PMU_LED_PATTERN_PULSE,          /* Fade in/out */
    PMU_LED_PATTERN_FLASH           /* Quick flash then off */
} PMU_LED_Pattern_t;

/**
 * @brief System status LED states
 */
typedef enum {
    PMU_LED_STATUS_POWER_ON = 0,    /* Green solid */
    PMU_LED_STATUS_RUNNING,         /* Green pulse */
    PMU_LED_STATUS_WARNING,         /* Orange blink */
    PMU_LED_STATUS_FAULT,           /* Red blink fast */
    PMU_LED_STATUS_CRITICAL,        /* Red solid */
    PMU_LED_STATUS_BOOTLOADER       /* Orange pulse */
} PMU_Status_LED_t;

/**
 * @brief Buzzer pattern
 */
typedef enum {
    PMU_BUZZER_OFF = 0,
    PMU_BUZZER_BEEP_SHORT,          /* 100ms */
    PMU_BUZZER_BEEP_LONG,           /* 500ms */
    PMU_BUZZER_BEEP_DOUBLE,         /* 2x 100ms */
    PMU_BUZZER_CONTINUOUS           /* Warning */
} PMU_Buzzer_Pattern_t;

/**
 * @brief Button state
 */
typedef enum {
    PMU_BUTTON_RELEASED = 0,
    PMU_BUTTON_PRESSED,
    PMU_BUTTON_HELD,                /* > 1 second */
    PMU_BUTTON_LONG_PRESS           /* > 3 seconds */
} PMU_Button_State_t;

/* Exported constants --------------------------------------------------------*/

/* Number of per-channel LEDs */
#define PMU_UI_NUM_CHANNEL_LEDS     30

/* LED update rate */
#define PMU_UI_LED_UPDATE_HZ        20      /* 20Hz = 50ms */

/* Button debounce time */
#define PMU_UI_DEBOUNCE_MS          50
#define PMU_UI_HOLD_TIME_MS         1000
#define PMU_UI_LONG_PRESS_MS        3000

/* Exported macro ------------------------------------------------------------*/

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize UI system
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_UI_Init(void);

/**
 * @brief Update UI system (call at 20Hz)
 * @retval None
 */
void PMU_UI_Update(void);

/**
 * @brief Set system status LED
 * @param status Status to display
 * @retval None
 */
void PMU_UI_SetStatusLED(PMU_Status_LED_t status);

/**
 * @brief Set channel LED color and pattern
 * @param channel Channel number (0-29)
 * @param color LED color
 * @param pattern LED pattern
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_UI_SetChannelLED(uint8_t channel, PMU_LED_Color_t color,
                                        PMU_LED_Pattern_t pattern);

/**
 * @brief Set all channel LEDs
 * @param color LED color for all
 * @param pattern LED pattern for all
 * @retval None
 */
void PMU_UI_SetAllChannelLEDs(PMU_LED_Color_t color, PMU_LED_Pattern_t pattern);

/**
 * @brief Play buzzer pattern
 * @param pattern Buzzer pattern
 * @retval None
 */
void PMU_UI_PlayBuzzer(PMU_Buzzer_Pattern_t pattern);

/**
 * @brief Stop buzzer
 * @retval None
 */
void PMU_UI_StopBuzzer(void);

/**
 * @brief Get button state
 * @param button Button index (0-based)
 * @retval Button state
 */
PMU_Button_State_t PMU_UI_GetButtonState(uint8_t button);

/**
 * @brief Check if button was just pressed (rising edge)
 * @param button Button index
 * @retval 1 if just pressed, 0 otherwise
 */
uint8_t PMU_UI_ButtonPressed(uint8_t button);

/**
 * @brief Check if button was just released (falling edge)
 * @param button Button index
 * @retval 1 if just released, 0 otherwise
 */
uint8_t PMU_UI_ButtonReleased(uint8_t button);

/**
 * @brief Show startup animation
 * @retval None
 */
void PMU_UI_StartupAnimation(void);

/**
 * @brief Update channel LEDs based on output states
 * @retval None
 */
void PMU_UI_UpdateChannelStatus(void);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_UI_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
