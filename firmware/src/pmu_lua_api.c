/**
 ******************************************************************************
 * @file           : pmu_lua_api.c
 * @brief          : Extended Lua API Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_lua_api.h"

#ifdef USE_LUA

#include "pmu_channel.h"
#include "pmu_logic_functions.h"
#include "pmu_protection.h"
#include <stdio.h>
#include <string.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/

/* Private function prototypes -----------------------------------------------*/

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Register all PMU API functions
 */
void PMU_Lua_RegisterAPI(lua_State* L)
{
    PMU_Lua_RegisterChannelAPI(L);
    PMU_Lua_RegisterLogicAPI(L);
    PMU_Lua_RegisterSystemAPI(L);
    PMU_Lua_RegisterUtilAPI(L);
}

/**
 * @brief Register channel access functions
 */
void PMU_Lua_RegisterChannelAPI(lua_State* L)
{
    /* Create 'channel' table */
    lua_newtable(L);

    /* channel.get */
    lua_pushstring(L, "get");
    lua_pushcfunction(L, lua_channel_get);
    lua_settable(L, -3);

    /* channel.set */
    lua_pushstring(L, "set");
    lua_pushcfunction(L, lua_channel_set);
    lua_settable(L, -3);

    /* channel.info */
    lua_pushstring(L, "info");
    lua_pushcfunction(L, lua_channel_info);
    lua_settable(L, -3);

    /* channel.find */
    lua_pushstring(L, "find");
    lua_pushcfunction(L, lua_channel_find);
    lua_settable(L, -3);

    /* channel.list */
    lua_pushstring(L, "list");
    lua_pushcfunction(L, lua_channel_list);
    lua_settable(L, -3);

    /* Set global 'channel' */
    lua_setglobal(L, "channel");
}

/**
 * @brief Register logic function API
 */
void PMU_Lua_RegisterLogicAPI(lua_State* L)
{
    /* Create 'logic' table */
    lua_newtable(L);

    lua_pushstring(L, "add");
    lua_pushcfunction(L, lua_logic_add);
    lua_settable(L, -3);

    lua_pushstring(L, "subtract");
    lua_pushcfunction(L, lua_logic_subtract);
    lua_settable(L, -3);

    lua_pushstring(L, "multiply");
    lua_pushcfunction(L, lua_logic_multiply);
    lua_settable(L, -3);

    lua_pushstring(L, "divide");
    lua_pushcfunction(L, lua_logic_divide);
    lua_settable(L, -3);

    lua_pushstring(L, "compare");
    lua_pushcfunction(L, lua_logic_compare);
    lua_settable(L, -3);

    lua_pushstring(L, "and");
    lua_pushcfunction(L, lua_logic_and);
    lua_settable(L, -3);

    lua_pushstring(L, "or");
    lua_pushcfunction(L, lua_logic_or);
    lua_settable(L, -3);

    lua_pushstring(L, "not");
    lua_pushcfunction(L, lua_logic_not);
    lua_settable(L, -3);

    lua_pushstring(L, "pid");
    lua_pushcfunction(L, lua_logic_pid);
    lua_settable(L, -3);

    lua_pushstring(L, "hysteresis");
    lua_pushcfunction(L, lua_logic_hysteresis);
    lua_settable(L, -3);

    lua_pushstring(L, "enable");
    lua_pushcfunction(L, lua_logic_enable);
    lua_settable(L, -3);

    lua_setglobal(L, "logic");
}

/**
 * @brief Register system functions API
 */
void PMU_Lua_RegisterSystemAPI(lua_State* L)
{
    lua_newtable(L);

    lua_pushstring(L, "voltage");
    lua_pushcfunction(L, lua_system_voltage);
    lua_settable(L, -3);

    lua_pushstring(L, "current");
    lua_pushcfunction(L, lua_system_current);
    lua_settable(L, -3);

    lua_pushstring(L, "temperature");
    lua_pushcfunction(L, lua_system_temperature);
    lua_settable(L, -3);

    lua_pushstring(L, "uptime");
    lua_pushcfunction(L, lua_system_uptime);
    lua_settable(L, -3);

    lua_setglobal(L, "system");
}

/**
 * @brief Register utility functions
 */
void PMU_Lua_RegisterUtilAPI(lua_State* L)
{
    /* Register global functions */
    lua_register(L, "print", lua_util_print);
    lua_register(L, "millis", lua_util_millis);
    lua_register(L, "sleep", lua_util_sleep);
}

/* Lua API Function Implementations ------------------------------------------*/

/* Channel API ---------------------------------------------------------------*/

/**
 * @brief Get channel value
 * Usage: value = channel.get(channel_id)
 */
