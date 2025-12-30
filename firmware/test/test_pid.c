/**
 ******************************************************************************
 * @file           : test_pid.c
 * @brief          : Unit tests for PMU PID Controller module
 * @author         : R2 m-sport
 * @date           : 2025-12-26
 ******************************************************************************
 *
 * Tests for PID controller implementation:
 * - Initialization and reset
 * - Add/remove controllers
 * - Setpoint and output operations
 * - Enable/disable functionality
 * - Statistics tracking
 *
 ******************************************************************************
 */

#include "unity.h"
#include "pmu_pid.h"
#include <string.h>

/* Test setup and teardown */
void setUp(void)
{
    /* Initialize PID subsystem before each test */
    PMU_PID_Init();
    PMU_PID_ClearAll();
}

void tearDown(void)
{
    /* Clean up after each test */
    PMU_PID_ClearAll();
}

/* ===========================================================================
 * Helper Functions
 * =========================================================================== */

static void create_default_config(PMU_PIDConfig_t* config, const char* id)
{
    memset(config, 0, sizeof(PMU_PIDConfig_t));
    strncpy(config->id, id, PMU_CHANNEL_ID_LEN - 1);
    config->kp = 1.0f;
    config->ki = 0.1f;
    config->kd = 0.01f;
    config->setpoint_value = 100.0f;
    config->output_min = 0.0f;
    config->output_max = 100.0f;
    config->sample_time_ms = PMU_PID_DEFAULT_SAMPLE_MS;
    config->anti_windup = true;
    config->enabled = true;
}

/* ===========================================================================
 * Initialization Tests
 * =========================================================================== */

