/**
 ******************************************************************************
 * @file           : test_handler.c
 * @brief          : Unit tests for PMU Event Handler System
 * @author         : R2 m-sport
 * @date           : 2025-12-26
 ******************************************************************************
 */

#include "unity.h"
#include "pmu_handler.h"
#include <string.h>

/* Test setup and teardown */
void setUp(void)
{
    /* Initialize handler system before each test */
    PMU_Handler_Init();
}

void tearDown(void)
{
    /* Clean up after each test */
    PMU_Handler_ClearAll();
}

/* ===========================================================================
 * Initialization Tests
 * =========================================================================== */

void test_handler_init(void)
{
    HAL_StatusTypeDef status = PMU_Handler_Init();
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_handler_init_clears_stats(void)
{
    /* Add a handler first */
    PMU_HandlerConfig_t config;
    memset(&config, 0, sizeof(config));
    strcpy(config.id, "test_handler");
    config.enabled = true;
    PMU_Handler_AddHandler(&config);

    /* Re-init should clear */
    PMU_Handler_Init();

    const PMU_HandlerStats_t* stats = PMU_Handler_GetStats();
    TEST_ASSERT_NOT_NULL(stats);
    TEST_ASSERT_EQUAL(0, stats->total_handlers);
    TEST_ASSERT_EQUAL(0, stats->enabled_handlers);
}

/* ===========================================================================
 * Handler Registration Tests
 * =========================================================================== */

void test_add_handler(void)
{
    PMU_HandlerConfig_t config;
    memset(&config, 0, sizeof(config));
    strcpy(config.id, "handler_1");
    config.enabled = true;
    config.event = PMU_EVENT_CHANNEL_ON;
    config.action = PMU_ACTION_WRITE_CHANNEL;

    HAL_StatusTypeDef status = PMU_Handler_AddHandler(&config);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    const PMU_HandlerStats_t* stats = PMU_Handler_GetStats();
    TEST_ASSERT_EQUAL(1, stats->total_handlers);
    TEST_ASSERT_EQUAL(1, stats->enabled_handlers);
}

void test_add_handler_null_config(void)
{
    HAL_StatusTypeDef status = PMU_Handler_AddHandler(NULL);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_add_handler_empty_id(void)
{
    PMU_HandlerConfig_t config;
    memset(&config, 0, sizeof(config));
    config.id[0] = '\0';  /* Empty ID */

    HAL_StatusTypeDef status = PMU_Handler_AddHandler(&config);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_add_multiple_handlers(void)
{
    PMU_HandlerConfig_t config;

    for (int i = 0; i < 5; i++) {
        memset(&config, 0, sizeof(config));
        snprintf(config.id, sizeof(config.id), "handler_%d", i);
        config.enabled = true;
        TEST_ASSERT_EQUAL(HAL_OK, PMU_Handler_AddHandler(&config));
    }

    const PMU_HandlerStats_t* stats = PMU_Handler_GetStats();
    TEST_ASSERT_EQUAL(5, stats->total_handlers);
    TEST_ASSERT_EQUAL(5, stats->enabled_handlers);
}

void test_add_handler_update_existing(void)
{
    PMU_HandlerConfig_t config;
    memset(&config, 0, sizeof(config));
    strcpy(config.id, "handler_1");
    config.enabled = true;
    config.value = 100.0f;

    /* Add first time */
    PMU_Handler_AddHandler(&config);

    /* Update with new value */
    config.value = 200.0f;
    HAL_StatusTypeDef status = PMU_Handler_AddHandler(&config);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    /* Should still be 1 handler */
    const PMU_HandlerStats_t* stats = PMU_Handler_GetStats();
    TEST_ASSERT_EQUAL(1, stats->total_handlers);

    /* Verify value was updated */
    const PMU_HandlerState_t* state = PMU_Handler_GetState("handler_1");
    TEST_ASSERT_NOT_NULL(state);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 200.0f, state->config.value);
}

void test_add_handler_max_handlers(void)
{
    PMU_HandlerConfig_t config;

    /* Fill all slots */
    for (int i = 0; i < PMU_HANDLER_MAX_HANDLERS; i++) {
        memset(&config, 0, sizeof(config));
        snprintf(config.id, sizeof(config.id), "h_%d", i);
        config.enabled = true;
        TEST_ASSERT_EQUAL(HAL_OK, PMU_Handler_AddHandler(&config));
    }

    /* Try to add one more - should fail */
    memset(&config, 0, sizeof(config));
    strcpy(config.id, "overflow");
    config.enabled = true;
    HAL_StatusTypeDef status = PMU_Handler_AddHandler(&config);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * Handler Removal Tests
 * =========================================================================== */

void test_remove_handler(void)
{
    PMU_HandlerConfig_t config;
    memset(&config, 0, sizeof(config));
    strcpy(config.id, "to_remove");
    config.enabled = true;
    PMU_Handler_AddHandler(&config);

    HAL_StatusTypeDef status = PMU_Handler_RemoveHandler("to_remove");
    TEST_ASSERT_EQUAL(HAL_OK, status);

    const PMU_HandlerStats_t* stats = PMU_Handler_GetStats();
    TEST_ASSERT_EQUAL(0, stats->total_handlers);
}

void test_remove_handler_not_found(void)
{
    HAL_StatusTypeDef status = PMU_Handler_RemoveHandler("nonexistent");
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_remove_handler_updates_enabled_count(void)
{
    PMU_HandlerConfig_t config;
    memset(&config, 0, sizeof(config));
    strcpy(config.id, "enabled_handler");
    config.enabled = true;
    PMU_Handler_AddHandler(&config);

    const PMU_HandlerStats_t* stats = PMU_Handler_GetStats();
    TEST_ASSERT_EQUAL(1, stats->enabled_handlers);

    PMU_Handler_RemoveHandler("enabled_handler");
    TEST_ASSERT_EQUAL(0, stats->enabled_handlers);
}

void test_clear_all_handlers(void)
{
    PMU_HandlerConfig_t config;

    /* Add several handlers */
    for (int i = 0; i < 10; i++) {
        memset(&config, 0, sizeof(config));
        snprintf(config.id, sizeof(config.id), "h_%d", i);
        config.enabled = true;
        PMU_Handler_AddHandler(&config);
    }

    HAL_StatusTypeDef status = PMU_Handler_ClearAll();
    TEST_ASSERT_EQUAL(HAL_OK, status);

    const PMU_HandlerStats_t* stats = PMU_Handler_GetStats();
    TEST_ASSERT_EQUAL(0, stats->total_handlers);
    TEST_ASSERT_EQUAL(0, stats->enabled_handlers);
}

/* ===========================================================================
 * Enable/Disable Tests
 * =========================================================================== */

void test_set_enabled(void)
{
    PMU_HandlerConfig_t config;
    memset(&config, 0, sizeof(config));
    strcpy(config.id, "toggle_handler");
    config.enabled = true;
    PMU_Handler_AddHandler(&config);

    /* Disable */
    HAL_StatusTypeDef status = PMU_Handler_SetEnabled("toggle_handler", false);
    TEST_ASSERT_EQUAL(HAL_OK, status);
    TEST_ASSERT_FALSE(PMU_Handler_IsEnabled("toggle_handler"));

    /* Enable */
    status = PMU_Handler_SetEnabled("toggle_handler", true);
    TEST_ASSERT_EQUAL(HAL_OK, status);
    TEST_ASSERT_TRUE(PMU_Handler_IsEnabled("toggle_handler"));
}

void test_set_enabled_not_found(void)
{
    HAL_StatusTypeDef status = PMU_Handler_SetEnabled("nonexistent", true);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

void test_is_enabled_not_found(void)
{
    bool enabled = PMU_Handler_IsEnabled("nonexistent");
    TEST_ASSERT_FALSE(enabled);
}

void test_enabled_count_updates(void)
{
    PMU_HandlerConfig_t config;
    memset(&config, 0, sizeof(config));
    strcpy(config.id, "counter_test");
    config.enabled = false;  /* Start disabled */
    PMU_Handler_AddHandler(&config);

    const PMU_HandlerStats_t* stats = PMU_Handler_GetStats();
    TEST_ASSERT_EQUAL(0, stats->enabled_handlers);

    PMU_Handler_SetEnabled("counter_test", true);
    TEST_ASSERT_EQUAL(1, stats->enabled_handlers);

    PMU_Handler_SetEnabled("counter_test", false);
    TEST_ASSERT_EQUAL(0, stats->enabled_handlers);
}

/* ===========================================================================
 * Event Queue Tests
 * =========================================================================== */

void test_push_event(void)
{
    HAL_StatusTypeDef status = PMU_Handler_PushEvent(
        PMU_EVENT_CHANNEL_ON, 100, 1);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_push_system_event(void)
{
    HAL_StatusTypeDef status = PMU_Handler_PushSystemEvent(
        PMU_EVENT_SYSTEM_UNDERVOLT);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

void test_push_multiple_events(void)
{
    for (int i = 0; i < PMU_HANDLER_EVENT_QUEUE_SIZE; i++) {
        HAL_StatusTypeDef status = PMU_Handler_PushEvent(
            PMU_EVENT_CHANNEL_ON, i, i);
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }
}

void test_push_event_queue_full(void)
{
    /* Fill queue */
    for (int i = 0; i < PMU_HANDLER_EVENT_QUEUE_SIZE; i++) {
        PMU_Handler_PushEvent(PMU_EVENT_CHANNEL_ON, i, i);
    }

    /* Try to push one more */
    HAL_StatusTypeDef status = PMU_Handler_PushEvent(
        PMU_EVENT_CHANNEL_ON, 999, 999);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* ===========================================================================
 * Handler State Tests
 * =========================================================================== */

void test_get_state(void)
{
    PMU_HandlerConfig_t config;
    memset(&config, 0, sizeof(config));
    strcpy(config.id, "state_test");
    strcpy(config.source_channel, "input_1");
    strcpy(config.target_channel, "output_1");
    config.enabled = true;
    config.event = PMU_EVENT_CHANNEL_ON;
    config.action = PMU_ACTION_WRITE_CHANNEL;
    config.value = 123.0f;
    PMU_Handler_AddHandler(&config);

    const PMU_HandlerState_t* state = PMU_Handler_GetState("state_test");
    TEST_ASSERT_NOT_NULL(state);
    TEST_ASSERT_TRUE(state->active);
    TEST_ASSERT_EQUAL_STRING("state_test", state->config.id);
    TEST_ASSERT_EQUAL_STRING("input_1", state->config.source_channel);
    TEST_ASSERT_EQUAL_STRING("output_1", state->config.target_channel);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 123.0f, state->config.value);
}

void test_get_state_not_found(void)
{
    const PMU_HandlerState_t* state = PMU_Handler_GetState("nonexistent");
    TEST_ASSERT_NULL(state);
}

void test_get_stats(void)
{
    const PMU_HandlerStats_t* stats = PMU_Handler_GetStats();
    TEST_ASSERT_NOT_NULL(stats);
}

/* ===========================================================================
 * List Handlers Tests
 * =========================================================================== */

void test_list_handlers(void)
{
    PMU_HandlerConfig_t configs[10];
    PMU_HandlerConfig_t config;

    /* Add 3 handlers */
    for (int i = 0; i < 3; i++) {
        memset(&config, 0, sizeof(config));
        snprintf(config.id, sizeof(config.id), "list_%d", i);
        config.enabled = true;
        PMU_Handler_AddHandler(&config);
    }

    uint8_t count = PMU_Handler_ListHandlers(configs, 10);
    TEST_ASSERT_EQUAL(3, count);
}

void test_list_handlers_max_count(void)
{
    PMU_HandlerConfig_t configs[2];
    PMU_HandlerConfig_t config;

    /* Add 5 handlers */
    for (int i = 0; i < 5; i++) {
        memset(&config, 0, sizeof(config));
        snprintf(config.id, sizeof(config.id), "h_%d", i);
        config.enabled = true;
        PMU_Handler_AddHandler(&config);
    }

    /* Request only 2 */
    uint8_t count = PMU_Handler_ListHandlers(configs, 2);
    TEST_ASSERT_EQUAL(2, count);
}

/* ===========================================================================
 * String Conversion Tests
 * =========================================================================== */

void test_event_type_to_string(void)
{
    TEST_ASSERT_EQUAL_STRING("channel_on",
        PMU_Handler_EventTypeToString(PMU_EVENT_CHANNEL_ON));
    TEST_ASSERT_EQUAL_STRING("channel_off",
        PMU_Handler_EventTypeToString(PMU_EVENT_CHANNEL_OFF));
    TEST_ASSERT_EQUAL_STRING("channel_fault",
        PMU_Handler_EventTypeToString(PMU_EVENT_CHANNEL_FAULT));
    TEST_ASSERT_EQUAL_STRING("channel_cleared",
        PMU_Handler_EventTypeToString(PMU_EVENT_CHANNEL_CLEARED));
    TEST_ASSERT_EQUAL_STRING("threshold_high",
        PMU_Handler_EventTypeToString(PMU_EVENT_THRESHOLD_HIGH));
    TEST_ASSERT_EQUAL_STRING("threshold_low",
        PMU_Handler_EventTypeToString(PMU_EVENT_THRESHOLD_LOW));
    TEST_ASSERT_EQUAL_STRING("system_undervolt",
        PMU_Handler_EventTypeToString(PMU_EVENT_SYSTEM_UNDERVOLT));
    TEST_ASSERT_EQUAL_STRING("system_overvolt",
        PMU_Handler_EventTypeToString(PMU_EVENT_SYSTEM_OVERVOLT));
    TEST_ASSERT_EQUAL_STRING("system_overtemp",
        PMU_Handler_EventTypeToString(PMU_EVENT_SYSTEM_OVERTEMP));
}

void test_action_type_to_string(void)
{
    TEST_ASSERT_EQUAL_STRING("write_channel",
        PMU_Handler_ActionTypeToString(PMU_ACTION_WRITE_CHANNEL));
    TEST_ASSERT_EQUAL_STRING("send_can",
        PMU_Handler_ActionTypeToString(PMU_ACTION_SEND_CAN));
    TEST_ASSERT_EQUAL_STRING("send_lin",
        PMU_Handler_ActionTypeToString(PMU_ACTION_SEND_LIN));
    TEST_ASSERT_EQUAL_STRING("run_lua",
        PMU_Handler_ActionTypeToString(PMU_ACTION_RUN_LUA));
    TEST_ASSERT_EQUAL_STRING("set_output",
        PMU_Handler_ActionTypeToString(PMU_ACTION_SET_OUTPUT));
}

void test_unknown_type_to_string(void)
{
    TEST_ASSERT_EQUAL_STRING("unknown",
        PMU_Handler_EventTypeToString((PMU_EventType_t)999));
    TEST_ASSERT_EQUAL_STRING("unknown",
        PMU_Handler_ActionTypeToString((PMU_ActionType_t)999));
}

/* ===========================================================================
 * Update/Process Tests
 * =========================================================================== */

void test_update_empty_queue(void)
{
    /* Should not crash with empty queue */
    PMU_Handler_Update();

    const PMU_HandlerStats_t* stats = PMU_Handler_GetStats();
    TEST_ASSERT_EQUAL(0, stats->events_processed);
}

void test_update_processes_events(void)
{
    /* Push an event */
    PMU_Handler_PushEvent(PMU_EVENT_CHANNEL_ON, 1, 100);

    /* Process */
    PMU_Handler_Update();

    const PMU_HandlerStats_t* stats = PMU_Handler_GetStats();
    TEST_ASSERT_EQUAL(1, stats->events_processed);
}

void test_update_clears_queue(void)
{
    /* Push multiple events */
    for (int i = 0; i < 5; i++) {
        PMU_Handler_PushEvent(PMU_EVENT_CHANNEL_ON, i, i);
    }

    /* Process all */
    PMU_Handler_Update();

    const PMU_HandlerStats_t* stats = PMU_Handler_GetStats();
    TEST_ASSERT_EQUAL(5, stats->events_processed);

    /* Queue should be empty, push should work */
    HAL_StatusTypeDef status = PMU_Handler_PushEvent(
        PMU_EVENT_CHANNEL_ON, 100, 100);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* ===========================================================================
 * Handler Configuration Tests
 * =========================================================================== */

void test_handler_with_condition_channel(void)
{
    PMU_HandlerConfig_t config;
    memset(&config, 0, sizeof(config));
    strcpy(config.id, "cond_handler");
    strcpy(config.condition_channel, "enable_flag");
    config.enabled = true;
    config.event = PMU_EVENT_CHANNEL_ON;
    config.action = PMU_ACTION_WRITE_CHANNEL;

    HAL_StatusTypeDef status = PMU_Handler_AddHandler(&config);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    const PMU_HandlerState_t* state = PMU_Handler_GetState("cond_handler");
    TEST_ASSERT_NOT_NULL(state);
    TEST_ASSERT_EQUAL_STRING("enable_flag", state->config.condition_channel);
}

void test_handler_with_threshold(void)
{
    PMU_HandlerConfig_t config;
    memset(&config, 0, sizeof(config));
    strcpy(config.id, "threshold_handler");
    strcpy(config.source_channel, "temp_sensor");
    config.enabled = true;
    config.event = PMU_EVENT_THRESHOLD_HIGH;
    config.threshold_value = 85.0f;
    config.action = PMU_ACTION_SET_OUTPUT;

    HAL_StatusTypeDef status = PMU_Handler_AddHandler(&config);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    const PMU_HandlerState_t* state = PMU_Handler_GetState("threshold_handler");
    TEST_ASSERT_NOT_NULL(state);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 85.0f, state->config.threshold_value);
}

void test_handler_with_can_message(void)
{
    PMU_HandlerConfig_t config;
    memset(&config, 0, sizeof(config));
    strcpy(config.id, "can_handler");
    config.enabled = true;
    config.event = PMU_EVENT_CHANNEL_FAULT;
    config.action = PMU_ACTION_SEND_CAN;
    config.message.bus = 1;
    config.message.message_id = 0x123;
    config.message.dlc = 8;
    config.message.data[0] = 0xAA;
    config.message.data[1] = 0xBB;

    HAL_StatusTypeDef status = PMU_Handler_AddHandler(&config);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    const PMU_HandlerState_t* state = PMU_Handler_GetState("can_handler");
    TEST_ASSERT_NOT_NULL(state);
    TEST_ASSERT_EQUAL(1, state->config.message.bus);
    TEST_ASSERT_EQUAL_HEX32(0x123, state->config.message.message_id);
    TEST_ASSERT_EQUAL_HEX8(0xAA, state->config.message.data[0]);
}

void test_handler_with_lua_function(void)
{
    PMU_HandlerConfig_t config;
    memset(&config, 0, sizeof(config));
    strcpy(config.id, "lua_handler");
    strcpy(config.lua_function, "on_fault_detected");
    config.enabled = true;
    config.event = PMU_EVENT_CHANNEL_FAULT;
    config.action = PMU_ACTION_RUN_LUA;

    HAL_StatusTypeDef status = PMU_Handler_AddHandler(&config);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    const PMU_HandlerState_t* state = PMU_Handler_GetState("lua_handler");
    TEST_ASSERT_NOT_NULL(state);
    TEST_ASSERT_EQUAL_STRING("on_fault_detected", state->config.lua_function);
}

/* ===========================================================================
 * Main Test Runner
 * =========================================================================== */

int test_handler_main(void)
{
    UNITY_BEGIN();

    /* Initialization */
    RUN_TEST(test_handler_init);
    RUN_TEST(test_handler_init_clears_stats);

    /* Registration */
    RUN_TEST(test_add_handler);
    RUN_TEST(test_add_handler_null_config);
    RUN_TEST(test_add_handler_empty_id);
    RUN_TEST(test_add_multiple_handlers);
    RUN_TEST(test_add_handler_update_existing);
    RUN_TEST(test_add_handler_max_handlers);

    /* Removal */
    RUN_TEST(test_remove_handler);
    RUN_TEST(test_remove_handler_not_found);
    RUN_TEST(test_remove_handler_updates_enabled_count);
    RUN_TEST(test_clear_all_handlers);

    /* Enable/Disable */
    RUN_TEST(test_set_enabled);
    RUN_TEST(test_set_enabled_not_found);
    RUN_TEST(test_is_enabled_not_found);
    RUN_TEST(test_enabled_count_updates);

    /* Event Queue */
    RUN_TEST(test_push_event);
    RUN_TEST(test_push_system_event);
    RUN_TEST(test_push_multiple_events);
    RUN_TEST(test_push_event_queue_full);

    /* State */
    RUN_TEST(test_get_state);
    RUN_TEST(test_get_state_not_found);
    RUN_TEST(test_get_stats);

    /* List */
    RUN_TEST(test_list_handlers);
    RUN_TEST(test_list_handlers_max_count);

    /* String Conversion */
    RUN_TEST(test_event_type_to_string);
    RUN_TEST(test_action_type_to_string);
    RUN_TEST(test_unknown_type_to_string);

    /* Update */
    RUN_TEST(test_update_empty_queue);
    RUN_TEST(test_update_processes_events);
    RUN_TEST(test_update_clears_queue);

    /* Configuration */
    RUN_TEST(test_handler_with_condition_channel);
    RUN_TEST(test_handler_with_threshold);
    RUN_TEST(test_handler_with_can_message);
    RUN_TEST(test_handler_with_lua_function);

    return UNITY_END();
}

#ifdef TEST_HANDLER_STANDALONE
int main(void) { return test_handler_main(); }
#endif
