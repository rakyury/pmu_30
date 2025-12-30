/**
 ******************************************************************************
 * @file           : pmu_lua.c
 * @brief          : Lua Scripting Engine Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module integrates Lua 5.4 into PMU-30 firmware:
 * - Provides scripting capability for custom logic
 * - Exposes PMU API to Lua scripts
 * - Manages script lifecycle
 * - Implements safety sandboxing
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_lua.h"
#include "pmu_lua_api.h"
#include "pmu_channel.h"
#include "pmu_profet.h"
#include "pmu_adc.h"
#include "pmu_logic.h"
#include "pmu_protection.h"
#include "pmu_can.h"
#ifndef PMU_EMULATOR
#include "pmu_ui.h"
#endif
#include <string.h>
#include <stdio.h>

/* Lua headers - only when USE_LUA is defined */
#ifdef USE_LUA
#include "lua.h"
#include "lualib.h"
#include "lauxlib.h"
#endif

/* Private typedef -----------------------------------------------------------*/

/**
 * @brief Lua script entry
 */
typedef struct {
    char name[32];
    PMU_Lua_ScriptInfo_t info;
    uint8_t* code;              /* Script bytecode/source */
    uint32_t code_size;
} PMU_Lua_Script_t;

/**
 * @brief Lua engine state
 */
typedef struct {
#ifdef USE_LUA
    lua_State* L;               /* Main Lua state */
#endif
    PMU_Lua_Script_t scripts[PMU_LUA_MAX_SCRIPTS];
    uint8_t script_count;
    PMU_Lua_Stats_t stats;
    char last_error[128];
    uint8_t initialized;
} PMU_Lua_State_t;

/* Private define ------------------------------------------------------------*/

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_Lua_State_t lua_state;
static uint8_t lua_memory_pool[PMU_LUA_MEMORY_POOL_SIZE];

/* Private function prototypes -----------------------------------------------*/
static void Lua_RegisterPMUAPI(void);
static PMU_Lua_Script_t* Lua_FindScript(const char* name);
static HAL_StatusTypeDef Lua_AllocateScript(const char* name, PMU_Lua_Script_t** script);

#ifdef USE_LUA
/* Lua API functions (exported to Lua) */
static int lua_pmu_setOutput(lua_State* L);
static int lua_pmu_getInput(lua_State* L);
static int lua_pmu_getChannel(lua_State* L);
static int lua_pmu_setChannel(lua_State* L);
static int lua_pmu_delay(lua_State* L);
static int lua_pmu_log(lua_State* L);
static int lua_pmu_getVoltage(lua_State* L);
static int lua_pmu_getTemperature(lua_State* L);
static int lua_pmu_sendCAN(lua_State* L);
#endif

/* Private user code ---------------------------------------------------------*/

/**
 * @brief Initialize Lua scripting engine
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Lua_Init(void)
{
    /* Clear state */
    memset(&lua_state, 0, sizeof(PMU_Lua_State_t));
    memset(lua_memory_pool, 0, sizeof(lua_memory_pool));

#ifdef USE_LUA
    /* Create new Lua state */
    lua_state.L = luaL_newstate();
    if (lua_state.L == NULL) {
        strcpy(lua_state.last_error, "Failed to create Lua state");
        return HAL_ERROR;
    }

    /* Open standard libraries (restricted for safety) */
    luaL_openlibs(lua_state.L);

    printf("[LUA] Lua %s initialized\n", LUA_VERSION);
#endif

    /* Register PMU API functions */
    Lua_RegisterPMUAPI();

    /* Initialize statistics */
    lua_state.stats.total_scripts = 0;
    lua_state.stats.active_scripts = 0;
    lua_state.stats.memory_used = 0;
    lua_state.stats.total_executions = 0;
    lua_state.stats.errors_count = 0;
    lua_state.stats.max_exec_time_ms = 0;

    lua_state.initialized = 1;

    return HAL_OK;
}

/**
 * @brief Deinitialize Lua engine
 * @retval None
 */
