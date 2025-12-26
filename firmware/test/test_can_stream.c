/**
 * @file test_can_stream.c
 * @brief Unit tests for pmu_can_stream module
 *
 * Tests:
 * - Initialization and configuration
 * - Enable/disable control
 * - Frame packing/unpacking
 * - Scaling conversions
 * - Statistics tracking
 */

#include "unity.h"
#include "pmu_can_stream.h"
#include <string.h>
#include <math.h>

/* ============================================================================
 * Test Helpers
 * ============================================================================ */

static PMU_CanStreamConfig_t default_config;

static void reset_to_defaults(void)
{
    memset(&default_config, 0, sizeof(default_config));
    default_config.enabled = true;
    default_config.can_bus = 1;
    default_config.base_id = PMU_CAN_STREAM_DEFAULT_BASE_ID;
    default_config.is_extended = false;
    default_config.include_extended = false;
}

/* ============================================================================
 * Initialization Tests
 * ============================================================================ */

void test_can_stream_init_default(void)
{
    reset_to_defaults();

    int result = PMU_CanStream_Init(&default_config);

    TEST_ASSERT_EQUAL_INT(0, result);
    TEST_ASSERT_TRUE(PMU_CanStream_IsEnabled());

    PMU_CanStream_Deinit();
}

void test_can_stream_init_null_config(void)
{
    int result = PMU_CanStream_Init(NULL);

    TEST_ASSERT_NOT_EQUAL(0, result);
}

void test_can_stream_init_custom_base_id(void)
{
    reset_to_defaults();
    default_config.base_id = 0x700;

    int result = PMU_CanStream_Init(&default_config);
    TEST_ASSERT_EQUAL_INT(0, result);

    PMU_CanStreamConfig_t readback;
    PMU_CanStream_GetConfig(&readback);
    TEST_ASSERT_EQUAL_HEX32(0x700, readback.base_id);

    PMU_CanStream_Deinit();
}

void test_can_stream_init_extended_id(void)
{
    reset_to_defaults();
    default_config.is_extended = true;
    default_config.base_id = 0x18FF0600;

    int result = PMU_CanStream_Init(&default_config);
    TEST_ASSERT_EQUAL_INT(0, result);

    PMU_CanStreamConfig_t readback;
    PMU_CanStream_GetConfig(&readback);
    TEST_ASSERT_TRUE(readback.is_extended);

    PMU_CanStream_Deinit();
}

void test_can_stream_init_can_bus_a(void)
{
    reset_to_defaults();
    default_config.can_bus = 1;

    int result = PMU_CanStream_Init(&default_config);
    TEST_ASSERT_EQUAL_INT(0, result);

    PMU_CanStream_Deinit();
}

void test_can_stream_init_can_bus_b(void)
{
    reset_to_defaults();
    default_config.can_bus = 2;

    int result = PMU_CanStream_Init(&default_config);
    TEST_ASSERT_EQUAL_INT(0, result);

    PMU_CanStream_Deinit();
}

void test_can_stream_init_include_extended_frames(void)
{
    reset_to_defaults();
    default_config.include_extended = true;

    int result = PMU_CanStream_Init(&default_config);
    TEST_ASSERT_EQUAL_INT(0, result);

    PMU_CanStreamConfig_t readback;
    PMU_CanStream_GetConfig(&readback);
    TEST_ASSERT_TRUE(readback.include_extended);

    PMU_CanStream_Deinit();
}

void test_can_stream_deinit(void)
{
    reset_to_defaults();
    PMU_CanStream_Init(&default_config);

    PMU_CanStream_Deinit();

    TEST_ASSERT_FALSE(PMU_CanStream_IsEnabled());
}

/* ============================================================================
 * Enable/Disable Tests
 * ============================================================================ */

void test_can_stream_enable(void)
{
    reset_to_defaults();
    default_config.enabled = false;
    PMU_CanStream_Init(&default_config);

    PMU_CanStream_SetEnabled(true);

    TEST_ASSERT_TRUE(PMU_CanStream_IsEnabled());

    PMU_CanStream_Deinit();
}

