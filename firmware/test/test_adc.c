/**
 ******************************************************************************
 * @file           : test_adc.c
 * @brief          : Unit tests for PMU ADC Input Driver
 * @author         : R2 m-sport
 * @date           : 2025-12-26
 ******************************************************************************
 */

#include "unity.h"
#include "pmu_adc.h"
#include <string.h>

#ifndef PMU30_NUM_ADC_INPUTS
#define PMU30_NUM_ADC_INPUTS 20
#endif

void setUp(void)
{
    PMU_ADC_Init();
}

void tearDown(void)
{
}

/* ===========================================================================
 * Initialization Tests
 * =========================================================================== */

void test_adc_init(void)
{
    HAL_StatusTypeDef status = PMU_ADC_Init();
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_adc_init_multiple(void)
{
    for (int i = 0; i < 3; i++) {
        HAL_StatusTypeDef status = PMU_ADC_Init();
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }
}

/* ===========================================================================
 * Raw Value Tests
 * =========================================================================== */

void test_get_raw_value(void)
{
    uint16_t value = PMU_ADC_GetRawValue(0);
    TEST_ASSERT_LESS_THAN(PMU_ADC_RESOLUTION, value);
}

void test_get_raw_value_all_channels(void)
{
    for (uint8_t i = 0; i < PMU30_NUM_ADC_INPUTS; i++) {
        uint16_t value = PMU_ADC_GetRawValue(i);
        TEST_ASSERT_LESS_THAN(PMU_ADC_RESOLUTION, value);
    }
}

void test_get_raw_value_invalid_channel(void)
{
    uint16_t value = PMU_ADC_GetRawValue(PMU30_NUM_ADC_INPUTS);
    TEST_ASSERT_EQUAL(0, value);
}

/* ===========================================================================
 * Scaled Value Tests
 * =========================================================================== */

void test_get_scaled_value(void)
{
    float value = PMU_ADC_GetScaledValue(0);
    /* Value should be a reasonable number */
    TEST_ASSERT_FALSE(isnan(value));
    TEST_ASSERT_FALSE(isinf(value));
}

void test_get_scaled_value_all_channels(void)
{
    for (uint8_t i = 0; i < PMU30_NUM_ADC_INPUTS; i++) {
        float value = PMU_ADC_GetScaledValue(i);
        TEST_ASSERT_FALSE(isnan(value));
    }
}

void test_get_scaled_value_invalid_channel(void)
{
    float value = PMU_ADC_GetScaledValue(PMU30_NUM_ADC_INPUTS);
    TEST_ASSERT_FLOAT_WITHIN(0.001f, 0.0f, value);
}

/* ===========================================================================
 * Digital State Tests
 * =========================================================================== */

void test_get_digital_state(void)
{
    uint8_t state = PMU_ADC_GetDigitalState(0);
    TEST_ASSERT_TRUE(state == 0 || state == 1);
}

void test_get_digital_state_all_channels(void)
{
    for (uint8_t i = 0; i < PMU30_NUM_ADC_INPUTS; i++) {
        uint8_t state = PMU_ADC_GetDigitalState(i);
        TEST_ASSERT_TRUE(state == 0 || state == 1);
    }
}

void test_get_digital_state_invalid_channel(void)
{
    uint8_t state = PMU_ADC_GetDigitalState(PMU30_NUM_ADC_INPUTS);
    TEST_ASSERT_EQUAL(0, state);
}

/* ===========================================================================
 * Frequency Tests
 * =========================================================================== */

void test_get_frequency(void)
{
    uint32_t freq = PMU_ADC_GetFrequency(0);
    /* In test mode, should be 0 or reasonable value */
    TEST_ASSERT_LESS_THAN(100000, freq);  /* Max 100kHz */
}

void test_get_frequency_invalid_channel(void)
{
    uint32_t freq = PMU_ADC_GetFrequency(PMU30_NUM_ADC_INPUTS);
    TEST_ASSERT_EQUAL(0, freq);
}

/* ===========================================================================
 * Input Data Tests
 * =========================================================================== */

void test_get_input_data(void)
{
    PMU_ADC_Input_t* data = PMU_ADC_GetInputData(0);
    TEST_ASSERT_NOT_NULL(data);
}

void test_get_input_data_all_channels(void)
{
    for (uint8_t i = 0; i < PMU30_NUM_ADC_INPUTS; i++) {
        PMU_ADC_Input_t* data = PMU_ADC_GetInputData(i);
        TEST_ASSERT_NOT_NULL(data);
    }
}

void test_get_input_data_invalid_channel(void)
{
    PMU_ADC_Input_t* data = PMU_ADC_GetInputData(PMU30_NUM_ADC_INPUTS);
    TEST_ASSERT_NULL(data);
}

void test_input_data_structure(void)
{
    PMU_ADC_Input_t* data = PMU_ADC_GetInputData(0);
    TEST_ASSERT_NOT_NULL(data);

    /* Verify structure fields are reasonable */
    TEST_ASSERT_LESS_THAN(PMU_ADC_RESOLUTION, data->raw_value);
    TEST_ASSERT_TRUE(data->digital_state == 0 || data->digital_state == 1);
    TEST_ASSERT_LESS_THAN(8, data->filter_index);
}

/* ===========================================================================
 * Configuration Tests
 * =========================================================================== */

void test_set_config(void)
{
    PMU_InputConfig_t config;
    memset(&config, 0, sizeof(config));

    config.analog.input_type = PMU_ANALOG_INPUT_LINEAR;
    config.analog.min_voltage = 0.0f;
    config.analog.max_voltage = 5.0f;
    config.analog.min_value = 0.0f;
    config.analog.max_value = 100.0f;

    HAL_StatusTypeDef status = PMU_ADC_SetConfig(0, &config);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_set_config_null(void)
{
    HAL_StatusTypeDef status = PMU_ADC_SetConfig(0, NULL);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_set_config_invalid_channel(void)
{
    PMU_InputConfig_t config;
    memset(&config, 0, sizeof(config));

    HAL_StatusTypeDef status = PMU_ADC_SetConfig(PMU30_NUM_ADC_INPUTS, &config);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * Update Tests
 * =========================================================================== */

void test_update(void)
{
    PMU_ADC_Update();
    TEST_PASS();
}

void test_update_multiple(void)
{
    for (int i = 0; i < 100; i++) {
        PMU_ADC_Update();
    }
    TEST_PASS();
}

/* ===========================================================================
 * Constants Tests
 * =========================================================================== */

void test_adc_constants(void)
{
    TEST_ASSERT_EQUAL(1024, PMU_ADC_RESOLUTION);
    TEST_ASSERT_EQUAL(3300, PMU_ADC_VREF_MV);
    TEST_ASSERT_EQUAL(2500, PMU_ADC_DEFAULT_HIGH_MV);
    TEST_ASSERT_EQUAL(800, PMU_ADC_DEFAULT_LOW_MV);
    TEST_ASSERT_EQUAL(20, PMU_ADC_DEFAULT_DEBOUNCE_MS);
}

/* ===========================================================================
 * Main Test Runner
 * =========================================================================== */

int test_adc_main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_adc_init);
    RUN_TEST(test_adc_init_multiple);

    RUN_TEST(test_get_raw_value);
    RUN_TEST(test_get_raw_value_all_channels);
    RUN_TEST(test_get_raw_value_invalid_channel);

    RUN_TEST(test_get_scaled_value);
    RUN_TEST(test_get_scaled_value_all_channels);
    RUN_TEST(test_get_scaled_value_invalid_channel);

    RUN_TEST(test_get_digital_state);
    RUN_TEST(test_get_digital_state_all_channels);
    RUN_TEST(test_get_digital_state_invalid_channel);

    RUN_TEST(test_get_frequency);
    RUN_TEST(test_get_frequency_invalid_channel);

    RUN_TEST(test_get_input_data);
    RUN_TEST(test_get_input_data_all_channels);
    RUN_TEST(test_get_input_data_invalid_channel);
    RUN_TEST(test_input_data_structure);

    RUN_TEST(test_set_config);
    RUN_TEST(test_set_config_null);
    RUN_TEST(test_set_config_invalid_channel);

    RUN_TEST(test_update);
    RUN_TEST(test_update_multiple);

    RUN_TEST(test_adc_constants);

    return UNITY_END();
}

#ifdef TEST_ADC_STANDALONE
int main(void) { return test_adc_main(); }
#endif
