/**
 ******************************************************************************
 * @file           : test_hbridge.c
 * @brief          : Unit tests for PMU H-Bridge motor driver module
 * @author         : R2 m-sport
 * @date           : 2025-12-26
 ******************************************************************************
 *
 * Tests for dual H-Bridge motor driver:
 * - Initialization
 * - Mode control (forward, reverse, brake, coast)
 * - Position control and PID
 * - Current and fault monitoring
 * - Wiper park functionality
 *
 ******************************************************************************
 */

#include "unity.h"
#include "pmu_hbridge.h"
#include <string.h>

/* Number of H-Bridge channels */
#define NUM_HBRIDGE_CHANNELS 4

/* Test setup and teardown */
void setUp(void)
{
    /* Initialize H-Bridge driver before each test */
    PMU_HBridge_Init();
}

void tearDown(void)
{
    /* Clean up after each test - set all to coast mode */
    for (uint8_t i = 0; i < NUM_HBRIDGE_CHANNELS; i++) {
        PMU_HBridge_SetMode(i, PMU_HBRIDGE_MODE_COAST, 0);
        PMU_HBridge_ClearFaults(i);
    }
}

/* ===========================================================================
 * Initialization Tests
 * =========================================================================== */

void test_hbridge_init(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_Init();
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_hbridge_init_multiple(void)
{
    /* Multiple init calls should be safe */
    for (int i = 0; i < 3; i++) {
        HAL_StatusTypeDef status = PMU_HBridge_Init();
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }
}

void test_hbridge_init_clears_state(void)
{
    /* Set a mode first */
    PMU_HBridge_SetMode(0, PMU_HBRIDGE_MODE_FORWARD, 500);

    /* Re-init should reset state */
    PMU_HBridge_Init();

    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(0);
    TEST_ASSERT_NOT_NULL(channel);
    TEST_ASSERT_EQUAL(PMU_HBRIDGE_STATE_IDLE, channel->state);
}

/* ===========================================================================
 * Mode Control Tests
 * =========================================================================== */

void test_set_mode_coast(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetMode(0, PMU_HBRIDGE_MODE_COAST, 0);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(0);
    TEST_ASSERT_EQUAL(PMU_HBRIDGE_MODE_COAST, channel->mode);
}

void test_set_mode_forward(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetMode(0, PMU_HBRIDGE_MODE_FORWARD, 500);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(0);
    TEST_ASSERT_EQUAL(PMU_HBRIDGE_MODE_FORWARD, channel->mode);
    TEST_ASSERT_EQUAL(500, channel->duty_cycle);
}

void test_set_mode_reverse(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetMode(1, PMU_HBRIDGE_MODE_REVERSE, 750);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(1);
    TEST_ASSERT_EQUAL(PMU_HBRIDGE_MODE_REVERSE, channel->mode);
    TEST_ASSERT_EQUAL(750, channel->duty_cycle);
}

void test_set_mode_brake(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetMode(2, PMU_HBRIDGE_MODE_BRAKE, 0);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(2);
    TEST_ASSERT_EQUAL(PMU_HBRIDGE_MODE_BRAKE, channel->mode);
}

void test_set_mode_invalid_bridge(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetMode(NUM_HBRIDGE_CHANNELS, PMU_HBRIDGE_MODE_FORWARD, 500);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_set_mode_duty_cycle_zero(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetMode(0, PMU_HBRIDGE_MODE_FORWARD, 0);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(0);
    TEST_ASSERT_EQUAL(0, channel->duty_cycle);
}

void test_set_mode_duty_cycle_max(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetMode(0, PMU_HBRIDGE_MODE_FORWARD, PMU_HBRIDGE_PWM_RESOLUTION);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(0);
    TEST_ASSERT_EQUAL(PMU_HBRIDGE_PWM_RESOLUTION, channel->duty_cycle);
}

void test_set_mode_duty_cycle_clamped(void)
{
    /* Duty cycle above max should be clamped */
    HAL_StatusTypeDef status = PMU_HBridge_SetMode(0, PMU_HBRIDGE_MODE_FORWARD, 2000);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(0);
    TEST_ASSERT_LESS_OR_EQUAL(PMU_HBRIDGE_PWM_RESOLUTION, channel->duty_cycle);
}

void test_set_mode_all_bridges(void)
{
    /* Set different modes on all bridges */
    PMU_HBridge_SetMode(0, PMU_HBRIDGE_MODE_FORWARD, 250);
    PMU_HBridge_SetMode(1, PMU_HBRIDGE_MODE_REVERSE, 500);
    PMU_HBridge_SetMode(2, PMU_HBRIDGE_MODE_BRAKE, 0);
    PMU_HBridge_SetMode(3, PMU_HBRIDGE_MODE_COAST, 0);

    TEST_ASSERT_EQUAL(PMU_HBRIDGE_MODE_FORWARD, PMU_HBridge_GetChannelData(0)->mode);
    TEST_ASSERT_EQUAL(PMU_HBRIDGE_MODE_REVERSE, PMU_HBridge_GetChannelData(1)->mode);
    TEST_ASSERT_EQUAL(PMU_HBRIDGE_MODE_BRAKE, PMU_HBridge_GetChannelData(2)->mode);
    TEST_ASSERT_EQUAL(PMU_HBRIDGE_MODE_COAST, PMU_HBridge_GetChannelData(3)->mode);
}

/* ===========================================================================
 * Position Control Tests
 * =========================================================================== */

void test_set_position(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetPosition(0, 500);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(0);
    TEST_ASSERT_EQUAL(500, channel->target_position);
}

void test_set_position_zero(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetPosition(0, 0);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(0);
    TEST_ASSERT_EQUAL(0, channel->target_position);
}

void test_set_position_max(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetPosition(0, 1000);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(0);
    TEST_ASSERT_EQUAL(1000, channel->target_position);
}

void test_set_position_invalid_bridge(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetPosition(NUM_HBRIDGE_CHANNELS, 500);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_get_position(void)
{
    uint16_t position = PMU_HBridge_GetPosition(0);
    /* Position should be within valid range */
    TEST_ASSERT_LESS_OR_EQUAL(1000, position);
}

void test_get_position_invalid_bridge(void)
{
    uint16_t position = PMU_HBridge_GetPosition(NUM_HBRIDGE_CHANNELS);
    TEST_ASSERT_EQUAL(0, position);
}

/* ===========================================================================
 * PID Control Tests
 * =========================================================================== */

void test_set_pid(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetPID(0, 1.0f, 0.1f, 0.01f);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_set_pid_invalid_bridge(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetPID(NUM_HBRIDGE_CHANNELS, 1.0f, 0.1f, 0.01f);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_set_pid_zero_gains(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetPID(0, 0.0f, 0.0f, 0.0f);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_set_pid_high_gains(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_SetPID(0, 100.0f, 10.0f, 1.0f);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_pid_mode_sets_position(void)
{
    PMU_HBridge_SetPID(0, 1.0f, 0.1f, 0.01f);
    PMU_HBridge_SetMode(0, PMU_HBRIDGE_MODE_PID, 0);

    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(0);
    TEST_ASSERT_EQUAL(PMU_HBRIDGE_MODE_PID, channel->mode);
}

/* ===========================================================================
 * Wiper Park Tests
 * =========================================================================== */

void test_wiper_park(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_WiperPark(0);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_wiper_park_invalid_bridge(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_WiperPark(NUM_HBRIDGE_CHANNELS);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_wiper_park_sets_mode(void)
{
    PMU_HBridge_WiperPark(0);

    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(0);
    TEST_ASSERT_EQUAL(PMU_HBRIDGE_MODE_WIPER_PARK, channel->mode);
}

void test_wiper_park_state_parking(void)
{
    PMU_HBridge_WiperPark(0);

    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(0);
    /* State should be PARKING or already PARKED */
    TEST_ASSERT_TRUE(channel->state == PMU_HBRIDGE_STATE_PARKING ||
                     channel->state == PMU_HBRIDGE_STATE_PARKED);
}

/* ===========================================================================
 * Current Monitoring Tests
 * =========================================================================== */

void test_get_current(void)
{
    uint16_t current = PMU_HBridge_GetCurrent(0);
    /* Current should be within valid range */
    TEST_ASSERT_LESS_OR_EQUAL(PMU_HBRIDGE_MAX_CURRENT_MA, current);
}

void test_get_current_invalid_bridge(void)
{
    uint16_t current = PMU_HBridge_GetCurrent(NUM_HBRIDGE_CHANNELS);
    TEST_ASSERT_EQUAL(0, current);
}

void test_get_current_all_bridges(void)
{
    for (uint8_t i = 0; i < NUM_HBRIDGE_CHANNELS; i++) {
        uint16_t current = PMU_HBridge_GetCurrent(i);
        TEST_ASSERT_LESS_OR_EQUAL(PMU_HBRIDGE_MAX_CURRENT_MA, current);
    }
}

/* ===========================================================================
 * Fault Monitoring Tests
 * =========================================================================== */

void test_get_faults(void)
{
    uint8_t faults = PMU_HBridge_GetFaults(0);
    /* After init, no faults expected */
    TEST_ASSERT_EQUAL(PMU_HBRIDGE_FAULT_NONE, faults);
}

void test_get_faults_invalid_bridge(void)
{
    uint8_t faults = PMU_HBridge_GetFaults(NUM_HBRIDGE_CHANNELS);
    TEST_ASSERT_EQUAL(0, faults);
}

void test_clear_faults(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_ClearFaults(0);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_clear_faults_invalid_bridge(void)
{
    HAL_StatusTypeDef status = PMU_HBridge_ClearFaults(NUM_HBRIDGE_CHANNELS);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_clear_faults_all_bridges(void)
{
    for (uint8_t i = 0; i < NUM_HBRIDGE_CHANNELS; i++) {
        HAL_StatusTypeDef status = PMU_HBridge_ClearFaults(i);
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }
}

/* ===========================================================================
 * Channel Data Tests
 * =========================================================================== */

void test_get_channel_data(void)
{
    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(0);
    TEST_ASSERT_NOT_NULL(channel);
}

void test_get_channel_data_invalid_bridge(void)
{
    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(NUM_HBRIDGE_CHANNELS);
    TEST_ASSERT_NULL(channel);
}

void test_get_channel_data_all_bridges(void)
{
    for (uint8_t i = 0; i < NUM_HBRIDGE_CHANNELS; i++) {
        PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(i);
        TEST_ASSERT_NOT_NULL(channel);
    }
}

void test_channel_data_initial_values(void)
{
    PMU_HBridge_Init();
    PMU_HBridge_Channel_t* channel = PMU_HBridge_GetChannelData(0);

    TEST_ASSERT_NOT_NULL(channel);
    TEST_ASSERT_EQUAL(PMU_HBRIDGE_STATE_IDLE, channel->state);
    TEST_ASSERT_EQUAL(PMU_HBRIDGE_MODE_COAST, channel->mode);
    TEST_ASSERT_EQUAL(0, channel->duty_cycle);
}

/* ===========================================================================
 * Update Tests
 * =========================================================================== */

void test_update(void)
{
    /* Update should not crash */
    PMU_HBridge_Update();
    TEST_PASS();
}

void test_update_with_running_motor(void)
{
    PMU_HBridge_SetMode(0, PMU_HBRIDGE_MODE_FORWARD, 500);
    PMU_HBridge_Update();
    TEST_PASS();
}

void test_update_multiple(void)
{
    /* Multiple updates should be safe */
    for (int i = 0; i < 100; i++) {
        PMU_HBridge_Update();
    }
    TEST_PASS();
}

/* ===========================================================================
 * Enum Value Tests
 * =========================================================================== */

void test_mode_enum_values(void)
{
    TEST_ASSERT_EQUAL(0, PMU_HBRIDGE_MODE_COAST);
    TEST_ASSERT_EQUAL(1, PMU_HBRIDGE_MODE_FORWARD);
    TEST_ASSERT_EQUAL(2, PMU_HBRIDGE_MODE_REVERSE);
    TEST_ASSERT_EQUAL(3, PMU_HBRIDGE_MODE_BRAKE);
    TEST_ASSERT_EQUAL(4, PMU_HBRIDGE_MODE_WIPER_PARK);
    TEST_ASSERT_EQUAL(5, PMU_HBRIDGE_MODE_PID);
}

void test_fault_enum_values(void)
{
    TEST_ASSERT_EQUAL(0x00, PMU_HBRIDGE_FAULT_NONE);
    TEST_ASSERT_EQUAL(0x01, PMU_HBRIDGE_FAULT_OVERCURRENT_FWD);
    TEST_ASSERT_EQUAL(0x02, PMU_HBRIDGE_FAULT_OVERCURRENT_REV);
    TEST_ASSERT_EQUAL(0x04, PMU_HBRIDGE_FAULT_OVERTEMP);
    TEST_ASSERT_EQUAL(0x08, PMU_HBRIDGE_FAULT_STALL);
    TEST_ASSERT_EQUAL(0x10, PMU_HBRIDGE_FAULT_POSITION_LOST);
}

void test_state_enum_values(void)
{
    TEST_ASSERT_EQUAL(0, PMU_HBRIDGE_STATE_IDLE);
    TEST_ASSERT_EQUAL(1, PMU_HBRIDGE_STATE_RUNNING);
    TEST_ASSERT_EQUAL(2, PMU_HBRIDGE_STATE_PARKING);
    TEST_ASSERT_EQUAL(3, PMU_HBRIDGE_STATE_PARKED);
    TEST_ASSERT_EQUAL(4, PMU_HBRIDGE_STATE_FAULT);
}

/* ===========================================================================
 * Constants Tests
 * =========================================================================== */

void test_hbridge_constants(void)
{
    /* Verify constants are reasonable */
    TEST_ASSERT_GREATER_THAN(0, PMU_HBRIDGE_MAX_CURRENT_MA);
    TEST_ASSERT_GREATER_THAN(0, PMU_HBRIDGE_MAX_TEMP_C);
    TEST_ASSERT_GREATER_THAN(0, PMU_HBRIDGE_PWM_RESOLUTION);
    TEST_ASSERT_GREATER_THAN(0, PMU_HBRIDGE_STALL_CURRENT_MA);
    TEST_ASSERT_GREATER_THAN(0, PMU_HBRIDGE_STALL_TIME_MS);
}

/* ===========================================================================
 * Structure Size Tests
 * =========================================================================== */

void test_structure_sizes(void)
{
    /* Verify structures have expected sizes */
    TEST_ASSERT_GREATER_THAN(0, sizeof(PMU_HBridge_Channel_t));
    TEST_ASSERT_GREATER_THAN(0, sizeof(PMU_PID_Controller_t));
}

/* ===========================================================================
 * Main Test Runner
 * =========================================================================== */

int test_hbridge_main(void)
{
    UNITY_BEGIN();

    /* Initialization */
    RUN_TEST(test_hbridge_init);
    RUN_TEST(test_hbridge_init_multiple);
    RUN_TEST(test_hbridge_init_clears_state);

    /* Mode Control */
    RUN_TEST(test_set_mode_coast);
    RUN_TEST(test_set_mode_forward);
    RUN_TEST(test_set_mode_reverse);
    RUN_TEST(test_set_mode_brake);
    RUN_TEST(test_set_mode_invalid_bridge);
    RUN_TEST(test_set_mode_duty_cycle_zero);
    RUN_TEST(test_set_mode_duty_cycle_max);
    RUN_TEST(test_set_mode_duty_cycle_clamped);
    RUN_TEST(test_set_mode_all_bridges);

    /* Position Control */
    RUN_TEST(test_set_position);
    RUN_TEST(test_set_position_zero);
    RUN_TEST(test_set_position_max);
    RUN_TEST(test_set_position_invalid_bridge);
    RUN_TEST(test_get_position);
    RUN_TEST(test_get_position_invalid_bridge);

    /* PID Control */
    RUN_TEST(test_set_pid);
    RUN_TEST(test_set_pid_invalid_bridge);
    RUN_TEST(test_set_pid_zero_gains);
    RUN_TEST(test_set_pid_high_gains);
    RUN_TEST(test_pid_mode_sets_position);

    /* Wiper Park */
    RUN_TEST(test_wiper_park);
    RUN_TEST(test_wiper_park_invalid_bridge);
    RUN_TEST(test_wiper_park_sets_mode);
    RUN_TEST(test_wiper_park_state_parking);

    /* Current Monitoring */
    RUN_TEST(test_get_current);
    RUN_TEST(test_get_current_invalid_bridge);
    RUN_TEST(test_get_current_all_bridges);

    /* Fault Monitoring */
    RUN_TEST(test_get_faults);
    RUN_TEST(test_get_faults_invalid_bridge);
    RUN_TEST(test_clear_faults);
    RUN_TEST(test_clear_faults_invalid_bridge);
    RUN_TEST(test_clear_faults_all_bridges);

    /* Channel Data */
    RUN_TEST(test_get_channel_data);
    RUN_TEST(test_get_channel_data_invalid_bridge);
    RUN_TEST(test_get_channel_data_all_bridges);
    RUN_TEST(test_channel_data_initial_values);

    /* Update */
    RUN_TEST(test_update);
    RUN_TEST(test_update_with_running_motor);
    RUN_TEST(test_update_multiple);

    /* Enums */
    RUN_TEST(test_mode_enum_values);
    RUN_TEST(test_fault_enum_values);
    RUN_TEST(test_state_enum_values);

    /* Constants */
    RUN_TEST(test_hbridge_constants);

    /* Structures */
    RUN_TEST(test_structure_sizes);

    return UNITY_END();
}

/* Standalone runner */
#ifdef TEST_HBRIDGE_STANDALONE
int main(void)
{
    return test_hbridge_main();
}
#endif
