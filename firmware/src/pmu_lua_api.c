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
#include "pmu_can.h"
#include "pmu_lin.h"
#include "pmu_pid.h"
#include "pmu_log.h"
#include <stdio.h>
#include <string.h>

/* Module identifier for logging */
#define LOG_SRC "LUA"

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/

/* Private macro -------------------------------------------------------------*/

/* Argument extraction helpers */
#define LUA_GET_UINT16(L, idx) ((uint16_t)lua_tointeger(L, idx))
#define LUA_GET_UINT8(L, idx)  ((uint8_t)lua_tointeger(L, idx))
#define LUA_GET_INT32(L, idx)  ((int32_t)lua_tointeger(L, idx))
#define LUA_GET_FLOAT(L, idx)  ((float)lua_tonumber(L, idx))

/* Argument count validation */
#define LUA_CHECK_ARGS(L, min_args, func_name) \
    do { \
        if (lua_gettop(L) < (min_args)) { \
            lua_pushfstring(L, "%s expects at least %d argument(s)", func_name, min_args); \
            lua_error(L); \
            return 0; \
        } \
    } while(0)

/* Table building helpers */
#define LUA_TABLE_SET_INT(L, key, val) \
    do { lua_pushstring(L, key); lua_pushinteger(L, val); lua_settable(L, -3); } while(0)

#define LUA_TABLE_SET_STRING(L, key, val) \
    do { lua_pushstring(L, key); lua_pushstring(L, val); lua_settable(L, -3); } while(0)

#define LUA_TABLE_SET_NUMBER(L, key, val) \
    do { lua_pushstring(L, key); lua_pushnumber(L, (lua_Number)(val)); lua_settable(L, -3); } while(0)

#define LUA_TABLE_SET_BOOL(L, key, val) \
    do { lua_pushstring(L, key); lua_pushboolean(L, val); lua_settable(L, -3); } while(0)

/* Private typedef -----------------------------------------------------------*/

/**
 * @brief Library function entry for registration helper
 */
typedef struct {
    const char* name;
    lua_CFunction func;
} PMU_Lua_LibFunc_t;

/* Private variables ---------------------------------------------------------*/

/* Private function prototypes -----------------------------------------------*/

/**
 * @brief Register a library of functions under a global table name
 */
static void PMU_Lua_RegisterLib(lua_State* L, const char* lib_name,
                                 const PMU_Lua_LibFunc_t* funcs, size_t count)
{
    lua_newtable(L);
    for (size_t i = 0; i < count; i++) {
        lua_pushstring(L, funcs[i].name);
        lua_pushcfunction(L, funcs[i].func);
        lua_settable(L, -3);
    }
    lua_setglobal(L, lib_name);
}

#define REGISTER_LIB(L, name, funcs) \
    PMU_Lua_RegisterLib(L, name, funcs, sizeof(funcs)/sizeof(funcs[0]))

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
    PMU_Lua_RegisterCanAPI(L);
    PMU_Lua_RegisterLinAPI(L);
    PMU_Lua_RegisterPidAPI(L);
}

/**
 * @brief Register channel access functions
 */
void PMU_Lua_RegisterChannelAPI(lua_State* L)
{
    static const PMU_Lua_LibFunc_t channel_funcs[] = {
        {"get",  lua_channel_get},
        {"set",  lua_channel_set},
        {"info", lua_channel_info},
        {"find", lua_channel_find},
        {"list", lua_channel_list},
    };
    REGISTER_LIB(L, "channel", channel_funcs);
}

/**
 * @brief Register logic function API
 */
void PMU_Lua_RegisterLogicAPI(lua_State* L)
{
    static const PMU_Lua_LibFunc_t logic_funcs[] = {
        {"add",        lua_logic_add},
        {"subtract",   lua_logic_subtract},
        {"multiply",   lua_logic_multiply},
        {"divide",     lua_logic_divide},
        {"compare",    lua_logic_compare},
        {"and",        lua_logic_and},
        {"or",         lua_logic_or},
        {"not",        lua_logic_not},
        {"pid",        lua_logic_pid},
        {"hysteresis", lua_logic_hysteresis},
        {"enable",     lua_logic_enable},
    };
    REGISTER_LIB(L, "logic", logic_funcs);
}

/**
 * @brief Register system functions API
 */
