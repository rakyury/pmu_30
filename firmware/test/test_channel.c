/**
 ******************************************************************************
 * @file           : test_channel.c
 * @brief          : Unit tests for PMU Channel Abstraction Layer
 * @author         : R2 m-sport
 * @date           : 2025-12-26
 ******************************************************************************
 */

#include "unity.h"
#include "pmu_channel.h"
#include <string.h>

/* Test setup and teardown */
void setUp(void)
{
    /* Initialize channel system before each test */
    PMU_Channel_Init();
}

void tearDown(void)
{
    /* Clean up after each test */
}

/* ===========================================================================
 * Initialization Tests
 * =========================================================================== */

void test_channel_init(void)
{
    /* Init is called in setUp, verify stats */
    const PMU_ChannelStats_t* stats = PMU_Channel_GetStats();

    TEST_ASSERT_NOT_NULL(stats);
    /* System channels + output sub-channels should be registered */
    TEST_ASSERT_GREATER_THAN(0, stats->total_channels);
}

void test_channel_system_channels_registered(void)
{
    /* Verify system channels are registered */
    const PMU_Channel_t* ch;

    ch = PMU_Channel_GetInfo(PMU_CHANNEL_SYSTEM_BATTERY_V);
    TEST_ASSERT_NOT_NULL(ch);
    TEST_ASSERT_EQUAL_STRING("Battery Voltage", ch->name);

    ch = PMU_Channel_GetInfo(PMU_CHANNEL_SYSTEM_TOTAL_I);
    TEST_ASSERT_NOT_NULL(ch);
    TEST_ASSERT_EQUAL_STRING("Total Current", ch->name);

    ch = PMU_Channel_GetInfo(PMU_CHANNEL_SYSTEM_MCU_TEMP);
    TEST_ASSERT_NOT_NULL(ch);
    TEST_ASSERT_EQUAL_STRING("MCU Temperature", ch->name);

    ch = PMU_Channel_GetInfo(PMU_CHANNEL_SYSTEM_UPTIME);
    TEST_ASSERT_NOT_NULL(ch);
    TEST_ASSERT_EQUAL_STRING("System Uptime", ch->name);
}

void test_channel_constant_channels(void)
{
    /* Verify constant channels: zero and one */
    const PMU_Channel_t* ch_zero = PMU_Channel_GetInfo(PMU_CHANNEL_CONST_ZERO);
    const PMU_Channel_t* ch_one = PMU_Channel_GetInfo(PMU_CHANNEL_CONST_ONE);

    TEST_ASSERT_NOT_NULL(ch_zero);
    TEST_ASSERT_NOT_NULL(ch_one);

    TEST_ASSERT_EQUAL_STRING("zero", ch_zero->name);
    TEST_ASSERT_EQUAL_STRING("one", ch_one->name);

    TEST_ASSERT_EQUAL(0, ch_zero->value);
    TEST_ASSERT_EQUAL(1000, ch_one->value);  /* 1.0 scaled */
}

void test_channel_output_subchannels(void)
{
    /* Verify output sub-channels for first output */
    char expected_name[32];

    const PMU_Channel_t* ch_status = PMU_Channel_GetInfo(PMU_CHANNEL_OUTPUT_STATUS_BASE);
    TEST_ASSERT_NOT_NULL(ch_status);
    snprintf(expected_name, sizeof(expected_name), "o_1.status");
    TEST_ASSERT_EQUAL_STRING(expected_name, ch_status->name);

    const PMU_Channel_t* ch_current = PMU_Channel_GetInfo(PMU_CHANNEL_OUTPUT_CURRENT_BASE);
    TEST_ASSERT_NOT_NULL(ch_current);
    snprintf(expected_name, sizeof(expected_name), "o_1.current");
    TEST_ASSERT_EQUAL_STRING(expected_name, ch_current->name);

    const PMU_Channel_t* ch_active = PMU_Channel_GetInfo(PMU_CHANNEL_OUTPUT_ACTIVE_BASE);
    TEST_ASSERT_NOT_NULL(ch_active);
    snprintf(expected_name, sizeof(expected_name), "o_1.active");
    TEST_ASSERT_EQUAL_STRING(expected_name, ch_active->name);

    /* Verify last output (output 30) */
    const PMU_Channel_t* ch_last = PMU_Channel_GetInfo(PMU_CHANNEL_OUTPUT_STATUS_BASE + 29);
    TEST_ASSERT_NOT_NULL(ch_last);
    snprintf(expected_name, sizeof(expected_name), "o_30.status");
    TEST_ASSERT_EQUAL_STRING(expected_name, ch_last->name);
}