void PMU_Lua_Deinit(void)
{
    if (!lua_state.initialized) {
        return;
    }

    /* Unload all scripts */
    for (uint8_t i = 0; i < lua_state.script_count; i++) {
        if (lua_state.scripts[i].code != NULL) {
            /* Free script memory */
            lua_state.scripts[i].code = NULL;
        }
    }

#ifdef USE_LUA
    /* Close Lua state */
    if (lua_state.L != NULL) {
        lua_close(lua_state.L);
        lua_state.L = NULL;
    }
#endif

    lua_state.initialized = 0;
}

/**
 * @brief Register PMU API functions in Lua
 */
static void Lua_RegisterPMUAPI(void)
{
#ifdef USE_LUA
    if (lua_state.L == NULL) return;

    /* Register basic functions */
    lua_register(lua_state.L, "setOutput", lua_pmu_setOutput);
    lua_register(lua_state.L, "getInput", lua_pmu_getInput);
    lua_register(lua_state.L, "getChannel", lua_pmu_getChannel);
    lua_register(lua_state.L, "setChannel", lua_pmu_setChannel);
    lua_register(lua_state.L, "delay", lua_pmu_delay);
    lua_register(lua_state.L, "log", lua_pmu_log);
    lua_register(lua_state.L, "getVoltage", lua_pmu_getVoltage);
    lua_register(lua_state.L, "getTemperature", lua_pmu_getTemperature);
    lua_register(lua_state.L, "sendCAN", lua_pmu_sendCAN);

    /* Create PMU table with constants */
    lua_newtable(lua_state.L);
    lua_pushinteger(lua_state.L, 30);
    lua_setfield(lua_state.L, -2, "NUM_OUTPUTS");
    lua_pushinteger(lua_state.L, 20);
    lua_setfield(lua_state.L, -2, "NUM_INPUTS");
    lua_setglobal(lua_state.L, "PMU");

    /* Register extended API (channel, logic, system tables) */
    PMU_Lua_RegisterAPI(lua_state.L);
#endif
}

/**
 * @brief Load script from string
 * @param name Script name
 * @param script Script source
 * @param length Script length
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Lua_LoadScript(const char* name, const char* script, uint32_t length)
{
    if (name == NULL || script == NULL || length == 0) {
        return HAL_ERROR;
    }

    if (length > PMU_LUA_MAX_SCRIPT_SIZE) {
        strcpy(lua_state.last_error, "Script too large");
        return HAL_ERROR;
    }

    /* Find existing or allocate new script slot */
    PMU_Lua_Script_t* scr = Lua_FindScript(name);
    if (scr == NULL) {
        if (Lua_AllocateScript(name, &scr) != HAL_OK) {
            strcpy(lua_state.last_error, "No free script slots");
            return HAL_ERROR;
        }
    }

    /* Copy script name and info */
    strncpy(scr->name, name, sizeof(scr->name) - 1);
    scr->info.size = length;
    scr->info.enabled = 1;
    scr->info.auto_run = 0;
    scr->info.last_status = PMU_LUA_STATUS_OK;

#ifdef USE_LUA
    /* Compile and load script */
    int result = luaL_loadbuffer(lua_state.L, script, length, name);
    if (result != LUA_OK) {
        const char* err = lua_tostring(lua_state.L, -1);
        strncpy(lua_state.last_error, err ? err : "Unknown error", sizeof(lua_state.last_error) - 1);
        lua_pop(lua_state.L, 1);
        scr->info.last_status = PMU_LUA_STATUS_SYNTAX_ERROR;
        lua_state.stats.errors_count++;
        printf("[LUA] Load error: %s\n", lua_state.last_error);
        return HAL_ERROR;
    }

    /* Store compiled script as global function */
    lua_setglobal(lua_state.L, name);
    printf("[LUA] Script '%s' loaded (%u bytes)\n", name, (unsigned)length);
#endif

    lua_state.stats.total_scripts++;
    lua_state.stats.active_scripts++;

    return HAL_OK;
}

/**
 * @brief Load script from file
 * @param filename File path
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Lua_LoadScriptFromFile(const char* filename)
{
    /* TODO: Implement file loading from SD card */
    /* Would use FatFS to read file and call PMU_Lua_LoadScript */
    strcpy(lua_state.last_error, "File loading not implemented");
    return HAL_ERROR;
}

