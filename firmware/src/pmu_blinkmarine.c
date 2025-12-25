/**
 ******************************************************************************
 * @file           : pmu_blinkmarine.c
 * @brief          : BlinkMarine CAN Keypad Implementation (PKP-2600-SI J1939)
 * @author         : R2 m-sport
 * @date           : 2025-12-25
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * Protocol Reference: PKP2600SI J1939 User Manual Rev 1.5
 *
 * Key Contact State message format:
 *   Byte 0: 04h (header)
 *   Byte 1: 1Bh (header)
 *   Byte 2: 01h (command - key contact state)
 *   Byte 3: Key number (01h-0Ch for 12 buttons)
 *   Byte 4: State (00h=released, 01h=pressed)
 *   Byte 5: Keypad identifier (default 21h)
 *   Byte 6-7: FFh (not used)
 *
 * LED Single State command format:
 *   Byte 0: 04h (header)
 *   Byte 1: 1Bh (header)
 *   Byte 2: 01h (command - set single LED)
 *   Byte 3: Key number (01h-0Ch)
 *   Byte 4: LED color (00h-09h)
 *   Byte 5: LED state (00h=off, 01h=on, 02h=blink, 03h=alt blink)
 *   Byte 6: Secondary color (for alt blink)
 *   Byte 7: FFh (not used)
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_blinkmarine.h"
#include "pmu_channel.h"
#include "pmu_logging.h"
#include <string.h>
#include <stdio.h>

/* Logging macros */
#ifndef PMU_LOG_DEBUG
#define PMU_LOG_DEBUG(source, fmt, ...) ((void)0)
#endif
#ifndef PMU_LOG_INFO
#define PMU_LOG_INFO(source, fmt, ...) ((void)0)
#endif
#ifndef PMU_LOG_WARN
#define PMU_LOG_WARN(source, fmt, ...) ((void)0)
#endif
#ifndef PMU_LOG_ERROR
#define PMU_LOG_ERROR(source, fmt, ...) ((void)0)
#endif

/* Private variables ---------------------------------------------------------*/
static PMU_BlinkMarine_Keypad_t s_keypads[PMU_BM_MAX_KEYPADS];
static uint8_t s_keypad_count = 0;
static uint32_t s_last_led_update_tick = 0;

/* LED update interval in ms */
#define LED_UPDATE_INTERVAL_MS  100

/* Our source address for CAN messages (PMU as master) */
#define PMU_CAN_SOURCE_ADDR     0x00

/* Private function prototypes -----------------------------------------------*/
static void ProcessButtonEvent(PMU_BlinkMarine_Keypad_t* keypad, uint8_t key_num, uint8_t pressed);
static void ProcessHeartbeat(PMU_BlinkMarine_Keypad_t* keypad, uint8_t* data, uint8_t dlc);
static void UpdateKeypadLeds(PMU_BlinkMarine_Keypad_t* keypad);
static void CheckKeypadTimeout(PMU_BlinkMarine_Keypad_t* keypad);
static HAL_StatusTypeDef SendSingleLedCommand(PMU_BlinkMarine_Keypad_t* keypad, uint8_t button_idx);
static uint8_t ExtractSourceAddress(uint32_t can_id);

/* Exported functions --------------------------------------------------------*/

HAL_StatusTypeDef PMU_BlinkMarine_Init(void)
{
    memset(s_keypads, 0, sizeof(s_keypads));
    s_keypad_count = 0;
    s_last_led_update_tick = 0;

    PMU_LOG_INFO("BlinkMarine", "Keypad subsystem initialized (J1939 protocol)");
    return HAL_OK;
}

void PMU_BlinkMarine_Update(void)
{
    uint32_t now = HAL_GetTick();

    for (uint8_t i = 0; i < s_keypad_count; i++) {
        PMU_BlinkMarine_Keypad_t* keypad = &s_keypads[i];
        if (!keypad->enabled) continue;

        /* Check communication timeout */
        CheckKeypadTimeout(keypad);

        /* Update LEDs based on channel values or control mode */
        UpdateKeypadLeds(keypad);
    }

    /* Send LED updates periodically */
    if (now - s_last_led_update_tick >= LED_UPDATE_INTERVAL_MS) {
        s_last_led_update_tick = now;

        for (uint8_t i = 0; i < s_keypad_count; i++) {
            PMU_BlinkMarine_Keypad_t* keypad = &s_keypads[i];
            if (keypad->enabled && keypad->online && keypad->led_update_needed) {
                PMU_BlinkMarine_SendLedUpdate(keypad);
                keypad->led_update_needed = 0;
            }
        }
    }
}

