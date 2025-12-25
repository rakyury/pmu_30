/**
 ******************************************************************************
 * @file           : pmu_blinkmarine.h
 * @brief          : BlinkMarine CAN Keypad Support (PKP-2600-SI J1939)
 * @author         : R2 m-sport
 * @date           : 2025-12-25
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * Supports BlinkMarine PKP series keypads with J1939 protocol:
 * - PKP-2600-SI: 2x6 (12 buttons)
 * - PKP-2800-SI: 2x8 (16 buttons) - assumed similar protocol
 *
 * Protocol Reference: PKP2600SI J1939 User Manual Rev 1.5
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
    PMU_BLINKMARINE_PKP2600SI = 0,  /* PKP-2600-SI: 12 buttons (2x6) J1939 */
    PMU_BLINKMARINE_PKP2800SI = 1,  /* PKP-2800-SI: 16 buttons (2x8) J1939 - assumed */
} PMU_BlinkMarine_Type_t;

/**
 * @brief Button state
 */
typedef enum {
    PMU_BM_BTN_RELEASED = 0,
    PMU_BM_BTN_PRESSED = 1,
} PMU_BM_ButtonState_t;

/**
 * @brief LED color (from PKP2600SI manual)
 */
typedef enum {
    PMU_BM_LED_OFF = 0x00,
    PMU_BM_LED_RED = 0x01,
    PMU_BM_LED_GREEN = 0x02,
    PMU_BM_LED_BLUE = 0x03,
    PMU_BM_LED_YELLOW = 0x04,
    PMU_BM_LED_CYAN = 0x05,
    PMU_BM_LED_MAGENTA = 0x06,
    PMU_BM_LED_WHITE = 0x07,
    PMU_BM_LED_AMBER = 0x08,
    PMU_BM_LED_YELLOW_GREEN = 0x09,
} PMU_BM_LedColor_t;

/**
 * @brief LED state/mode (from PKP2600SI manual)
 */
typedef enum {
    PMU_BM_LED_STATE_OFF = 0x00,
    PMU_BM_LED_STATE_ON = 0x01,
    PMU_BM_LED_STATE_BLINK = 0x02,
    PMU_BM_LED_STATE_ALT_BLINK = 0x03,
} PMU_BM_LedState_t;

/**
 * @brief LED control mode (how LEDs are controlled by PMU)
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
    PMU_BM_LedColor_t led_off_color;    /* LED color when OFF (0=off) */
    PMU_BM_LedColor_t led_secondary;    /* Secondary color for alt blink */
    PMU_BM_LedCtrlMode_t led_ctrl_mode; /* LED control mode */
    char led_channel_name[32];          /* Channel name for LED control (if CHANNEL mode) */
    /* Runtime state */
    uint8_t state;                      /* Current button state (0=released, 1=pressed) */
    uint8_t prev_state;                 /* Previous button state (for edge detection) */
    PMU_BM_LedColor_t current_led_color;/* Current LED color being displayed */
    PMU_BM_LedState_t current_led_state;/* Current LED state being displayed */
    uint16_t virtual_channel_id;        /* Resolved channel_id for button state */
    uint16_t led_channel_id;            /* Resolved channel_id for LED control */
} PMU_BM_ButtonConfig_t;

/**
 * @brief BlinkMarine keypad configuration
 */
typedef struct {
    char name[32];                      /* Human-readable name (unique identifier) */
    PMU_BlinkMarine_Type_t type;        /* Keypad type (PKP2600SI, PKP2800SI) */
    PMU_CAN_Bus_t can_bus;              /* CAN bus (1-4) */
    uint8_t source_address;             /* Keypad CAN source address (default 0x21) */
    uint8_t keypad_identifier;          /* Keypad identifier (default 0x21) */
    uint8_t destination_address;        /* Our address for receiving (default 0xFF=broadcast) */
    uint8_t use_extended_id;            /* Use 29-bit extended CAN IDs (J1939) */
    uint16_t timeout_ms;                /* Communication timeout in ms */
    uint8_t enabled;                    /* Keypad enabled flag */
    uint8_t led_brightness;             /* LED brightness 0x00-0x3F (0-100%) */
    uint8_t backlight_brightness;       /* Backlight brightness 0x00-0x3F */
    PMU_BM_LedColor_t backlight_color;  /* Backlight color */
    PMU_BM_ButtonConfig_t buttons[16];  /* Button configurations (max 16 for PKP2800) */
    /* Runtime state */
    uint32_t last_rx_tick;              /* Last message received timestamp */
    uint8_t online;                     /* Keypad online status */
    uint8_t led_update_needed;          /* Flag to trigger LED update */
} PMU_BlinkMarine_Keypad_t;