void PMU_Lua_RegisterSystemAPI(lua_State* L)
{
    static const PMU_Lua_LibFunc_t system_funcs[] = {
        {"voltage",     lua_system_voltage},
        {"current",     lua_system_current},
        {"temperature", lua_system_temperature},
        {"uptime",      lua_system_uptime},
    };
    REGISTER_LIB(L, "system", system_funcs);
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

    /* Check if channel exists */
    const PMU_Channel_t* ch = PMU_Channel_GetInfo(channel_id);
    if (!ch) {
        PMU_LOG_WARN(LOG_SRC, "channel.get: Invalid channel ID %u", channel_id);
        lua_pushnil(L);
        return 1;
    }

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

    /* Check if channel exists */
    const PMU_Channel_t* ch = PMU_Channel_GetInfo(channel_id);
    if (!ch) {
        PMU_LOG_WARN(LOG_SRC, "channel.set: Invalid channel ID %u", channel_id);
        lua_pushboolean(L, 0);
        return 1;
    }

    HAL_StatusTypeDef status = PMU_Channel_SetValue(channel_id, value);

    if (status != HAL_OK) {
        PMU_LOG_WARN(LOG_SRC, "channel.set: Failed to set channel %u to %ld", channel_id, (long)value);
    }

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
        PMU_LOG_WARN(LOG_SRC, "channel.info: Invalid channel ID %u", channel_id);
        lua_pushnil(L);
        return 1;
    }

    /* Create info table using helper macros */
    lua_newtable(L);
    LUA_TABLE_SET_INT(L, "id", info->channel_id);
    LUA_TABLE_SET_STRING(L, "name", info->name);
    LUA_TABLE_SET_INT(L, "type", info->hw_class);
    LUA_TABLE_SET_INT(L, "value", info->value);
    LUA_TABLE_SET_INT(L, "min", info->min_value);
    LUA_TABLE_SET_INT(L, "max", info->max_value);
    LUA_TABLE_SET_STRING(L, "unit", info->unit);
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
        lua_pushinteger(L, -1);  /* Return -1 if channel not found */
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
        LUA_TABLE_SET_INT(L, "id", channels[i].channel_id);
        LUA_TABLE_SET_STRING(L, "name", channels[i].name);
        LUA_TABLE_SET_INT(L, "value", channels[i].value);

        lua_settable(L, -3);
    }

    return 1;
}

/* Logic API -----------------------------------------------------------------*/

/**
 * @brief Helper for creating math logic functions
 */
static int lua_logic_math_helper(lua_State* L, PMU_FunctionType_t func_type, const char* func_name)
{
    LUA_CHECK_ARGS(L, 3, func_name);

    uint16_t output_ch = LUA_GET_UINT16(L, 1);
    uint16_t input_a = LUA_GET_UINT16(L, 2);
    uint16_t input_b = LUA_GET_UINT16(L, 3);

    uint16_t func_id = PMU_LogicFunctions_CreateMath(func_type, output_ch, input_a, input_b);

    lua_pushinteger(L, func_id);
    return 1;
}

/**
 * @brief Create ADD logic function
 * Usage: func_id = logic.add(output_ch, input_a, input_b)
 */
int lua_logic_add(lua_State* L)
{
    return lua_logic_math_helper(L, PMU_FUNC_ADD, "logic.add");
}

/**
 * @brief Create SUBTRACT logic function
 */
int lua_logic_subtract(lua_State* L)
{
    return lua_logic_math_helper(L, PMU_FUNC_SUBTRACT, "logic.subtract");
}

/**
 * @brief Create MULTIPLY logic function
 */
int lua_logic_multiply(lua_State* L)
{
    return lua_logic_math_helper(L, PMU_FUNC_MULTIPLY, "logic.multiply");
}

/**
 * @brief Create DIVIDE logic function
 */
int lua_logic_divide(lua_State* L)
{
    return lua_logic_math_helper(L, PMU_FUNC_DIVIDE, "logic.divide");
}

/**
 * @brief Create comparison logic function
 * Usage: func_id = logic.compare(output_ch, input_a, input_b, ">")
 */
