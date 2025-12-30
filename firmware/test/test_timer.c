/**
 ******************************************************************************
 * @file           : test_timer.c
 * @brief          : Unit tests for PMU Timer Channel System
 * @author         : R2 m-sport
 * @date           : 2025-12-26
 ******************************************************************************
 */

#include "unity.h"
#include "pmu_timer.h"
#include <string.h>

void setUp(void)
{
    PMU_Timer_Init();
}

void tearDown(void)
{
    PMU_Timer_ClearAll();
}

/* ===========================================================================
 * Initialization Tests
 * =========================================================================== */

void test_timer_init(void)
{
    HAL_StatusTypeDef status = PMU_Timer_Init();
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_timer_init_multiple(void)
{
    for (int i = 0; i < 3; i++) {
        HAL_StatusTypeDef status = PMU_Timer_Init();
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }
}

/* ===========================================================================
 * Add Timer Tests
 * =========================================================================== */

void test_add_timer(void)
{
    PMU_TimerConfig_t config;
    memset(&config, 0, sizeof(config));

    strncpy(config.id, "test_timer1", sizeof(config.id));
    config.mode = PMU_TIMER_MODE_STOPWATCH;
    config.limit_ms = 5000;

    HAL_StatusTypeDef status = PMU_Timer_AddTimer(&config);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_add_timer_null(void)
{
    HAL_StatusTypeDef status = PMU_Timer_AddTimer(NULL);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_add_multiple_timers(void)
{
    PMU_TimerConfig_t config;

    for (int i = 0; i < 5; i++) {
        memset(&config, 0, sizeof(config));
        snprintf(config.id, sizeof(config.id), "timer_%d", i);
        config.mode = PMU_TIMER_MODE_STOPWATCH;
        config.limit_ms = 1000 * (i + 1);

        HAL_StatusTypeDef status = PMU_Timer_AddTimer(&config);
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }

    const PMU_TimerStats_t* stats = PMU_Timer_GetStats();
    TEST_ASSERT_EQUAL(5, stats->total_timers);
}

void test_add_timer_max(void)
{
    PMU_TimerConfig_t config;

    /* Add maximum timers */
    for (int i = 0; i < PMU_TIMER_MAX_TIMERS; i++) {
        memset(&config, 0, sizeof(config));
        snprintf(config.id, sizeof(config.id), "timer_%d", i);
        config.mode = PMU_TIMER_MODE_COUNTDOWN;
        config.limit_ms = 1000;

        HAL_StatusTypeDef status = PMU_Timer_AddTimer(&config);
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }

    /* One more should fail */
    memset(&config, 0, sizeof(config));
    strncpy(config.id, "overflow_timer", sizeof(config.id));
    HAL_StatusTypeDef status = PMU_Timer_AddTimer(&config);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * Remove Timer Tests
 * =========================================================================== */

void test_remove_timer(void)
{
    PMU_TimerConfig_t config;
    memset(&config, 0, sizeof(config));
    strncpy(config.id, "removable", sizeof(config.id));
    PMU_Timer_AddTimer(&config);

    HAL_StatusTypeDef status = PMU_Timer_RemoveTimer("removable");
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_remove_timer_nonexistent(void)
{
    HAL_StatusTypeDef status = PMU_Timer_RemoveTimer("nonexistent");
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_remove_timer_null(void)
{
    HAL_StatusTypeDef status = PMU_Timer_RemoveTimer(NULL);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * Clear All Tests
 * =========================================================================== */

void test_clear_all(void)
{
    PMU_TimerConfig_t config;

    for (int i = 0; i < 3; i++) {
        memset(&config, 0, sizeof(config));
        snprintf(config.id, sizeof(config.id), "clear_t%d", i);
        PMU_Timer_AddTimer(&config);
    }

    HAL_StatusTypeDef status = PMU_Timer_ClearAll();
    TEST_ASSERT_EQUAL(HAL_OK, status);

    const PMU_TimerStats_t* stats = PMU_Timer_GetStats();
    TEST_ASSERT_EQUAL(0, stats->total_timers);
}

/* ===========================================================================
 * Start/Stop/Reset Tests
 * =========================================================================== */

void test_start_timer(void)
{
    PMU_TimerConfig_t config;
    memset(&config, 0, sizeof(config));
    strncpy(config.id, "startable", sizeof(config.id));
    config.mode = PMU_TIMER_MODE_STOPWATCH;
    PMU_Timer_AddTimer(&config);

    HAL_StatusTypeDef status = PMU_Timer_Start("startable");
    TEST_ASSERT_EQUAL(HAL_OK, status);

    TEST_ASSERT_TRUE(PMU_Timer_IsRunning("startable"));
}

void test_stop_timer(void)
{
    PMU_TimerConfig_t config;
    memset(&config, 0, sizeof(config));
    strncpy(config.id, "stoppable", sizeof(config.id));
    config.mode = PMU_TIMER_MODE_STOPWATCH;
    PMU_Timer_AddTimer(&config);

    PMU_Timer_Start("stoppable");
    HAL_StatusTypeDef status = PMU_Timer_Stop("stoppable");
    TEST_ASSERT_EQUAL(HAL_OK, status);

    TEST_ASSERT_FALSE(PMU_Timer_IsRunning("stoppable"));
}

void test_reset_timer(void)
{
    PMU_TimerConfig_t config;
    memset(&config, 0, sizeof(config));
    strncpy(config.id, "resettable", sizeof(config.id));
    config.mode = PMU_TIMER_MODE_STOPWATCH;
    PMU_Timer_AddTimer(&config);

    HAL_StatusTypeDef status = PMU_Timer_Reset("resettable");
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_start_nonexistent(void)
{
    HAL_StatusTypeDef status = PMU_Timer_Start("nonexistent");
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_stop_nonexistent(void)
{
    HAL_StatusTypeDef status = PMU_Timer_Stop("nonexistent");
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * Value/State Tests
 * =========================================================================== */

void test_get_value(void)
{
    PMU_TimerConfig_t config;
    memset(&config, 0, sizeof(config));
    strncpy(config.id, "valued", sizeof(config.id));
    PMU_Timer_AddTimer(&config);

    float value = PMU_Timer_GetValue("valued");
    TEST_ASSERT_GREATER_OR_EQUAL(0.0f, value);
}

void test_get_value_nonexistent(void)
{
    float value = PMU_Timer_GetValue("nonexistent");
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, value);
}

void test_is_running_false_initially(void)
{
    PMU_TimerConfig_t config;
    memset(&config, 0, sizeof(config));
    strncpy(config.id, "check_run", sizeof(config.id));
    PMU_Timer_AddTimer(&config);

    TEST_ASSERT_FALSE(PMU_Timer_IsRunning("check_run"));
}

void test_is_expired_false_initially(void)
{
    PMU_TimerConfig_t config;
    memset(&config, 0, sizeof(config));
    strncpy(config.id, "check_exp", sizeof(config.id));
    PMU_Timer_AddTimer(&config);

    TEST_ASSERT_FALSE(PMU_Timer_IsExpired("check_exp"));
}

/* ===========================================================================
 * State Structure Tests
 * =========================================================================== */

void test_get_state(void)
{
    PMU_TimerConfig_t config;
    memset(&config, 0, sizeof(config));
    strncpy(config.id, "stateful", sizeof(config.id));
    config.mode = PMU_TIMER_MODE_COUNTDOWN;
    config.limit_ms = 3000;
    PMU_Timer_AddTimer(&config);

    const PMU_TimerState_t* state = PMU_Timer_GetState("stateful");
    TEST_ASSERT_NOT_NULL(state);
    TEST_ASSERT_EQUAL(3000, state->limit_ms);
}

void test_get_state_nonexistent(void)
{
    const PMU_TimerState_t* state = PMU_Timer_GetState("nonexistent");
    TEST_ASSERT_NULL(state);
}

/* ===========================================================================
 * Statistics Tests
 * =========================================================================== */

void test_get_stats(void)
{
    const PMU_TimerStats_t* stats = PMU_Timer_GetStats();
    TEST_ASSERT_NOT_NULL(stats);
    TEST_ASSERT_EQUAL(0, stats->total_timers);
}

void test_stats_updated(void)
{
    PMU_TimerConfig_t config;
    memset(&config, 0, sizeof(config));
    strncpy(config.id, "stat_timer", sizeof(config.id));
    PMU_Timer_AddTimer(&config);

    const PMU_TimerStats_t* stats = PMU_Timer_GetStats();
    TEST_ASSERT_EQUAL(1, stats->total_timers);
}

/* ===========================================================================
 * List Timers Tests
 * =========================================================================== */

void test_list_timers(void)
{
    PMU_TimerConfig_t config;

    for (int i = 0; i < 3; i++) {
        memset(&config, 0, sizeof(config));
        snprintf(config.id, sizeof(config.id), "list_%d", i);
        PMU_Timer_AddTimer(&config);
    }

    PMU_TimerConfig_t configs[10];
    uint8_t count = PMU_Timer_ListTimers(configs, 10);
    TEST_ASSERT_EQUAL(3, count);
}

void test_list_timers_limited(void)
{
    PMU_TimerConfig_t config;

    for (int i = 0; i < 5; i++) {
        memset(&config, 0, sizeof(config));
        snprintf(config.id, sizeof(config.id), "lim_%d", i);
        PMU_Timer_AddTimer(&config);
    }

    PMU_TimerConfig_t configs[3];
    uint8_t count = PMU_Timer_ListTimers(configs, 3);
    TEST_ASSERT_EQUAL(3, count);
}

/* ===========================================================================
 * Update Tests
 * =========================================================================== */

void test_update(void)
{
    PMU_Timer_Update();
    TEST_PASS();
}

void test_update_with_running_timer(void)
{
    PMU_TimerConfig_t config;
    memset(&config, 0, sizeof(config));
    strncpy(config.id, "running", sizeof(config.id));
    config.mode = PMU_TIMER_MODE_STOPWATCH;
    PMU_Timer_AddTimer(&config);
    PMU_Timer_Start("running");

    for (int i = 0; i < 10; i++) {
        PMU_Timer_Update();
    }
    TEST_PASS();
}

/* ===========================================================================
 * Constants Tests
 * =========================================================================== */

void test_timer_constants(void)
{
    TEST_ASSERT_EQUAL(16, PMU_TIMER_MAX_TIMERS);
}

/* ===========================================================================
 * Main Test Runner
 * =========================================================================== */

int test_timer_main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_timer_init);
    RUN_TEST(test_timer_init_multiple);

    RUN_TEST(test_add_timer);
    RUN_TEST(test_add_timer_null);
    RUN_TEST(test_add_multiple_timers);
    RUN_TEST(test_add_timer_max);

    RUN_TEST(test_remove_timer);
    RUN_TEST(test_remove_timer_nonexistent);
    RUN_TEST(test_remove_timer_null);

    RUN_TEST(test_clear_all);

    RUN_TEST(test_start_timer);
    RUN_TEST(test_stop_timer);
    RUN_TEST(test_reset_timer);
    RUN_TEST(test_start_nonexistent);
    RUN_TEST(test_stop_nonexistent);

    RUN_TEST(test_get_value);
    RUN_TEST(test_get_value_nonexistent);
    RUN_TEST(test_is_running_false_initially);
    RUN_TEST(test_is_expired_false_initially);

    RUN_TEST(test_get_state);
    RUN_TEST(test_get_state_nonexistent);

    RUN_TEST(test_get_stats);
    RUN_TEST(test_stats_updated);

    RUN_TEST(test_list_timers);
    RUN_TEST(test_list_timers_limited);

    RUN_TEST(test_update);
    RUN_TEST(test_update_with_running_timer);

    RUN_TEST(test_timer_constants);

    return UNITY_END();
}

#ifdef TEST_TIMER_STANDALONE
int main(void) { return test_timer_main(); }
#endif