/* Exported constants --------------------------------------------------------*/

#define PMU_BM_MAX_KEYPADS          4       /* Maximum number of keypads */
#define PMU_BM_MAX_BUTTONS_2X6      12      /* Buttons in PKP2600SI */
#define PMU_BM_MAX_BUTTONS_2X8      16      /* Buttons in PKP2800SI */
#define PMU_BM_DEFAULT_TIMEOUT_MS   1000    /* Default communication timeout */

/* J1939 Protocol Constants (from PKP2600SI manual) */
#define PMU_BM_J1939_PRIORITY       6       /* Message priority */
#define PMU_BM_J1939_PGN_PROP_A     0xEF00  /* PGN 61184 - Proprietary A */
#define PMU_BM_J1939_PGN_AUX_IO2    0xA700  /* PGN 42752 - Multiple LED color 1 */
#define PMU_BM_J1939_PGN_AUX_IO3    0xA600  /* PGN 42496 - Multiple LED color 2 */

/* BlinkMarine Protocol Constants */
#define PMU_BM_HEADER_BYTE0         0x04
#define PMU_BM_HEADER_BYTE1         0x1B

/* Command codes (from manual) */
#define PMU_BM_CMD_KEY_STATE        0x01    /* Key contact state */
#define PMU_BM_CMD_LED_BRIGHTNESS   0x02    /* Set LED brightness */
#define PMU_BM_CMD_BACKLIGHT        0x03    /* Set backlight level */
#define PMU_BM_CMD_GET_SW_VERSION   0x2A    /* Get software version */
#define PMU_BM_CMD_SET_DEST_ADDR    0x6E    /* Set destination address */
#define PMU_BM_CMD_SET_BAUDRATE     0x6F    /* Set baud rate */
#define PMU_BM_CMD_SET_SRC_ADDR     0x70    /* Set source address */
#define PMU_BM_CMD_PERIODIC_TX      0x71    /* Periodic key-state transmission */
#define PMU_BM_CMD_EVENT_TX         0x72    /* Event state transmission */
#define PMU_BM_CMD_LED_ACK          0x73    /* LED acknowledgment */
#define PMU_BM_CMD_ADDR_CLAIM       0x74    /* Address claim at boot */
#define PMU_BM_CMD_HEARTBEAT        0x75    /* Heartbeat */
#define PMU_BM_CMD_KEYSTATE_PERIOD  0x77    /* Key-state message period */
#define PMU_BM_CMD_DEF_BACKLIGHT    0x7B    /* Default backlight brightness */
#define PMU_BM_CMD_DEF_LED_BRIGHT   0x7C    /* Default LED brightness */
#define PMU_BM_CMD_DEF_BL_COLOR     0x7D    /* Default backlight color */
#define PMU_BM_CMD_HEARTBEAT_MSG    0xF9    /* Heartbeat message from keypad */

/* Default addresses (from manual) */
#define PMU_BM_DEFAULT_SRC_ADDR     0x21    /* Default keypad source address */
#define PMU_BM_DEFAULT_KEYPAD_ID    0x21    /* Default keypad identifier */
#define PMU_BM_DEFAULT_DEST_ADDR    0xFF    /* Broadcast */

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize BlinkMarine keypad subsystem
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_Init(void);

/**
 * @brief Update BlinkMarine keypads (call periodically)
 */
void PMU_BlinkMarine_Update(void);

/**
 * @brief Add a BlinkMarine keypad
 * @param keypad Keypad configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_AddKeypad(PMU_BlinkMarine_Keypad_t* keypad);

/**
 * @brief Remove a BlinkMarine keypad by name
 * @param name Keypad name
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_RemoveKeypad(const char* name);

/**
 * @brief Get keypad by name
 * @param name Keypad name
 * @retval Pointer to keypad or NULL
 */