int lua_channel_get(lua_State* L)
{
    if (!lua_isnumber(L, 1)) {
        lua_pushstring(L, "channel.get expects channel_id (number)");
        lua_error(L);
        return 0;
    }

    uint16_t channel_id = (uint16_t)lua_tointeger(L, 1);
    int32_t value = PMU_Channel_GetValue(channel_id);

    lua_pushinteger(L, value);
    return 1;
}

/**
 * @brief Set channel value
 * Usage: channel.set(channel_id, value)
 */
int lua_channel_set(lua_State* L)
{
    if (!lua_isnumber(L, 1) || !lua_isnumber(L, 2)) {
        lua_pushstring(L, "channel.set expects (channel_id, value)");
        lua_error(L);
        return 0;
    }

    uint16_t channel_id = (uint16_t)lua_tointeger(L, 1);
    int32_t value = (int32_t)lua_tointeger(L, 2);

    HAL_StatusTypeDef status = PMU_Channel_SetValue(channel_id, value);

    lua_pushboolean(L, status == HAL_OK);
    return 1;
}

/**
 * @brief Get channel info
 * Usage: info = channel.info(channel_id)
 * Returns: {id, name, type, value, min, max, unit}
 */
int lua_channel_info(lua_State* L)
{
    if (!lua_isnumber(L, 1)) {
        lua_pushstring(L, "channel.info expects channel_id (number)");
        lua_error(L);
        return 0;
    }

    uint16_t channel_id = (uint16_t)lua_tointeger(L, 1);
    const PMU_Channel_t* info = PMU_Channel_GetInfo(channel_id);

    if (info == NULL) {
        lua_pushnil(L);
        return 1;
    }

    /* Create info table */
    lua_newtable(L);

    lua_pushstring(L, "id");
    lua_pushinteger(L, info->channel_id);
    lua_settable(L, -3);

    lua_pushstring(L, "name");
    lua_pushstring(L, info->name);
    lua_settable(L, -3);

    lua_pushstring(L, "type");
    lua_pushinteger(L, info->type);
    lua_settable(L, -3);

    lua_pushstring(L, "value");
    lua_pushinteger(L, info->value);
    lua_settable(L, -3);

    lua_pushstring(L, "min");
    lua_pushinteger(L, info->min_value);
    lua_settable(L, -3);

    lua_pushstring(L, "max");
    lua_pushinteger(L, info->max_value);
    lua_settable(L, -3);

    lua_pushstring(L, "unit");
    lua_pushstring(L, info->unit);
    lua_settable(L, -3);

    return 1;
}

/**
 * @brief Find channel by name
 * Usage: channel_id = channel.find("Channel_Name")
 */
int lua_channel_find(lua_State* L)
{
    if (!lua_isstring(L, 1)) {
        lua_pushstring(L, "channel.find expects name (string)");
        lua_error(L);
        return 0;
    }

    const char* name = lua_tostring(L, 1);
    const PMU_Channel_t* ch = PMU_Channel_GetByName(name);

    if (ch) {
        lua_pushinteger(L, ch->channel_id);
    } else {
        lua_pushnil(L);
    }

    return 1;
}

/**
 * @brief List all channels
 * Usage: channels = channel.list()
 * Returns: array of channel info tables
 */
int lua_channel_list(lua_State* L)
{
    PMU_Channel_t channels[100];
    uint16_t count = PMU_Channel_List(channels, 100);

    lua_newtable(L);

    for (uint16_t i = 0; i < count; i++) {
        lua_pushinteger(L, i + 1);  /* Lua arrays start at 1 */

        /* Create channel info table */
        lua_newtable(L);

        lua_pushstring(L, "id");
        lua_pushinteger(L, channels[i].channel_id);
        lua_settable(L, -3);

        lua_pushstring(L, "name");
        lua_pushstring(L, channels[i].name);
        lua_settable(L, -3);

        lua_pushstring(L, "value");
        lua_pushinteger(L, channels[i].value);
        lua_settable(L, -3);

        lua_settable(L, -3);
    }

    return 1;
}

/* Logic API -----------------------------------------------------------------*/

/**
 * @brief Create ADD logic function
 * Usage: func_id = logic.add(output_ch, input_a, input_b)
 */
int lua_logic_add(lua_State* L)
{
    if (lua_gettop(L) < 3) {
        lua_pushstring(L, "logic.add expects (output_ch, input_a, input_b)");
        lua_error(L);
        return 0;
    }

    uint16_t output_ch = (uint16_t)lua_tointeger(L, 1);
    uint16_t input_a = (uint16_t)lua_tointeger(L, 2);
    uint16_t input_b = (uint16_t)lua_tointeger(L, 3);

    uint16_t func_id = PMU_LogicFunctions_CreateMath(PMU_FUNC_ADD, output_ch, input_a, input_b);

    lua_pushinteger(L, func_id);
    return 1;
}

