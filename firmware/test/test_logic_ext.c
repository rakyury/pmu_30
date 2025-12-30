/**
 ******************************************************************************
 * @file           : test_logic_ext.c
 * @brief          : Extended unit tests for PMU Logic Engine
 * @author         : R2 m-sport
 * @date           : 2025-12-26
 ******************************************************************************
 *
 * Tests for logic operations, virtual channels, timers, and counters.
 * Extends existing test coverage with more comprehensive scenarios.
 *
 ******************************************************************************
 */

#include "unity.h"
#include "pmu_logic.h"
#include <string.h>
#include <math.h>

/* Test setup and teardown */
void setUp(void)
{
    /* Initialize logic engine before each test */
    PMU_Logic_Init();
}

void tearDown(void)
{
    /* Clean up after each test */
}

/* ===========================================================================
 * Initialization Tests
 * =========================================================================== */

void test_logic_init(void)
{
    HAL_StatusTypeDef status = PMU_Logic_Init();
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_logic_init_multiple(void)
{
    /* Multiple init calls should be safe */
    for (int i = 0; i < 3; i++) {
        HAL_StatusTypeDef status = PMU_Logic_Init();
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }
}

/* ===========================================================================
 * Virtual Channel Tests
 * =========================================================================== */

void test_vchannel_set_get(void)
{
    /* Set and get virtual channel value */
    HAL_StatusTypeDef status = PMU_Logic_SetVChannel(0, 100.0f);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    float value = PMU_Logic_GetVChannel(0);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 100.0f, value);
}

void test_vchannel_multiple(void)
{
    /* Set multiple virtual channels */
    for (uint16_t i = 0; i < 10; i++) {
        HAL_StatusTypeDef status = PMU_Logic_SetVChannel(i, (float)i * 10.0f);
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }

    /* Verify all values */
    for (uint16_t i = 0; i < 10; i++) {
        float value = PMU_Logic_GetVChannel(i);
        TEST_ASSERT_FLOAT_WITHIN(0.01f, (float)i * 10.0f, value);
    }
}

void test_vchannel_negative_value(void)
{
    /* Test negative values */
    PMU_Logic_SetVChannel(5, -50.0f);
    float value = PMU_Logic_GetVChannel(5);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, -50.0f, value);
}

void test_vchannel_zero_value(void)
{
    /* Test zero value */
    PMU_Logic_SetVChannel(6, 0.0f);
    float value = PMU_Logic_GetVChannel(6);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.0f, value);
}

void test_vchannel_large_value(void)
{
    /* Test large value */
    PMU_Logic_SetVChannel(7, 100000.0f);
    float value = PMU_Logic_GetVChannel(7);
    TEST_ASSERT_FLOAT_WITHIN(1.0f, 100000.0f, value);
}

void test_vchannel_invalid_index(void)
{
    /* Test invalid index - should return 0 */
    float value = PMU_Logic_GetVChannel(PMU_LOGIC_MAX_VCHANNELS);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.0f, value);
}

void test_vchannel_overwrite(void)
{
    /* Set, then overwrite */
    PMU_Logic_SetVChannel(10, 100.0f);
    PMU_Logic_SetVChannel(10, 200.0f);

    float value = PMU_Logic_GetVChannel(10);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 200.0f, value);
}

/* ===========================================================================
 * Logic Function Tests
 * =========================================================================== */

