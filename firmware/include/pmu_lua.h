/**
 ******************************************************************************
 * @file           : pmu_lua.h
 * @brief          : Lua Scripting Engine Header
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module provides Lua scripting support for PMU-30:
 * - Custom logic functions in Lua
 * - Access to all PMU functions from scripts
 * - Script loading from flash/SD card
 * - Real-time script execution
 * - Sandboxing for safety
 *
 ******************************************************************************
 */

#ifndef __PMU_LUA_H
#define __PMU_LUA_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Lua script execution status
 */
typedef enum {
    PMU_LUA_STATUS_OK = 0,
    PMU_LUA_STATUS_ERROR,
    PMU_LUA_STATUS_SYNTAX_ERROR,
    PMU_LUA_STATUS_RUNTIME_ERROR,
    PMU_LUA_STATUS_MEMORY_ERROR,
    PMU_LUA_STATUS_TIMEOUT
} PMU_Lua_Status_t;

/**
 * @brief Lua script information
 */
typedef struct {
    char name[32];              /* Script name */
    uint32_t size;              /* Script size in bytes */
    uint8_t enabled;            /* Enabled flag */
    uint8_t auto_run;           /* Auto-run on startup */
    uint32_t last_run_time;     /* Last execution time (ms) */
    uint32_t execution_count;   /* Number of times executed */
    PMU_Lua_Status_t last_status; /* Last execution status */
} PMU_Lua_ScriptInfo_t;

/**
 * @brief Lua execution statistics
 */
typedef struct {
    uint32_t total_scripts;     /* Total scripts loaded */
    uint32_t active_scripts;    /* Currently active scripts */
    uint32_t memory_used;       /* Lua memory usage (bytes) */
    uint32_t total_executions;  /* Total script executions */
    uint32_t errors_count;      /* Total errors */
    uint32_t max_exec_time_ms;  /* Maximum execution time */
} PMU_Lua_Stats_t;

/* Exported constants --------------------------------------------------------*/

/* Maximum number of scripts */
#define PMU_LUA_MAX_SCRIPTS         8

/* Maximum script size (32KB) */
#define PMU_LUA_MAX_SCRIPT_SIZE     (32 * 1024)

/* Maximum execution time per cycle (ms) */
#define PMU_LUA_MAX_EXEC_TIME_MS    10

/* Lua memory pool size (128KB) */
#define PMU_LUA_MEMORY_POOL_SIZE    (128 * 1024)

/* Exported macro ------------------------------------------------------------*/

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize Lua scripting engine
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Lua_Init(void);

/**
 * @brief Deinitialize Lua engine
 * @retval None
 */
void PMU_Lua_Deinit(void);

/**
 * @brief Load script from string
 * @param name Script name
 * @param script Script source code
 * @param length Script length
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Lua_LoadScript(const char* name, const char* script, uint32_t length);

/**
 * @brief Load script from file
 * @param filename File path
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Lua_LoadScriptFromFile(const char* filename);

/**
 * @brief Unload script
 * @param name Script name
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Lua_UnloadScript(const char* name);

/**
 * @brief Execute script by name
 * @param name Script name
 * @retval Execution status
 */
PMU_Lua_Status_t PMU_Lua_ExecuteScript(const char* name);

/**
 * @brief Execute Lua code directly
 * @param code Lua code string
 * @retval Execution status
 */
PMU_Lua_Status_t PMU_Lua_ExecuteCode(const char* code);

/**
 * @brief Update Lua engine (call periodically)
 * @retval None
 */
void PMU_Lua_Update(void);

/**
 * @brief Enable/disable script
 * @param name Script name
 * @param enabled Enable flag
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Lua_SetScriptEnabled(const char* name, uint8_t enabled);

/**
 * @brief Set script auto-run flag
 * @param name Script name
 * @param auto_run Auto-run flag
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Lua_SetScriptAutoRun(const char* name, uint8_t auto_run);

/**
 * @brief Get script information
 * @param name Script name
 * @retval Pointer to script info or NULL
 */
PMU_Lua_ScriptInfo_t* PMU_Lua_GetScriptInfo(const char* name);

/**
 * @brief Get Lua statistics
 * @retval Pointer to statistics
 */
PMU_Lua_Stats_t* PMU_Lua_GetStats(void);

/**
 * @brief List all loaded scripts
 * @param scripts Array to fill
 * @param max_count Maximum scripts
 * @retval Number of scripts
 */
uint8_t PMU_Lua_ListScripts(PMU_Lua_ScriptInfo_t* scripts, uint8_t max_count);

/**
 * @brief Clear Lua error state
 * @retval None
 */
void PMU_Lua_ClearErrors(void);

/**
 * @brief Get last error message
 * @retval Error message string
 */
const char* PMU_Lua_GetLastError(void);

/**
 * @brief Register custom Lua function
 * @param name Function name in Lua
 * @param func C function pointer
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Lua_RegisterFunction(const char* name, void* func);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_LUA_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