PMU_BlinkMarine_Keypad_t* PMU_BlinkMarine_GetKeypad(const char* name);

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
 * @param can_id CAN message ID (29-bit for J1939)
 * @param is_extended True if 29-bit ID
 * @param data Message data
 * @param dlc Data length
 * @retval 1 if message was handled, 0 otherwise
 */
uint8_t PMU_BlinkMarine_HandleRxMessage(PMU_CAN_Bus_t bus, uint32_t can_id,
                                         uint8_t is_extended, uint8_t* data, uint8_t dlc);

/**
 * @brief Set single LED state
 * @param keypad Keypad pointer
 * @param button_idx Button index (0-based, maps to key 1-12/16)
 * @param color LED color
 * @param state LED state (on/off/blink)
 * @param secondary Secondary color for alt blink
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_SetLed(PMU_BlinkMarine_Keypad_t* keypad,
                                          uint8_t button_idx,
                                          PMU_BM_LedColor_t color,
                                          PMU_BM_LedState_t state,
                                          PMU_BM_LedColor_t secondary);

/**
 * @brief Send LED update to keypad via CAN (single LED mode)
 * @param keypad Keypad pointer
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_SendLedUpdate(PMU_BlinkMarine_Keypad_t* keypad);

/**
 * @brief Send LED brightness command
 * @param keypad Keypad pointer
 * @param brightness Brightness value 0x00-0x3F
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_SetLedBrightness(PMU_BlinkMarine_Keypad_t* keypad,
                                                    uint8_t brightness);

/**
 * @brief Send backlight command
 * @param keypad Keypad pointer
 * @param brightness Brightness value 0x00-0x3F
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_BlinkMarine_SetBacklight(PMU_BlinkMarine_Keypad_t* keypad,
                                                uint8_t brightness);

/**
 * @brief Get button state
 * @param keypad Keypad pointer
 * @param button_idx Button index (0-15)
 * @retval Button state (0=released, 1=pressed)
 */
uint8_t PMU_BlinkMarine_GetButtonState(PMU_BlinkMarine_Keypad_t* keypad, uint8_t button_idx);

/**
 * @brief Check if keypad is online
 * @param keypad Keypad pointer
 * @retval 1 if online, 0 if offline
 */
uint8_t PMU_BlinkMarine_IsOnline(PMU_BlinkMarine_Keypad_t* keypad);

/**
 * @brief Get number of buttons for keypad type
 * @param type Keypad type
 * @retval Number of buttons
 */
static inline uint8_t PMU_BlinkMarine_GetButtonCount(PMU_BlinkMarine_Type_t type) {
    return (type == PMU_BLINKMARINE_PKP2600SI) ? PMU_BM_MAX_BUTTONS_2X6 : PMU_BM_MAX_BUTTONS_2X8;
}

/**
 * @brief Build J1939 CAN ID for sending to keypad
 * @param dest_addr Destination address (keypad's source address)
 * @param src_addr Our source address
 * @retval 29-bit CAN ID
 */
static inline uint32_t PMU_BlinkMarine_BuildTxCanId(uint8_t dest_addr, uint8_t src_addr) {
    /* Format: Priority(3) + R(1) + DP(1) + PF(8) + PS/DA(8) + SA(8) */
    /* 18EFxxss where xx=dest_addr, ss=src_addr */
    return (0x18EF0000UL) | ((uint32_t)dest_addr << 8) | src_addr;
}

/**
 * @brief Build J1939 CAN ID for multiple LED command (PGN A700)
 * @param dest_addr Destination address
 * @param src_addr Our source address
 * @retval 29-bit CAN ID
 */
static inline uint32_t PMU_BlinkMarine_BuildLedMultiCanId1(uint8_t dest_addr, uint8_t src_addr) {
    return (0x18A70000UL) | ((uint32_t)dest_addr << 8) | src_addr;
}

/**
 * @brief Build J1939 CAN ID for multiple LED command (PGN A600)
 */
static inline uint32_t PMU_BlinkMarine_BuildLedMultiCanId2(uint8_t dest_addr, uint8_t src_addr) {
    return (0x18A60000UL) | ((uint32_t)dest_addr << 8) | src_addr;
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