/**
 * @brief Create SUBTRACT logic function
 */
int lua_logic_subtract(lua_State* L)
{
    if (lua_gettop(L) < 3) {
        lua_pushstring(L, "logic.subtract expects (output_ch, input_a, input_b)");
        lua_error(L);
        return 0;
    }

    uint16_t output_ch = (uint16_t)lua_tointeger(L, 1);
    uint16_t input_a = (uint16_t)lua_tointeger(L, 2);
    uint16_t input_b = (uint16_t)lua_tointeger(L, 3);

    uint16_t func_id = PMU_LogicFunctions_CreateMath(PMU_FUNC_SUBTRACT, output_ch, input_a, input_b);

    lua_pushinteger(L, func_id);
    return 1;
}

/**
 * @brief Create MULTIPLY logic function
 */
int lua_logic_multiply(lua_State* L)
{
    if (lua_gettop(L) < 3) {
        lua_pushstring(L, "logic.multiply expects (output_ch, input_a, input_b)");
        lua_error(L);
        return 0;
    }

    uint16_t output_ch = (uint16_t)lua_tointeger(L, 1);
    uint16_t input_a = (uint16_t)lua_tointeger(L, 2);
    uint16_t input_b = (uint16_t)lua_tointeger(L, 3);

    uint16_t func_id = PMU_LogicFunctions_CreateMath(PMU_FUNC_MULTIPLY, output_ch, input_a, input_b);

    lua_pushinteger(L, func_id);
    return 1;
}

/**
 * @brief Create DIVIDE logic function
 */
int lua_logic_divide(lua_State* L)
{
    if (lua_gettop(L) < 3) {
        lua_pushstring(L, "logic.divide expects (output_ch, input_a, input_b)");
        lua_error(L);
        return 0;
    }

    uint16_t output_ch = (uint16_t)lua_tointeger(L, 1);
    uint16_t input_a = (uint16_t)lua_tointeger(L, 2);
    uint16_t input_b = (uint16_t)lua_tointeger(L, 3);

    uint16_t func_id = PMU_LogicFunctions_CreateMath(PMU_FUNC_DIVIDE, output_ch, input_a, input_b);

    lua_pushinteger(L, func_id);
    return 1;
}

/**
 * @brief Create comparison logic function
 * Usage: func_id = logic.compare(output_ch, input_a, input_b, ">")
 */
int lua_logic_compare(lua_State* L)
{
    if (lua_gettop(L) < 4 || !lua_isstring(L, 4)) {
        lua_pushstring(L, "logic.compare expects (output_ch, input_a, input_b, operator)");
        lua_error(L);
        return 0;
    }

    uint16_t output_ch = (uint16_t)lua_tointeger(L, 1);
    uint16_t input_a = (uint16_t)lua_tointeger(L, 2);
    uint16_t input_b = (uint16_t)lua_tointeger(L, 3);
    const char* op = lua_tostring(L, 4);

    PMU_FunctionType_t type = PMU_FUNC_GREATER;

    if (strcmp(op, ">") == 0) type = PMU_FUNC_GREATER;
    else if (strcmp(op, "<") == 0) type = PMU_FUNC_LESS;
    else if (strcmp(op, "==") == 0) type = PMU_FUNC_EQUAL;
    else if (strcmp(op, "!=") == 0) type = PMU_FUNC_NOT_EQUAL;
    else if (strcmp(op, ">=") == 0) type = PMU_FUNC_GREATER_EQUAL;
    else if (strcmp(op, "<=") == 0) type = PMU_FUNC_LESS_EQUAL;

    uint16_t func_id = PMU_LogicFunctions_CreateComparison(type, output_ch, input_a, input_b);

    lua_pushinteger(L, func_id);
    return 1;
}

/**
 * @brief Create AND logic function
 */
int lua_logic_and(lua_State* L)
{
    /* TODO: Implement multi-input logic functions */
    lua_pushnil(L);
    return 1;
}

/**
 * @brief Create OR logic function
 */
int lua_logic_or(lua_State* L)
{
    /* TODO: Implement multi-input logic functions */
    lua_pushnil(L);
    return 1;
}

/**
 * @brief Create NOT logic function
 */
int lua_logic_not(lua_State* L)
{
    /* TODO: Implement NOT logic function */
    lua_pushnil(L);
    return 1;
}

/**
 * @brief Create PID controller
 * Usage: func_id = logic.pid(output_ch, input_ch, setpoint, kp, ki, kd)
 */