/* ===========================================================================
 * Registration Tests
 * =========================================================================== */

void test_channel_register_valid(void)
{
    PMU_Channel_t test_ch;
    memset(&test_ch, 0, sizeof(test_ch));

    test_ch.channel_id = 50;
    test_ch.hw_class = PMU_CHANNEL_CLASS_INPUT_ANALOG;
    test_ch.direction = PMU_CHANNEL_DIR_INPUT;
    test_ch.format = PMU_CHANNEL_FORMAT_VOLTAGE;
    test_ch.physical_index = 0;
    test_ch.flags = PMU_CHANNEL_FLAG_ENABLED;
    test_ch.min_value = 0;
    test_ch.max_value = 5000;
    strncpy(test_ch.name, "Test Analog", sizeof(test_ch.name));
    strncpy(test_ch.unit, "mV", sizeof(test_ch.unit));

    HAL_StatusTypeDef status = PMU_Channel_Register(&test_ch);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    /* Verify registration */
    const PMU_Channel_t* ch = PMU_Channel_GetInfo(50);
    TEST_ASSERT_NOT_NULL(ch);
    TEST_ASSERT_EQUAL_STRING("Test Analog", ch->name);
    TEST_ASSERT_EQUAL(5000, ch->max_value);
}

void test_channel_register_null(void)
{
    HAL_StatusTypeDef status = PMU_Channel_Register(NULL);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_channel_register_invalid_id(void)
{
    PMU_Channel_t test_ch;
    memset(&test_ch, 0, sizeof(test_ch));

    test_ch.channel_id = PMU_CHANNEL_MAX_CHANNELS;  /* Out of range */
    strncpy(test_ch.name, "Invalid", sizeof(test_ch.name));

    HAL_StatusTypeDef status = PMU_Channel_Register(&test_ch);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_channel_register_duplicate(void)
{
    PMU_Channel_t test_ch;
    memset(&test_ch, 0, sizeof(test_ch));

    test_ch.channel_id = 60;
    test_ch.hw_class = PMU_CHANNEL_CLASS_INPUT_DIGITAL;
    strncpy(test_ch.name, "Digital 1", sizeof(test_ch.name));

    /* First registration should succeed */
    HAL_StatusTypeDef status = PMU_Channel_Register(&test_ch);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    /* Second registration with same ID should fail */
    strncpy(test_ch.name, "Digital 2", sizeof(test_ch.name));
    status = PMU_Channel_Register(&test_ch);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);

    /* Original should still be there */
    const PMU_Channel_t* ch = PMU_Channel_GetInfo(60);
    TEST_ASSERT_EQUAL_STRING("Digital 1", ch->name);
}

/* ===========================================================================
 * Unregistration Tests
 * =========================================================================== */

void test_channel_unregister_valid(void)
{
    PMU_Channel_t test_ch;
    memset(&test_ch, 0, sizeof(test_ch));

    test_ch.channel_id = 70;
    test_ch.hw_class = PMU_CHANNEL_CLASS_INPUT_DIGITAL;
    strncpy(test_ch.name, "ToRemove", sizeof(test_ch.name));

    PMU_Channel_Register(&test_ch);

    /* Verify it exists */
    TEST_ASSERT_NOT_NULL(PMU_Channel_GetInfo(70));

    /* Unregister */
    HAL_StatusTypeDef status = PMU_Channel_Unregister(70);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    /* Verify it's gone */
    TEST_ASSERT_NULL(PMU_Channel_GetInfo(70));
}

void test_channel_unregister_nonexistent(void)
{
    HAL_StatusTypeDef status = PMU_Channel_Unregister(999);  /* Unused ID */
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_channel_unregister_invalid_id(void)
{
    HAL_StatusTypeDef status = PMU_Channel_Unregister(PMU_CHANNEL_MAX_CHANNELS);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * Value Get/Set Tests
 * =========================================================================== */

void test_channel_get_value_nonexistent(void)
{
    int32_t value = PMU_Channel_GetValue(999);  /* Unused ID */
    TEST_ASSERT_EQUAL(0, value);
}

void test_channel_set_value_output(void)
{
    PMU_Channel_t test_ch;
    memset(&test_ch, 0, sizeof(test_ch));

    test_ch.channel_id = 110;
    test_ch.hw_class = PMU_CHANNEL_CLASS_OUTPUT_POWER;
    test_ch.direction = PMU_CHANNEL_DIR_OUTPUT;
    test_ch.format = PMU_CHANNEL_FORMAT_PERCENT;
    test_ch.flags = PMU_CHANNEL_FLAG_ENABLED;
    test_ch.min_value = 0;
    test_ch.max_value = 1000;
    strncpy(test_ch.name, "Test Output", sizeof(test_ch.name));

    PMU_Channel_Register(&test_ch);

    /* Set value */
    HAL_StatusTypeDef status = PMU_Channel_SetValue(110, 500);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    /* Get value */
    int32_t value = PMU_Channel_GetValue(110);
    TEST_ASSERT_EQUAL(500, value);
}

void test_channel_set_value_clamping(void)
{
    PMU_Channel_t test_ch;
    memset(&test_ch, 0, sizeof(test_ch));

    test_ch.channel_id = 111;
    test_ch.hw_class = PMU_CHANNEL_CLASS_OUTPUT_PWM;
    test_ch.direction = PMU_CHANNEL_DIR_OUTPUT;
    test_ch.flags = PMU_CHANNEL_FLAG_ENABLED;
    test_ch.min_value = 0;
    test_ch.max_value = 100;
    strncpy(test_ch.name, "PWM Out", sizeof(test_ch.name));

    PMU_Channel_Register(&test_ch);

    /* Set above max - should clamp */
    PMU_Channel_SetValue(111, 200);
    TEST_ASSERT_EQUAL(100, PMU_Channel_GetValue(111));

    /* Set below min - should clamp */
    PMU_Channel_SetValue(111, -50);
    TEST_ASSERT_EQUAL(0, PMU_Channel_GetValue(111));
}

void test_channel_set_value_input_fails(void)
{
    /* Try to set value on an input channel - should fail */
    HAL_StatusTypeDef status = PMU_Channel_SetValue(PMU_CHANNEL_SYSTEM_BATTERY_V, 12000);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_channel_set_value_disabled_fails(void)
{
    PMU_Channel_t test_ch;
    memset(&test_ch, 0, sizeof(test_ch));

    test_ch.channel_id = 112;
    test_ch.hw_class = PMU_CHANNEL_CLASS_OUTPUT_POWER;
    test_ch.direction = PMU_CHANNEL_DIR_OUTPUT;
    test_ch.flags = 0;  /* Not enabled */
    test_ch.min_value = 0;
    test_ch.max_value = 1000;
    strncpy(test_ch.name, "Disabled Out", sizeof(test_ch.name));

    PMU_Channel_Register(&test_ch);

    HAL_StatusTypeDef status = PMU_Channel_SetValue(112, 500);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * Lookup Tests
 * =========================================================================== */

void test_channel_get_by_name(void)
{
    const PMU_Channel_t* ch = PMU_Channel_GetByName("Battery Voltage");
    TEST_ASSERT_NOT_NULL(ch);
    TEST_ASSERT_EQUAL(PMU_CHANNEL_SYSTEM_BATTERY_V, ch->channel_id);
}

void test_channel_get_by_name_nonexistent(void)
{
    const PMU_Channel_t* ch = PMU_Channel_GetByName("NonExistent Channel");
    TEST_ASSERT_NULL(ch);
}

void test_channel_get_by_name_null(void)
{
    const PMU_Channel_t* ch = PMU_Channel_GetByName(NULL);
    TEST_ASSERT_NULL(ch);
}

void test_channel_get_index_by_id(void)
{
    uint16_t id = PMU_Channel_GetIndexByID("Battery Voltage");
    TEST_ASSERT_EQUAL(PMU_CHANNEL_SYSTEM_BATTERY_V, id);
}

void test_channel_get_index_by_id_not_found(void)
{
    uint16_t id = PMU_Channel_GetIndexByID("No Such Channel");
    TEST_ASSERT_EQUAL(0xFFFF, id);
}

/* ===========================================================================
 * Statistics Tests
 * =========================================================================== */

void test_channel_stats_updated(void)
{
    const PMU_ChannelStats_t* stats_before = PMU_Channel_GetStats();
    uint16_t total_before = stats_before->total_channels;
    uint16_t input_before = stats_before->input_channels;

    /* Register a new input channel */
    PMU_Channel_t test_ch;
    memset(&test_ch, 0, sizeof(test_ch));
    test_ch.channel_id = 80;
    test_ch.hw_class = PMU_CHANNEL_CLASS_INPUT_ANALOG;
    test_ch.direction = PMU_CHANNEL_DIR_INPUT;
    strncpy(test_ch.name, "Stats Test", sizeof(test_ch.name));

    PMU_Channel_Register(&test_ch);

    const PMU_ChannelStats_t* stats_after = PMU_Channel_GetStats();
    TEST_ASSERT_EQUAL(total_before + 1, stats_after->total_channels);
    TEST_ASSERT_EQUAL(input_before + 1, stats_after->input_channels);
}

void test_channel_stats_on_unregister(void)
{
    /* Register then unregister */
    PMU_Channel_t test_ch;
    memset(&test_ch, 0, sizeof(test_ch));
    test_ch.channel_id = 81;
    test_ch.hw_class = PMU_CHANNEL_CLASS_OUTPUT_POWER;
    test_ch.direction = PMU_CHANNEL_DIR_OUTPUT;
    strncpy(test_ch.name, "Temp Out", sizeof(test_ch.name));

    PMU_Channel_Register(&test_ch);
    const PMU_ChannelStats_t* stats1 = PMU_Channel_GetStats();
    uint16_t total1 = stats1->total_channels;

    PMU_Channel_Unregister(81);
    const PMU_ChannelStats_t* stats2 = PMU_Channel_GetStats();
    TEST_ASSERT_EQUAL(total1 - 1, stats2->total_channels);
}

/* ===========================================================================
 * List Tests
 * =========================================================================== */

void test_channel_list(void)
{
    PMU_Channel_t channels[10];
    uint16_t count = PMU_Channel_List(channels, 10);

    /* Should return at least some channels */
    TEST_ASSERT_GREATER_THAN(0, count);
    TEST_ASSERT_LESS_OR_EQUAL(10, count);
}

void test_channel_list_null(void)
{
    uint16_t count = PMU_Channel_List(NULL, 10);
    TEST_ASSERT_EQUAL(0, count);
}

void test_channel_list_zero_count(void)
{
    PMU_Channel_t channels[10];
    uint16_t count = PMU_Channel_List(channels, 0);
    TEST_ASSERT_EQUAL(0, count);
}

/* ===========================================================================
 * Enable/Disable Tests
 * =========================================================================== */

void test_channel_enable_disable(void)
{
    PMU_Channel_t test_ch;
    memset(&test_ch, 0, sizeof(test_ch));

    test_ch.channel_id = 90;
    test_ch.hw_class = PMU_CHANNEL_CLASS_OUTPUT_POWER;
    test_ch.direction = PMU_CHANNEL_DIR_OUTPUT;
    test_ch.flags = PMU_CHANNEL_FLAG_ENABLED;
    strncpy(test_ch.name, "Toggle", sizeof(test_ch.name));

    PMU_Channel_Register(&test_ch);

    /* Disable */
    HAL_StatusTypeDef status = PMU_Channel_SetEnabled(90, false);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    const PMU_Channel_t* ch = PMU_Channel_GetInfo(90);
    TEST_ASSERT_FALSE(ch->flags & PMU_CHANNEL_FLAG_ENABLED);

    /* Enable */
    status = PMU_Channel_SetEnabled(90, true);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    ch = PMU_Channel_GetInfo(90);
    TEST_ASSERT_TRUE(ch->flags & PMU_CHANNEL_FLAG_ENABLED);
}

void test_channel_enable_nonexistent(void)
{
    HAL_StatusTypeDef status = PMU_Channel_SetEnabled(999, true);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * ID Generation Tests
 * =========================================================================== */

void test_channel_generate_id(void)
{
    uint16_t id1 = PMU_Channel_GenerateID();
    uint16_t id2 = PMU_Channel_GenerateID();
    uint16_t id3 = PMU_Channel_GenerateID();

    /* IDs should be unique and incrementing */
    TEST_ASSERT_NOT_EQUAL(id1, id2);
    TEST_ASSERT_NOT_EQUAL(id2, id3);
    TEST_ASSERT_EQUAL(id1 + 1, id2);
    TEST_ASSERT_EQUAL(id2 + 1, id3);
}

/* ===========================================================================
 * Classification Tests
 * =========================================================================== */

void test_channel_is_input(void)
{
    TEST_ASSERT_TRUE(PMU_Channel_IsInput(PMU_CHANNEL_CLASS_INPUT_ANALOG));
    TEST_ASSERT_TRUE(PMU_Channel_IsInput(PMU_CHANNEL_CLASS_INPUT_DIGITAL));
    TEST_ASSERT_TRUE(PMU_Channel_IsInput(PMU_CHANNEL_CLASS_INPUT_CAN));
    TEST_ASSERT_FALSE(PMU_Channel_IsInput(PMU_CHANNEL_CLASS_OUTPUT_POWER));
    TEST_ASSERT_FALSE(PMU_Channel_IsInput(PMU_CHANNEL_CLASS_OUTPUT_FUNCTION));
}

void test_channel_is_output(void)
{
    TEST_ASSERT_TRUE(PMU_Channel_IsOutput(PMU_CHANNEL_CLASS_OUTPUT_POWER));
    TEST_ASSERT_TRUE(PMU_Channel_IsOutput(PMU_CHANNEL_CLASS_OUTPUT_PWM));
    TEST_ASSERT_TRUE(PMU_Channel_IsOutput(PMU_CHANNEL_CLASS_OUTPUT_FUNCTION));
    TEST_ASSERT_FALSE(PMU_Channel_IsOutput(PMU_CHANNEL_CLASS_INPUT_ANALOG));
    TEST_ASSERT_FALSE(PMU_Channel_IsOutput(PMU_CHANNEL_CLASS_INPUT_CAN));
}

void test_channel_is_virtual(void)
{
    TEST_ASSERT_TRUE(PMU_Channel_IsVirtual(PMU_CHANNEL_CLASS_INPUT_CAN));
    TEST_ASSERT_TRUE(PMU_Channel_IsVirtual(PMU_CHANNEL_CLASS_INPUT_CALCULATED));
    TEST_ASSERT_TRUE(PMU_Channel_IsVirtual(PMU_CHANNEL_CLASS_OUTPUT_FUNCTION));
    TEST_ASSERT_TRUE(PMU_Channel_IsVirtual(PMU_CHANNEL_CLASS_OUTPUT_TABLE));
    TEST_ASSERT_FALSE(PMU_Channel_IsVirtual(PMU_CHANNEL_CLASS_INPUT_ANALOG));
    TEST_ASSERT_FALSE(PMU_Channel_IsVirtual(PMU_CHANNEL_CLASS_OUTPUT_POWER));
}

void test_channel_is_physical(void)
{
    TEST_ASSERT_TRUE(PMU_Channel_IsPhysical(PMU_CHANNEL_CLASS_INPUT_ANALOG));
    TEST_ASSERT_TRUE(PMU_Channel_IsPhysical(PMU_CHANNEL_CLASS_INPUT_DIGITAL));
    TEST_ASSERT_TRUE(PMU_Channel_IsPhysical(PMU_CHANNEL_CLASS_OUTPUT_POWER));
    TEST_ASSERT_FALSE(PMU_Channel_IsPhysical(PMU_CHANNEL_CLASS_INPUT_CAN));
    TEST_ASSERT_FALSE(PMU_Channel_IsPhysical(PMU_CHANNEL_CLASS_OUTPUT_FUNCTION));
}

/* ===========================================================================
 * Inversion Tests
 * =========================================================================== */

void test_channel_inverted_output(void)
{
    PMU_Channel_t test_ch;
    memset(&test_ch, 0, sizeof(test_ch));

    test_ch.channel_id = 120;
    test_ch.hw_class = PMU_CHANNEL_CLASS_OUTPUT_PWM;
    test_ch.direction = PMU_CHANNEL_DIR_OUTPUT;
    test_ch.format = PMU_CHANNEL_FORMAT_PERCENT;
    test_ch.flags = PMU_CHANNEL_FLAG_ENABLED | PMU_CHANNEL_FLAG_INVERTED;
    test_ch.min_value = 0;
    test_ch.max_value = 1000;
    strncpy(test_ch.name, "Inverted", sizeof(test_ch.name));

    PMU_Channel_Register(&test_ch);

    /* Set 25% (250) - should be stored as inverted */
    PMU_Channel_SetValue(120, 250);

    /* Get should return inverted value */
    int32_t value = PMU_Channel_GetValue(120);
    /* Inversion: max - value = 1000 - 750 = 250 (inverted of 750) */
    /* Actually SetValue inverts on write, GetValue inverts on read */
    /* So set 250 -> store 750, read 750 -> return 250 */
    TEST_ASSERT_EQUAL(250, value);
}

/* ===========================================================================
 * Main Test Runner
 * =========================================================================== */

int test_channel_main(void)
{
    UNITY_BEGIN();

    /* Initialization */
    RUN_TEST(test_channel_init);
    RUN_TEST(test_channel_system_channels_registered);
    RUN_TEST(test_channel_constant_channels);
    RUN_TEST(test_channel_output_subchannels);

    /* Registration */
    RUN_TEST(test_channel_register_valid);
    RUN_TEST(test_channel_register_null);
    RUN_TEST(test_channel_register_invalid_id);
    RUN_TEST(test_channel_register_duplicate);

    /* Unregistration */
    RUN_TEST(test_channel_unregister_valid);
    RUN_TEST(test_channel_unregister_nonexistent);
    RUN_TEST(test_channel_unregister_invalid_id);

    /* Get/Set Value */
    RUN_TEST(test_channel_get_value_nonexistent);
    RUN_TEST(test_channel_set_value_output);
    RUN_TEST(test_channel_set_value_clamping);
    RUN_TEST(test_channel_set_value_input_fails);
    RUN_TEST(test_channel_set_value_disabled_fails);

    /* Lookup */
    RUN_TEST(test_channel_get_by_name);
    RUN_TEST(test_channel_get_by_name_nonexistent);
    RUN_TEST(test_channel_get_by_name_null);
    RUN_TEST(test_channel_get_index_by_id);
    RUN_TEST(test_channel_get_index_by_id_not_found);

    /* Statistics */
    RUN_TEST(test_channel_stats_updated);
    RUN_TEST(test_channel_stats_on_unregister);

    /* List */
    RUN_TEST(test_channel_list);
    RUN_TEST(test_channel_list_null);
    RUN_TEST(test_channel_list_zero_count);

    /* Enable/Disable */
    RUN_TEST(test_channel_enable_disable);
    RUN_TEST(test_channel_enable_nonexistent);

    /* ID Generation */
    RUN_TEST(test_channel_generate_id);

    /* Classification */
    RUN_TEST(test_channel_is_input);
    RUN_TEST(test_channel_is_output);
    RUN_TEST(test_channel_is_virtual);
    RUN_TEST(test_channel_is_physical);

    /* Inversion */
    RUN_TEST(test_channel_inverted_output);

    return UNITY_END();
}

/* Standalone runner */
#ifdef TEST_CHANNEL_STANDALONE
int main(void)
{
    return test_channel_main();
}
#endif
