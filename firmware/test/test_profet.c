/**
 ******************************************************************************
 * @file           : test_profet.c
 * @brief          : Unit tests for PMU PROFET Output Driver
 * @author         : R2 m-sport
 * @date           : 2025-12-26
 ******************************************************************************
 *
 * Tests for PROFET high-side output driver:
 * - Initialization
 * - State control (on/off)
 * - PWM duty cycle
 * - Current sensing
 * - Fault detection and handling
 * - Manual override
 *
 ******************************************************************************
 */

#include "unity.h"
#include "pmu_profet.h"
#include <string.h>

/* Number of PROFET channels (from pmu_config.h) */
#ifndef PMU30_NUM_OUTPUTS
#define PMU30_NUM_OUTPUTS 30
#endif

/* Test setup and teardown */
void setUp(void)
{
    /* Initialize PROFET driver before each test */
    PMU_PROFET_Init();
}

void tearDown(void)
{
    /* Clear all outputs after each test */
    for (uint8_t i = 0; i < PMU30_NUM_OUTPUTS; i++) {
        PMU_PROFET_SetState(i, 0);
        PMU_PROFET_ClearFaults(i);
    }
    PMU_PROFET_ClearAllManualOverrides();
}

/* ===========================================================================
 * Initialization Tests
 * =========================================================================== */

