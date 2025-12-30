/**
 ******************************************************************************
 * @file           : pmu_blinkmarine.c
 * @brief          : BlinkMarine CAN Keypad Implementation (CANopen Protocol)
 * @author         : R2 m-sport
 * @date           : 2025-12-29
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * CANopen Protocol for BlinkMarine PKP keypads:
 *
 * TPDO1 (Button States) - COB-ID: 0x180 + Node_ID
 *   Byte 0-1: Button states as bitmask (bit 0 = button 1)
 *   Keypad transmits on button change or periodically
 *
 * RPDO1 (LED Control) - COB-ID: 0x200 + Node_ID
 *   Byte 0-1: LED on/off bitmask
 *   Byte 2-3: LED blink bitmask
 *   Byte 4:   LED color (all LEDs)
 *   PMU transmits to control LEDs
 *
 * Heartbeat - COB-ID: 0x700 + Node_ID
 *   Byte 0: NMT state
 *   Used for online detection
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

#define LED_UPDATE_INTERVAL_MS  100

/* Private function prototypes -----------------------------------------------*/
static void ProcessButtonStates(PMU_BlinkMarine_Keypad_t* keypad, uint16_t button_mask);
static void UpdateKeypadLeds(PMU_BlinkMarine_Keypad_t* keypad);
static void CheckKeypadTimeout(PMU_BlinkMarine_Keypad_t* keypad);

/* Exported functions --------------------------------------------------------*/

HAL_StatusTypeDef PMU_BlinkMarine_Init(void)
{
    memset(s_keypads, 0, sizeof(s_keypads));
    s_keypad_count = 0;
    s_last_led_update_tick = 0;

    PMU_LOG_INFO("BlinkMarine", "Keypad subsystem initialized (CANopen)");
    return HAL_OK;
}

void PMU_BlinkMarine_Update(void)
{
    uint32_t now = HAL_GetTick();

    for (uint8_t i = 0; i < s_keypad_count; i++) {
        PMU_BlinkMarine_Keypad_t* keypad = &s_keypads[i];
        if (!keypad->enabled) continue;

        CheckKeypadTimeout(keypad);
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

    /* Set defaults */
    if (kp->node_id == 0) kp->node_id = 1;
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
        btn->current_led = PMU_BM_LED_OFF;
        btn->virtual_channel_id = 0xFFFF;
        btn->led_channel_id = 0xFFFF;

        /* Auto-create virtual channel for button state */
        char btn_channel_name[64];
        snprintf(btn_channel_name, sizeof(btn_channel_name), "%s - Button %d", kp->name, b + 1);
        const PMU_Channel_t* ch = PMU_Channel_GetByName(btn_channel_name);
        if (ch) {
            btn->virtual_channel_id = ch->channel_id;
        }

        /* Resolve LED control channel */
        if (btn->led_ctrl_mode == PMU_BM_LED_CTRL_CHANNEL && btn->led_channel_name[0]) {
            const PMU_Channel_t* led_ch = PMU_Channel_GetByName(btn->led_channel_name);
            if (led_ch) {
                btn->led_channel_id = led_ch->channel_id;
            }
        }
    }

    s_keypad_count++;
    PMU_LOG_INFO("BlinkMarine", "Added keypad '%s' (%s) CAN%d NodeID:%d",
                 keypad->name,
                 keypad->type == PMU_BLINKMARINE_PKP2600SI ? "PKP2600SI" : "PKP2800SI",
                 keypad->can_bus,
                 keypad->node_id);

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
                                        uint8_t* data, uint8_t dlc)
{
    /* Check each keypad for matching CANopen messages */
    for (uint8_t i = 0; i < s_keypad_count; i++) {
        PMU_BlinkMarine_Keypad_t* keypad = &s_keypads[i];
        if (!keypad->enabled) continue;
        if (keypad->can_bus != bus) continue;

        uint32_t tpdo1_id = PMU_BM_CANOPEN_TPDO1_BASE + keypad->node_id;
        uint32_t heartbeat_id = PMU_BM_CANOPEN_HEARTBEAT + keypad->node_id;

        /* TPDO1: Button states */
        if (can_id == tpdo1_id && dlc >= 2) {
            keypad->last_rx_tick = HAL_GetTick();
            keypad->online = 1;

            uint16_t button_mask = data[0] | ((uint16_t)data[1] << 8);
            ProcessButtonStates(keypad, button_mask);
            return 1;
        }

        /* Heartbeat: Online detection */
        if (can_id == heartbeat_id && dlc >= 1) {
            keypad->last_rx_tick = HAL_GetTick();
            keypad->online = 1;
            return 1;
        }
    }

    return 0;
}

