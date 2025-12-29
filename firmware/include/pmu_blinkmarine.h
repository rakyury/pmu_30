/**
 ******************************************************************************
 * @file           : pmu_blinkmarine.h
 * @brief          : BlinkMarine CAN Keypad Support (CANopen Protocol)
 * @author         : R2 m-sport
 * @date           : 2025-12-29
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * Supports BlinkMarine PKP series keypads via CANopen protocol:
 * - PKP-2600-SI: 2x6 (12 buttons)
 * - PKP-2800-SI: 2x8 (16 buttons)
 *
 * CANopen Communication:
 * - TPDO1 (0x180 + NodeID): Button states from keypad
 * - RPDO1 (0x200 + NodeID): LED control to keypad
 * - Heartbeat (0x700 + NodeID): Node monitoring
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
    PMU_BLINKMARINE_PKP2600SI = 0,  /* PKP-2600-SI: 12 buttons (2x6) */
    PMU_BLINKMARINE_PKP2800SI = 1,  /* PKP-2800-SI: 16 buttons (2x8) */
} PMU_BlinkMarine_Type_t;

/**
 * @brief LED color
 */
typedef enum {
    PMU_BM_LED_OFF = 0,
    PMU_BM_LED_RED = 1,
    PMU_BM_LED_GREEN = 2,
    PMU_BM_LED_BLUE = 3,
    PMU_BM_LED_YELLOW = 4,
    PMU_BM_LED_CYAN = 5,
    PMU_BM_LED_MAGENTA = 6,
    PMU_BM_LED_WHITE = 7,
} PMU_BM_LedColor_t;

/**
 * @brief LED state/mode
 */
typedef enum {
    PMU_BM_LED_STATE_OFF = 0,
    PMU_BM_LED_STATE_ON = 1,
    PMU_BM_LED_STATE_BLINK = 2,
} PMU_BM_LedState_t;

/**
 * @brief LED control mode
 */
typedef enum {
    PMU_BM_LED_CTRL_OFF = 0,        /* LED always off */
    PMU_BM_LED_CTRL_FOLLOW = 1,     /* LED follows button state */
    PMU_BM_LED_CTRL_CHANNEL = 2,    /* LED controlled by channel value */
    PMU_BM_LED_CTRL_TOGGLE = 3,     /* LED toggles on press */
} PMU_BM_LedCtrlMode_t;

/**
 * @brief Button configuration
 */
typedef struct {
    uint8_t enabled;                    /* Button enabled flag */
    PMU_BM_LedColor_t led_on_color;     /* LED color when ON */
    PMU_BM_LedColor_t led_off_color;    /* LED color when OFF */
    PMU_BM_LedCtrlMode_t led_ctrl_mode; /* LED control mode */
    char led_channel_name[32];          /* Channel name for LED control */
    /* Runtime state */
    uint8_t state;                      /* Current button state */
    uint8_t prev_state;                 /* Previous state (edge detection) */
    PMU_BM_LedColor_t current_led;      /* Current LED color */
    uint16_t virtual_channel_id;        /* Channel ID for button state */
    uint16_t led_channel_id;            /* Channel ID for LED control */
} PMU_BM_ButtonConfig_t;

/**
 * @brief BlinkMarine keypad configuration (CANopen)
 */
typedef struct {
    char name[32];                      /* Unique identifier */
    PMU_BlinkMarine_Type_t type;        /* Keypad type */
    PMU_CAN_Bus_t can_bus;              /* CAN bus (1-4) */
    uint8_t node_id;                    /* CANopen Node ID (1-127) */
    uint16_t timeout_ms;                /* Communication timeout */
    uint8_t enabled;                    /* Keypad enabled flag */
    uint8_t led_brightness;             /* LED brightness (0-100%) */
    PMU_BM_ButtonConfig_t buttons[16];  /* Button configurations */
    /* Runtime state */
    uint32_t last_rx_tick;              /* Last message timestamp */
    uint8_t online;                     /* Keypad online status */
    uint8_t led_update_needed;          /* LED update flag */
} PMU_BlinkMarine_Keypad_t;