void test_profet_init(void)
{
    HAL_StatusTypeDef status = PMU_PROFET_Init();
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_profet_init_multiple(void)
{
    /* Multiple init calls should be safe */
    for (int i = 0; i < 3; i++) {
        HAL_StatusTypeDef status = PMU_PROFET_Init();
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }
}

void test_profet_initial_state_off(void)
{
    /* All channels should be off after init */
    for (uint8_t i = 0; i < PMU30_NUM_OUTPUTS; i++) {
        PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(i);
        if (ch) {
            TEST_ASSERT_EQUAL(PMU_PROFET_STATE_OFF, ch->state);
        }
    }
}

/* ===========================================================================
 * State Control Tests
 * =========================================================================== */

void test_set_state_on(void)
{
    HAL_StatusTypeDef status = PMU_PROFET_SetState(0, 1);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(0);
    TEST_ASSERT_NOT_NULL(ch);
    TEST_ASSERT_EQUAL(PMU_PROFET_STATE_ON, ch->state);
}

void test_set_state_off(void)
{
    /* Turn on first */
    PMU_PROFET_SetState(1, 1);

    /* Then turn off */
    HAL_StatusTypeDef status = PMU_PROFET_SetState(1, 0);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(1);
    TEST_ASSERT_NOT_NULL(ch);
    TEST_ASSERT_EQUAL(PMU_PROFET_STATE_OFF, ch->state);
}

void test_set_state_invalid_channel(void)
{
    HAL_StatusTypeDef status = PMU_PROFET_SetState(PMU30_NUM_OUTPUTS, 1);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_set_state_multiple_channels(void)
{
    /* Turn on multiple channels */
    for (uint8_t i = 0; i < 5; i++) {
        HAL_StatusTypeDef status = PMU_PROFET_SetState(i, 1);
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }

    /* Verify all are on */
    for (uint8_t i = 0; i < 5; i++) {
        PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(i);
        TEST_ASSERT_EQUAL(PMU_PROFET_STATE_ON, ch->state);
    }

    /* Verify remaining are off */
    for (uint8_t i = 5; i < PMU30_NUM_OUTPUTS; i++) {
        PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(i);
        if (ch) {
            TEST_ASSERT_EQUAL(PMU_PROFET_STATE_OFF, ch->state);
        }
    }
}

/* ===========================================================================
 * PWM Tests
 * =========================================================================== */

void test_set_pwm_valid(void)
{
    HAL_StatusTypeDef status = PMU_PROFET_SetPWM(2, 500);  /* 50% */
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(2);
    TEST_ASSERT_NOT_NULL(ch);
    TEST_ASSERT_EQUAL(500, ch->pwm_duty);
    TEST_ASSERT_EQUAL(PMU_PROFET_STATE_PWM, ch->state);
}

void test_set_pwm_zero(void)
{
    /* 0% PWM should turn off */
    PMU_PROFET_SetPWM(3, 0);

    PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(3);
    TEST_ASSERT_EQUAL(0, ch->pwm_duty);
}

void test_set_pwm_full(void)
{
    /* 100% PWM */
    HAL_StatusTypeDef status = PMU_PROFET_SetPWM(4, 1000);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(4);
    TEST_ASSERT_EQUAL(1000, ch->pwm_duty);
}

void test_set_pwm_clamp_above_max(void)
{
    /* Value above 1000 should be clamped */
    PMU_PROFET_SetPWM(5, 1500);

    PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(5);
    TEST_ASSERT_LESS_OR_EQUAL(1000, ch->pwm_duty);
}

void test_set_pwm_invalid_channel(void)
{
    HAL_StatusTypeDef status = PMU_PROFET_SetPWM(PMU30_NUM_OUTPUTS, 500);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * Current Sensing Tests
 * =========================================================================== */

void test_get_current(void)
{
    uint16_t current = PMU_PROFET_GetCurrent(0);
    /* In unit test mode, current should be 0 or a reasonable value */
    TEST_ASSERT_LESS_OR_EQUAL(PMU_PROFET_MAX_CURRENT_MA, current);
}

void test_get_current_invalid_channel(void)
{
    uint16_t current = PMU_PROFET_GetCurrent(PMU30_NUM_OUTPUTS);
    TEST_ASSERT_EQUAL(0, current);
}

void test_get_current_all_channels(void)
{
    /* Get current for all channels */
    for (uint8_t i = 0; i < PMU30_NUM_OUTPUTS; i++) {
        uint16_t current = PMU_PROFET_GetCurrent(i);
        TEST_ASSERT_LESS_OR_EQUAL(PMU_PROFET_MAX_CURRENT_MA, current);
    }
}

/* ===========================================================================
 * Temperature Tests
 * =========================================================================== */

void test_get_temperature(void)
{
    int16_t temp = PMU_PROFET_GetTemperature(0);
    /* Temperature should be reasonable (-40 to 150°C) */
    TEST_ASSERT_GREATER_OR_EQUAL(-40, temp);
    TEST_ASSERT_LESS_OR_EQUAL(PMU_PROFET_MAX_TEMP_C, temp);
}

void test_get_temperature_invalid_channel(void)
{
    int16_t temp = PMU_PROFET_GetTemperature(PMU30_NUM_OUTPUTS);
    TEST_ASSERT_EQUAL(0, temp);
}

/* ===========================================================================
 * Fault Tests
 * =========================================================================== */

void test_get_faults_no_fault(void)
{
    uint8_t faults = PMU_PROFET_GetFaults(0);
    TEST_ASSERT_EQUAL(PMU_PROFET_FAULT_NONE, faults);
}

void test_inject_fault(void)
{
    HAL_StatusTypeDef status = PMU_PROFET_InjectFault(6, PMU_PROFET_FAULT_OVERCURRENT);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    uint8_t faults = PMU_PROFET_GetFaults(6);
    TEST_ASSERT_TRUE(faults & PMU_PROFET_FAULT_OVERCURRENT);
}

void test_inject_multiple_faults(void)
{
    uint8_t combined = PMU_PROFET_FAULT_OVERCURRENT | PMU_PROFET_FAULT_OVERTEMP;
    PMU_PROFET_InjectFault(7, combined);

    uint8_t faults = PMU_PROFET_GetFaults(7);
    TEST_ASSERT_TRUE(faults & PMU_PROFET_FAULT_OVERCURRENT);
    TEST_ASSERT_TRUE(faults & PMU_PROFET_FAULT_OVERTEMP);
}

void test_clear_faults(void)
{
    /* Inject fault */
    PMU_PROFET_InjectFault(8, PMU_PROFET_FAULT_SHORT_CIRCUIT);

    /* Clear it */
    HAL_StatusTypeDef status = PMU_PROFET_ClearFaults(8);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    /* Verify cleared */
    uint8_t faults = PMU_PROFET_GetFaults(8);
    TEST_ASSERT_EQUAL(PMU_PROFET_FAULT_NONE, faults);
}

void test_inject_fault_invalid_channel(void)
{
    HAL_StatusTypeDef status = PMU_PROFET_InjectFault(PMU30_NUM_OUTPUTS, PMU_PROFET_FAULT_OVERCURRENT);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_clear_faults_invalid_channel(void)
{
    HAL_StatusTypeDef status = PMU_PROFET_ClearFaults(PMU30_NUM_OUTPUTS);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * Manual Override Tests
 * =========================================================================== */

void test_set_state_manual(void)
{
    HAL_StatusTypeDef status = PMU_PROFET_SetStateManual(9, 1);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    /* Should have override flag set */
    uint8_t has_override = PMU_PROFET_HasManualOverride(9);
    TEST_ASSERT_EQUAL(1, has_override);
}

void test_has_override_default_false(void)
{
    /* No override by default */
    uint8_t has_override = PMU_PROFET_HasManualOverride(10);
    TEST_ASSERT_EQUAL(0, has_override);
}

void test_clear_manual_override(void)
{
    /* Set override */
    PMU_PROFET_SetStateManual(11, 1);
    TEST_ASSERT_EQUAL(1, PMU_PROFET_HasManualOverride(11));

    /* Clear it */
    PMU_PROFET_ClearManualOverride(11);
    TEST_ASSERT_EQUAL(0, PMU_PROFET_HasManualOverride(11));
}

void test_clear_all_manual_overrides(void)
{
    /* Set overrides on multiple channels */
    PMU_PROFET_SetStateManual(12, 1);
    PMU_PROFET_SetStateManual(13, 1);
    PMU_PROFET_SetStateManual(14, 1);

    /* Clear all */
    PMU_PROFET_ClearAllManualOverrides();

    /* Verify all cleared */
    TEST_ASSERT_EQUAL(0, PMU_PROFET_HasManualOverride(12));
    TEST_ASSERT_EQUAL(0, PMU_PROFET_HasManualOverride(13));
    TEST_ASSERT_EQUAL(0, PMU_PROFET_HasManualOverride(14));
}

/* ===========================================================================
 * Channel Data Tests
 * =========================================================================== */

void test_get_channel_data(void)
{
    PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(0);
    TEST_ASSERT_NOT_NULL(ch);
}

void test_get_channel_data_invalid(void)
{
    PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(PMU30_NUM_OUTPUTS);
    TEST_ASSERT_NULL(ch);
}

void test_get_channel_data_all(void)
{
    /* All valid channels should return non-NULL */
    for (uint8_t i = 0; i < PMU30_NUM_OUTPUTS; i++) {
        PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(i);
        TEST_ASSERT_NOT_NULL(ch);
    }
}

/* ===========================================================================
 * Update Tests
 * =========================================================================== */

void test_update(void)
{
    /* Update should not crash */
    PMU_PROFET_Update();
    TEST_PASS();
}

void test_update_multiple(void)
{
    /* Multiple updates should be safe */
    for (int i = 0; i < 100; i++) {
        PMU_PROFET_Update();
    }
    TEST_PASS();
}

/* ===========================================================================
 * Calibration Tests
 * =========================================================================== */

void test_calibrate_current(void)
{
    HAL_StatusTypeDef status = PMU_PROFET_CalibrateCurrent();
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* ===========================================================================
 * SPI Diagnostics Tests
 * =========================================================================== */

void test_enable_spi_diag(void)
{
    HAL_StatusTypeDef status = PMU_PROFET_EnableSPIDiag(1);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    status = PMU_PROFET_EnableSPIDiag(0);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* ===========================================================================
 * State Enum Tests
 * =========================================================================== */

void test_state_enum_values(void)
{
    /* ECUMaster compatible state values */
    TEST_ASSERT_EQUAL(0, PMU_PROFET_STATE_OFF);
    TEST_ASSERT_EQUAL(1, PMU_PROFET_STATE_ON);
    TEST_ASSERT_EQUAL(2, PMU_PROFET_STATE_OC);
    TEST_ASSERT_EQUAL(3, PMU_PROFET_STATE_OT);
    TEST_ASSERT_EQUAL(4, PMU_PROFET_STATE_SC);
    TEST_ASSERT_EQUAL(5, PMU_PROFET_STATE_OL);
    TEST_ASSERT_EQUAL(6, PMU_PROFET_STATE_PWM);
    TEST_ASSERT_EQUAL(7, PMU_PROFET_STATE_DIS);
}

void test_fault_enum_values(void)
{
    TEST_ASSERT_EQUAL(0x00, PMU_PROFET_FAULT_NONE);
    TEST_ASSERT_EQUAL(0x01, PMU_PROFET_FAULT_OVERCURRENT);
    TEST_ASSERT_EQUAL(0x02, PMU_PROFET_FAULT_OVERTEMP);
    TEST_ASSERT_EQUAL(0x04, PMU_PROFET_FAULT_SHORT_CIRCUIT);
    TEST_ASSERT_EQUAL(0x08, PMU_PROFET_FAULT_OPEN_LOAD);
    TEST_ASSERT_EQUAL(0x10, PMU_PROFET_FAULT_UNDERVOLTAGE);
}

/* ===========================================================================
 * Constants Tests
 * =========================================================================== */

void test_profet_constants(void)
{
    TEST_ASSERT_EQUAL(40000, PMU_PROFET_MAX_CURRENT_MA);
    TEST_ASSERT_EQUAL(160000, PMU_PROFET_MAX_INRUSH_MA);
    TEST_ASSERT_EQUAL(150, PMU_PROFET_MAX_TEMP_C);
    TEST_ASSERT_EQUAL(1000, PMU_PROFET_PWM_RESOLUTION);
}

/* ===========================================================================
 * Main Test Runner
 * =========================================================================== */

int test_profet_main(void)
{
    UNITY_BEGIN();

    /* Initialization */
    RUN_TEST(test_profet_init);
    RUN_TEST(test_profet_init_multiple);
    RUN_TEST(test_profet_initial_state_off);

    /* State Control */
    RUN_TEST(test_set_state_on);
    RUN_TEST(test_set_state_off);
    RUN_TEST(test_set_state_invalid_channel);
    RUN_TEST(test_set_state_multiple_channels);

    /* PWM */
    RUN_TEST(test_set_pwm_valid);
    RUN_TEST(test_set_pwm_zero);
    RUN_TEST(test_set_pwm_full);
    RUN_TEST(test_set_pwm_clamp_above_max);
    RUN_TEST(test_set_pwm_invalid_channel);

    /* Current */
    RUN_TEST(test_get_current);
    RUN_TEST(test_get_current_invalid_channel);
    RUN_TEST(test_get_current_all_channels);

    /* Temperature */
    RUN_TEST(test_get_temperature);
    RUN_TEST(test_get_temperature_invalid_channel);

    /* Faults */
    RUN_TEST(test_get_faults_no_fault);
    RUN_TEST(test_inject_fault);
    RUN_TEST(test_inject_multiple_faults);
    RUN_TEST(test_clear_faults);
    RUN_TEST(test_inject_fault_invalid_channel);
    RUN_TEST(test_clear_faults_invalid_channel);

    /* Manual Override */
    RUN_TEST(test_set_state_manual);
    RUN_TEST(test_has_override_default_false);
    RUN_TEST(test_clear_manual_override);
    RUN_TEST(test_clear_all_manual_overrides);

    /* Channel Data */
    RUN_TEST(test_get_channel_data);
    RUN_TEST(test_get_channel_data_invalid);
    RUN_TEST(test_get_channel_data_all);

    /* Update */
    RUN_TEST(test_update);
    RUN_TEST(test_update_multiple);

    /* Calibration */
    RUN_TEST(test_calibrate_current);

    /* SPI Diagnostics */
    RUN_TEST(test_enable_spi_diag);

    /* Enums */
    RUN_TEST(test_state_enum_values);
    RUN_TEST(test_fault_enum_values);

    /* Constants */
    RUN_TEST(test_profet_constants);

    return UNITY_END();
}

/* Standalone runner */
#ifdef TEST_PROFET_STANDALONE
int main(void)
{
    return test_profet_main();
}
#endif