int lua_logic_compare(lua_State* L)
{
    LUA_CHECK_ARGS(L, 4, "logic.compare");

    if (!lua_isstring(L, 4)) {
        lua_pushstring(L, "logic.compare: operator must be a string");
        lua_error(L);
        return 0;
    }

    uint16_t output_ch = LUA_GET_UINT16(L, 1);
    uint16_t input_a = LUA_GET_UINT16(L, 2);
    uint16_t input_b = LUA_GET_UINT16(L, 3);
    const char* op = lua_tostring(L, 4);

    /* Operator lookup table */
    static const struct { const char* op; PMU_FunctionType_t type; } op_map[] = {
        {">",  PMU_FUNC_GREATER},
        {"<",  PMU_FUNC_LESS},
        {"==", PMU_FUNC_EQUAL},
        {"!=", PMU_FUNC_NOT_EQUAL},
        {">=", PMU_FUNC_GREATER_EQUAL},
        {"<=", PMU_FUNC_LESS_EQUAL},
    };

    PMU_FunctionType_t type = PMU_FUNC_GREATER;
    for (size_t i = 0; i < sizeof(op_map)/sizeof(op_map[0]); i++) {
        if (strcmp(op, op_map[i].op) == 0) {
            type = op_map[i].type;
            break;
        }
    }

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
    LUA_CHECK_ARGS(L, 6, "logic.pid");

    uint16_t output_ch = LUA_GET_UINT16(L, 1);
    uint16_t input_ch = LUA_GET_UINT16(L, 2);
    float setpoint = LUA_GET_FLOAT(L, 3);
    float kp = LUA_GET_FLOAT(L, 4);
    float ki = LUA_GET_FLOAT(L, 5);
    float kd = LUA_GET_FLOAT(L, 6);

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
    LUA_CHECK_ARGS(L, 4, "logic.hysteresis");

    uint16_t output_ch = LUA_GET_UINT16(L, 1);
    uint16_t input_ch = LUA_GET_UINT16(L, 2);
    int32_t threshold_on = LUA_GET_INT32(L, 3);
    int32_t threshold_off = LUA_GET_INT32(L, 4);

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
    LUA_CHECK_ARGS(L, 2, "logic.enable");

    uint16_t func_id = LUA_GET_UINT16(L, 1);
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

/* CAN API ===================================================================*/

/**
 * @brief Register CAN bus functions API
 */
void PMU_Lua_RegisterCanAPI(lua_State* L)
{
    static const PMU_Lua_LibFunc_t can_funcs[] = {
        {"send",       lua_can_send},
        {"get",        lua_can_get},
        {"set",        lua_can_set},
        {"on_receive", lua_can_on_receive},
        {"status",     lua_can_status},
    };
    REGISTER_LIB(L, "can", can_funcs);
}

/**
 * @brief Send CAN message
 * Usage: can.send(bus, id, {d0, d1, d2, d3, d4, d5, d6, d7})
 * @param bus CAN bus (1-4)
 * @param id CAN message ID
 * @param data Table with 1-8 data bytes
 * @return true on success
 */
int lua_can_send(lua_State* L)
{
    LUA_CHECK_ARGS(L, 3, "can.send");

    uint8_t bus = LUA_GET_UINT8(L, 1);
    uint32_t id = (uint32_t)lua_tointeger(L, 2);

    uint8_t data[8] = {0};
    uint8_t length = 0;

    if (lua_istable(L, 3)) {
        for (int i = 1; i <= 8; i++) {
            lua_rawgeti(L, 3, i);
            if (lua_isnil(L, -1)) {
                lua_pop(L, 1);
                break;
            }
            data[i-1] = (uint8_t)lua_tointeger(L, -1);
            lua_pop(L, 1);
            length++;
        }
    }

    /* Send CAN message */
    HAL_StatusTypeDef status = PMU_CAN_TransmitFrame(bus, id, data, length);

    lua_pushboolean(L, status == HAL_OK);
    return 1;
}

/**
 * @brief Get signal value from CAN message
 * Usage: value = can.get("msg_id", "signal_name")
 */
int lua_can_get(lua_State* L)
{
    if (!lua_isstring(L, 1)) {
        lua_pushstring(L, "can.get expects (msg_id_string, signal_name)");
        lua_error(L);
        return 0;
    }

    const char* msg_id = lua_tostring(L, 1);
    const char* signal = lua_isstring(L, 2) ? lua_tostring(L, 2) : NULL;

    /* Get message by ID and extract signal value */
    /* For now, return value from channel system */
    const PMU_Channel_t* ch = PMU_Channel_GetByName(msg_id);
    if (ch) {
        lua_pushnumber(L, (lua_Number)ch->value / 1000.0);
    } else {
        lua_pushnil(L);
    }

    return 1;
}

/**
 * @brief Set signal value for CAN TX message
 * Usage: can.set("msg_id", "signal_name", value)
 */
int lua_can_set(lua_State* L)
{
    if (!lua_isstring(L, 1) || !lua_isnumber(L, 3)) {
        lua_pushstring(L, "can.set expects (msg_id, signal_name, value)");
        lua_error(L);
        return 0;
    }

    const char* msg_id = lua_tostring(L, 1);
    lua_Number value = lua_tonumber(L, 3);

    /* Set value via channel system */
    uint16_t ch_idx = PMU_Channel_GetIndexByID(msg_id);
    if (ch_idx != 0xFFFF) {
        PMU_Channel_SetValue(ch_idx, (int32_t)(value * 1000.0));
        lua_pushboolean(L, 1);
    } else {
        lua_pushboolean(L, 0);
    }

    return 1;
}

/**
 * @brief Register callback for CAN message receive
 * Usage: can.on_receive(msg_id, callback_function)
 */
int lua_can_on_receive(lua_State* L)
{
    /* TODO: Implement CAN receive callbacks */
    lua_pushboolean(L, 0);
    return 1;
}

/**
 * @brief Get CAN bus status
 * Usage: status = can.status(bus)
 * Returns: {state, tx_count, rx_count, error_count, bus_off}
 */
int lua_can_status(lua_State* L)
{
    uint8_t bus = LUA_GET_UINT8(L, 1);

    lua_newtable(L);

    PMU_CAN_Stats_t stats;
    if (PMU_CAN_GetStats(bus, &stats) == HAL_OK) {
        LUA_TABLE_SET_INT(L, "state", stats.state);
        LUA_TABLE_SET_INT(L, "tx_count", stats.tx_count);
        LUA_TABLE_SET_INT(L, "rx_count", stats.rx_count);
        LUA_TABLE_SET_INT(L, "error_count", stats.error_count);
        LUA_TABLE_SET_BOOL(L, "bus_off", stats.bus_off);
    }

    return 1;
}

/* LIN API ===================================================================*/

/**
 * @brief Register LIN bus functions API
 */
void PMU_Lua_RegisterLinAPI(lua_State* L)
{
    static const PMU_Lua_LibFunc_t lin_funcs[] = {
        {"send",    lua_lin_send},
        {"get",     lua_lin_get},
        {"set",     lua_lin_set},
        {"request", lua_lin_request},
        {"wakeup",  lua_lin_wakeup},
        {"sleep",   lua_lin_sleep},
        {"status",  lua_lin_status},
    };
    REGISTER_LIB(L, "lin", lin_funcs);
}

/**
 * @brief Send LIN frame
 * Usage: lin.send(bus, frame_id, {d0, d1, d2, ...})
 */
int lua_lin_send(lua_State* L)
{
    LUA_CHECK_ARGS(L, 3, "lin.send");

    uint8_t bus = LUA_GET_UINT8(L, 1);
    uint8_t frame_id = LUA_GET_UINT8(L, 2) & 0x3F;

    uint8_t data[8] = {0};
    uint8_t length = 0;

    if (lua_istable(L, 3)) {
        for (int i = 1; i <= 8; i++) {
            lua_rawgeti(L, 3, i);
            if (lua_isnil(L, -1)) {
                lua_pop(L, 1);
                break;
            }
            data[i-1] = (uint8_t)lua_tointeger(L, -1);
            lua_pop(L, 1);
            length++;
        }
    }

    /* Send LIN frame */
    HAL_StatusTypeDef status = PMU_LIN_TransmitFrame(bus, frame_id, data, length);

    lua_pushboolean(L, status == HAL_OK);
    return 1;
}

/**
 * @brief Get signal value from LIN frame
 * Usage: value = lin.get("frame_id", "signal_name")
 */
int lua_lin_get(lua_State* L)
{
    if (!lua_isstring(L, 1)) {
        lua_pushstring(L, "lin.get expects (frame_id_string, signal_name)");
        lua_error(L);
        return 0;
    }

    const char* frame_id = lua_tostring(L, 1);

    /* Get input signal by frame reference */
    PMU_LIN_Input_t* input = PMU_LIN_GetInput(frame_id);
    if (input) {
        lua_pushnumber(L, (lua_Number)input->current_value);
    } else {
        lua_pushnil(L);
    }

    return 1;
}

/**
 * @brief Set signal value for LIN TX frame
 * Usage: lin.set("frame_id", "signal_name", value)
 */
int lua_lin_set(lua_State* L)
{
    if (!lua_isstring(L, 1) || !lua_isnumber(L, 3)) {
        lua_pushstring(L, "lin.set expects (frame_id, signal_name, value)");
        lua_error(L);
        return 0;
    }

    const char* frame_id = lua_tostring(L, 1);
    lua_Number value = lua_tonumber(L, 3);

    /* Get output signal and set value */
    PMU_LIN_Output_t* output = PMU_LIN_GetOutput(frame_id);
    if (output) {
        output->current_value = (float)value;
        lua_pushboolean(L, 1);
    } else {
        lua_pushboolean(L, 0);
    }

    return 1;
}

/**
 * @brief Request LIN frame (master mode)
 * Usage: lin.request(frame_id)
 */
int lua_lin_request(lua_State* L)
{
    uint8_t frame_id = LUA_GET_UINT8(L, 1) & 0x3F;

    HAL_StatusTypeDef status = PMU_LIN_RequestFrame(PMU_LIN_BUS_1, frame_id);

    lua_pushboolean(L, status == HAL_OK);
    return 1;
}

/**
 * @brief Send LIN wakeup signal
 * Usage: lin.wakeup(bus)
 */
int lua_lin_wakeup(lua_State* L)
{
    uint8_t bus = LUA_GET_UINT8(L, 1);

    HAL_StatusTypeDef status = PMU_LIN_SendWakeup(bus);

    lua_pushboolean(L, status == HAL_OK);
    return 1;
}

/**
 * @brief Put LIN bus to sleep
 * Usage: lin.sleep(bus)
 */
int lua_lin_sleep(lua_State* L)
{
    uint8_t bus = LUA_GET_UINT8(L, 1);

    HAL_StatusTypeDef status = PMU_LIN_GoToSleep(bus);

    lua_pushboolean(L, status == HAL_OK);
    return 1;
}

/**
 * @brief Get LIN bus status
 * Usage: status = lin.status(bus)
 * Returns: {state, is_master, tx_count, rx_count, error_count}
 */
int lua_lin_status(lua_State* L)
{
    uint8_t bus = LUA_GET_UINT8(L, 1);

    lua_newtable(L);

    PMU_LIN_Stats_t stats;
    if (PMU_LIN_GetStats(bus, &stats) == HAL_OK) {
        LUA_TABLE_SET_INT(L, "state", stats.state);
        LUA_TABLE_SET_BOOL(L, "is_master", stats.is_master);
        LUA_TABLE_SET_INT(L, "tx_count", stats.frames_tx);
        LUA_TABLE_SET_INT(L, "rx_count", stats.frames_rx);
        LUA_TABLE_SET_INT(L, "error_count", stats.errors);
    }

    return 1;
}

/* PID API ===================================================================*/

/**
 * @brief Register PID controller functions API
 */
void PMU_Lua_RegisterPidAPI(lua_State* L)
{
    static const PMU_Lua_LibFunc_t pid_funcs[] = {
        {"create",    lua_pid_create},
        {"setpoint",  lua_pid_setpoint},
        {"configure", lua_pid_configure},
        {"limits",    lua_pid_limits},
        {"compute",   lua_pid_compute},
        {"reset",     lua_pid_reset},
        {"get",       lua_pid_get},
        {"enable",    lua_pid_enable},
    };
    REGISTER_LIB(L, "pid", pid_funcs);
}

/**
 * @brief Create a new PID controller
 * Usage: id = pid.create("name", kp, ki, kd)
 */
int lua_pid_create(lua_State* L)
{
    LUA_CHECK_ARGS(L, 4, "pid.create");

    const char* name = lua_tostring(L, 1);
    float kp = LUA_GET_FLOAT(L, 2);
    float ki = LUA_GET_FLOAT(L, 3);
    float kd = LUA_GET_FLOAT(L, 4);

    PMU_PID_Config_t config = {
        .kp = kp,
        .ki = ki,
        .kd = kd,
        .output_min = -1000.0f,
        .output_max = 1000.0f,
        .sample_time_ms = 10,
        .enabled = true
    };
    strncpy(config.id, name, PMU_PID_ID_LEN - 1);

    int id = PMU_PID_Create(&config);

    if (id >= 0) {
        lua_pushinteger(L, id);
    } else {
        lua_pushnil(L);
    }

    return 1;
}

/**
 * @brief Set PID controller setpoint
 * Usage: pid.setpoint(id, value)
 */
int lua_pid_setpoint(lua_State* L)
{
    LUA_CHECK_ARGS(L, 2, "pid.setpoint");

    int id = LUA_GET_INT32(L, 1);
    float setpoint = LUA_GET_FLOAT(L, 2);

    HAL_StatusTypeDef status = PMU_PID_SetSetpoint(id, setpoint);

    lua_pushboolean(L, status == HAL_OK);
    return 1;
}

/**
 * @brief Configure PID controller gains
 * Usage: pid.configure(id, kp, ki, kd)
 */
int lua_pid_configure(lua_State* L)
{
    LUA_CHECK_ARGS(L, 4, "pid.configure");

    int id = LUA_GET_INT32(L, 1);
    float kp = LUA_GET_FLOAT(L, 2);
    float ki = LUA_GET_FLOAT(L, 3);
    float kd = LUA_GET_FLOAT(L, 4);

    HAL_StatusTypeDef status = PMU_PID_SetGains(id, kp, ki, kd);

    lua_pushboolean(L, status == HAL_OK);
    return 1;
}

/**
 * @brief Set PID controller output limits
 * Usage: pid.limits(id, min, max)
 */
int lua_pid_limits(lua_State* L)
{
    LUA_CHECK_ARGS(L, 3, "pid.limits");

    int id = LUA_GET_INT32(L, 1);
    float min_val = LUA_GET_FLOAT(L, 2);
    float max_val = LUA_GET_FLOAT(L, 3);

    HAL_StatusTypeDef status = PMU_PID_SetLimits(id, min_val, max_val);

    lua_pushboolean(L, status == HAL_OK);
    return 1;
}

/**
 * @brief Compute PID output for given input
 * Usage: output = pid.compute(id, input)
 */
int lua_pid_compute(lua_State* L)
{
    LUA_CHECK_ARGS(L, 2, "pid.compute");

    int id = LUA_GET_INT32(L, 1);
    float input = LUA_GET_FLOAT(L, 2);

    float output = PMU_PID_Compute(id, input);

    lua_pushnumber(L, (lua_Number)output);
    return 1;
}

/**
 * @brief Reset PID controller state
 * Usage: pid.reset(id)
 */
int lua_pid_reset(lua_State* L)
{
    int id = LUA_GET_INT32(L, 1);

    HAL_StatusTypeDef status = PMU_PID_Reset(id);

    lua_pushboolean(L, status == HAL_OK);
    return 1;
}

/**
 * @brief Get PID controller state
 * Usage: info = pid.get(id)
 * Returns: {output, error, integral, derivative, setpoint, enabled}
 */
int lua_pid_get(lua_State* L)
{
    int id = LUA_GET_INT32(L, 1);

    lua_newtable(L);

    PMU_PID_State_t state;
    if (PMU_PID_GetState(id, &state) == HAL_OK) {
        LUA_TABLE_SET_NUMBER(L, "output", state.output);
        LUA_TABLE_SET_NUMBER(L, "error", state.error);
        LUA_TABLE_SET_NUMBER(L, "integral", state.integral);
        LUA_TABLE_SET_NUMBER(L, "derivative", state.derivative);
        LUA_TABLE_SET_NUMBER(L, "setpoint", state.setpoint);
        LUA_TABLE_SET_BOOL(L, "enabled", state.enabled);
    }

    return 1;
}

/**
 * @brief Enable/disable PID controller
 * Usage: pid.enable(id, enabled)
 */
int lua_pid_enable(lua_State* L)
{
    LUA_CHECK_ARGS(L, 2, "pid.enable");

    int id = LUA_GET_INT32(L, 1);
    bool enabled = lua_toboolean(L, 2);

    HAL_StatusTypeDef status = PMU_PID_SetEnabled(id, enabled);

    lua_pushboolean(L, status == HAL_OK);
    return 1;
}

#else /* !USE_LUA */

/* Stub implementations when Lua is not available */
void PMU_Lua_RegisterAPI(lua_State* L) { (void)L; }
void PMU_Lua_RegisterChannelAPI(lua_State* L) { (void)L; }
void PMU_Lua_RegisterLogicAPI(lua_State* L) { (void)L; }
void PMU_Lua_RegisterSystemAPI(lua_State* L) { (void)L; }
void PMU_Lua_RegisterUtilAPI(lua_State* L) { (void)L; }
void PMU_Lua_RegisterCanAPI(lua_State* L) { (void)L; }
void PMU_Lua_RegisterLinAPI(lua_State* L) { (void)L; }
void PMU_Lua_RegisterPidAPI(lua_State* L) { (void)L; }

#endif /* USE_LUA */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