void test_can_stream_disable(void)
{
    reset_to_defaults();
    PMU_CanStream_Init(&default_config);

    PMU_CanStream_SetEnabled(false);

    TEST_ASSERT_FALSE(PMU_CanStream_IsEnabled());

    PMU_CanStream_Deinit();
}

void test_can_stream_toggle(void)
{
    reset_to_defaults();
    PMU_CanStream_Init(&default_config);

    PMU_CanStream_SetEnabled(false);
    TEST_ASSERT_FALSE(PMU_CanStream_IsEnabled());

    PMU_CanStream_SetEnabled(true);
    TEST_ASSERT_TRUE(PMU_CanStream_IsEnabled());

    PMU_CanStream_SetEnabled(false);
    TEST_ASSERT_FALSE(PMU_CanStream_IsEnabled());

    PMU_CanStream_Deinit();
}

/* ============================================================================
 * Configuration Tests
 * ============================================================================ */

void test_can_stream_configure(void)
{
    reset_to_defaults();
    PMU_CanStream_Init(&default_config);

    PMU_CanStreamConfig_t new_config = default_config;
    new_config.base_id = 0x500;
    new_config.can_bus = 2;

    int result = PMU_CanStream_Configure(&new_config);
    TEST_ASSERT_EQUAL_INT(0, result);

    PMU_CanStreamConfig_t readback;
    PMU_CanStream_GetConfig(&readback);
    TEST_ASSERT_EQUAL_HEX32(0x500, readback.base_id);
    TEST_ASSERT_EQUAL_UINT8(2, readback.can_bus);

    PMU_CanStream_Deinit();
}

void test_can_stream_get_config(void)
{
    reset_to_defaults();
    default_config.base_id = 0x650;
    default_config.can_bus = 1;
    default_config.is_extended = true;
    PMU_CanStream_Init(&default_config);

    PMU_CanStreamConfig_t readback;
    PMU_CanStream_GetConfig(&readback);

    TEST_ASSERT_EQUAL_HEX32(0x650, readback.base_id);
    TEST_ASSERT_EQUAL_UINT8(1, readback.can_bus);
    TEST_ASSERT_TRUE(readback.is_extended);

    PMU_CanStream_Deinit();
}

/* ============================================================================
 * Scaling Conversion Tests
 * ============================================================================ */

void test_vbat_to_raw_conversion(void)
{
    // 12V should give approximately 110 raw
    float voltage = 12.0f;
    uint8_t raw = PMU_STREAM_VBAT_TO_RAW(voltage);
    TEST_ASSERT_UINT8_WITHIN(2, 110, raw);
}

void test_raw_to_vbat_conversion(void)
{
    // 110 raw should give approximately 12V
    uint8_t raw = 110;
    float voltage = PMU_STREAM_RAW_TO_VBAT(raw);
    TEST_ASSERT_FLOAT_WITHIN(0.2f, 12.0f, voltage);
}

void test_vbat_roundtrip(void)
{
    float original = 13.8f;
    uint8_t raw = PMU_STREAM_VBAT_TO_RAW(original);
    float converted = PMU_STREAM_RAW_TO_VBAT(raw);
    TEST_ASSERT_FLOAT_WITHIN(0.15f, original, converted);
}

void test_ain_to_raw_conversion(void)
{
    // 2.5V should give approximately 127 raw
    float voltage = 2.5f;
    uint8_t raw = PMU_STREAM_AIN_TO_RAW(voltage);
    TEST_ASSERT_UINT8_WITHIN(2, 127, raw);
}

void test_raw_to_ain_conversion(void)
{
    // 255 raw should give approximately 5V
    uint8_t raw = 255;
    float voltage = PMU_STREAM_RAW_TO_AIN(raw);
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 5.0f, voltage);
}

void test_ain_roundtrip(void)
{
    float original = 3.3f;
    uint8_t raw = PMU_STREAM_AIN_TO_RAW(original);
    float converted = PMU_STREAM_RAW_TO_AIN(raw);
    TEST_ASSERT_FLOAT_WITHIN(0.05f, original, converted);
}

