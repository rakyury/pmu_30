/**
 ******************************************************************************
 * @file           : test_ui.c
 * @brief          : Unit tests for PMU UI System
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 */

#include "unity.h"
#include "pmu_ui.h"
#include <string.h>

/* Test setup and teardown */
void setUp(void)
{
    PMU_UI_Init();
}

void tearDown(void)
{
    /* Clean up */
}

/* Test: UI initialization */
void test_ui_init(void)
{
    HAL_StatusTypeDef status = PMU_UI_Init();
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: Set status LED */
void test_set_status_led(void)
{
    PMU_UI_SetStatusLED(PMU_STATUS_POWER_ON);
    PMU_UI_SetStatusLED(PMU_STATUS_RUNNING);
    PMU_UI_SetStatusLED(PMU_STATUS_WARNING);
    PMU_UI_SetStatusLED(PMU_STATUS_FAULT);
    PMU_UI_SetStatusLED(PMU_STATUS_CRITICAL);
    PMU_UI_SetStatusLED(PMU_STATUS_BOOTLOADER);
    /* Should not crash */
}

/* Test: Set channel LED */
void test_set_channel_led(void)
{
    HAL_StatusTypeDef status;

    /* Valid channel */
    status = PMU_UI_SetChannelLED(0, PMU_LED_GREEN, PMU_LED_PATTERN_SOLID);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    status = PMU_UI_SetChannelLED(29, PMU_LED_RED, PMU_LED_PATTERN_BLINK_FAST);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    /* Invalid channel */
    status = PMU_UI_SetChannelLED(30, PMU_LED_GREEN, PMU_LED_PATTERN_SOLID);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* Test: Set all channel LEDs */
void test_set_all_leds(void)
{
    PMU_UI_SetAllChannelLEDs(PMU_LED_GREEN, PMU_LED_PATTERN_SOLID);
    PMU_UI_SetAllChannelLEDs(PMU_LED_OFF, PMU_LED_PATTERN_OFF);
    /* Should not crash */
}

/* Test: LED colors */
void test_led_colors(void)
{
    HAL_StatusTypeDef status;

    status = PMU_UI_SetChannelLED(0, PMU_LED_OFF, PMU_LED_PATTERN_OFF);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    status = PMU_UI_SetChannelLED(1, PMU_LED_GREEN, PMU_LED_PATTERN_SOLID);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    status = PMU_UI_SetChannelLED(2, PMU_LED_RED, PMU_LED_PATTERN_SOLID);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    status = PMU_UI_SetChannelLED(3, PMU_LED_ORANGE, PMU_LED_PATTERN_SOLID);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: LED patterns */
void test_led_patterns(void)
{
    HAL_StatusTypeDef status;

    status = PMU_UI_SetChannelLED(0, PMU_LED_GREEN, PMU_LED_PATTERN_OFF);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    status = PMU_UI_SetChannelLED(1, PMU_LED_GREEN, PMU_LED_PATTERN_SOLID);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    status = PMU_UI_SetChannelLED(2, PMU_LED_GREEN, PMU_LED_PATTERN_BLINK_SLOW);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    status = PMU_UI_SetChannelLED(3, PMU_LED_GREEN, PMU_LED_PATTERN_BLINK_FAST);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    status = PMU_UI_SetChannelLED(4, PMU_LED_GREEN, PMU_LED_PATTERN_PULSE);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    status = PMU_UI_SetChannelLED(5, PMU_LED_GREEN, PMU_LED_PATTERN_FLASH);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: Buzzer patterns */
void test_buzzer_patterns(void)
{
    PMU_UI_PlayBuzzer(PMU_BUZZER_BEEP_SHORT);
    PMU_UI_PlayBuzzer(PMU_BUZZER_BEEP_LONG);
    PMU_UI_PlayBuzzer(PMU_BUZZER_BEEP_DOUBLE);
    PMU_UI_PlayBuzzer(PMU_BUZZER_CONTINUOUS);
    PMU_UI_StopBuzzer();
    /* Should not crash */
}

/* Test: Stop buzzer */
void test_stop_buzzer(void)
{
    PMU_UI_PlayBuzzer(PMU_BUZZER_CONTINUOUS);
    PMU_UI_StopBuzzer();
    /* Should not crash */
}

/* Test: Button state */
void test_button_state(void)
{
    PMU_Button_State_t state;

    /* Valid button */
    state = PMU_UI_GetButtonState(0);
    TEST_ASSERT_TRUE(state >= PMU_BUTTON_RELEASED && state <= PMU_BUTTON_LONG_PRESS);

    /* Invalid button */
    state = PMU_UI_GetButtonState(4);
    TEST_ASSERT_EQUAL(PMU_BUTTON_RELEASED, state);
}

/* Test: Button pressed */
void test_button_pressed(void)
{
    uint8_t pressed;

    /* Valid button */
    pressed = PMU_UI_ButtonPressed(0);
    TEST_ASSERT_TRUE(pressed == 0 || pressed == 1);

    /* Invalid button */
    pressed = PMU_UI_ButtonPressed(4);
    TEST_ASSERT_EQUAL(0, pressed);
}

/* Test: Button released */
void test_button_released(void)
{
    uint8_t released;

    /* Valid button */
    released = PMU_UI_ButtonReleased(0);
    TEST_ASSERT_TRUE(released == 0 || released == 1);

    /* Invalid button */
    released = PMU_UI_ButtonReleased(4);
    TEST_ASSERT_EQUAL(0, released);
}

/* Test: UI update */
void test_ui_update(void)
{
    /* Call update multiple times */
    for (int i = 0; i < 100; i++) {
        PMU_UI_Update();
    }
    /* Should not crash */
}

/* Test: Update channel status */
void test_update_channel_status(void)
{
    PMU_UI_UpdateChannelStatus();
    /* Should not crash */
}

/* Test: Startup animation */
void test_startup_animation(void)
{
    /* This would normally block, but should not crash */
    /* PMU_UI_StartupAnimation(); */
    /* Skip in unit tests to avoid HAL_Delay */
}

/* Test: Multiple LED updates */
void test_multiple_led_updates(void)
{
    for (uint8_t i = 0; i < PMU_UI_NUM_CHANNEL_LEDS; i++) {
        PMU_UI_SetChannelLED(i, PMU_LED_GREEN, PMU_LED_PATTERN_BLINK_SLOW);
    }

    PMU_UI_Update();

    for (uint8_t i = 0; i < PMU_UI_NUM_CHANNEL_LEDS; i++) {
        PMU_UI_SetChannelLED(i, PMU_LED_OFF, PMU_LED_PATTERN_OFF);
    }
}

/* Test: Status LED states */
void test_all_status_states(void)
{
    PMU_Status_LED_t states[] = {
        PMU_STATUS_POWER_ON,
        PMU_STATUS_RUNNING,
        PMU_STATUS_WARNING,
        PMU_STATUS_FAULT,
        PMU_STATUS_CRITICAL,
        PMU_STATUS_BOOTLOADER
    };

    for (int i = 0; i < sizeof(states) / sizeof(states[0]); i++) {
        PMU_UI_SetStatusLED(states[i]);
        PMU_UI_Update();
    }
}

/* Main test runner */
int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_ui_init);
    RUN_TEST(test_set_status_led);
    RUN_TEST(test_set_channel_led);
    RUN_TEST(test_set_all_leds);
    RUN_TEST(test_led_colors);
    RUN_TEST(test_led_patterns);
    RUN_TEST(test_buzzer_patterns);
    RUN_TEST(test_stop_buzzer);
    RUN_TEST(test_button_state);
    RUN_TEST(test_button_pressed);
    RUN_TEST(test_button_released);
    RUN_TEST(test_ui_update);
    RUN_TEST(test_update_channel_status);
    RUN_TEST(test_multiple_led_updates);
    RUN_TEST(test_all_status_states);

    return UNITY_END();
}
