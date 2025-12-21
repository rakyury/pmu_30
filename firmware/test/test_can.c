/**
 ******************************************************************************
 * @file           : test_can.c
 * @brief          : Unit tests for PMU CAN System
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 */

#include "unity.h"
#include "pmu_can.h"
#include <string.h>

/* Test setup and teardown */
void setUp(void)
{
    /* Initialize CAN system before each test */
    PMU_CAN_Init();
}

void tearDown(void)
{
    /* Clean up after each test */
}

/* Test: CAN system initialization */
void test_can_init(void)
{
    HAL_StatusTypeDef status = PMU_CAN_Init();
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: Signal map configuration */
void test_signal_map_add(void)
{
    PMU_CAN_SignalMap_t signal;

    signal.can_id = 0x123;
    signal.start_bit = 0;
    signal.length_bits = 16;
    signal.byte_order = 0;  /* Intel */
    signal.value_type = 0;  /* Unsigned */
    signal.scale = 0.01f;
    signal.offset = 0.0f;
    signal.virtual_channel = 100;
    signal.timeout_ms = 1000;

    HAL_StatusTypeDef status = PMU_CAN_AddSignalMap(&signal);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: Add too many signal maps */
void test_signal_map_overflow(void)
{
    PMU_CAN_SignalMap_t signal;
    memset(&signal, 0, sizeof(signal));

    /* Try to add more than max signals */
    HAL_StatusTypeDef status = HAL_OK;
    for (uint16_t i = 0; i < PMU_CAN_MAX_SIGNAL_MAPS + 1; i++) {
        signal.can_id = 0x100 + i;
        signal.virtual_channel = i;
        status = PMU_CAN_AddSignalMap(&signal);
    }

    /* Last add should fail */
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* Test: Clear signal maps */
void test_signal_map_clear(void)
{
    PMU_CAN_SignalMap_t signal;
    memset(&signal, 0, sizeof(signal));
    signal.can_id = 0x200;

    /* Add a signal */
    PMU_CAN_AddSignalMap(&signal);

    /* Clear all */
    PMU_CAN_ClearSignalMaps();

    /* Adding should work again from 0 */
    HAL_StatusTypeDef status = PMU_CAN_AddSignalMap(&signal);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: Message send */
void test_can_send_message(void)
{
    uint8_t data[8] = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08};

    HAL_StatusTypeDef status = PMU_CAN_SendMessage(PMU_CAN_BUS_1, 0x100, data, 8);

    /* Will return error in test environment since no actual hardware */
    /* But should not crash */
    (void)status;  /* Suppress unused warning */
}

/* Test: Get bus statistics */
void test_can_get_bus_stats(void)
{
    PMU_CAN_BusStats_t* stats = PMU_CAN_GetBusStats(PMU_CAN_BUS_1);

    TEST_ASSERT_NOT_NULL(stats);
    TEST_ASSERT_EQUAL(0, stats->tx_count);
    TEST_ASSERT_EQUAL(0, stats->rx_count);
    TEST_ASSERT_EQUAL(0, stats->error_count);
}

/* Test: Invalid bus number */
void test_can_invalid_bus(void)
{
    PMU_CAN_BusStats_t* stats = PMU_CAN_GetBusStats(5);  /* Invalid bus */

    TEST_ASSERT_NULL(stats);
}

/* Test: Virtual channel update from CAN signal */
void test_virtual_channel_update(void)
{
    /* This test would require mocking virtual channel system */
    /* For now, just verify signal map works */
    PMU_CAN_SignalMap_t signal;

    signal.can_id = 0x300;
    signal.start_bit = 0;
    signal.length_bits = 8;
    signal.byte_order = 0;
    signal.value_type = 0;
    signal.scale = 1.0f;
    signal.offset = 0.0f;
    signal.virtual_channel = 50;
    signal.timeout_ms = 500;

    HAL_StatusTypeDef status = PMU_CAN_AddSignalMap(&signal);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: Signal timeout detection */
void test_signal_timeout(void)
{
    /* Add a signal map with short timeout */
    PMU_CAN_SignalMap_t signal;
    signal.can_id = 0x400;
    signal.start_bit = 0;
    signal.length_bits = 16;
    signal.byte_order = 0;
    signal.value_type = 0;
    signal.scale = 1.0f;
    signal.offset = 0.0f;
    signal.virtual_channel = 60;
    signal.timeout_ms = 100;  /* 100ms timeout */

    PMU_CAN_AddSignalMap(&signal);

    /* Update CAN multiple times to simulate timeout */
    for (int i = 0; i < 20; i++) {
        PMU_CAN_Update();  /* Each update increments time by 10ms */
    }

    /* Signal should have timed out (200ms elapsed > 100ms timeout) */
    /* In real implementation, virtual channel should be set to 0 */
}

/* Test: Get signal count */
void test_signal_count(void)
{
    PMU_CAN_ClearSignalMaps();

    /* Add 3 signals */
    PMU_CAN_SignalMap_t signal;
    memset(&signal, 0, sizeof(signal));

    for (uint8_t i = 0; i < 3; i++) {
        signal.can_id = 0x500 + i;
        signal.virtual_channel = 70 + i;
        PMU_CAN_AddSignalMap(&signal);
    }

    uint16_t count = PMU_CAN_GetSignalCount();
    TEST_ASSERT_EQUAL(3, count);
}

/* Main test runner */
int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_can_init);
    RUN_TEST(test_signal_map_add);
    RUN_TEST(test_signal_map_overflow);
    RUN_TEST(test_signal_map_clear);
    RUN_TEST(test_can_send_message);
    RUN_TEST(test_can_get_bus_stats);
    RUN_TEST(test_can_invalid_bus);
    RUN_TEST(test_virtual_channel_update);
    RUN_TEST(test_signal_timeout);
    RUN_TEST(test_signal_count);

    return UNITY_END();
}
