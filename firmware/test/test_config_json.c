/**
 ******************************************************************************
 * @file           : test_config_json.c
 * @brief          : Unit tests for PMU JSON Configuration System
 * @author         : R2 m-sport
 * @date           : 2025-12-26
 ******************************************************************************
 *
 * Note: Full JSON parsing tests require PMU_EMULATOR environment.
 * These tests cover the API that works in UNIT_TEST mode:
 * - Init/Clear functions
 * - Channel count getters
 * - Update loop functions (with mocked channels)
 *
 ******************************************************************************
 */

#include "unity.h"
#include "pmu_config_json.h"
#include "pmu_channel.h"
#include <string.h>

/* Test setup and teardown */
void setUp(void)
{
    /* Initialize channel system first (required by JSON module) */
    PMU_Channel_Init();

    /* Initialize JSON configuration system */
    PMU_JSON_Init();
}

void tearDown(void)
{
    /* Clear all configurations */
    PMU_JSON_ClearConfig();
}

/* ===========================================================================
 * Initialization Tests
 * =========================================================================== */

void test_json_init(void)
{
    HAL_StatusTypeDef status = PMU_JSON_Init();
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_json_clear_config(void)
{
    HAL_StatusTypeDef status = PMU_JSON_ClearConfig();
    TEST_ASSERT_EQUAL(HAL_OK, status);

    /* After clear, all counts should be zero */
    TEST_ASSERT_EQUAL(0, PMU_PowerOutput_GetCount());
    TEST_ASSERT_EQUAL(0, PMU_LogicChannel_GetCount());
    TEST_ASSERT_EQUAL(0, PMU_NumberChannel_GetCount());
    TEST_ASSERT_EQUAL(0, PMU_SwitchChannel_GetCount());
    TEST_ASSERT_EQUAL(0, PMU_FilterChannel_GetCount());
    TEST_ASSERT_EQUAL(0, PMU_TimerChannel_GetCount());
}

/* ===========================================================================
 * Count Getter Tests
 * =========================================================================== */

void test_power_output_count_initial(void)
{
    PMU_PowerOutput_ClearConfig();
    TEST_ASSERT_EQUAL(0, PMU_PowerOutput_GetCount());
}

void test_logic_channel_count_initial(void)
{
    PMU_LogicChannel_ClearConfig();
    TEST_ASSERT_EQUAL(0, PMU_LogicChannel_GetCount());
}

void test_number_channel_count_initial(void)
{
    PMU_NumberChannel_ClearConfig();
    TEST_ASSERT_EQUAL(0, PMU_NumberChannel_GetCount());
}

void test_switch_channel_count_initial(void)
{
    PMU_SwitchChannel_ClearConfig();
    TEST_ASSERT_EQUAL(0, PMU_SwitchChannel_GetCount());
}

void test_filter_channel_count_initial(void)
{
    PMU_FilterChannel_ClearConfig();
    TEST_ASSERT_EQUAL(0, PMU_FilterChannel_GetCount());
}

void test_timer_channel_count_initial(void)
{
    PMU_TimerChannel_ClearConfig();
    TEST_ASSERT_EQUAL(0, PMU_TimerChannel_GetCount());
}

/* ===========================================================================
 * Clear Config Tests
 * =========================================================================== */

void test_power_output_clear(void)
{
    PMU_PowerOutput_ClearConfig();
    TEST_ASSERT_EQUAL(0, PMU_PowerOutput_GetCount());
}

void test_logic_channel_clear(void)
{
    PMU_LogicChannel_ClearConfig();
    TEST_ASSERT_EQUAL(0, PMU_LogicChannel_GetCount());
}

void test_number_channel_clear(void)
{
    PMU_NumberChannel_ClearConfig();
    TEST_ASSERT_EQUAL(0, PMU_NumberChannel_GetCount());
}

void test_switch_channel_clear(void)
{
    PMU_SwitchChannel_ClearConfig();
    TEST_ASSERT_EQUAL(0, PMU_SwitchChannel_GetCount());
}

void test_filter_channel_clear(void)
{
    PMU_FilterChannel_ClearConfig();
    TEST_ASSERT_EQUAL(0, PMU_FilterChannel_GetCount());
}

void test_timer_channel_clear(void)
{
    PMU_TimerChannel_ClearConfig();
    TEST_ASSERT_EQUAL(0, PMU_TimerChannel_GetCount());
}

/* ===========================================================================
 * Update Loop Tests (with empty config)
 * =========================================================================== */

void test_power_output_update_empty(void)
{
    PMU_PowerOutput_ClearConfig();

    /* Should not crash with empty config */
    PMU_PowerOutput_Update();

    TEST_PASS();
}

void test_logic_channel_update_empty(void)
{
    PMU_LogicChannel_ClearConfig();

    /* Should not crash with empty config */
    PMU_LogicChannel_Update();

    TEST_PASS();
}

void test_number_channel_update_empty(void)
{
    PMU_NumberChannel_ClearConfig();

    /* Should not crash with empty config */
    PMU_NumberChannel_Update();

    TEST_PASS();
}

void test_switch_channel_update_empty(void)
{
    PMU_SwitchChannel_ClearConfig();

    /* Should not crash with empty config */
    PMU_SwitchChannel_Update();

    TEST_PASS();
}

void test_filter_channel_update_empty(void)
{
    PMU_FilterChannel_ClearConfig();

    /* Should not crash with empty config */
    PMU_FilterChannel_Update();

    TEST_PASS();
}

void test_timer_channel_update_empty(void)
{
    PMU_TimerChannel_ClearConfig();

    /* Should not crash with empty config */
    PMU_TimerChannel_Update();

    TEST_PASS();
}

/* ===========================================================================
 * Error Message Tests
 * =========================================================================== */

void test_get_last_error(void)
{
    const char* error = PMU_JSON_GetLastError();

    /* Should return a valid string (even if empty) */
    TEST_ASSERT_NOT_NULL(error);
}

/* ===========================================================================
 * Filter Channel Value Tests
 * =========================================================================== */

void test_filter_channel_get_value_invalid_index(void)
{
    PMU_FilterChannel_ClearConfig();

    /* Invalid index should return 0 */
    int32_t value = PMU_FilterChannel_GetValue(255);
    TEST_ASSERT_EQUAL(0, value);
}

void test_filter_channel_get_id_invalid_index(void)
{
    PMU_FilterChannel_ClearConfig();

    /* Invalid index should return 0 */
    uint16_t id = PMU_FilterChannel_GetChannelID(255);
    TEST_ASSERT_EQUAL(0, id);
}

/* ===========================================================================
 * Version String Tests
 * =========================================================================== */

void test_version_constants(void)
{
    /* Verify version constants are defined correctly */
    TEST_ASSERT_EQUAL_STRING("1.0", PMU_JSON_VERSION_1_0);
    TEST_ASSERT_EQUAL_STRING("2.0", PMU_JSON_VERSION_2_0);
    TEST_ASSERT_EQUAL_STRING("3.0", PMU_JSON_VERSION_3_0);
    TEST_ASSERT_EQUAL_STRING("3.0", PMU_JSON_VERSION_CURRENT);
}

/* ===========================================================================
 * Status Enum Tests
 * =========================================================================== */

void test_status_enum_values(void)
{
    /* Verify status enum values */
    TEST_ASSERT_EQUAL(0, PMU_JSON_OK);
    TEST_ASSERT_NOT_EQUAL(0, PMU_JSON_ERROR_PARSE);
    TEST_ASSERT_NOT_EQUAL(0, PMU_JSON_ERROR_VALIDATION);
    TEST_ASSERT_NOT_EQUAL(0, PMU_JSON_ERROR_VERSION);
    TEST_ASSERT_NOT_EQUAL(0, PMU_JSON_ERROR_MEMORY);
    TEST_ASSERT_NOT_EQUAL(0, PMU_JSON_ERROR_FILE);
}

/* ===========================================================================
 * Multiple Clear/Init Cycle Tests
 * =========================================================================== */

void test_multiple_init_cycles(void)
{
    /* Multiple init/clear cycles should not cause issues */
    for (int i = 0; i < 5; i++) {
        HAL_StatusTypeDef status = PMU_JSON_Init();
        TEST_ASSERT_EQUAL(HAL_OK, status);

        status = PMU_JSON_ClearConfig();
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }
}

void test_multiple_channel_clear_cycles(void)
{
    /* Multiple clear cycles for each channel type */
    for (int i = 0; i < 3; i++) {
        PMU_PowerOutput_ClearConfig();
        PMU_LogicChannel_ClearConfig();
        PMU_NumberChannel_ClearConfig();
        PMU_SwitchChannel_ClearConfig();
        PMU_FilterChannel_ClearConfig();
        PMU_TimerChannel_ClearConfig();

        TEST_ASSERT_EQUAL(0, PMU_PowerOutput_GetCount());
        TEST_ASSERT_EQUAL(0, PMU_LogicChannel_GetCount());
        TEST_ASSERT_EQUAL(0, PMU_NumberChannel_GetCount());
    }
}

/* ===========================================================================
 * Load Stats Structure Tests
 * =========================================================================== */

void test_load_stats_struct_init(void)
{
    PMU_JSON_LoadStats_t stats;
    memset(&stats, 0, sizeof(stats));

    /* Verify all fields are zero after memset */
    TEST_ASSERT_EQUAL(0, stats.total_channels);
    TEST_ASSERT_EQUAL(0, stats.can_messages);
    TEST_ASSERT_EQUAL(0, stats.digital_inputs);
    TEST_ASSERT_EQUAL(0, stats.analog_inputs);
    TEST_ASSERT_EQUAL(0, stats.power_outputs);
    TEST_ASSERT_EQUAL(0, stats.logic_functions);
    TEST_ASSERT_EQUAL(0, stats.numbers);
    TEST_ASSERT_EQUAL(0, stats.filters);
    TEST_ASSERT_EQUAL(0, stats.timers);
    TEST_ASSERT_EQUAL(0, stats.tables_2d);
    TEST_ASSERT_EQUAL(0, stats.tables_3d);
    TEST_ASSERT_EQUAL(0, stats.switches);
    TEST_ASSERT_EQUAL(0, stats.can_rx);
    TEST_ASSERT_EQUAL(0, stats.can_tx);
    TEST_ASSERT_EQUAL(0, stats.parse_time_ms);
    TEST_ASSERT_FALSE(stats.stream_enabled);
}

/* ===========================================================================
 * Main Test Runner
 * =========================================================================== */

int test_config_json_main(void)
{
    UNITY_BEGIN();

    /* Initialization */
    RUN_TEST(test_json_init);
    RUN_TEST(test_json_clear_config);

    /* Count Getters */
    RUN_TEST(test_power_output_count_initial);
    RUN_TEST(test_logic_channel_count_initial);
    RUN_TEST(test_number_channel_count_initial);
    RUN_TEST(test_switch_channel_count_initial);
    RUN_TEST(test_filter_channel_count_initial);
    RUN_TEST(test_timer_channel_count_initial);

    /* Clear Config */
    RUN_TEST(test_power_output_clear);
    RUN_TEST(test_logic_channel_clear);
    RUN_TEST(test_number_channel_clear);
    RUN_TEST(test_switch_channel_clear);
    RUN_TEST(test_filter_channel_clear);
    RUN_TEST(test_timer_channel_clear);

    /* Update Loops */
    RUN_TEST(test_power_output_update_empty);
    RUN_TEST(test_logic_channel_update_empty);
    RUN_TEST(test_number_channel_update_empty);
    RUN_TEST(test_switch_channel_update_empty);
    RUN_TEST(test_filter_channel_update_empty);
    RUN_TEST(test_timer_channel_update_empty);

    /* Error Messages */
    RUN_TEST(test_get_last_error);

    /* Filter Channel */
    RUN_TEST(test_filter_channel_get_value_invalid_index);
    RUN_TEST(test_filter_channel_get_id_invalid_index);

    /* Constants */
    RUN_TEST(test_version_constants);
    RUN_TEST(test_status_enum_values);

    /* Cycles */
    RUN_TEST(test_multiple_init_cycles);
    RUN_TEST(test_multiple_channel_clear_cycles);

    /* Structures */
    RUN_TEST(test_load_stats_struct_init);

    return UNITY_END();
}

/* Standalone runner */
#ifdef TEST_CONFIG_JSON_STANDALONE
int main(void)
{
    return test_config_json_main();
}
#endif
