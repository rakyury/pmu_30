/**
 ******************************************************************************
 * @file           : pmu_lua_api.h
 * @brief          : Extended Lua API for PMU-30
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * This file defines the extended Lua API that provides access to:
 * - Universal channel abstraction
 * - Logic functions
 * - System functions
 * - Peripheral access
 *
 * Available Lua functions:
 *
 * -- Channel Access
 * value = channel.get(channel_id)
 * channel.set(channel_id, value)
 * info = channel.info(channel_id)
 * ch_id = channel.find("Channel_Name")
 *
 * -- Logic Functions
 * func_id = logic.add(output_ch, input_a, input_b)
 * func_id = logic.pid(output_ch, input_ch, setpoint, kp, ki, kd)
 * func_id = logic.hysteresis(output_ch, input_ch, on_threshold, off_threshold)
 * logic.enable(func_id, true/false)
 *
 * -- System Functions
 * voltage = system.voltage()
 * current = system.current()
 * temp = system.temperature()
 * uptime = system.uptime()
 *
 * -- Utilities
 * print(message)  -- Log to debug output
 * sleep(ms)       -- Delay
 * time = millis() -- Get tick count
 *
 ******************************************************************************
 */

#ifndef PMU_LUA_API_H
#define PMU_LUA_API_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32h7xx_hal.h"

/* Optional Lua support - only include if Lua library is available */
#ifdef USE_LUA
#include "lua.h"
#include "lualib.h"
#include "lauxlib.h"
#else
/* Forward declaration for Lua state when Lua is not available */
typedef struct lua_State lua_State;
#endif

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Lua callback function type
 */
typedef int (*PMU_Lua_CallbackFunc_t)(lua_State* L);

/**
 * @brief Lua library function registration
 */
typedef struct {
    const char* name;
    PMU_Lua_CallbackFunc_t func;
} PMU_Lua_Reg_t;

/* Exported constants --------------------------------------------------------*/

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Register PMU API functions into Lua state
 * @param L Lua state
 * @retval None
 */
void PMU_Lua_RegisterAPI(lua_State* L);

/**
 * @brief Register channel access functions
 * @param L Lua state
 * @retval None
 */
void PMU_Lua_RegisterChannelAPI(lua_State* L);

/**
 * @brief Register logic function API
 * @param L Lua state
 * @retval None
 */
void PMU_Lua_RegisterLogicAPI(lua_State* L);

/**
 * @brief Register system functions API
 * @param L Lua state
 * @retval None
 */
void PMU_Lua_RegisterSystemAPI(lua_State* L);

/**
 * @brief Register utility functions
 * @param L Lua state
 * @retval None
 */
void PMU_Lua_RegisterUtilAPI(lua_State* L);

/* Lua API Functions (C implementations) -------------------------------------*/

/* Channel API */
int lua_channel_get(lua_State* L);          /* channel.get(id) */
int lua_channel_set(lua_State* L);          /* channel.set(id, value) */
int lua_channel_info(lua_State* L);         /* channel.info(id) */
int lua_channel_find(lua_State* L);         /* channel.find("name") */
int lua_channel_list(lua_State* L);         /* channel.list() */

/* Logic API */
int lua_logic_add(lua_State* L);            /* logic.add(out, a, b) */
int lua_logic_subtract(lua_State* L);       /* logic.subtract(out, a, b) */
int lua_logic_multiply(lua_State* L);       /* logic.multiply(out, a, b) */
int lua_logic_divide(lua_State* L);         /* logic.divide(out, a, b) */
int lua_logic_compare(lua_State* L);        /* logic.compare(out, a, b, ">") */
int lua_logic_and(lua_State* L);            /* logic.and(out, ...) */
int lua_logic_or(lua_State* L);             /* logic.or(out, ...) */
int lua_logic_not(lua_State* L);            /* logic.not(out, in) */
int lua_logic_pid(lua_State* L);            /* logic.pid(out, in, sp, kp, ki, kd) */
int lua_logic_hysteresis(lua_State* L);     /* logic.hysteresis(out, in, on, off) */
int lua_logic_enable(lua_State* L);         /* logic.enable(func_id, enabled) */

/* System API */
int lua_system_voltage(lua_State* L);       /* system.voltage() */
int lua_system_current(lua_State* L);       /* system.current() */
int lua_system_temperature(lua_State* L);   /* system.temperature() */
int lua_system_uptime(lua_State* L);        /* system.uptime() */

/* Utility API */
int lua_util_print(lua_State* L);           /* print(msg) */
int lua_util_millis(lua_State* L);          /* millis() */
int lua_util_sleep(lua_State* L);           /* sleep(ms) */

#ifdef __cplusplus
}
#endif

#endif /* PMU_LUA_API_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
