/**
 ******************************************************************************
 * @file           : pmu_blinkmarine.h
 * @brief          : BlinkMarine CAN Keypad Support (PKP-2600-SI, PKP-2800-SI)
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * Supports BlinkMarine PKP series keypads:
 * - PKP-2600-SI: 2x6 (12 buttons)
 * - PKP-2800-SI: 2x8 (16 buttons)
 *
 ******************************************************************************
 */

#ifndef __PMU_BLINKMARINE_H
#define __PMU_BLINKMARINE_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "pmu_types.h"
#include "pmu_can.h"

/* Exported types ------------------------------------------------------------*/

/**
 * @brief BlinkMarine keypad type
 */
typedef enum {
    PMU_BLINKMARINE_2X6 = 0,    /* PKP-2600-SI: 12 buttons (2 rows x 6 columns) */
    PMU_BLINKMARINE_2X8 = 1,    /* PKP-2800-SI: 16 buttons (2 rows x 8 columns) */
} PMU_BlinkMarine_Type_t;

/**
 * @brief Button state
 */
typedef enum {
    PMU_BM_BTN_RELEASED = 0,
    PMU_BM_BTN_PRESSED = 1,
} PMU_BM_ButtonState_t;

/**
 * @brief LED color
 */
typedef enum {
    PMU_BM_LED_OFF = 0,
    PMU_BM_LED_RED = 1,
    PMU_BM_LED_GREEN = 2,
    PMU_BM_LED_AMBER = 3,       /* Red + Green = Amber/Yellow */
    PMU_BM_LED_BLUE = 4,        /* If supported */
    PMU_BM_LED_WHITE = 7,       /* All colors */
} PMU_BM_LedColor_t;

/**
 * @brief LED mode
 */
typedef enum {
    PMU_BM_LED_MODE_OFF = 0,
    PMU_BM_LED_MODE_ON = 1,
    PMU_BM_LED_MODE_BLINK_SLOW = 2,
    PMU_BM_LED_MODE_BLINK_FAST = 3,
} PMU_BM_LedMode_t;

/**
 * @brief LED control mode (how LEDs are controlled)
 */
typedef enum {
    PMU_BM_LED_CTRL_MANUAL = 0,     /* LED controlled by channel value */
    PMU_BM_LED_CTRL_FOLLOW = 1,     /* LED follows button state */
    PMU_BM_LED_CTRL_TOGGLE = 2,     /* LED toggles on press */
} PMU_BM_LedCtrlMode_t;

/**
 * @brief Button configuration
 */
typedef struct {
    char channel_id[32];            /* Output channel ID (button state maps to this) */
    uint8_t enabled;                /* Button enabled flag */
    PMU_BM_LedColor_t led_on_color;  /* LED color when ON */
    PMU_BM_LedColor_t led_off_color; /* LED color when OFF */
    PMU_BM_LedCtrlMode_t led_mode;   /* LED control mode */
    /* Runtime state */
    uint8_t state;                  /* Current button state (0=released, 1=pressed) */
    uint8_t led_state;              /* Current LED state */
    uint16_t virtual_channel;       /* Resolved virtual channel index */
} PMU_BM_ButtonConfig_t;

/**
 * @brief BlinkMarine keypad configuration
 */
typedef struct {
    char id[32];                    /* Unique keypad identifier */
    char name[32];                  /* Human-readable name */
    PMU_BlinkMarine_Type_t type;    /* Keypad type (2x6 or 2x8) */
    PMU_CAN_Bus_t can_bus;          /* CAN bus (1-4) */
    uint32_t rx_base_id;            /* Base CAN ID for button events (from keypad) */
    uint32_t tx_base_id;            /* Base CAN ID for LED control (to keypad) */
    uint8_t enabled;                /* Keypad enabled flag */
    PMU_BM_ButtonConfig_t buttons[16];  /* Button configurations (max 16 for 2x8) */
    /* Runtime state */
    uint32_t last_rx_tick;          /* Last message received timestamp */
    uint8_t online;                 /* Keypad online status */
} PMU_BlinkMarine_Keypad_t;

/* Exported constants --------------------------------------------------------*/