void test_add_function(void)
{
    PMU_Logic_Function_t func;
    memset(&func, 0, sizeof(func));

    func.enabled = 1;
    func.operation_count = 1;
    func.operations[0].operation = LOGIC_OP_SET;
    func.operations[0].output = 50;
    func.operations[0].use_constant_a = 1;
    func.operations[0].constant_a = 42.0f;
    strncpy(func.name, "Test Function", sizeof(func.name));

    HAL_StatusTypeDef status = PMU_Logic_AddFunction(0, &func);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_add_function_null(void)
{
    HAL_StatusTypeDef status = PMU_Logic_AddFunction(0, NULL);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_add_function_invalid_index(void)
{
    PMU_Logic_Function_t func;
    memset(&func, 0, sizeof(func));
    func.enabled = 1;

    HAL_StatusTypeDef status = PMU_Logic_AddFunction(PMU_LOGIC_MAX_FUNCTIONS, &func);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_enable_function(void)
{
    PMU_Logic_Function_t func;
    memset(&func, 0, sizeof(func));
    func.enabled = 1;
    func.operation_count = 0;

    PMU_Logic_AddFunction(5, &func);

    /* Disable */
    HAL_StatusTypeDef status = PMU_Logic_EnableFunction(5, 0);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    /* Re-enable */
    status = PMU_Logic_EnableFunction(5, 1);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_enable_function_invalid_index(void)
{
    HAL_StatusTypeDef status = PMU_Logic_EnableFunction(PMU_LOGIC_MAX_FUNCTIONS, 1);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * Timer Tests
 * =========================================================================== */

void test_timer_start(void)
{
    HAL_StatusTypeDef status = PMU_Logic_StartTimer(0, 1000);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_timer_not_expired_immediately(void)
{
    PMU_Logic_StartTimer(1, 1000);

    /* Timer should not be expired immediately after start */
    uint8_t expired = PMU_Logic_TimerExpired(1);
    TEST_ASSERT_EQUAL(0, expired);
}

void test_timer_invalid_index(void)
{
    HAL_StatusTypeDef status = PMU_Logic_StartTimer(PMU_LOGIC_MAX_TIMERS, 1000);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_timer_expired_invalid_index(void)
{
    uint8_t expired = PMU_Logic_TimerExpired(PMU_LOGIC_MAX_TIMERS);
    TEST_ASSERT_EQUAL(0, expired);
}

void test_timer_zero_duration(void)
{
    /* Zero duration timer should expire immediately */
    PMU_Logic_StartTimer(2, 0);

    /* Execute logic to process timer */
    PMU_Logic_Execute();

    uint8_t expired = PMU_Logic_TimerExpired(2);
    TEST_ASSERT_EQUAL(1, expired);
}

void test_timer_restart(void)
{
    /* Start timer */
    PMU_Logic_StartTimer(3, 1000);

    /* Restart with different duration */
    HAL_StatusTypeDef status = PMU_Logic_StartTimer(3, 2000);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* ===========================================================================
 * Execute Tests
 * =========================================================================== */

void test_execute_empty(void)
{
    /* Execute with no functions configured - should not crash */
    PMU_Logic_Execute();
    TEST_PASS();
}

void test_execute_with_function(void)
{
    PMU_Logic_Function_t func;
    memset(&func, 0, sizeof(func));

    func.enabled = 1;
    func.operation_count = 1;
    func.operations[0].operation = LOGIC_OP_SET;
    func.operations[0].output = 100;
    func.operations[0].use_constant_a = 1;
    func.operations[0].constant_a = 42.0f;

    PMU_Logic_AddFunction(0, &func);

    /* Execute logic */
    PMU_Logic_Execute();

    /* Check output channel has the value */
    float value = PMU_Logic_GetVChannel(100);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 42.0f, value);
}

void test_execute_disabled_function(void)
{
    PMU_Logic_Function_t func;
    memset(&func, 0, sizeof(func));

    func.enabled = 0;  /* Disabled */
    func.operation_count = 1;
    func.operations[0].operation = LOGIC_OP_SET;
    func.operations[0].output = 101;
    func.operations[0].use_constant_a = 1;
    func.operations[0].constant_a = 99.0f;

    PMU_Logic_AddFunction(1, &func);

    /* Clear output first */
    PMU_Logic_SetVChannel(101, 0.0f);

    /* Execute logic */
    PMU_Logic_Execute();

    /* Disabled function should not affect output */
    float value = PMU_Logic_GetVChannel(101);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 0.0f, value);
}

/* ===========================================================================
 * Update/Apply Tests
 * =========================================================================== */

void test_update_vchannels(void)
{
    /* Should not crash */
    PMU_Logic_UpdateVChannels();
    TEST_PASS();
}

void test_apply_outputs(void)
{
    /* Should not crash */
    PMU_Logic_ApplyOutputs();
    TEST_PASS();
}

/* ===========================================================================
 * Operation Enum Tests
 * =========================================================================== */

void test_operation_enum_values(void)
{
    /* Verify operation enum starts at 0 and is sequential */
    TEST_ASSERT_EQUAL(0, LOGIC_OP_AND);
    TEST_ASSERT_EQUAL(1, LOGIC_OP_OR);
    TEST_ASSERT_EQUAL(2, LOGIC_OP_NOT);
    TEST_ASSERT_EQUAL(3, LOGIC_OP_XOR);

    /* Verify comparison operations */
    TEST_ASSERT_EQUAL(4, LOGIC_OP_GREATER);
    TEST_ASSERT_EQUAL(5, LOGIC_OP_LESS);
    TEST_ASSERT_EQUAL(6, LOGIC_OP_EQUAL);
}

void test_vchan_type_enum_values(void)
{
    /* Verify virtual channel type enum */
    TEST_ASSERT_EQUAL(0, VCHAN_TYPE_CONSTANT);
    TEST_ASSERT_EQUAL(1, VCHAN_TYPE_ADC_INPUT);
    TEST_ASSERT_EQUAL(2, VCHAN_TYPE_PROFET_OUTPUT);
    TEST_ASSERT_LESS_THAN(256, VCHAN_TYPE_COUNT);
}

/* ===========================================================================
 * Constants Tests
 * =========================================================================== */

void test_logic_constants(void)
{
    /* Verify constants are reasonable */
    TEST_ASSERT_GREATER_THAN(0, PMU_LOGIC_MAX_FUNCTIONS);
    TEST_ASSERT_GREATER_THAN(0, PMU_LOGIC_MAX_OPERATIONS);
    TEST_ASSERT_GREATER_THAN(0, PMU_LOGIC_MAX_VCHANNELS);
    TEST_ASSERT_GREATER_THAN(0, PMU_LOGIC_MAX_TIMERS);
    TEST_ASSERT_GREATER_THAN(0, PMU_LOGIC_MAX_COUNTERS);
    TEST_ASSERT_GREATER_THAN(0, PMU_LOGIC_MAX_HYSTERESIS);
}

/* ===========================================================================
 * Structure Size Tests
 * =========================================================================== */

void test_structure_sizes(void)
{
    /* Verify structures have expected sizes */
    TEST_ASSERT_GREATER_THAN(0, sizeof(PMU_VChannel_t));
    TEST_ASSERT_GREATER_THAN(0, sizeof(PMU_Logic_Operation_t));
    TEST_ASSERT_GREATER_THAN(0, sizeof(PMU_Logic_Function_t));
    TEST_ASSERT_GREATER_THAN(0, sizeof(PMU_Logic_Timer_t));
    TEST_ASSERT_GREATER_THAN(0, sizeof(PMU_Logic_Counter_t));
    TEST_ASSERT_GREATER_THAN(0, sizeof(PMU_Logic_Hysteresis_t));
}

/* ===========================================================================
 * Main Test Runner
 * =========================================================================== */

int test_logic_ext_main(void)
{
    UNITY_BEGIN();

    /* Initialization */
    RUN_TEST(test_logic_init);
    RUN_TEST(test_logic_init_multiple);

    /* Virtual Channels */
    RUN_TEST(test_vchannel_set_get);
    RUN_TEST(test_vchannel_multiple);
    RUN_TEST(test_vchannel_negative_value);
    RUN_TEST(test_vchannel_zero_value);
    RUN_TEST(test_vchannel_large_value);
    RUN_TEST(test_vchannel_invalid_index);
    RUN_TEST(test_vchannel_overwrite);

    /* Logic Functions */
    RUN_TEST(test_add_function);
    RUN_TEST(test_add_function_null);
    RUN_TEST(test_add_function_invalid_index);
    RUN_TEST(test_enable_function);
    RUN_TEST(test_enable_function_invalid_index);

    /* Timers */
    RUN_TEST(test_timer_start);
    RUN_TEST(test_timer_not_expired_immediately);
    RUN_TEST(test_timer_invalid_index);
    RUN_TEST(test_timer_expired_invalid_index);
    RUN_TEST(test_timer_zero_duration);
    RUN_TEST(test_timer_restart);

    /* Execute */
    RUN_TEST(test_execute_empty);
    RUN_TEST(test_execute_with_function);
    RUN_TEST(test_execute_disabled_function);

    /* Update/Apply */
    RUN_TEST(test_update_vchannels);
    RUN_TEST(test_apply_outputs);

    /* Enums */
    RUN_TEST(test_operation_enum_values);
    RUN_TEST(test_vchan_type_enum_values);

    /* Constants */
    RUN_TEST(test_logic_constants);

    /* Structures */
    RUN_TEST(test_structure_sizes);

    return UNITY_END();
}

/* Standalone runner */
#ifdef TEST_LOGIC_EXT_STANDALONE
int main(void)
{
    return test_logic_ext_main();
}
#endif