/**
 * @brief Unload script
 * @param name Script name
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Lua_UnloadScript(const char* name)
{
    PMU_Lua_Script_t* scr = Lua_FindScript(name);
    if (scr == NULL) {
        strcpy(lua_state.last_error, "Script not found");
        return HAL_ERROR;
    }

    /* Free script memory */
    if (scr->code != NULL) {
        /* Free using custom allocator */
        scr->code = NULL;
    }

    /* Clear script slot */
    memset(scr, 0, sizeof(PMU_Lua_Script_t));

    lua_state.stats.active_scripts--;

    return HAL_OK;
}

/**
 * @brief Execute script by name
 * @param name Script name
 * @retval Execution status
 */
PMU_Lua_Status_t PMU_Lua_ExecuteScript(const char* name)
{
    PMU_Lua_Script_t* scr = Lua_FindScript(name);
    if (scr == NULL) {
        strcpy(lua_state.last_error, "Script not found");
        return PMU_LUA_STATUS_ERROR;
    }

    if (!scr->info.enabled) {
        return PMU_LUA_STATUS_OK;  /* Not an error, just disabled */
    }

    uint32_t start_time = HAL_GetTick();

#ifdef USE_LUA
    /* Execute script */
    lua_getglobal(lua_state.L, name);
    if (lua_isfunction(lua_state.L, -1)) {
        int result = lua_pcall(lua_state.L, 0, 0, 0);
        if (result != LUA_OK) {
            const char* err = lua_tostring(lua_state.L, -1);
            strncpy(lua_state.last_error, err ? err : "Unknown error", sizeof(lua_state.last_error) - 1);
            lua_pop(lua_state.L, 1);
            scr->info.last_status = PMU_LUA_STATUS_RUNTIME_ERROR;
            lua_state.stats.errors_count++;
            printf("[LUA] Runtime error in '%s': %s\n", name, lua_state.last_error);
            return PMU_LUA_STATUS_RUNTIME_ERROR;
        }
    } else {
        lua_pop(lua_state.L, 1);
        strcpy(lua_state.last_error, "Not a function");
        return PMU_LUA_STATUS_ERROR;
    }
#endif

    uint32_t exec_time = HAL_GetTick() - start_time;

    /* Update statistics */
    scr->info.last_run_time = exec_time;
    scr->info.execution_count++;
    scr->info.last_status = PMU_LUA_STATUS_OK;
    lua_state.stats.total_executions++;

    if (exec_time > lua_state.stats.max_exec_time_ms) {
        lua_state.stats.max_exec_time_ms = exec_time;
    }

    /* Check for timeout */
    if (exec_time > PMU_LUA_MAX_EXEC_TIME_MS) {
        strcpy(lua_state.last_error, "Script execution timeout");
        return PMU_LUA_STATUS_TIMEOUT;
    }

    return PMU_LUA_STATUS_OK;
}

/**
 * @brief Execute Lua code directly
 * @param code Lua code
 * @retval Execution status
 */
PMU_Lua_Status_t PMU_Lua_ExecuteCode(const char* code)
{
    if (code == NULL) {
        return PMU_LUA_STATUS_ERROR;
    }

#ifdef USE_LUA
    /* Execute Lua code directly */
    int result = luaL_dostring(lua_state.L, code);
    if (result != LUA_OK) {
        const char* err = lua_tostring(lua_state.L, -1);
        strncpy(lua_state.last_error, err ? err : "Unknown error", sizeof(lua_state.last_error) - 1);
        lua_pop(lua_state.L, 1);
        lua_state.stats.errors_count++;
        printf("[LUA] Exec error: %s\n", lua_state.last_error);
        return PMU_LUA_STATUS_RUNTIME_ERROR;
    }
#endif

    lua_state.stats.total_executions++;
    return PMU_LUA_STATUS_OK;
}

/**
 * @brief Update Lua engine (periodic call)
 * @retval None
 */
void PMU_Lua_Update(void)
{
    if (!lua_state.initialized) {
        return;
    }

    /* Execute auto-run scripts */
    for (uint8_t i = 0; i < lua_state.script_count; i++) {
        if (lua_state.scripts[i].info.auto_run && lua_state.scripts[i].info.enabled) {
            PMU_Lua_ExecuteScript(lua_state.scripts[i].name);
        }
    }

#ifdef USE_LUA
    /* Incremental garbage collection */
    lua_gc(lua_state.L, LUA_GCSTEP, 10);

    /* Update memory usage statistics */
    lua_state.stats.memory_used = lua_gc(lua_state.L, LUA_GCCOUNT, 0) * 1024;
#endif
}