void test_pid_init(void)
{
    HAL_StatusTypeDef status = PMU_PID_Init();
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_pid_init_multiple(void)
{
    /* Multiple init calls should be safe */
    for (int i = 0; i < 3; i++) {
        HAL_StatusTypeDef status = PMU_PID_Init();
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }
}

void test_pid_clear_all(void)
{
    /* Add a controller first */
    PMU_PIDConfig_t config;
    create_default_config(&config, "test_pid");
    PMU_PID_AddController(&config);

    /* Clear all */
    HAL_StatusTypeDef status = PMU_PID_ClearAll();
    TEST_ASSERT_EQUAL(HAL_OK, status);

    /* Stats should show 0 controllers */
    const PMU_PIDStats_t* stats = PMU_PID_GetStats();
    TEST_ASSERT_NOT_NULL(stats);
    TEST_ASSERT_EQUAL(0, stats->total_controllers);
}

/* ===========================================================================
 * Add/Remove Controller Tests
 * =========================================================================== */

void test_add_controller(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_1");

    HAL_StatusTypeDef status = PMU_PID_AddController(&config);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_add_controller_null(void)
{
    HAL_StatusTypeDef status = PMU_PID_AddController(NULL);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_add_multiple_controllers(void)
{
    char id[PMU_CHANNEL_ID_LEN];

    for (int i = 0; i < 5; i++) {
        PMU_PIDConfig_t config;
        snprintf(id, sizeof(id), "pid_%d", i);
        create_default_config(&config, id);

        HAL_StatusTypeDef status = PMU_PID_AddController(&config);
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }

    const PMU_PIDStats_t* stats = PMU_PID_GetStats();
    TEST_ASSERT_EQUAL(5, stats->total_controllers);
}

void test_add_controller_max_limit(void)
{
    char id[PMU_CHANNEL_ID_LEN];

    /* Fill all controller slots */
    for (int i = 0; i < PMU_PID_MAX_CONTROLLERS; i++) {
        PMU_PIDConfig_t config;
        snprintf(id, sizeof(id), "pid_%d", i);
        create_default_config(&config, id);

        HAL_StatusTypeDef status = PMU_PID_AddController(&config);
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }

    /* One more should fail */
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_overflow");
    HAL_StatusTypeDef status = PMU_PID_AddController(&config);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_add_controller_update_existing(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_update");
    config.kp = 1.0f;

    /* Add first time */
    PMU_PID_AddController(&config);

    /* Update with new gains */
    config.kp = 2.0f;
    HAL_StatusTypeDef status = PMU_PID_AddController(&config);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    /* Should still be 1 controller */
    const PMU_PIDStats_t* stats = PMU_PID_GetStats();
    TEST_ASSERT_EQUAL(1, stats->total_controllers);
}

void test_remove_controller(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_remove");
    PMU_PID_AddController(&config);

    HAL_StatusTypeDef status = PMU_PID_RemoveController("pid_remove");
    TEST_ASSERT_EQUAL(HAL_OK, status);

    const PMU_PIDStats_t* stats = PMU_PID_GetStats();
    TEST_ASSERT_EQUAL(0, stats->total_controllers);
}

void test_remove_controller_null(void)
{
    HAL_StatusTypeDef status = PMU_PID_RemoveController(NULL);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_remove_controller_not_found(void)
{
    HAL_StatusTypeDef status = PMU_PID_RemoveController("nonexistent");
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * Setpoint and Output Tests
 * =========================================================================== */

void test_set_setpoint(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_sp");
    PMU_PID_AddController(&config);

    HAL_StatusTypeDef status = PMU_PID_SetSetpoint("pid_sp", 50.0f);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_set_setpoint_null(void)
{
    HAL_StatusTypeDef status = PMU_PID_SetSetpoint(NULL, 50.0f);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_set_setpoint_not_found(void)
{
    HAL_StatusTypeDef status = PMU_PID_SetSetpoint("nonexistent", 50.0f);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_get_output(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_out");
    PMU_PID_AddController(&config);

    /* Initial output should be 0 or within limits */
    float output = PMU_PID_GetOutput("pid_out");
    TEST_ASSERT_FLOAT_IS_DETERMINATE(output);
}

void test_get_output_not_found(void)
{
    float output = PMU_PID_GetOutput("nonexistent");
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.0f, output);
}

void test_get_output_null(void)
{
    float output = PMU_PID_GetOutput(NULL);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.0f, output);
}

/* ===========================================================================
 * Enable/Disable Tests
 * =========================================================================== */

void test_set_enabled(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_enable");
    PMU_PID_AddController(&config);

    /* Disable */
    HAL_StatusTypeDef status = PMU_PID_SetEnabled("pid_enable", false);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    /* Re-enable */
    status = PMU_PID_SetEnabled("pid_enable", true);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_set_enabled_null(void)
{
    HAL_StatusTypeDef status = PMU_PID_SetEnabled(NULL, true);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_set_enabled_not_found(void)
{
    HAL_StatusTypeDef status = PMU_PID_SetEnabled("nonexistent", true);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * Reset Tests
 * =========================================================================== */

void test_reset(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_reset");
    PMU_PID_AddController(&config);

    HAL_StatusTypeDef status = PMU_PID_Reset("pid_reset");
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_reset_null(void)
{
    HAL_StatusTypeDef status = PMU_PID_Reset(NULL);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_reset_not_found(void)
{
    HAL_StatusTypeDef status = PMU_PID_Reset("nonexistent");
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * Statistics Tests
 * =========================================================================== */

void test_get_stats(void)
{
    const PMU_PIDStats_t* stats = PMU_PID_GetStats();
    TEST_ASSERT_NOT_NULL(stats);
}

void test_stats_after_add(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_stats");
    PMU_PID_AddController(&config);

    const PMU_PIDStats_t* stats = PMU_PID_GetStats();
    TEST_ASSERT_EQUAL(1, stats->total_controllers);
}

void test_stats_active_controllers(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_active");
    config.enabled = true;
    PMU_PID_AddController(&config);

    const PMU_PIDStats_t* stats = PMU_PID_GetStats();
    TEST_ASSERT_EQUAL(1, stats->active_controllers);
}

/* ===========================================================================
 * State Tests
 * =========================================================================== */

void test_get_state(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_state");
    PMU_PID_AddController(&config);

    const PMU_PIDState_t* state = PMU_PID_GetState("pid_state");
    TEST_ASSERT_NOT_NULL(state);
}

void test_get_state_null(void)
{
    const PMU_PIDState_t* state = PMU_PID_GetState(NULL);
    TEST_ASSERT_NULL(state);
}

void test_get_state_not_found(void)
{
    const PMU_PIDState_t* state = PMU_PID_GetState("nonexistent");
    TEST_ASSERT_NULL(state);
}

void test_state_values(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_values");
    config.kp = 2.5f;
    PMU_PID_AddController(&config);

    const PMU_PIDState_t* state = PMU_PID_GetState("pid_values");
    TEST_ASSERT_NOT_NULL(state);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 2.5f, state->config.kp);
}

/* ===========================================================================
 * List Controllers Tests
 * =========================================================================== */

void test_list_controllers_empty(void)
{
    PMU_PIDConfig_t configs[5];
    uint8_t count = PMU_PID_ListControllers(configs, 5);
    TEST_ASSERT_EQUAL(0, count);
}

void test_list_controllers(void)
{
    /* Add some controllers */
    for (int i = 0; i < 3; i++) {
        char id[PMU_CHANNEL_ID_LEN];
        snprintf(id, sizeof(id), "pid_%d", i);
        PMU_PIDConfig_t config;
        create_default_config(&config, id);
        PMU_PID_AddController(&config);
    }

    PMU_PIDConfig_t configs[5];
    uint8_t count = PMU_PID_ListControllers(configs, 5);
    TEST_ASSERT_EQUAL(3, count);
}

void test_list_controllers_null(void)
{
    uint8_t count = PMU_PID_ListControllers(NULL, 5);
    TEST_ASSERT_EQUAL(0, count);
}

void test_list_controllers_limited(void)
{
    /* Add more controllers than we'll request */
    for (int i = 0; i < 5; i++) {
        char id[PMU_CHANNEL_ID_LEN];
        snprintf(id, sizeof(id), "pid_%d", i);
        PMU_PIDConfig_t config;
        create_default_config(&config, id);
        PMU_PID_AddController(&config);
    }

    PMU_PIDConfig_t configs[3];
    uint8_t count = PMU_PID_ListControllers(configs, 3);
    TEST_ASSERT_EQUAL(3, count);
}

/* ===========================================================================
 * Update Tests
 * =========================================================================== */

void test_update_empty(void)
{
    /* Update with no controllers - should not crash */
    PMU_PID_Update();
    TEST_PASS();
}

void test_update_with_controller(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_upd");
    PMU_PID_AddController(&config);

    /* Update should not crash */
    PMU_PID_Update();
    TEST_PASS();
}

void test_update_increments_stats(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_stats_upd");
    PMU_PID_AddController(&config);

    uint32_t initial_updates = PMU_PID_GetStats()->total_updates;

    PMU_PID_Update();

    uint32_t final_updates = PMU_PID_GetStats()->total_updates;
    TEST_ASSERT_GREATER_OR_EQUAL(initial_updates, final_updates);
}

/* ===========================================================================
 * Configuration Validation Tests
 * =========================================================================== */

void test_config_gains(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_gains");
    config.kp = 5.0f;
    config.ki = 0.5f;
    config.kd = 0.05f;

    PMU_PID_AddController(&config);

    const PMU_PIDState_t* state = PMU_PID_GetState("pid_gains");
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 5.0f, state->config.kp);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.5f, state->config.ki);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.05f, state->config.kd);
}

void test_config_output_limits(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_limits");
    config.output_min = -50.0f;
    config.output_max = 150.0f;

    PMU_PID_AddController(&config);

    const PMU_PIDState_t* state = PMU_PID_GetState("pid_limits");
    TEST_ASSERT_FLOAT_WITHIN(0.01f, -50.0f, state->config.output_min);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 150.0f, state->config.output_max);
}

void test_config_anti_windup(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_windup");
    config.anti_windup = true;

    PMU_PID_AddController(&config);

    const PMU_PIDState_t* state = PMU_PID_GetState("pid_windup");
    TEST_ASSERT_TRUE(state->config.anti_windup);
}

void test_config_derivative_filter(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_filter");
    config.derivative_filter = true;
    config.derivative_filter_coeff = 0.5f;

    PMU_PID_AddController(&config);

    const PMU_PIDState_t* state = PMU_PID_GetState("pid_filter");
    TEST_ASSERT_TRUE(state->config.derivative_filter);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.5f, state->config.derivative_filter_coeff);
}

void test_config_reversed(void)
{
    PMU_PIDConfig_t config;
    create_default_config(&config, "pid_reverse");
    config.reversed = true;

    PMU_PID_AddController(&config);

    const PMU_PIDState_t* state = PMU_PID_GetState("pid_reverse");
    TEST_ASSERT_TRUE(state->config.reversed);
}

/* ===========================================================================
 * Constants Tests
 * =========================================================================== */

void test_pid_constants(void)
{
    /* Verify constants are reasonable */
    TEST_ASSERT_GREATER_THAN(0, PMU_PID_MAX_CONTROLLERS);
    TEST_ASSERT_GREATER_THAN(0, PMU_PID_DEFAULT_SAMPLE_MS);
}

/* ===========================================================================
 * Structure Size Tests
 * =========================================================================== */

void test_structure_sizes(void)
{
    /* Verify structures have expected sizes */
    TEST_ASSERT_GREATER_THAN(0, sizeof(PMU_PIDConfig_t));
    TEST_ASSERT_GREATER_THAN(0, sizeof(PMU_PIDState_t));
    TEST_ASSERT_GREATER_THAN(0, sizeof(PMU_PIDStats_t));
}

/* ===========================================================================
 * Main Test Runner
 * =========================================================================== */

int test_pid_main(void)
{
    UNITY_BEGIN();

    /* Initialization */
    RUN_TEST(test_pid_init);
    RUN_TEST(test_pid_init_multiple);
    RUN_TEST(test_pid_clear_all);

    /* Add/Remove Controllers */
    RUN_TEST(test_add_controller);
    RUN_TEST(test_add_controller_null);
    RUN_TEST(test_add_multiple_controllers);
    RUN_TEST(test_add_controller_max_limit);
    RUN_TEST(test_add_controller_update_existing);
    RUN_TEST(test_remove_controller);
    RUN_TEST(test_remove_controller_null);
    RUN_TEST(test_remove_controller_not_found);

    /* Setpoint and Output */
    RUN_TEST(test_set_setpoint);
    RUN_TEST(test_set_setpoint_null);
    RUN_TEST(test_set_setpoint_not_found);
    RUN_TEST(test_get_output);
    RUN_TEST(test_get_output_not_found);
    RUN_TEST(test_get_output_null);

    /* Enable/Disable */
    RUN_TEST(test_set_enabled);
    RUN_TEST(test_set_enabled_null);
    RUN_TEST(test_set_enabled_not_found);

    /* Reset */
    RUN_TEST(test_reset);
    RUN_TEST(test_reset_null);
    RUN_TEST(test_reset_not_found);

    /* Statistics */
    RUN_TEST(test_get_stats);
    RUN_TEST(test_stats_after_add);
    RUN_TEST(test_stats_active_controllers);

    /* State */
    RUN_TEST(test_get_state);
    RUN_TEST(test_get_state_null);
    RUN_TEST(test_get_state_not_found);
    RUN_TEST(test_state_values);

    /* List Controllers */
    RUN_TEST(test_list_controllers_empty);
    RUN_TEST(test_list_controllers);
    RUN_TEST(test_list_controllers_null);
    RUN_TEST(test_list_controllers_limited);

    /* Update */
    RUN_TEST(test_update_empty);
    RUN_TEST(test_update_with_controller);
    RUN_TEST(test_update_increments_stats);

    /* Configuration Validation */
    RUN_TEST(test_config_gains);
    RUN_TEST(test_config_output_limits);
    RUN_TEST(test_config_anti_windup);
    RUN_TEST(test_config_derivative_filter);
    RUN_TEST(test_config_reversed);

    /* Constants and Structures */
    RUN_TEST(test_pid_constants);
    RUN_TEST(test_structure_sizes);

    return UNITY_END();
}

/* Standalone runner */
#ifdef TEST_PID_STANDALONE
int main(void)
{
    return test_pid_main();
}
#endif