/* Exported constants --------------------------------------------------------*/

#define PMU_BM_MAX_KEYPADS          4       /* Maximum keypads */
#define PMU_BM_MAX_BUTTONS_2X6      12      /* PKP2600SI buttons */
#define PMU_BM_MAX_BUTTONS_2X8      16      /* PKP2800SI buttons */
#define PMU_BM_DEFAULT_TIMEOUT_MS   1000    /* Default timeout */

/* CANopen COB-ID bases */
#define PMU_BM_CANOPEN_TPDO1_BASE   0x180   /* TPDO1: button states */
#define PMU_BM_CANOPEN_RPDO1_BASE   0x200   /* RPDO1: LED control */
#define PMU_BM_CANOPEN_HEARTBEAT    0x700   /* Heartbeat */

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize BlinkMarine keypad subsystem
 */
HAL_StatusTypeDef PMU_BlinkMarine_Init(void);

/**
 * @brief Update BlinkMarine keypads (call periodically)
 */
void PMU_BlinkMarine_Update(void);

/**
 * @brief Add a BlinkMarine keypad
 */
HAL_StatusTypeDef PMU_BlinkMarine_AddKeypad(PMU_BlinkMarine_Keypad_t* keypad);

/**
 * @brief Remove a BlinkMarine keypad by name
 */
HAL_StatusTypeDef PMU_BlinkMarine_RemoveKeypad(const char* name);

/**
 * @brief Get keypad by name
 */
PMU_BlinkMarine_Keypad_t* PMU_BlinkMarine_GetKeypad(const char* name);

/**
 * @brief Get keypad by index
 */
PMU_BlinkMarine_Keypad_t* PMU_BlinkMarine_GetKeypadByIndex(uint8_t index);

/**
 * @brief Get number of configured keypads
 */
uint8_t PMU_BlinkMarine_GetKeypadCount(void);

/**
 * @brief Clear all keypads
 */
HAL_StatusTypeDef PMU_BlinkMarine_ClearKeypads(void);

/**
 * @brief Handle received CAN message (CANopen TPDO)
 * @param bus CAN bus
 * @param can_id CAN message ID (11-bit standard)
 * @param data Message data
 * @param dlc Data length
 * @return 1 if handled, 0 otherwise
 */
uint8_t PMU_BlinkMarine_HandleRxMessage(PMU_CAN_Bus_t bus, uint32_t can_id,
                                        uint8_t* data, uint8_t dlc);

/**
 * @brief Set LED state for a button
 */
HAL_StatusTypeDef PMU_BlinkMarine_SetLed(PMU_BlinkMarine_Keypad_t* keypad,
                                         uint8_t button_idx,
                                         PMU_BM_LedColor_t color,
                                         PMU_BM_LedState_t state);

/**
 * @brief Send LED update via CANopen RPDO
 */
HAL_StatusTypeDef PMU_BlinkMarine_SendLedUpdate(PMU_BlinkMarine_Keypad_t* keypad);

/**
 * @brief Get button state
 */
uint8_t PMU_BlinkMarine_GetButtonState(PMU_BlinkMarine_Keypad_t* keypad, uint8_t button_idx);

/**
 * @brief Check if keypad is online
 */
uint8_t PMU_BlinkMarine_IsOnline(PMU_BlinkMarine_Keypad_t* keypad);

/**
 * @brief Get button count for keypad type
 */
static inline uint8_t PMU_BlinkMarine_GetButtonCount(PMU_BlinkMarine_Type_t type) {
    return (type == PMU_BLINKMARINE_PKP2600SI) ? PMU_BM_MAX_BUTTONS_2X6 : PMU_BM_MAX_BUTTONS_2X8;
}

/**
 * @brief Simulate button press/release (for emulator)
 */
HAL_StatusTypeDef PMU_BlinkMarine_SimulateButton(uint8_t keypad_idx, uint8_t button_idx, uint8_t pressed);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_BLINKMARINE_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