int lua_logic_pid(lua_State* L)
{
    if (lua_gettop(L) < 6) {
        lua_pushstring(L, "logic.pid expects (output_ch, input_ch, setpoint, kp, ki, kd)");
        lua_error(L);
        return 0;
    }

    uint16_t output_ch = (uint16_t)lua_tointeger(L, 1);
    uint16_t input_ch = (uint16_t)lua_tointeger(L, 2);
    float setpoint = (float)lua_tonumber(L, 3);
    float kp = (float)lua_tonumber(L, 4);
    float ki = (float)lua_tonumber(L, 5);
    float kd = (float)lua_tonumber(L, 6);

    uint16_t func_id = PMU_LogicFunctions_CreatePID(output_ch, input_ch, setpoint, kp, ki, kd);

    lua_pushinteger(L, func_id);
    return 1;
}

/**
 * @brief Create hysteresis function
 * Usage: func_id = logic.hysteresis(output_ch, input_ch, threshold_on, threshold_off)
 */
int lua_logic_hysteresis(lua_State* L)
{
    if (lua_gettop(L) < 4) {
        lua_pushstring(L, "logic.hysteresis expects (output_ch, input_ch, on_threshold, off_threshold)");
        lua_error(L);
        return 0;
    }

    uint16_t output_ch = (uint16_t)lua_tointeger(L, 1);
    uint16_t input_ch = (uint16_t)lua_tointeger(L, 2);
    int32_t threshold_on = (int32_t)lua_tointeger(L, 3);
    int32_t threshold_off = (int32_t)lua_tointeger(L, 4);

    uint16_t func_id = PMU_LogicFunctions_CreateHysteresis(output_ch, input_ch, threshold_on, threshold_off);

    lua_pushinteger(L, func_id);
    return 1;
}

/**
 * @brief Enable/disable logic function
 * Usage: logic.enable(func_id, true/false)
 */
int lua_logic_enable(lua_State* L)
{
    if (lua_gettop(L) < 2) {
        lua_pushstring(L, "logic.enable expects (func_id, enabled)");
        lua_error(L);
        return 0;
    }

    uint16_t func_id = (uint16_t)lua_tointeger(L, 1);
    bool enabled = lua_toboolean(L, 2);

    HAL_StatusTypeDef status = PMU_LogicFunctions_SetEnabled(func_id, enabled);

    lua_pushboolean(L, status == HAL_OK);
    return 1;
}

/* System API ----------------------------------------------------------------*/

/**
 * @brief Get battery voltage
 * Usage: voltage = system.voltage()
 */
int lua_system_voltage(lua_State* L)
{
    int32_t voltage = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
    lua_pushinteger(L, voltage);
    return 1;
}

/**
 * @brief Get total current
 * Usage: current = system.current()
 */
int lua_system_current(lua_State* L)
{
    int32_t current = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_TOTAL_I);
    lua_pushinteger(L, current);
    return 1;
}

/**
 * @brief Get MCU temperature
 * Usage: temp = system.temperature()
 */
int lua_system_temperature(lua_State* L)
{
    int32_t temp = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_MCU_TEMP);
    lua_pushinteger(L, temp);
    return 1;
}

/**
 * @brief Get system uptime
 * Usage: uptime = system.uptime()
 */
int lua_system_uptime(lua_State* L)
{
    uint32_t uptime = HAL_GetTick();
    lua_pushinteger(L, uptime);
    return 1;
}

/* Utility API ---------------------------------------------------------------*/

/**
 * @brief Print message (debug output)
 * Usage: print("Hello from Lua!")
 */
int lua_util_print(lua_State* L)
{
    const char* msg = lua_tostring(L, 1);
    if (msg) {
        /* TODO: Add actual debug output (UART/RTT/etc) */
        (void)msg;
    }
    return 0;
}

/**
 * @brief Get tick count in milliseconds
 * Usage: time = millis()
 */
int lua_util_millis(lua_State* L)
{
    uint32_t ticks = HAL_GetTick();
    lua_pushinteger(L, ticks);
    return 1;
}

/**
 * @brief Sleep for specified milliseconds
 * Usage: sleep(100)
 */
int lua_util_sleep(lua_State* L)
{
    if (!lua_isnumber(L, 1)) {
        lua_pushstring(L, "sleep expects milliseconds (number)");
        lua_error(L);
        return 0;
    }

    uint32_t ms = (uint32_t)lua_tointeger(L, 1);
    HAL_Delay(ms);

    return 0;
}

#else /* !USE_LUA */

/* Stub implementations when Lua is not available */
void PMU_Lua_RegisterAPI(lua_State* L) { (void)L; }
void PMU_Lua_RegisterChannelAPI(lua_State* L) { (void)L; }
void PMU_Lua_RegisterLogicAPI(lua_State* L) { (void)L; }
void PMU_Lua_RegisterSystemAPI(lua_State* L) { (void)L; }
void PMU_Lua_RegisterUtilAPI(lua_State* L) { (void)L; }

#endif /* USE_LUA */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