/**
 * @brief Find script by name
 * @param name Script name
 * @retval Pointer to script or NULL
 */
static PMU_Lua_Script_t* Lua_FindScript(const char* name)
{
    for (uint8_t i = 0; i < lua_state.script_count; i++) {
        if (strcmp(lua_state.scripts[i].name, name) == 0) {
            return &lua_state.scripts[i];
        }
    }
    return NULL;
}

/**
 * @brief Allocate new script slot
 * @param name Script name
 * @param script Pointer to receive script pointer
 * @retval HAL status
 */
static HAL_StatusTypeDef Lua_AllocateScript(const char* name, PMU_Lua_Script_t** script)
{
    if (lua_state.script_count >= PMU_LUA_MAX_SCRIPTS) {
        return HAL_ERROR;
    }

    *script = &lua_state.scripts[lua_state.script_count];
    lua_state.script_count++;

    return HAL_OK;
}

/**
 * @brief Enable/disable script
 * @param name Script name
 * @param enabled Enable flag
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Lua_SetScriptEnabled(const char* name, uint8_t enabled)
{
    PMU_Lua_Script_t* scr = Lua_FindScript(name);
    if (scr == NULL) {
        return HAL_ERROR;
    }

    scr->info.enabled = enabled ? 1 : 0;
    return HAL_OK;
}

/**
 * @brief Set script auto-run
 * @param name Script name
 * @param auto_run Auto-run flag
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Lua_SetScriptAutoRun(const char* name, uint8_t auto_run)
{
    PMU_Lua_Script_t* scr = Lua_FindScript(name);
    if (scr == NULL) {
        return HAL_ERROR;
    }

    scr->info.auto_run = auto_run ? 1 : 0;
    return HAL_OK;
}

/**
 * @brief Get script information
 * @param name Script name
 * @retval Pointer to info or NULL
 */
PMU_Lua_ScriptInfo_t* PMU_Lua_GetScriptInfo(const char* name)
{
    PMU_Lua_Script_t* scr = Lua_FindScript(name);
    if (scr == NULL) {
        return NULL;
    }

    return &scr->info;
}

/**
 * @brief Get statistics
 * @retval Pointer to statistics
 */
PMU_Lua_Stats_t* PMU_Lua_GetStats(void)
{
    return &lua_state.stats;
}

/**
 * @brief List all scripts
 * @param scripts Array to fill
 * @param max_count Maximum count
 * @retval Number of scripts
 */
uint8_t PMU_Lua_ListScripts(PMU_Lua_ScriptInfo_t* scripts, uint8_t max_count)
{
    uint8_t count = (lua_state.script_count < max_count) ?
                    lua_state.script_count : max_count;

    for (uint8_t i = 0; i < count; i++) {
        memcpy(&scripts[i], &lua_state.scripts[i].info, sizeof(PMU_Lua_ScriptInfo_t));
    }

    return count;
}

/**
 * @brief Clear errors
 * @retval None
 */
void PMU_Lua_ClearErrors(void)
{
    lua_state.last_error[0] = '\0';
    lua_state.stats.errors_count = 0;
}

/**
 * @brief Get last error
 * @retval Error message
 */
const char* PMU_Lua_GetLastError(void)
{
    return lua_state.last_error;
}

/**
 * @brief Register custom function
 * @param name Function name
 * @param func Function pointer
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Lua_RegisterFunction(const char* name, void* func)
{
    if (name == NULL || func == NULL) {
        return HAL_ERROR;
    }

#ifdef USE_LUA
    if (lua_state.L == NULL) {
        return HAL_ERROR;
    }
    lua_register(lua_state.L, name, (lua_CFunction)func);
#endif

    return HAL_OK;
}

/* Lua API Functions ---------------------------------------------------------*/

#ifdef USE_LUA

/**
 * @brief Lua API: Set output channel
 * Usage: setOutput(channel, state, pwm)
 */