void test_current_to_raw_conversion(void)
{
    // 10A should give 40 raw
    float current = 10.0f;
    uint8_t raw = PMU_STREAM_CURRENT_TO_RAW(current);
    TEST_ASSERT_EQUAL_UINT8(40, raw);
}

void test_raw_to_current_conversion(void)
{
    // 40 raw should give 10A
    uint8_t raw = 40;
    float current = PMU_STREAM_RAW_TO_CURRENT(raw);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 10.0f, current);
}

void test_current_roundtrip(void)
{
    float original = 25.0f;
    uint8_t raw = PMU_STREAM_CURRENT_TO_RAW(original);
    float converted = PMU_STREAM_RAW_TO_CURRENT(raw);
    TEST_ASSERT_FLOAT_WITHIN(0.25f, original, converted);
}

void test_vout_to_raw_conversion(void)
{
    // 12V should give approximately 189 raw
    float voltage = 12.0f;
    uint8_t raw = PMU_STREAM_VOUT_TO_RAW(voltage);
    TEST_ASSERT_UINT8_WITHIN(2, 189, raw);
}

void test_raw_to_vout_conversion(void)
{
    // 189 raw should give approximately 12V
    uint8_t raw = 189;
    float voltage = PMU_STREAM_RAW_TO_VOUT(raw);
    TEST_ASSERT_FLOAT_WITHIN(0.1f, 12.0f, voltage);
}

void test_vout_roundtrip(void)
{
    float original = 14.0f;
    uint8_t raw = PMU_STREAM_VOUT_TO_RAW(original);
    float converted = PMU_STREAM_RAW_TO_VOUT(raw);
    TEST_ASSERT_FLOAT_WITHIN(0.1f, original, converted);
}

/* ============================================================================
 * Output State Packing/Unpacking Tests
 * ============================================================================ */

void test_pack_output_state_both_off(void)
{
    uint8_t packed = PMU_CanStream_PackOutputState(
        PMU_OUTPUT_STATUS_OFF, false,
        PMU_OUTPUT_STATUS_OFF, false
    );
    TEST_ASSERT_EQUAL_HEX8(0x00, packed);
}

void test_pack_output_state_both_active(void)
{
    uint8_t packed = PMU_CanStream_PackOutputState(
        PMU_OUTPUT_STATUS_ACTIVE, true,
        PMU_OUTPUT_STATUS_ACTIVE, true
    );
    // Odd: status=1 (bits 5-7), active=1 (bit 4) -> 0x30
    // Even: status=1 (bits 1-3), active=1 (bit 0) -> 0x03
    TEST_ASSERT_EQUAL_HEX8(0x33, packed);
}

void test_pack_output_state_odd_active_only(void)
{
    uint8_t packed = PMU_CanStream_PackOutputState(
        PMU_OUTPUT_STATUS_ACTIVE, true,
        PMU_OUTPUT_STATUS_OFF, false
    );
    TEST_ASSERT_EQUAL_HEX8(0x30, packed);
}

void test_pack_output_state_even_active_only(void)
{
    uint8_t packed = PMU_CanStream_PackOutputState(
        PMU_OUTPUT_STATUS_OFF, false,
        PMU_OUTPUT_STATUS_ACTIVE, true
    );
    TEST_ASSERT_EQUAL_HEX8(0x03, packed);
}

void test_pack_output_state_overcurrent(void)
{
    uint8_t packed = PMU_CanStream_PackOutputState(
        PMU_OUTPUT_STATUS_OVERCURRENT, true,
        PMU_OUTPUT_STATUS_OVERCURRENT, true
    );
    // Odd: status=3 (bits 5-7)=0x60, active=1 (bit 4)=0x10 -> 0x70
    // Even: status=3 (bits 1-3)=0x06, active=1 (bit 0)=0x01 -> 0x07
    TEST_ASSERT_EQUAL_HEX8(0x77, packed);
}