HAL_StatusTypeDef PMU_BlinkMarine_AddKeypad(PMU_BlinkMarine_Keypad_t* keypad)
{
    if (!keypad) return HAL_ERROR;
    if (s_keypad_count >= PMU_BM_MAX_KEYPADS) {
        PMU_LOG_ERROR("BlinkMarine", "Max keypads reached (%d)", PMU_BM_MAX_KEYPADS);
        return HAL_ERROR;
    }

    /* Check for duplicate name */
    for (uint8_t i = 0; i < s_keypad_count; i++) {
        if (strcmp(s_keypads[i].name, keypad->name) == 0) {
            PMU_LOG_ERROR("BlinkMarine", "Duplicate keypad name: %s", keypad->name);
            return HAL_ERROR;
        }
    }

    /* Copy keypad configuration */
    memcpy(&s_keypads[s_keypad_count], keypad, sizeof(PMU_BlinkMarine_Keypad_t));
    PMU_BlinkMarine_Keypad_t* kp = &s_keypads[s_keypad_count];

    /* Set defaults if not specified */
    if (kp->source_address == 0) kp->source_address = PMU_BM_DEFAULT_SRC_ADDR;
    if (kp->keypad_identifier == 0) kp->keypad_identifier = PMU_BM_DEFAULT_KEYPAD_ID;
    if (kp->destination_address == 0) kp->destination_address = PMU_BM_DEFAULT_DEST_ADDR;
    if (kp->timeout_ms == 0) kp->timeout_ms = PMU_BM_DEFAULT_TIMEOUT_MS;

    /* Initialize runtime state */
    kp->last_rx_tick = 0;
    kp->online = 0;
    kp->led_update_needed = 0;

    /* Resolve virtual channels for buttons */
    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
    for (uint8_t b = 0; b < button_count; b++) {
        PMU_BM_ButtonConfig_t* btn = &kp->buttons[b];
        btn->state = 0;
        btn->prev_state = 0;
        btn->current_led_color = PMU_BM_LED_OFF;
        btn->current_led_state = PMU_BM_LED_STATE_OFF;
        btn->virtual_channel_id = 0xFFFF;
        btn->led_channel_id = 0xFFFF;

        /* Auto-create virtual channel for button state */
        /* Format: "KeypadName - Button N" */
        char btn_channel_name[64];
        snprintf(btn_channel_name, sizeof(btn_channel_name), "%s - Button %d", kp->name, b + 1);
        const PMU_Channel_t* ch = PMU_Channel_GetByName(btn_channel_name);
        if (ch) {
            btn->virtual_channel_id = ch->channel_id;
        }

        /* Resolve LED control channel if in CHANNEL mode */
        if (btn->led_ctrl_mode == PMU_BM_LED_CTRL_CHANNEL && btn->led_channel_name[0]) {
            const PMU_Channel_t* led_ch = PMU_Channel_GetByName(btn->led_channel_name);
            if (led_ch) {
                btn->led_channel_id = led_ch->channel_id;
            }
        }
    }

    s_keypad_count++;
    PMU_LOG_INFO("BlinkMarine", "Added keypad '%s' (%s) CAN%d SA:0x%02X",
                 keypad->name,
                 keypad->type == PMU_BLINKMARINE_PKP2600SI ? "PKP2600SI" : "PKP2800SI",
                 keypad->can_bus,
                 keypad->source_address);

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BlinkMarine_RemoveKeypad(const char* name)
{
    if (!name) return HAL_ERROR;

    for (uint8_t i = 0; i < s_keypad_count; i++) {
        if (strcmp(s_keypads[i].name, name) == 0) {
            for (uint8_t j = i; j < s_keypad_count - 1; j++) {
                memcpy(&s_keypads[j], &s_keypads[j + 1], sizeof(PMU_BlinkMarine_Keypad_t));
            }
            s_keypad_count--;
            PMU_LOG_INFO("BlinkMarine", "Removed keypad: %s", name);
            return HAL_OK;
        }
    }
    return HAL_ERROR;
}

PMU_BlinkMarine_Keypad_t* PMU_BlinkMarine_GetKeypad(const char* name)
{
    if (!name) return NULL;
    for (uint8_t i = 0; i < s_keypad_count; i++) {
        if (strcmp(s_keypads[i].name, name) == 0) {
            return &s_keypads[i];
        }
    }
    return NULL;
}

PMU_BlinkMarine_Keypad_t* PMU_BlinkMarine_GetKeypadByIndex(uint8_t index)
{
    if (index >= s_keypad_count) return NULL;
    return &s_keypads[index];
}

uint8_t PMU_BlinkMarine_GetKeypadCount(void)
{
    return s_keypad_count;
}

HAL_StatusTypeDef PMU_BlinkMarine_ClearKeypads(void)
{
    memset(s_keypads, 0, sizeof(s_keypads));
    s_keypad_count = 0;
    PMU_LOG_INFO("BlinkMarine", "Cleared all keypads");
    return HAL_OK;
}

uint8_t PMU_BlinkMarine_HandleRxMessage(PMU_CAN_Bus_t bus, uint32_t can_id,
                                         uint8_t is_extended, uint8_t* data, uint8_t dlc)
{
    if (dlc < 3) return 0;  /* Minimum message size */

    /* Check each keypad */
    for (uint8_t i = 0; i < s_keypad_count; i++) {
        PMU_BlinkMarine_Keypad_t* keypad = &s_keypads[i];
        if (!keypad->enabled) continue;
        if (keypad->can_bus != bus) continue;

        /* For J1939, check if message is from this keypad */
        if (keypad->use_extended_id && is_extended) {
            /* Extract source address from CAN ID (lowest 8 bits) */
            uint8_t src_addr = ExtractSourceAddress(can_id);
            if (src_addr != keypad->source_address) continue;

            /* Check PGN (bits 8-23 of CAN ID) */
            uint16_t pgn = (can_id >> 8) & 0xFFFF;
            if (pgn != PMU_BM_J1939_PGN_PROP_A) continue;

            /* Validate BlinkMarine header */
            if (data[0] != PMU_BM_HEADER_BYTE0 || data[1] != PMU_BM_HEADER_BYTE1) continue;

            keypad->last_rx_tick = HAL_GetTick();
            keypad->online = 1;

            /* Parse command */
            uint8_t cmd = data[2];

            if (cmd == PMU_BM_CMD_KEY_STATE && dlc >= 6) {
                /* Key contact state message:
                 * data[3] = Key number (1-12/16)
                 * data[4] = State (0=released, 1=pressed)
                 * data[5] = Keypad identifier
                 */
                uint8_t key_num = data[3];
                uint8_t state = data[4];
                uint8_t kp_id = data[5];

                /* Validate keypad identifier */
                if (kp_id == keypad->keypad_identifier) {
                    ProcessButtonEvent(keypad, key_num, state);
                }
                return 1;
            }
            else if (cmd == PMU_BM_CMD_HEARTBEAT_MSG && dlc >= 8) {
                /* Heartbeat message with button states */
                ProcessHeartbeat(keypad, data, dlc);
                return 1;
            }
        }
        else if (!keypad->use_extended_id && !is_extended) {
            /* Standard 11-bit CAN ID mode (legacy/custom) */
            /* This mode is not standard BlinkMarine but kept for compatibility */
            /* Not implemented for real PKP2600SI */
        }
    }

    return 0;
}

HAL_StatusTypeDef PMU_BlinkMarine_SetLed(PMU_BlinkMarine_Keypad_t* keypad,
                                          uint8_t button_idx,
                                          PMU_BM_LedColor_t color,
                                          PMU_BM_LedState_t state,
                                          PMU_BM_LedColor_t secondary)
{
    if (!keypad) return HAL_ERROR;

    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
    if (button_idx >= button_count) return HAL_ERROR;

    PMU_BM_ButtonConfig_t* btn = &keypad->buttons[button_idx];
    btn->current_led_color = color;
    btn->current_led_state = state;
    btn->led_secondary = secondary;
    keypad->led_update_needed = 1;

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BlinkMarine_SendLedUpdate(PMU_BlinkMarine_Keypad_t* keypad)
{
    if (!keypad || !keypad->enabled) return HAL_ERROR;

    /* Send single LED commands for each button that needs update */
    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
    for (uint8_t b = 0; b < button_count; b++) {
        SendSingleLedCommand(keypad, b);
    }

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BlinkMarine_SetLedBrightness(PMU_BlinkMarine_Keypad_t* keypad,
                                                    uint8_t brightness)
{
    if (!keypad) return HAL_ERROR;

    /* Build J1939 CAN ID */
    uint32_t can_id = PMU_BlinkMarine_BuildTxCanId(keypad->source_address, PMU_CAN_SOURCE_ADDR);

    /* Build LED brightness command: 04 1B 02 XX FF FF FF FF */
    uint8_t data[8] = {
        PMU_BM_HEADER_BYTE0,
        PMU_BM_HEADER_BYTE1,
        PMU_BM_CMD_LED_BRIGHTNESS,
        brightness & 0x3F,  /* Limit to 0-63 */
        0xFF, 0xFF, 0xFF, 0xFF
    };

    return PMU_CAN_SendExtended(keypad->can_bus, can_id, data, 8);
}

HAL_StatusTypeDef PMU_BlinkMarine_SetBacklight(PMU_BlinkMarine_Keypad_t* keypad,
                                                uint8_t brightness)
{
    if (!keypad) return HAL_ERROR;

    uint32_t can_id = PMU_BlinkMarine_BuildTxCanId(keypad->source_address, PMU_CAN_SOURCE_ADDR);

    /* Build backlight command: 04 1B 03 XX FF FF FF FF */
    uint8_t data[8] = {
        PMU_BM_HEADER_BYTE0,
        PMU_BM_HEADER_BYTE1,
        PMU_BM_CMD_BACKLIGHT,
        brightness & 0x3F,
        0xFF, 0xFF, 0xFF, 0xFF
    };

    return PMU_CAN_SendExtended(keypad->can_bus, can_id, data, 8);
}

uint8_t PMU_BlinkMarine_GetButtonState(PMU_BlinkMarine_Keypad_t* keypad, uint8_t button_idx)
{
    if (!keypad) return 0;
    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
    if (button_idx >= button_count) return 0;
    return keypad->buttons[button_idx].state;
}

uint8_t PMU_BlinkMarine_IsOnline(PMU_BlinkMarine_Keypad_t* keypad)
{
    if (!keypad) return 0;
    return keypad->online;
}

/* Private functions ---------------------------------------------------------*/

static uint8_t ExtractSourceAddress(uint32_t can_id)
{
    /* J1939 29-bit ID format: SA is the lowest 8 bits */
    return can_id & 0xFF;
}

static void ProcessButtonEvent(PMU_BlinkMarine_Keypad_t* keypad, uint8_t key_num, uint8_t pressed)
{
    /* Key numbers are 1-based in protocol, convert to 0-based index */
    if (key_num < 1 || key_num > 16) return;
    uint8_t button_idx = key_num - 1;

    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
    if (button_idx >= button_count) return;

    PMU_BM_ButtonConfig_t* btn = &keypad->buttons[button_idx];
    btn->prev_state = btn->state;
    btn->state = pressed ? 1 : 0;

    PMU_LOG_DEBUG("BlinkMarine", "%s Key%d: %s",
                  keypad->name, key_num, pressed ? "PRESSED" : "RELEASED");

    /* Update virtual channel for button state */
    if (btn->virtual_channel_id != 0xFFFF) {
        PMU_Channel_SetValue(btn->virtual_channel_id, btn->state);
    }

    /* Update LED based on control mode */
    if (btn->led_ctrl_mode == PMU_BM_LED_CTRL_FOLLOW) {
        /* LED follows button state */
        if (btn->state) {
            btn->current_led_color = btn->led_on_color;
            btn->current_led_state = PMU_BM_LED_STATE_ON;
        } else {
            btn->current_led_color = btn->led_off_color;
            btn->current_led_state = (btn->led_off_color == PMU_BM_LED_OFF) ?
                                      PMU_BM_LED_STATE_OFF : PMU_BM_LED_STATE_ON;
        }
        keypad->led_update_needed = 1;
    }
    else if (btn->led_ctrl_mode == PMU_BM_LED_CTRL_TOGGLE && pressed && !btn->prev_state) {
        /* Toggle LED on press (rising edge only) */
        if (btn->current_led_state == PMU_BM_LED_STATE_OFF ||
            btn->current_led_color == btn->led_off_color) {
            btn->current_led_color = btn->led_on_color;
            btn->current_led_state = PMU_BM_LED_STATE_ON;
        } else {
            btn->current_led_color = btn->led_off_color;
            btn->current_led_state = (btn->led_off_color == PMU_BM_LED_OFF) ?
                                      PMU_BM_LED_STATE_OFF : PMU_BM_LED_STATE_ON;
        }
        keypad->led_update_needed = 1;
    }
}

static void ProcessHeartbeat(PMU_BlinkMarine_Keypad_t* keypad, uint8_t* data, uint8_t dlc)
{
    /* Heartbeat message format:
     * data[0]: 04h
     * data[1]: 1Bh
     * data[2]: F9h (heartbeat command)
     * data[3]: Message counter
     * data[4]: K8-K1 button states (bit = pressed)
     * data[5]: K12-K9 button states
     * data[6]: FFh
     * data[7]: Keypad identifier
     */
    if (dlc < 8) return;
    if (data[7] != keypad->keypad_identifier) return;

    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
    uint16_t button_mask = data[4] | ((uint16_t)data[5] << 8);

    for (uint8_t b = 0; b < button_count; b++) {
        uint8_t pressed = (button_mask >> b) & 0x01;
        if (keypad->buttons[b].state != pressed) {
            ProcessButtonEvent(keypad, b + 1, pressed);
        }
    }
}

static void UpdateKeypadLeds(PMU_BlinkMarine_Keypad_t* keypad)
{
    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);

    for (uint8_t b = 0; b < button_count; b++) {
        PMU_BM_ButtonConfig_t* btn = &keypad->buttons[b];

        /* For CHANNEL control mode, update LED based on channel value */
        if (btn->led_ctrl_mode == PMU_BM_LED_CTRL_CHANNEL && btn->led_channel_id != 0xFFFF) {
            int32_t value = PMU_Channel_GetValue(btn->led_channel_id);
            PMU_BM_LedColor_t new_color;
            PMU_BM_LedState_t new_state;

            if (value > 0) {
                new_color = btn->led_on_color;
                new_state = PMU_BM_LED_STATE_ON;
            } else {
                new_color = btn->led_off_color;
                new_state = (btn->led_off_color == PMU_BM_LED_OFF) ?
                            PMU_BM_LED_STATE_OFF : PMU_BM_LED_STATE_ON;
            }

            if (new_color != btn->current_led_color || new_state != btn->current_led_state) {
                btn->current_led_color = new_color;
                btn->current_led_state = new_state;
                keypad->led_update_needed = 1;
            }
        }
    }
}

static void CheckKeypadTimeout(PMU_BlinkMarine_Keypad_t* keypad)
{
    if (!keypad->online) return;

    uint32_t now = HAL_GetTick();
    if (now - keypad->last_rx_tick > keypad->timeout_ms) {
        keypad->online = 0;
        PMU_LOG_WARN("BlinkMarine", "Keypad '%s' timeout - offline", keypad->name);

        /* Reset all button states on timeout */
        uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
        for (uint8_t b = 0; b < button_count; b++) {
            if (keypad->buttons[b].state != 0) {
                ProcessButtonEvent(keypad, b + 1, 0);
            }
        }
    }
}

static HAL_StatusTypeDef SendSingleLedCommand(PMU_BlinkMarine_Keypad_t* keypad, uint8_t button_idx)
{
    PMU_BM_ButtonConfig_t* btn = &keypad->buttons[button_idx];

    /* Build J1939 CAN ID for LED command */
    uint32_t can_id = PMU_BlinkMarine_BuildTxCanId(keypad->source_address, PMU_CAN_SOURCE_ADDR);

    /* Build single LED state command:
     * Byte 0: 04h (header)
     * Byte 1: 1Bh (header)
     * Byte 2: 01h (set single LED state)
     * Byte 3: Key number (1-based)
     * Byte 4: LED color
     * Byte 5: LED state
     * Byte 6: Secondary color (for alt blink)
     * Byte 7: FFh
     */
    uint8_t data[8] = {
        PMU_BM_HEADER_BYTE0,
        PMU_BM_HEADER_BYTE1,
        0x01,  /* LED command (same as key state for single LED) */
        button_idx + 1,  /* Key number (1-based) */
        btn->current_led_color,
        btn->current_led_state,
        btn->led_secondary,
        0xFF
    };

    return PMU_CAN_SendExtended(keypad->can_bus, can_id, data, 8);
}

HAL_StatusTypeDef PMU_BlinkMarine_SimulateButton(uint8_t keypad_idx, uint8_t button_idx, uint8_t pressed)
{
    if (keypad_idx >= s_keypad_count) {
        return HAL_ERROR;
    }

    PMU_BlinkMarine_Keypad_t* keypad = &s_keypads[keypad_idx];
    if (!keypad->enabled) {
        return HAL_ERROR;
    }

    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
    if (button_idx >= button_count) {
        return HAL_ERROR;
    }

    /* Mark keypad as online (simulated) */
    keypad->online = 1;
    keypad->last_rx_tick = HAL_GetTick();

    /* Process the button state change (key_num is 1-based) */
    ProcessButtonEvent(keypad, button_idx + 1, pressed ? 1 : 0);

    PMU_LOG_INFO("BlinkMarine", "Simulated button %d %s on keypad '%s'",
                 button_idx + 1, pressed ? "PRESS" : "RELEASE", keypad->name);

    return HAL_OK;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
