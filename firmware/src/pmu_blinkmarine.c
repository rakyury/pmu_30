/**
 ******************************************************************************
 * @file           : pmu_blinkmarine.c
 * @brief          : BlinkMarine CAN Keypad Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_blinkmarine.h"
#include "pmu_channel.h"
#include "pmu_logging.h"
#include <string.h>

/* Logging macros - define as no-ops if not provided */
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

/* Private function prototypes -----------------------------------------------*/
static void ProcessButtonPress(PMU_BlinkMarine_Keypad_t* keypad, uint8_t button_idx, uint8_t pressed);
static void UpdateKeypadLeds(PMU_BlinkMarine_Keypad_t* keypad);
static void CheckKeypadTimeout(PMU_BlinkMarine_Keypad_t* keypad);

/* Exported functions --------------------------------------------------------*/

HAL_StatusTypeDef PMU_BlinkMarine_Init(void)
{
    memset(s_keypads, 0, sizeof(s_keypads));
    s_keypad_count = 0;
    s_last_led_update_tick = 0;

    PMU_LOG_INFO("BlinkMarine", "Keypad subsystem initialized");
    return HAL_OK;
}

void PMU_BlinkMarine_Update(void)
{
    uint32_t now = HAL_GetTick();

    /* Check timeouts and update LEDs */
    for (uint8_t i = 0; i < s_keypad_count; i++) {
        PMU_BlinkMarine_Keypad_t* keypad = &s_keypads[i];
        if (!keypad->enabled) continue;

        /* Check communication timeout */
        CheckKeypadTimeout(keypad);

        /* Update LEDs based on channel values */
        UpdateKeypadLeds(keypad);
    }

    /* Send LED updates periodically */
    if (now - s_last_led_update_tick >= LED_UPDATE_INTERVAL_MS) {
        s_last_led_update_tick = now;

        for (uint8_t i = 0; i < s_keypad_count; i++) {
            PMU_BlinkMarine_Keypad_t* keypad = &s_keypads[i];
            if (keypad->enabled && keypad->online) {
                PMU_BlinkMarine_SendLedUpdate(keypad);
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

    /* Check for duplicate ID */
    for (uint8_t i = 0; i < s_keypad_count; i++) {
        if (strcmp(s_keypads[i].id, keypad->id) == 0) {
            PMU_LOG_ERROR("BlinkMarine", "Duplicate keypad ID: %s", keypad->id);
            return HAL_ERROR;
        }
    }

    /* Copy keypad configuration */
    memcpy(&s_keypads[s_keypad_count], keypad, sizeof(PMU_BlinkMarine_Keypad_t));

    /* Initialize runtime state */
    s_keypads[s_keypad_count].last_rx_tick = 0;
    s_keypads[s_keypad_count].online = 0;

    /* Resolve virtual channels for buttons */
    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
    for (uint8_t b = 0; b < button_count; b++) {
        PMU_BM_ButtonConfig_t* btn = &s_keypads[s_keypad_count].buttons[b];
        if (btn->enabled && btn->channel_id[0] != '\0') {
            const PMU_Channel_t* ch = PMU_Channel_GetByName(btn->channel_id);
            if (ch != NULL) {
                btn->virtual_channel = ch->channel_id;
            } else {
                btn->virtual_channel = 0xFFFF;
                PMU_LOG_WARN("BlinkMarine", "Button %d: channel '%s' not found", b, btn->channel_id);
            }
        }
    }

    s_keypad_count++;
    PMU_LOG_INFO("BlinkMarine", "Added keypad '%s' (%s) on CAN%d RX:0x%03X TX:0x%03X",
                 keypad->id,
                 keypad->type == PMU_BLINKMARINE_2X6 ? "2x6" : "2x8",
                 keypad->can_bus,
                 (unsigned int)keypad->rx_base_id,
                 (unsigned int)keypad->tx_base_id);

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BlinkMarine_RemoveKeypad(const char* keypad_id)
{
    if (!keypad_id) return HAL_ERROR;

    for (uint8_t i = 0; i < s_keypad_count; i++) {
        if (strcmp(s_keypads[i].id, keypad_id) == 0) {
            /* Shift remaining keypads */
            for (uint8_t j = i; j < s_keypad_count - 1; j++) {
                memcpy(&s_keypads[j], &s_keypads[j + 1], sizeof(PMU_BlinkMarine_Keypad_t));
            }
            s_keypad_count--;
            PMU_LOG_INFO("BlinkMarine", "Removed keypad: %s", keypad_id);
            return HAL_OK;
        }
    }

    return HAL_ERROR;
}

PMU_BlinkMarine_Keypad_t* PMU_BlinkMarine_GetKeypad(const char* keypad_id)
{
    if (!keypad_id) return NULL;

    for (uint8_t i = 0; i < s_keypad_count; i++) {
        if (strcmp(s_keypads[i].id, keypad_id) == 0) {
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
                                         uint8_t* data, uint8_t dlc)
{
    /* Check each keypad for matching RX ID */
    for (uint8_t i = 0; i < s_keypad_count; i++) {
        PMU_BlinkMarine_Keypad_t* keypad = &s_keypads[i];
        if (!keypad->enabled) continue;
        if (keypad->can_bus != bus) continue;

        /* Check if CAN ID matches the keypad's RX ID range */
        /* BlinkMarine typically uses base_id + button_index for each button */
        /* Or sends all button states in a single message */

        if (can_id == keypad->rx_base_id) {
            /* Single message with all button states */
            keypad->last_rx_tick = HAL_GetTick();
            keypad->online = 1;

            /* Parse button states from data */
            /* BlinkMarine format: each bit represents a button state */
            /* Bytes 0-1: Button states (bit = 1 means pressed) */
            uint16_t button_mask = (dlc >= 2) ? (data[0] | (data[1] << 8)) : data[0];
            uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);

            for (uint8_t b = 0; b < button_count; b++) {
                uint8_t pressed = (button_mask >> b) & 0x01;
                if (keypad->buttons[b].state != pressed) {
                    ProcessButtonPress(keypad, b, pressed);
                }
            }
            return 1;
        }

        /* Alternative: Individual button messages (base_id + button_index) */
        uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
        if (can_id >= keypad->rx_base_id && can_id < keypad->rx_base_id + button_count) {
            uint8_t button_idx = can_id - keypad->rx_base_id;
            keypad->last_rx_tick = HAL_GetTick();
            keypad->online = 1;

            /* First byte is button state */
            uint8_t pressed = (dlc >= 1) ? data[0] : 0;
            if (keypad->buttons[button_idx].state != pressed) {
                ProcessButtonPress(keypad, button_idx, pressed);
            }
            return 1;
        }
    }

    return 0;
}

HAL_StatusTypeDef PMU_BlinkMarine_SetLed(const char* keypad_id, uint8_t button_idx,
                                          PMU_BM_LedColor_t color, PMU_BM_LedMode_t mode)
{
    PMU_BlinkMarine_Keypad_t* keypad = PMU_BlinkMarine_GetKeypad(keypad_id);
    if (!keypad) return HAL_ERROR;

    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
    if (button_idx >= button_count) return HAL_ERROR;

    PMU_BM_ButtonConfig_t* btn = &keypad->buttons[button_idx];
    btn->led_on_color = color;

    /* Update LED state based on mode */
    if (mode == PMU_BM_LED_MODE_OFF) {
        btn->led_state = 0;
    } else {
        btn->led_state = (color & 0x07) | ((mode & 0x03) << 4);
    }

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BlinkMarine_SetAllLeds(const char* keypad_id,
                                              PMU_BM_LedColor_t* colors,
                                              PMU_BM_LedMode_t* modes)
{
    PMU_BlinkMarine_Keypad_t* keypad = PMU_BlinkMarine_GetKeypad(keypad_id);
    if (!keypad || !colors || !modes) return HAL_ERROR;

    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
    for (uint8_t b = 0; b < button_count; b++) {
        PMU_BM_ButtonConfig_t* btn = &keypad->buttons[b];
        if (modes[b] == PMU_BM_LED_MODE_OFF) {
            btn->led_state = 0;
        } else {
            btn->led_state = (colors[b] & 0x07) | ((modes[b] & 0x03) << 4);
        }
    }

    return HAL_OK;
}

uint8_t PMU_BlinkMarine_GetButtonState(const char* keypad_id, uint8_t button_idx)
{
    PMU_BlinkMarine_Keypad_t* keypad = PMU_BlinkMarine_GetKeypad(keypad_id);
    if (!keypad) return 0;

    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
    if (button_idx >= button_count) return 0;

    return keypad->buttons[button_idx].state;
}

uint8_t PMU_BlinkMarine_IsOnline(const char* keypad_id)
{
    PMU_BlinkMarine_Keypad_t* keypad = PMU_BlinkMarine_GetKeypad(keypad_id);
    if (!keypad) return 0;
    return keypad->online;
}

HAL_StatusTypeDef PMU_BlinkMarine_SendLedUpdate(PMU_BlinkMarine_Keypad_t* keypad)
{
    if (!keypad || !keypad->enabled) return HAL_ERROR;

    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);

    /* Build LED control message */
    /* BlinkMarine LED format:
     * Bytes 0-7: LED states (color | mode << 4) for buttons 0-7
     * For 2x8: Need second message for buttons 8-15
     */
    uint8_t led_data[8] = {0};

    for (uint8_t b = 0; b < 8 && b < button_count; b++) {
        led_data[b] = keypad->buttons[b].led_state;
    }

    /* Send first LED message */
    HAL_StatusTypeDef status = PMU_CAN_Send(keypad->can_bus, keypad->tx_base_id, led_data, 8);

    /* For 2x8, send second message with buttons 8-15 */
    if (keypad->type == PMU_BLINKMARINE_2X8) {
        memset(led_data, 0, sizeof(led_data));
        for (uint8_t b = 8; b < button_count; b++) {
            led_data[b - 8] = keypad->buttons[b].led_state;
        }
        status = PMU_CAN_Send(keypad->can_bus, keypad->tx_base_id + 1, led_data, 8);
    }

    return status;
}

/* Private functions ---------------------------------------------------------*/

static void ProcessButtonPress(PMU_BlinkMarine_Keypad_t* keypad, uint8_t button_idx, uint8_t pressed)
{
    PMU_BM_ButtonConfig_t* btn = &keypad->buttons[button_idx];
    btn->state = pressed;

    PMU_LOG_DEBUG("BlinkMarine", "Keypad '%s' button %d: %s",
                  keypad->id, button_idx, pressed ? "PRESSED" : "RELEASED");

    /* Update virtual channel if configured */
    if (btn->enabled && btn->virtual_channel != 0xFFFF) {
        PMU_Channel_SetValue(btn->virtual_channel, pressed ? 1 : 0);
    }

    /* Update LED based on control mode */
    if (btn->led_mode == PMU_BM_LED_CTRL_FOLLOW) {
        /* LED follows button state */
        btn->led_state = pressed ?
            ((btn->led_on_color & 0x07) | (PMU_BM_LED_MODE_ON << 4)) :
            ((btn->led_off_color & 0x07) | (PMU_BM_LED_MODE_ON << 4));
    } else if (btn->led_mode == PMU_BM_LED_CTRL_TOGGLE && pressed) {
        /* Toggle LED on press */
        if (btn->led_state == 0 || (btn->led_state & 0x07) == btn->led_off_color) {
            btn->led_state = (btn->led_on_color & 0x07) | (PMU_BM_LED_MODE_ON << 4);
        } else {
            btn->led_state = (btn->led_off_color & 0x07) | (PMU_BM_LED_MODE_ON << 4);
        }
    }
}

static void UpdateKeypadLeds(PMU_BlinkMarine_Keypad_t* keypad)
{
    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);

    for (uint8_t b = 0; b < button_count; b++) {
        PMU_BM_ButtonConfig_t* btn = &keypad->buttons[b];

        /* For manual control mode, update LED based on channel value */
        if (btn->led_mode == PMU_BM_LED_CTRL_MANUAL && btn->virtual_channel != 0xFFFF) {
            int32_t value = PMU_Channel_GetValue(btn->virtual_channel);
            if (value > 0) {
                btn->led_state = (btn->led_on_color & 0x07) | (PMU_BM_LED_MODE_ON << 4);
            } else {
                btn->led_state = (btn->led_off_color & 0x07) | (PMU_BM_LED_MODE_ON << 4);
                if (btn->led_off_color == PMU_BM_LED_OFF) {
                    btn->led_state = 0;
                }
            }
        }
    }
}

static void CheckKeypadTimeout(PMU_BlinkMarine_Keypad_t* keypad)
{
    if (!keypad->online) return;

    uint32_t now = HAL_GetTick();
    if (now - keypad->last_rx_tick > PMU_BM_TIMEOUT_MS) {
        keypad->online = 0;
        PMU_LOG_WARN("BlinkMarine", "Keypad '%s' timeout - offline", keypad->id);

        /* Reset all button states on timeout */
        uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
        for (uint8_t b = 0; b < button_count; b++) {
            if (keypad->buttons[b].state != 0) {
                ProcessButtonPress(keypad, b, 0);
            }
        }
    }
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
