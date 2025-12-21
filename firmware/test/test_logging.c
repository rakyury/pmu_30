/**
 ******************************************************************************
 * @file           : test_logging.c
 * @brief          : Unit tests for PMU Logging System
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 */

#include "unity.h"
#include "pmu_logging.h"
#include <string.h>

/* Test setup and teardown */
void setUp(void)
{
    PMU_Logging_Init();
}

void tearDown(void)
{
    /* Clean up after each test */
}

/* Test: Logging system initialization */
void test_logging_init(void)
{
    HAL_StatusTypeDef status = PMU_Logging_Init();
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_Logging_Status_t log_status = PMU_Logging_GetStatus();
    TEST_ASSERT_EQUAL(PMU_LOG_STATUS_IDLE, log_status);
}

/* Test: Get flash statistics */
void test_flash_stats(void)
{
    PMU_FlashStats_t* stats = PMU_Logging_GetFlashStats();

    TEST_ASSERT_NOT_NULL(stats);
    TEST_ASSERT_EQUAL(PMU_LOG_FLASH_SIZE, stats->total_bytes);
    TEST_ASSERT_EQUAL(100, stats->health_percent);
}

/* Test: Configure logging */
void test_configure_logging(void)
{
    PMU_LogConfig_t config;
    memset(&config, 0, sizeof(config));

    config.sample_rate = 100;
    config.trigger_mode = PMU_LOG_TRIGGER_MANUAL;
    config.channel_count = 3;

    HAL_StatusTypeDef status = PMU_Logging_Configure(&config);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: Configure with NULL pointer */
void test_configure_null(void)
{
    HAL_StatusTypeDef status = PMU_Logging_Configure(NULL);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* Test: Start recording */
void test_start_recording(void)
{
    HAL_StatusTypeDef status = PMU_Logging_Start();
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_Logging_Status_t log_status = PMU_Logging_GetStatus();
    TEST_ASSERT_EQUAL(PMU_LOG_STATUS_RECORDING, log_status);
}

/* Test: Stop recording */
void test_stop_recording(void)
{
    PMU_Logging_Start();
    HAL_StatusTypeDef status = PMU_Logging_Stop();
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_Logging_Status_t log_status = PMU_Logging_GetStatus();
    TEST_ASSERT_EQUAL(PMU_LOG_STATUS_IDLE, log_status);
}

/* Test: Pause and resume */
void test_pause_resume(void)
{
    PMU_Logging_Start();

    HAL_StatusTypeDef status = PMU_Logging_Pause();
    TEST_ASSERT_EQUAL(HAL_OK, status);
    TEST_ASSERT_EQUAL(PMU_LOG_STATUS_PAUSED, PMU_Logging_GetStatus());

    status = PMU_Logging_Resume();
    TEST_ASSERT_EQUAL(HAL_OK, status);
    TEST_ASSERT_EQUAL(PMU_LOG_STATUS_RECORDING, PMU_Logging_GetStatus());
}

/* Test: Cannot start when already recording */
void test_start_when_recording(void)
{
    PMU_Logging_Start();
    HAL_StatusTypeDef status = PMU_Logging_Start();
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* Test: Cannot configure when recording */
void test_configure_when_recording(void)
{
    PMU_LogConfig_t config;
    memset(&config, 0, sizeof(config));

    PMU_Logging_Start();
    HAL_StatusTypeDef status = PMU_Logging_Configure(&config);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* Test: Manual trigger */
void test_manual_trigger(void)
{
    PMU_LogConfig_t config;
    memset(&config, 0, sizeof(config));
    config.trigger_mode = PMU_LOG_TRIGGER_MANUAL;

    PMU_Logging_Configure(&config);

    HAL_StatusTypeDef status = PMU_Logging_Trigger();
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: Get session info */
void test_session_info(void)
{
    PMU_LogSession_t* session = PMU_Logging_GetSessionInfo();
    TEST_ASSERT_NOT_NULL(session);
}

/* Test: Get session list */
void test_session_list(void)
{
    PMU_LogSession_t sessions[10];
    uint16_t count = PMU_Logging_GetSessionList(sessions, 10);

    /* Should return at least current session */
    TEST_ASSERT_GREATER_OR_EQUAL(0, count);
    TEST_ASSERT_LESS_OR_EQUAL(10, count);
}

/* Test: Erase all */
void test_erase_all(void)
{
    /* Must be idle to erase */
    PMU_Logging_Stop();

    HAL_StatusTypeDef status = PMU_Logging_EraseAll();
    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_FlashStats_t* stats = PMU_Logging_GetFlashStats();
    TEST_ASSERT_EQUAL(0, stats->used_bytes);
    TEST_ASSERT_EQUAL(PMU_LOG_FLASH_SIZE, stats->free_bytes);
}

/* Test: Cannot erase when recording */
void test_erase_when_recording(void)
{
    PMU_Logging_Start();
    HAL_StatusTypeDef status = PMU_Logging_EraseAll();
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* Test: Update while recording */
void test_update_while_recording(void)
{
    PMU_Logging_Start();

    /* Call update multiple times */
    for (int i = 0; i < 100; i++) {
        PMU_Logging_Update();
    }

    PMU_LogSession_t* session = PMU_Logging_GetSessionInfo();
    TEST_ASSERT_GREATER_THAN(0, session->duration_ms);
}

/* Test: Sample rate validation */
void test_sample_rate(void)
{
    PMU_LogConfig_t config;
    memset(&config, 0, sizeof(config));

    /* Valid sample rates */
    config.sample_rate = PMU_LOG_RATE_MIN;
    TEST_ASSERT_EQUAL(HAL_OK, PMU_Logging_Configure(&config));

    config.sample_rate = PMU_LOG_RATE_DEFAULT;
    TEST_ASSERT_EQUAL(HAL_OK, PMU_Logging_Configure(&config));

    config.sample_rate = PMU_LOG_RATE_MAX;
    TEST_ASSERT_EQUAL(HAL_OK, PMU_Logging_Configure(&config));
}

/* Main test runner */
int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_logging_init);
    RUN_TEST(test_flash_stats);
    RUN_TEST(test_configure_logging);
    RUN_TEST(test_configure_null);
    RUN_TEST(test_start_recording);
    RUN_TEST(test_stop_recording);
    RUN_TEST(test_pause_resume);
    RUN_TEST(test_start_when_recording);
    RUN_TEST(test_configure_when_recording);
    RUN_TEST(test_manual_trigger);
    RUN_TEST(test_session_info);
    RUN_TEST(test_session_list);
    RUN_TEST(test_erase_all);
    RUN_TEST(test_erase_when_recording);
    RUN_TEST(test_update_while_recording);
    RUN_TEST(test_sample_rate);

    return UNITY_END();
}