void test_pack_output_state_thermal_shutdown(void)
{
    uint8_t packed = PMU_CanStream_PackOutputState(
        PMU_OUTPUT_STATUS_THERMAL_SHUTDOWN, false,
        PMU_OUTPUT_STATUS_THERMAL_SHUTDOWN, false
    );
    // Odd: status=7 (bits 5-7)=0xE0
    // Even: status=7 (bits 1-3)=0x0E
    TEST_ASSERT_EQUAL_HEX8(0xEE, packed);
}

void test_unpack_output_state_both_off(void)
{
    PMU_OutputStatus_t odd_status, even_status;
    bool odd_active, even_active;

    PMU_CanStream_UnpackOutputState(0x00,
        &odd_status, &odd_active,
        &even_status, &even_active);

    TEST_ASSERT_EQUAL_INT(PMU_OUTPUT_STATUS_OFF, odd_status);
    TEST_ASSERT_FALSE(odd_active);
    TEST_ASSERT_EQUAL_INT(PMU_OUTPUT_STATUS_OFF, even_status);
    TEST_ASSERT_FALSE(even_active);
}

void test_unpack_output_state_both_active(void)
{
    PMU_OutputStatus_t odd_status, even_status;
    bool odd_active, even_active;

    PMU_CanStream_UnpackOutputState(0x33,
        &odd_status, &odd_active,
        &even_status, &even_active);

    TEST_ASSERT_EQUAL_INT(PMU_OUTPUT_STATUS_ACTIVE, odd_status);
    TEST_ASSERT_TRUE(odd_active);
    TEST_ASSERT_EQUAL_INT(PMU_OUTPUT_STATUS_ACTIVE, even_status);
    TEST_ASSERT_TRUE(even_active);
}

void test_unpack_roundtrip(void)
{
    PMU_OutputStatus_t orig_odd = PMU_OUTPUT_STATUS_SHORT_GND;
    bool orig_odd_active = true;
    PMU_OutputStatus_t orig_even = PMU_OUTPUT_STATUS_OPEN_LOAD;
    bool orig_even_active = false;

    uint8_t packed = PMU_CanStream_PackOutputState(
        orig_odd, orig_odd_active,
        orig_even, orig_even_active);

    PMU_OutputStatus_t odd_status, even_status;
    bool odd_active, even_active;

    PMU_CanStream_UnpackOutputState(packed,
        &odd_status, &odd_active,
        &even_status, &even_active);

    TEST_ASSERT_EQUAL_INT(orig_odd, odd_status);
    TEST_ASSERT_EQUAL(orig_odd_active, odd_active);
    TEST_ASSERT_EQUAL_INT(orig_even, even_status);
    TEST_ASSERT_EQUAL(orig_even_active, even_active);
}

/* ============================================================================
 * Statistics Tests
 * ============================================================================ */

void test_can_stream_stats_initial(void)
{
    reset_to_defaults();
    PMU_CanStream_Init(&default_config);

    uint32_t frames_sent = 0, errors = 0;
    PMU_CanStream_GetStats(&frames_sent, &errors);

    TEST_ASSERT_EQUAL_UINT32(0, frames_sent);
    TEST_ASSERT_EQUAL_UINT32(0, errors);

    PMU_CanStream_Deinit();
}

void test_can_stream_stats_reset(void)
{
    reset_to_defaults();
    PMU_CanStream_Init(&default_config);

    // Call Process a few times to generate some frames
    for (int i = 0; i < 100; i++) {
        PMU_CanStream_Process();
    }

    PMU_CanStream_ResetStats();

    uint32_t frames_sent = 0, errors = 0;
    PMU_CanStream_GetStats(&frames_sent, &errors);

    TEST_ASSERT_EQUAL_UINT32(0, frames_sent);
    TEST_ASSERT_EQUAL_UINT32(0, errors);

    PMU_CanStream_Deinit();
}

/* ============================================================================
 * Constants Tests
 * ============================================================================ */

void test_constants_frame_counts(void)
{
    TEST_ASSERT_EQUAL_INT(8, PMU_CAN_STREAM_STD_FRAME_COUNT);
    TEST_ASSERT_EQUAL_INT(8, PMU_CAN_STREAM_EXT_FRAME_COUNT);
    TEST_ASSERT_EQUAL_INT(16, PMU_CAN_STREAM_TOTAL_FRAME_COUNT);
}