HAL_StatusTypeDef PMU_BlinkMarine_SetLed(PMU_BlinkMarine_Keypad_t* keypad,
                                         uint8_t button_idx,
                                         PMU_BM_LedColor_t color,
                                         PMU_BM_LedState_t state)
{
    if (!keypad) return HAL_ERROR;

    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
    if (button_idx >= button_count) return HAL_ERROR;

    PMU_BM_ButtonConfig_t* btn = &keypad->buttons[button_idx];
    btn->current_led = (state == PMU_BM_LED_STATE_OFF) ? PMU_BM_LED_OFF : color;
    keypad->led_update_needed = 1;

    return HAL_OK;
}

HAL_StatusTypeDef PMU_BlinkMarine_SendLedUpdate(PMU_BlinkMarine_Keypad_t* keypad)
{
    if (!keypad || !keypad->enabled) return HAL_ERROR;

    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);

    /* Build LED bitmasks */
    uint16_t led_on_mask = 0;
    uint16_t led_blink_mask = 0;
    uint8_t led_color = PMU_BM_LED_GREEN;  /* Default color */

    for (uint8_t b = 0; b < button_count; b++) {
        PMU_BM_ButtonConfig_t* btn = &keypad->buttons[b];
        if (btn->current_led != PMU_BM_LED_OFF) {
            led_on_mask |= (1 << b);
            led_color = btn->current_led;  /* Use last non-off color */
        }
    }

    /* Build CANopen RPDO1 message */
    uint32_t rpdo1_id = PMU_BM_CANOPEN_RPDO1_BASE + keypad->node_id;
    uint8_t data[8] = {
        led_on_mask & 0xFF,
        (led_on_mask >> 8) & 0xFF,
        led_blink_mask & 0xFF,
        (led_blink_mask >> 8) & 0xFF,
        led_color,
        keypad->led_brightness,
        0x00,
        0x00
    };

    return PMU_CAN_Send(keypad->can_bus, rpdo1_id, data, 8);
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

static void ProcessButtonStates(PMU_BlinkMarine_Keypad_t* keypad, uint16_t button_mask)
{
    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);

    for (uint8_t b = 0; b < button_count; b++) {
        PMU_BM_ButtonConfig_t* btn = &keypad->buttons[b];
        uint8_t pressed = (button_mask >> b) & 0x01;

        if (btn->state != pressed) {
            btn->prev_state = btn->state;
            btn->state = pressed;

            PMU_LOG_DEBUG("BlinkMarine", "%s Button%d: %s",
                         keypad->name, b + 1, pressed ? "PRESSED" : "RELEASED");

            /* Update virtual channel */
            if (btn->virtual_channel_id != 0xFFFF) {
                PMU_Channel_SetValue(btn->virtual_channel_id, btn->state);
            }

            /* Update LED based on control mode */
            if (btn->led_ctrl_mode == PMU_BM_LED_CTRL_FOLLOW) {
                btn->current_led = pressed ? btn->led_on_color : btn->led_off_color;
                keypad->led_update_needed = 1;
            }
            else if (btn->led_ctrl_mode == PMU_BM_LED_CTRL_TOGGLE && pressed && !btn->prev_state) {
                /* Toggle on rising edge */
                btn->current_led = (btn->current_led == btn->led_off_color) ?
                                   btn->led_on_color : btn->led_off_color;
                keypad->led_update_needed = 1;
            }
        }
    }
}

static void UpdateKeypadLeds(PMU_BlinkMarine_Keypad_t* keypad)
{
    uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);

    for (uint8_t b = 0; b < button_count; b++) {
        PMU_BM_ButtonConfig_t* btn = &keypad->buttons[b];

        /* Channel-controlled LED mode */
        if (btn->led_ctrl_mode == PMU_BM_LED_CTRL_CHANNEL && btn->led_channel_id != 0xFFFF) {
            int32_t value = PMU_Channel_GetValue(btn->led_channel_id);
            PMU_BM_LedColor_t new_color = (value > 0) ? btn->led_on_color : btn->led_off_color;

            if (new_color != btn->current_led) {
                btn->current_led = new_color;
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

        /* Reset all button states */
        uint8_t button_count = PMU_BlinkMarine_GetButtonCount(keypad->type);
        for (uint8_t b = 0; b < button_count; b++) {
            if (keypad->buttons[b].state != 0) {
                keypad->buttons[b].prev_state = keypad->buttons[b].state;
                keypad->buttons[b].state = 0;
                if (keypad->buttons[b].virtual_channel_id != 0xFFFF) {
                    PMU_Channel_SetValue(keypad->buttons[b].virtual_channel_id, 0);
                }
            }
        }
    }
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

    /* Build button mask with this button's state */
    uint16_t button_mask = 0;
    for (uint8_t b = 0; b < button_count; b++) {
        if (b == button_idx) {
            if (pressed) button_mask |= (1 << b);
        } else {
            if (keypad->buttons[b].state) button_mask |= (1 << b);
        }
    }

    ProcessButtonStates(keypad, button_mask);

    PMU_LOG_INFO("BlinkMarine", "Simulated button %d %s on keypad '%s'",
                 button_idx + 1, pressed ? "PRESS" : "RELEASE", keypad->name);

    return HAL_OK;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