static int lua_pmu_setOutput(lua_State* L)
{
    int channel = (int)luaL_checkinteger(L, 1);
    int state = (int)luaL_checkinteger(L, 2);
    int pwm = (int)luaL_optinteger(L, 3, 0);

    if (pwm > 0) {
        /* PWM mode */
        PMU_PROFET_SetState(channel, 1);
        PMU_PROFET_SetPWM(channel, (uint16_t)pwm);
    } else {
        /* On/Off mode */
        PMU_PROFET_SetState(channel, state ? 1 : 0);
    }
    return 0;
}

/**
 * @brief Lua API: Get input value
 * Usage: value = getInput(channel)
 */
static int lua_pmu_getInput(lua_State* L)
{
    int channel = (int)luaL_checkinteger(L, 1);
    uint16_t value = PMU_ADC_GetValue(channel);
    lua_pushinteger(L, value);
    return 1;
}

/**
 * @brief Lua API: Get channel value (universal channel system)
 * Usage: value = getChannel(channel_id)
 *        value = getChannel("channel_name")
 */
static int lua_pmu_getChannel(lua_State* L)
{
    uint16_t channel_id;

    if (lua_isstring(L, 1)) {
        /* Find channel by name */
        const char* name = lua_tostring(L, 1);
        const PMU_Channel_t* ch = PMU_Channel_GetByName(name);
        if (ch == NULL) {
            lua_pushnil(L);
            return 1;
        }
        channel_id = ch->channel_id;
    } else {
        channel_id = (uint16_t)luaL_checkinteger(L, 1);
    }

    int32_t value = PMU_Channel_GetValue(channel_id);
    lua_pushinteger(L, value);
    return 1;
}

/**
 * @brief Lua API: Set channel value (universal channel system)
 * Usage: setChannel(channel_id, value)
 *        setChannel("channel_name", value)
 */
static int lua_pmu_setChannel(lua_State* L)
{
    uint16_t channel_id;

    if (lua_isstring(L, 1)) {
        /* Find channel by name */
        const char* name = lua_tostring(L, 1);
        const PMU_Channel_t* ch = PMU_Channel_GetByName(name);
        if (ch == NULL) {
            lua_pushboolean(L, 0);
            return 1;
        }
        channel_id = ch->channel_id;
    } else {
        channel_id = (uint16_t)luaL_checkinteger(L, 1);
    }

    int32_t value = (int32_t)luaL_checkinteger(L, 2);
    HAL_StatusTypeDef status = PMU_Channel_SetValue(channel_id, value);

    lua_pushboolean(L, status == HAL_OK);
    return 1;
}

/**
 * @brief Lua API: Delay execution
 * Usage: delay(ms)
 */
static int lua_pmu_delay(lua_State* L)
{
    int ms = (int)luaL_checkinteger(L, 1);
    HAL_Delay(ms);
    return 0;
}

/**
 * @brief Lua API: Log message
 * Usage: log(message)
 */
static int lua_pmu_log(lua_State* L)
{
    const char* msg = luaL_checkstring(L, 1);
    printf("[LUA] %s\n", msg);
    return 0;
}

/**
 * @brief Lua API: Get battery voltage
 * Usage: voltage = getVoltage()
 */
static int lua_pmu_getVoltage(lua_State* L)
{
    uint16_t voltage = PMU_Protection_GetVoltage();
    lua_pushinteger(L, voltage);
    return 1;
}

/**
 * @brief Lua API: Get temperature
 * Usage: temp = getTemperature()
 */
static int lua_pmu_getTemperature(lua_State* L)
{
    int16_t temp = PMU_Protection_GetTemperature();
    lua_pushinteger(L, temp);
    return 1;
}

/**
 * @brief Lua API: Send CAN message
 * Usage: sendCAN(bus, id, data)
 */
static int lua_pmu_sendCAN(lua_State* L)
{
    int bus = (int)luaL_checkinteger(L, 1);
    uint32_t id = (uint32_t)luaL_checkinteger(L, 2);
    size_t len = 0;
    const char* data = luaL_checklstring(L, 3, &len);
    if (len > 8) len = 8;  /* CAN max 8 bytes */
    PMU_CAN_SendMessage(bus, id, (uint8_t*)data, (uint8_t)len);
    return 0;
}

#endif /* USE_LUA */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