#define PMU_BM_MAX_KEYPADS          4       /* Maximum number of keypads */
#define PMU_BM_MAX_BUTTONS_2X6      12      /* Buttons in 2x6 keypad */
#define PMU_BM_MAX_BUTTONS_2X8      16      /* Buttons in 2x8 keypad */
#define PMU_BM_TIMEOUT_MS           1000    /* Keypad communication timeout */

/* Default CAN IDs (BlinkMarine standard) */
#define PMU_BM_DEFAULT_RX_ID        0x100   /* Button events from keypad */
#define PMU_BM_DEFAULT_TX_ID        0x101   /* LED control to keypad */

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize BlinkMarine keypad subsystem
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_Init(void);

/**
 * @brief Update BlinkMarine keypads (call periodically)
 *
 * Processes button states, updates LEDs, and checks timeouts.
 */
void PMU_BlinkMarine_Update(void);

/**
 * @brief Add a BlinkMarine keypad
 * @param keypad Keypad configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_AddKeypad(PMU_BlinkMarine_Keypad_t* keypad);

/**
 * @brief Remove a BlinkMarine keypad by ID
 * @param keypad_id Keypad ID
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_RemoveKeypad(const char* keypad_id);

/**
 * @brief Get keypad by ID
 * @param keypad_id Keypad ID
 * @retval Pointer to keypad or NULL
 */
PMU_BlinkMarine_Keypad_t* PMU_BlinkMarine_GetKeypad(const char* keypad_id);

/**
 * @brief Get keypad by index
 * @param index Keypad index (0 to count-1)
 * @retval Pointer to keypad or NULL
 */
PMU_BlinkMarine_Keypad_t* PMU_BlinkMarine_GetKeypadByIndex(uint8_t index);

/**
 * @brief Get number of configured keypads
 * @retval Number of keypads
 */
uint8_t PMU_BlinkMarine_GetKeypadCount(void);

/**
 * @brief Clear all keypads
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_ClearKeypads(void);

/**
 * @brief Handle received CAN message from keypad
 * @param bus CAN bus
 * @param can_id CAN message ID
 * @param data Message data
 * @param dlc Data length
 * @retval 1 if message was handled, 0 otherwise
 */
uint8_t PMU_BlinkMarine_HandleRxMessage(PMU_CAN_Bus_t bus, uint32_t can_id,
                                         uint8_t* data, uint8_t dlc);

/**
 * @brief Set LED state for a button
 * @param keypad_id Keypad ID
 * @param button_idx Button index (0-15)
 * @param color LED color
 * @param mode LED mode (on/off/blink)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_SetLed(const char* keypad_id, uint8_t button_idx,
                                          PMU_BM_LedColor_t color, PMU_BM_LedMode_t mode);

/**
 * @brief Set all LEDs on a keypad
 * @param keypad_id Keypad ID
 * @param colors Array of LED colors (one per button)
 * @param modes Array of LED modes (one per button)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_SetAllLeds(const char* keypad_id,
                                              PMU_BM_LedColor_t* colors,
                                              PMU_BM_LedMode_t* modes);

/**
 * @brief Get button state
 * @param keypad_id Keypad ID
 * @param button_idx Button index (0-15)
 * @retval Button state (0=released, 1=pressed)
 */
uint8_t PMU_BlinkMarine_GetButtonState(const char* keypad_id, uint8_t button_idx);

/**
 * @brief Check if keypad is online
 * @param keypad_id Keypad ID
 * @retval 1 if online, 0 if offline
 */
uint8_t PMU_BlinkMarine_IsOnline(const char* keypad_id);

/**
 * @brief Send LED update to keypad via CAN
 * @param keypad Keypad pointer
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_SendLedUpdate(PMU_BlinkMarine_Keypad_t* keypad);

/**
 * @brief Get number of buttons for keypad type
 * @param type Keypad type
 * @retval Number of buttons
 */
static inline uint8_t PMU_BlinkMarine_GetButtonCount(PMU_BlinkMarine_Type_t type) {
    return (type == PMU_BLINKMARINE_2X6) ? PMU_BM_MAX_BUTTONS_2X6 : PMU_BM_MAX_BUTTONS_2X8;
}

/**
 * @brief Simulate button press/release (for emulator)
 * @param keypad_idx Keypad index (0-3)
 * @param button_idx Button index (0-15)
 * @param pressed 1 for press, 0 for release
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_SimulateButton(uint8_t keypad_idx, uint8_t button_idx, uint8_t pressed);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_BLINKMARINE_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