void test_constants_default_base_id(void)
{
    TEST_ASSERT_EQUAL_HEX32(0x600, PMU_CAN_STREAM_DEFAULT_BASE_ID);
}

void test_constants_rates(void)
{
    TEST_ASSERT_EQUAL_INT(50, PMU_CAN_STREAM_RATE_20HZ);
    TEST_ASSERT_EQUAL_INT(16, PMU_CAN_STREAM_RATE_62HZ);
}

/* ============================================================================
 * Enum Value Tests
 * ============================================================================ */

void test_status_enum_values(void)
{
    TEST_ASSERT_EQUAL_INT(0, PMU_STATUS_OK);
    TEST_ASSERT_EQUAL_INT(1, PMU_STATUS_WARNING);
    TEST_ASSERT_EQUAL_INT(7, PMU_STATUS_THERMAL_SHUTDOWN);
}

void test_output_status_enum_values(void)
{
    TEST_ASSERT_EQUAL_INT(0, PMU_OUTPUT_STATUS_OFF);
    TEST_ASSERT_EQUAL_INT(1, PMU_OUTPUT_STATUS_ACTIVE);
    TEST_ASSERT_EQUAL_INT(7, PMU_OUTPUT_STATUS_THERMAL_SHUTDOWN);
}

void test_hbridge_status_enum_values(void)
{
    TEST_ASSERT_EQUAL_INT(0, PMU_HBRIDGE_STATUS_IDLE);
    TEST_ASSERT_EQUAL_INT(1, PMU_HBRIDGE_STATUS_FORWARD);
    TEST_ASSERT_EQUAL_INT(2, PMU_HBRIDGE_STATUS_REVERSE);
    TEST_ASSERT_EQUAL_INT(7, PMU_HBRIDGE_STATUS_THERMAL);
}

/* ============================================================================
 * Frame Structure Size Tests
 * ============================================================================ */

void test_frame0_size(void)
{
    TEST_ASSERT_EQUAL_INT(8, sizeof(PMU_StreamFrame0_t));
}

void test_frame1_size(void)
{
    TEST_ASSERT_EQUAL_INT(8, sizeof(PMU_StreamFrame1_t));
}

void test_frame_analog_size(void)
{
    TEST_ASSERT_EQUAL_INT(8, sizeof(PMU_StreamFrameAnalog_t));
}

void test_frame_current_size(void)
{
    TEST_ASSERT_EQUAL_INT(8, sizeof(PMU_StreamFrameCurrent_t));
}

void test_frame_voltage_size(void)
{
    TEST_ASSERT_EQUAL_INT(8, sizeof(PMU_StreamFrameVoltage_t));
}

void test_frame_digital_size(void)
{
    TEST_ASSERT_EQUAL_INT(8, sizeof(PMU_StreamFrameDigital_t));
}

void test_frame_hbridge_size(void)
{
    TEST_ASSERT_EQUAL_INT(8, sizeof(PMU_StreamFrameHBridge_t));
}

/* ============================================================================
 * Bit Mask Tests
 * ============================================================================ */

void test_status_mask(void)
{
    TEST_ASSERT_EQUAL_HEX8(0x07, PMU_STREAM_STATUS_MASK);
}

void test_user_error_bit(void)
{
    TEST_ASSERT_EQUAL_INT(3, PMU_STREAM_USER_ERROR_BIT);
    TEST_ASSERT_EQUAL_HEX8(0x08, PMU_STREAM_USER_ERROR_MASK);
}

void test_odd_output_masks(void)
{
    TEST_ASSERT_EQUAL_HEX8(0xE0, PMU_STREAM_ODD_STATUS_MASK);
    TEST_ASSERT_EQUAL_INT(5, PMU_STREAM_ODD_STATUS_SHIFT);
    TEST_ASSERT_EQUAL_HEX8(0x10, PMU_STREAM_ODD_ACTIVE_MASK);
    TEST_ASSERT_EQUAL_INT(4, PMU_STREAM_ODD_ACTIVE_BIT);
}

