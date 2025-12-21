/**
 ******************************************************************************
 * @file           : test_protection.c
 * @brief          : Unit tests for PMU Protection System
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 */

#include "unity.h"
#include "pmu_protection.h"
#include <string.h>

/* Test setup and teardown */
void setUp(void)
{
    /* Initialize protection system before each test */
    PMU_Protection_Init();
}

void tearDown(void)
{
    /* Clean up after each test */
}

/* Test: Protection system initialization */
void test_protection_init(void)
{
    HAL_StatusTypeDef status = PMU_Protection_Init();

    TEST_ASSERT_EQUAL(HAL_OK, status);

    PMU_Protection_State_t* state = PMU_Protection_GetState();
    TEST_ASSERT_NOT_NULL(state);
    TEST_ASSERT_EQUAL(PMU_PROT_STATUS_OK, state->status);
    TEST_ASSERT_EQUAL(PMU_PROT_FAULT_NONE, state->fault_flags);
}

/* Test: Voltage monitoring */
void test_voltage_monitoring(void)
{
    PMU_Protection_State_t* state = PMU_Protection_GetState();

    /* Verify voltage thresholds are set correctly */
    TEST_ASSERT_EQUAL(PMU_VOLTAGE_MIN, state->voltage.voltage_min_mV);
    TEST_ASSERT_EQUAL(PMU_VOLTAGE_MAX, state->voltage.voltage_max_mV);
    TEST_ASSERT_EQUAL(PMU_VOLTAGE_WARN_LOW, state->voltage.voltage_warn_low_mV);
    TEST_ASSERT_EQUAL(PMU_VOLTAGE_WARN_HIGH, state->voltage.voltage_warn_high_mV);
}

/* Test: Temperature monitoring */
void test_temperature_monitoring(void)
{
    PMU_Protection_State_t* state = PMU_Protection_GetState();

    /* Verify temperature thresholds */
    TEST_ASSERT_EQUAL(PMU_TEMP_WARNING, state->temperature.temp_warn_C);
    TEST_ASSERT_EQUAL(PMU_TEMP_CRITICAL, state->temperature.temp_critical_C);
}

/* Test: Power monitoring */
void test_power_monitoring(void)
{
    PMU_Protection_State_t* state = PMU_Protection_GetState();

    /* Verify power limits */
    TEST_ASSERT_EQUAL(PMU_TOTAL_CURRENT_MAX_MA, state->power.max_current_mA);
    TEST_ASSERT_EQUAL(PMU_TOTAL_POWER_MAX_W, state->power.max_power_W);
}

/* Test: Fault detection - undervoltage */
void test_fault_undervoltage(void)
{
    PMU_Protection_State_t* state = PMU_Protection_GetState();

    /* Simulate undervoltage by setting low voltage */
    state->voltage.voltage_mV = 5000;  /* 5V - below 6V minimum */

    /* Run protection update multiple times to exceed threshold */
    for (int i = 0; i < PMU_FAULT_THRESHOLD + 1; i++) {
        PMU_Protection_Update();
    }

    /* Check if undervoltage fault is detected */
    TEST_ASSERT_TRUE(state->fault_flags & PMU_PROT_FAULT_UNDERVOLTAGE);
    TEST_ASSERT_EQUAL(PMU_PROT_STATUS_CRITICAL, state->status);
}

/* Test: Fault recovery */
void test_fault_recovery(void)
{
    PMU_Protection_State_t* state = PMU_Protection_GetState();

    /* Set a fault */
    state->fault_flags = PMU_PROT_FAULT_OVERTEMP_WARNING;
    state->status = PMU_PROT_STATUS_FAULT;

    /* Clear faults */
    HAL_StatusTypeDef status = PMU_Protection_ClearFaults();

    TEST_ASSERT_EQUAL(HAL_OK, status);
    TEST_ASSERT_EQUAL(PMU_PROT_FAULT_NONE, state->fault_flags);
    TEST_ASSERT_EQUAL(PMU_PROT_STATUS_OK, state->status);
}

/* Test: Fault recovery blocked in critical state */
void test_fault_recovery_critical_blocked(void)
{
    PMU_Protection_State_t* state = PMU_Protection_GetState();

    /* Set critical fault */
    state->fault_flags = PMU_PROT_FAULT_OVERTEMP_CRITICAL;
    state->status = PMU_PROT_STATUS_CRITICAL;

    /* Try to clear faults - should fail */
    HAL_StatusTypeDef status = PMU_Protection_ClearFaults();

    TEST_ASSERT_EQUAL(HAL_ERROR, status);
    TEST_ASSERT_NOT_EQUAL(PMU_PROT_FAULT_NONE, state->fault_flags);
}

/* Test: Load shedding enable/disable */
void test_load_shedding(void)
{
    PMU_Protection_State_t* state = PMU_Protection_GetState();

    /* Enable load shedding */
    PMU_Protection_SetLoadShedding(1);
    TEST_ASSERT_EQUAL(1, state->load_shedding_active);

    /* Disable load shedding */
    PMU_Protection_SetLoadShedding(0);
    TEST_ASSERT_EQUAL(0, state->load_shedding_active);
}

/* Test: Uptime counter */
void test_uptime_counter(void)
{
    PMU_Protection_State_t* state = PMU_Protection_GetState();
    uint32_t initial_uptime = state->uptime_seconds;

    /* Run update 1000 times (1 second at 1kHz) */
    for (int i = 0; i < 1000; i++) {
        PMU_Protection_Update();
    }

    /* Uptime should have incremented by 1 second */
    TEST_ASSERT_EQUAL(initial_uptime + 1, state->uptime_seconds);
}

/* Test: Getter functions */
void test_getter_functions(void)
{
    PMU_Protection_State_t* state = PMU_Protection_GetState();

    /* Set known values */
    state->voltage.voltage_mV = 12000;
    state->temperature.board_temp_C = 45;
    state->power.total_current_mA = 15000;

    /* Test getters */
    TEST_ASSERT_EQUAL(12000, PMU_Protection_GetVoltage());
    TEST_ASSERT_EQUAL(45, PMU_Protection_GetTemperature());
    TEST_ASSERT_EQUAL(15000, PMU_Protection_GetTotalCurrent());
}

/* Test: Fault state check */
void test_is_faulted(void)
{
    PMU_Protection_State_t* state = PMU_Protection_GetState();

    /* No fault initially */
    state->status = PMU_PROT_STATUS_OK;
    TEST_ASSERT_EQUAL(0, PMU_Protection_IsFaulted());

    /* Set warning (not faulted) */
    state->status = PMU_PROT_STATUS_WARNING;
    TEST_ASSERT_EQUAL(0, PMU_Protection_IsFaulted());

    /* Set fault */
    state->status = PMU_PROT_STATUS_FAULT;
    TEST_ASSERT_EQUAL(1, PMU_Protection_IsFaulted());

    /* Set critical */
    state->status = PMU_PROT_STATUS_CRITICAL;
    TEST_ASSERT_EQUAL(1, PMU_Protection_IsFaulted());
}

/* Main test runner */
int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_protection_init);
    RUN_TEST(test_voltage_monitoring);
    RUN_TEST(test_temperature_monitoring);
    RUN_TEST(test_power_monitoring);
    RUN_TEST(test_fault_undervoltage);
    RUN_TEST(test_fault_recovery);
    RUN_TEST(test_fault_recovery_critical_blocked);
    RUN_TEST(test_load_shedding);
    RUN_TEST(test_uptime_counter);
    RUN_TEST(test_getter_functions);
    RUN_TEST(test_is_faulted);

    return UNITY_END();
}
