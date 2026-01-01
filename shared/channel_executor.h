/**
 * @file channel_executor.h
 * @brief Channel Executor - Connects Channels to Logic Engine
 *
 * The executor is the bridge between the channel system and the Logic Engine.
 * It reads channel values, feeds them to pure functions, and writes results.
 *
 * Design:
 * - Channel Manager owns channel definitions and current values
 * - Executor processes channels using Logic Engine functions
 * - State for stateful functions (Timer, PID, etc.) is stored per-channel
 * - No hardware access - works with channel values only
 *
 * @version 1.0
 * @date January 2026
 */

#ifndef PMU_CHANNEL_EXECUTOR_H
#define PMU_CHANNEL_EXECUTOR_H

#include <stdint.h>
#include <stdbool.h>
#include "channel_types.h"
#include "channel_config.h"
#include "engine/engine.h"

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Constants
 *============================================================================*/

#define EXEC_MAX_CHANNELS       256     /**< Maximum channels to process */
#define EXEC_MAX_INPUTS         8       /**< Max inputs per channel */

/*============================================================================
 * Channel Runtime State
 *============================================================================*/

/**
 * Union of all possible channel states.
 * Only one is active based on channel type.
 */
typedef union {
    Timer_State_t       timer;
    Counter_State_t     counter;
    PID_State_t         pid;
    SMA_State_t         sma;
    EMA_State_t         ema;
    LPF_State_t         lpf;
    Median_State_t      median;
    RateLimiter_State_t rate_limiter;
    Debounce_State_t    debounce;
    FlipFlop_State_t    flipflop;
    Hysteresis_State_t  hysteresis;
    Window_State_t      window;
    MultiLevel_State_t  multilevel;
} ChannelState_t;

/**
 * Runtime channel data.
 */
typedef struct {
    uint16_t    id;             /**< Channel ID */
    uint8_t     type;           /**< ChannelType_t */
    uint8_t     flags;          /**< Runtime flags */
    int32_t     value;          /**< Current value */
    int32_t     prev_value;     /**< Previous value (for change detection) */
    void*       config;         /**< Pointer to type-specific config */
    ChannelState_t state;       /**< Runtime state for stateful channels */
} ChannelRuntime_t;

/*============================================================================
 * Value Provider Interface
 *============================================================================*/

/**
 * Function to get channel value by ID.
 * Provided by the channel manager.
 */
typedef int32_t (*Exec_GetValueFunc)(uint16_t channel_id, void* user_data);

/**
 * Function to set channel value by ID.
 * Provided by the channel manager.
 */
typedef void (*Exec_SetValueFunc)(uint16_t channel_id, int32_t value, void* user_data);

/*============================================================================
 * Executor Context
 *============================================================================*/

typedef struct {
    Exec_GetValueFunc   get_value;      /**< Get channel value function */
    Exec_SetValueFunc   set_value;      /**< Set channel value function */
    void*               user_data;      /**< User data for callbacks */
    uint32_t            now_ms;         /**< Current timestamp (ms) */
    uint32_t            last_ms;        /**< Last execution timestamp */
    uint32_t            dt_ms;          /**< Delta time since last execution */
} ExecContext_t;

/*============================================================================
 * Executor Functions
 *============================================================================*/

/**
 * Initialize executor context.
 *
 * @param ctx           Executor context
 * @param get_value     Function to get channel values
 * @param set_value     Function to set channel values
 * @param user_data     User data for callbacks
 */
void Exec_Init(
    ExecContext_t* ctx,
    Exec_GetValueFunc get_value,
    Exec_SetValueFunc set_value,
    void* user_data
);

/**
 * Execute a single channel.
 *
 * @param ctx           Executor context
 * @param runtime       Channel runtime data
 * @return New channel value
 */
int32_t Exec_ProcessChannel(
    ExecContext_t* ctx,
    ChannelRuntime_t* runtime
);

/**
 * Update executor timestamp and calculate delta.
 *
 * @param ctx           Executor context
 * @param now_ms        Current time in milliseconds
 */
void Exec_UpdateTime(ExecContext_t* ctx, uint32_t now_ms);

/*============================================================================
 * Type-Specific Execution Functions
 *============================================================================*/

/**
 * Execute logic channel.
 */
int32_t Exec_Logic(
    ExecContext_t* ctx,
    const CfgLogic_t* config
);

/**
 * Execute math channel.
 */
int32_t Exec_Math(
    ExecContext_t* ctx,
    const CfgMath_t* config
);

/**
 * Execute timer channel.
 */
int32_t Exec_Timer(
    ExecContext_t* ctx,
    Timer_State_t* state,
    const CfgTimer_t* config
);

/**
 * Execute PID channel.
 */
int32_t Exec_PID(
    ExecContext_t* ctx,
    PID_State_t* state,
    const CfgPid_t* config
);

/**
 * Execute filter channel.
 */
int32_t Exec_Filter(
    ExecContext_t* ctx,
    ChannelState_t* state,
    const CfgFilter_t* config
);

/**
 * Execute 2D table channel.
 */
int32_t Exec_Table2D(
    ExecContext_t* ctx,
    const CfgTable2D_t* config
);

/**
 * Execute switch channel.
 */
int32_t Exec_Switch(
    ExecContext_t* ctx,
    const CfgSwitch_t* config
);

/**
 * Execute counter channel.
 */
int32_t Exec_Counter(
    ExecContext_t* ctx,
    Counter_State_t* state,
    const CfgCounter_t* config
);

/**
 * Execute hysteresis channel.
 */
int32_t Exec_Hysteresis(
    ExecContext_t* ctx,
    Hysteresis_State_t* state,
    const CfgHysteresis_t* config
);

/*============================================================================
 * Channel Initialization
 *============================================================================*/

/**
 * Initialize channel runtime state.
 *
 * @param runtime       Channel runtime to initialize
 * @param type          Channel type
 */
void Exec_InitChannelState(ChannelRuntime_t* runtime, ChannelType_t type);

/**
 * Reset channel state to defaults.
 *
 * @param runtime       Channel runtime to reset
 */
void Exec_ResetChannelState(ChannelRuntime_t* runtime);

#ifdef __cplusplus
}
#endif

#endif /* PMU_CHANNEL_EXECUTOR_H */