void test_even_output_masks(void)
{
    TEST_ASSERT_EQUAL_HEX8(0x0E, PMU_STREAM_EVEN_STATUS_MASK);
    TEST_ASSERT_EQUAL_INT(1, PMU_STREAM_EVEN_STATUS_SHIFT);
    TEST_ASSERT_EQUAL_HEX8(0x01, PMU_STREAM_EVEN_ACTIVE_MASK);
    TEST_ASSERT_EQUAL_INT(0, PMU_STREAM_EVEN_ACTIVE_BIT);
}

/* ============================================================================
 * Main Test Runner
 * ============================================================================ */

int test_can_stream_main(void)
{
    UNITY_BEGIN();

    /* Initialization Tests */
    RUN_TEST(test_can_stream_init_default);
    RUN_TEST(test_can_stream_init_null_config);
    RUN_TEST(test_can_stream_init_custom_base_id);
    RUN_TEST(test_can_stream_init_extended_id);
    RUN_TEST(test_can_stream_init_can_bus_a);
    RUN_TEST(test_can_stream_init_can_bus_b);
    RUN_TEST(test_can_stream_init_include_extended_frames);
    RUN_TEST(test_can_stream_deinit);

    /* Enable/Disable Tests */
    RUN_TEST(test_can_stream_enable);
    RUN_TEST(test_can_stream_disable);
    RUN_TEST(test_can_stream_toggle);

    /* Configuration Tests */
    RUN_TEST(test_can_stream_configure);
    RUN_TEST(test_can_stream_get_config);

    /* Scaling Conversion Tests */
    RUN_TEST(test_vbat_to_raw_conversion);
    RUN_TEST(test_raw_to_vbat_conversion);
    RUN_TEST(test_vbat_roundtrip);
    RUN_TEST(test_ain_to_raw_conversion);
    RUN_TEST(test_raw_to_ain_conversion);
    RUN_TEST(test_ain_roundtrip);
    RUN_TEST(test_current_to_raw_conversion);
    RUN_TEST(test_raw_to_current_conversion);
    RUN_TEST(test_current_roundtrip);
    RUN_TEST(test_vout_to_raw_conversion);
    RUN_TEST(test_raw_to_vout_conversion);
    RUN_TEST(test_vout_roundtrip);

    /* Output State Packing/Unpacking Tests */
    RUN_TEST(test_pack_output_state_both_off);
    RUN_TEST(test_pack_output_state_both_active);
    RUN_TEST(test_pack_output_state_odd_active_only);
    RUN_TEST(test_pack_output_state_even_active_only);
    RUN_TEST(test_pack_output_state_overcurrent);
    RUN_TEST(test_pack_output_state_thermal_shutdown);
    RUN_TEST(test_unpack_output_state_both_off);
    RUN_TEST(test_unpack_output_state_both_active);
    RUN_TEST(test_unpack_roundtrip);

    /* Statistics Tests */
    RUN_TEST(test_can_stream_stats_initial);
    RUN_TEST(test_can_stream_stats_reset);

    /* Constants Tests */
    RUN_TEST(test_constants_frame_counts);
    RUN_TEST(test_constants_default_base_id);
    RUN_TEST(test_constants_rates);

    /* Enum Value Tests */
    RUN_TEST(test_status_enum_values);
    RUN_TEST(test_output_status_enum_values);
    RUN_TEST(test_hbridge_status_enum_values);

    /* Frame Structure Size Tests */
    RUN_TEST(test_frame0_size);
    RUN_TEST(test_frame1_size);
    RUN_TEST(test_frame_analog_size);
    RUN_TEST(test_frame_current_size);
    RUN_TEST(test_frame_voltage_size);
    RUN_TEST(test_frame_digital_size);
    RUN_TEST(test_frame_hbridge_size);

    /* Bit Mask Tests */
    RUN_TEST(test_status_mask);
    RUN_TEST(test_user_error_bit);
    RUN_TEST(test_odd_output_masks);
    RUN_TEST(test_even_output_masks);

    return UNITY_END();
}
