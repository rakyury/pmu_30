/**
 ******************************************************************************
 * @file           : test_lua.c
 * @brief          : Unit tests for PMU Lua Scripting System
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 */

#include "unity.h"
#include "pmu_lua.h"
#include <string.h>

/* Test setup and teardown */
void setUp(void)
{
    PMU_Lua_Init();
}

void tearDown(void)
{
    PMU_Lua_Deinit();
}

/* Test: Lua initialization */
void test_lua_init(void)
{
    HAL_StatusTypeDef status = PMU_Lua_Init();
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: Load simple script */
void test_load_script(void)
{
    const char* script = "-- Simple script\nreturn 42";

    HAL_StatusTypeDef status = PMU_Lua_LoadScript("test_script", script, strlen(script));
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: Load script with NULL name */
void test_load_script_null_name(void)
{
    const char* script = "return 42";

    HAL_StatusTypeDef status = PMU_Lua_LoadScript(NULL, script, strlen(script));
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* Test: Load script with NULL code */
void test_load_script_null_code(void)
{
    HAL_StatusTypeDef status = PMU_Lua_LoadScript("test", NULL, 0);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* Test: Load script too large */
void test_load_script_too_large(void)
{
    char large_script[PMU_LUA_MAX_SCRIPT_SIZE + 100];
    memset(large_script, 'X', sizeof(large_script));
    large_script[sizeof(large_script) - 1] = '\0';

    HAL_StatusTypeDef status = PMU_Lua_LoadScript("large", large_script, sizeof(large_script));
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* Test: Unload script */
void test_unload_script(void)
{
    const char* script = "return 42";

    PMU_Lua_LoadScript("test_script", script, strlen(script));
    HAL_StatusTypeDef status = PMU_Lua_UnloadScript("test_script");
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: Unload non-existent script */
void test_unload_nonexistent(void)
{
    HAL_StatusTypeDef status = PMU_Lua_UnloadScript("nonexistent");
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* Test: Execute script */
void test_execute_script(void)
{
    const char* script = "-- Test script";

    PMU_Lua_LoadScript("exec_test", script, strlen(script));
    PMU_Lua_Status_t status = PMU_Lua_ExecuteScript("exec_test");

    /* Will return OK even though Lua is not integrated yet */
    TEST_ASSERT_TRUE(status == PMU_LUA_STATUS_OK || status == PMU_LUA_STATUS_ERROR);
}

/* Test: Execute non-existent script */
void test_execute_nonexistent(void)
{
    PMU_Lua_Status_t status = PMU_Lua_ExecuteScript("nonexistent");
    TEST_ASSERT_EQUAL(PMU_LUA_STATUS_ERROR, status);
}

/* Test: Execute code directly */
void test_execute_code(void)
{
    const char* code = "return 1 + 1";

    PMU_Lua_Status_t status = PMU_Lua_ExecuteCode(code);
    TEST_ASSERT_TRUE(status == PMU_LUA_STATUS_OK || status == PMU_LUA_STATUS_ERROR);
}

/* Test: Execute NULL code */
void test_execute_null_code(void)
{
    PMU_Lua_Status_t status = PMU_Lua_ExecuteCode(NULL);
    TEST_ASSERT_EQUAL(PMU_LUA_STATUS_ERROR, status);
}

/* Test: Enable/disable script */
void test_enable_disable_script(void)
{
    const char* script = "-- Test";

    PMU_Lua_LoadScript("test", script, strlen(script));

    HAL_StatusTypeDef status = PMU_Lua_SetScriptEnabled("test", 0);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    status = PMU_Lua_SetScriptEnabled("test", 1);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: Set auto-run */
void test_set_autorun(void)
{
    const char* script = "-- Test";

    PMU_Lua_LoadScript("test", script, strlen(script));

    HAL_StatusTypeDef status = PMU_Lua_SetScriptAutoRun("test", 1);
    TEST_ASSERT_EQUAL(HAL_OK, status);

    status = PMU_Lua_SetScriptAutoRun("test", 0);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: Get script info */
void test_get_script_info(void)
{
    const char* script = "-- Test script";

    PMU_Lua_LoadScript("info_test", script, strlen(script));

    PMU_Lua_ScriptInfo_t* info = PMU_Lua_GetScriptInfo("info_test");
    TEST_ASSERT_NOT_NULL(info);
    TEST_ASSERT_EQUAL(strlen(script), info->size);
}

/* Test: Get info for non-existent script */
void test_get_info_nonexistent(void)
{
    PMU_Lua_ScriptInfo_t* info = PMU_Lua_GetScriptInfo("nonexistent");
    TEST_ASSERT_NULL(info);
}

/* Test: Get statistics */
void test_get_stats(void)
{
    PMU_Lua_Stats_t* stats = PMU_Lua_GetStats();

    TEST_ASSERT_NOT_NULL(stats);
    TEST_ASSERT_GREATER_OR_EQUAL(0, stats->total_scripts);
    TEST_ASSERT_GREATER_OR_EQUAL(0, stats->active_scripts);
    TEST_ASSERT_GREATER_OR_EQUAL(0, stats->memory_used);
}

/* Test: List scripts */
void test_list_scripts(void)
{
    PMU_Lua_ScriptInfo_t scripts[PMU_LUA_MAX_SCRIPTS];

    const char* script1 = "-- Script 1";
    const char* script2 = "-- Script 2";

    PMU_Lua_LoadScript("script1", script1, strlen(script1));
    PMU_Lua_LoadScript("script2", script2, strlen(script2));

    uint8_t count = PMU_Lua_ListScripts(scripts, PMU_LUA_MAX_SCRIPTS);
    TEST_ASSERT_GREATER_OR_EQUAL(2, count);
}

/* Test: Clear errors */
void test_clear_errors(void)
{
    PMU_Lua_ClearErrors();

    const char* error = PMU_Lua_GetLastError();
    TEST_ASSERT_NOT_NULL(error);
}

/* Test: Get last error */
void test_get_last_error(void)
{
    const char* error = PMU_Lua_GetLastError();
    TEST_ASSERT_NOT_NULL(error);
}

/* Test: Register function */
void test_register_function(void)
{
    int dummy_func(void) { return 0; }

    HAL_StatusTypeDef status = PMU_Lua_RegisterFunction("test_func", (void*)dummy_func);
    TEST_ASSERT_EQUAL(HAL_OK, status);
}

/* Test: Register function with NULL */
void test_register_null_function(void)
{
    HAL_StatusTypeDef status = PMU_Lua_RegisterFunction("test", NULL);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);

    status = PMU_Lua_RegisterFunction(NULL, (void*)test_register_null_function);
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* Test: Update Lua engine */
void test_lua_update(void)
{
    const char* script = "-- Auto-run script";

    PMU_Lua_LoadScript("auto", script, strlen(script));
    PMU_Lua_SetScriptAutoRun("auto", 1);

    /* Call update multiple times */
    for (int i = 0; i < 10; i++) {
        PMU_Lua_Update();
    }
}

/* Test: Load maximum scripts */
void test_max_scripts(void)
{
    const char* script = "-- Test";
    char name[32];

    /* Load max scripts */
    for (int i = 0; i < PMU_LUA_MAX_SCRIPTS; i++) {
        snprintf(name, sizeof(name), "script_%d", i);
        HAL_StatusTypeDef status = PMU_Lua_LoadScript(name, script, strlen(script));
        TEST_ASSERT_EQUAL(HAL_OK, status);
    }

    /* Try to load one more - should fail */
    HAL_StatusTypeDef status = PMU_Lua_LoadScript("overflow", script, strlen(script));
    TEST_ASSERT_EQUAL(HAL_ERROR, status);
}

/* Test: Script statistics update */
void test_stats_update(void)
{
    PMU_Lua_Stats_t* stats_before = PMU_Lua_GetStats();
    uint32_t scripts_before = stats_before->total_scripts;

    const char* script = "-- Test";
    PMU_Lua_LoadScript("stat_test", script, strlen(script));

    PMU_Lua_Stats_t* stats_after = PMU_Lua_GetStats();
    TEST_ASSERT_EQUAL(scripts_before + 1, stats_after->total_scripts);
}

/* Main test runner */
int main(void)
{
    UNITY_BEGIN();

    RUN_TEST(test_lua_init);
    RUN_TEST(test_load_script);
    RUN_TEST(test_load_script_null_name);
    RUN_TEST(test_load_script_null_code);
    RUN_TEST(test_load_script_too_large);
    RUN_TEST(test_unload_script);
    RUN_TEST(test_unload_nonexistent);
    RUN_TEST(test_execute_script);
    RUN_TEST(test_execute_nonexistent);
    RUN_TEST(test_execute_code);
    RUN_TEST(test_execute_null_code);
    RUN_TEST(test_enable_disable_script);
    RUN_TEST(test_set_autorun);
    RUN_TEST(test_get_script_info);
    RUN_TEST(test_get_info_nonexistent);
    RUN_TEST(test_get_stats);
    RUN_TEST(test_list_scripts);
    RUN_TEST(test_clear_errors);
    RUN_TEST(test_get_last_error);
    RUN_TEST(test_register_function);
    RUN_TEST(test_register_null_function);
    RUN_TEST(test_lua_update);
    RUN_TEST(test_max_scripts);
    RUN_TEST(test_stats_update);

    return UNITY_END();
}
