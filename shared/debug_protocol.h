/**
 * @file debug_protocol.h
 * @brief PMU-30 Debug Protocol Definitions
 *
 * Defines debug message types and structures for real-time debugging.
 * Debug messages are sent asynchronously from the device to the configurator.
 *
 * @version 1.0
 * @date January 2026
 */

#ifndef PMU_DEBUG_PROTOCOL_H
#define PMU_DEBUG_PROTOCOL_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Debug Message Types
 *============================================================================*/

typedef enum {
    /* Text messages */
    DEBUG_MSG_LOG          = 0x01,   /**< Log message (text) */
    DEBUG_MSG_ERROR        = 0x02,   /**< Error message */
    DEBUG_MSG_WARNING      = 0x03,   /**< Warning message */
    DEBUG_MSG_INFO         = 0x04,   /**< Info message */
    DEBUG_MSG_TRACE        = 0x05,   /**< Trace message (verbose) */

    /* Variable monitoring */
    DEBUG_MSG_VAR_INT      = 0x10,   /**< Integer variable value */
    DEBUG_MSG_VAR_FLOAT    = 0x11,   /**< Float variable value */
    DEBUG_MSG_VAR_STRING   = 0x12,   /**< String variable value */
    DEBUG_MSG_VAR_ARRAY    = 0x13,   /**< Array of values */

    /* Channel debug */
    DEBUG_MSG_CH_STATE     = 0x20,   /**< Channel state change */
    DEBUG_MSG_CH_VALUE     = 0x21,   /**< Channel value update */
    DEBUG_MSG_CH_FAULT     = 0x22,   /**< Channel fault */
    DEBUG_MSG_CH_TRACE     = 0x23,   /**< Channel execution trace */

    /* Logic debug */
    DEBUG_MSG_LOGIC_EVAL   = 0x30,   /**< Logic evaluation result */
    DEBUG_MSG_LOGIC_INPUT  = 0x31,   /**< Logic input values */
    DEBUG_MSG_LOGIC_GATE   = 0x32,   /**< Logic gate result */

    /* Timer debug */
    DEBUG_MSG_TIMER_STATE  = 0x40,   /**< Timer state change */
    DEBUG_MSG_TIMER_TICK   = 0x41,   /**< Timer tick event */
    DEBUG_MSG_TIMER_EXPIRE = 0x42,   /**< Timer expired */

    /* Protocol debug */
    DEBUG_MSG_PROTO_RX     = 0x50,   /**< Protocol frame received */
    DEBUG_MSG_PROTO_TX     = 0x51,   /**< Protocol frame sent */
    DEBUG_MSG_PROTO_ERR    = 0x52,   /**< Protocol error */

    /* Performance */
    DEBUG_MSG_PERF_CPU     = 0x60,   /**< CPU usage */
    DEBUG_MSG_PERF_MEM     = 0x61,   /**< Memory usage */
    DEBUG_MSG_PERF_LOOP    = 0x62,   /**< Main loop timing */
    DEBUG_MSG_PERF_ISR     = 0x63,   /**< ISR timing */

    /* System events */
    DEBUG_MSG_SYS_BOOT     = 0x70,   /**< System boot */
    DEBUG_MSG_SYS_RESET    = 0x71,   /**< System reset */
    DEBUG_MSG_SYS_FAULT    = 0x72,   /**< System fault */
    DEBUG_MSG_SYS_CONFIG   = 0x73,   /**< Config change */

    /* CAN debug */
    DEBUG_MSG_CAN_RX       = 0x80,   /**< CAN frame received */
    DEBUG_MSG_CAN_TX       = 0x81,   /**< CAN frame sent */
    DEBUG_MSG_CAN_ERR      = 0x82,   /**< CAN error */

    /* Custom/Lua debug */
    DEBUG_MSG_LUA_PRINT    = 0x90,   /**< Lua print() output */
    DEBUG_MSG_LUA_ERROR    = 0x91,   /**< Lua error */
    DEBUG_MSG_LUA_TRACE    = 0x92,   /**< Lua execution trace */

} DebugMsgType_t;

/*============================================================================
 * Debug Log Level
 *============================================================================*/

typedef enum {
    DEBUG_LEVEL_NONE     = 0,   /**< No debug output */
    DEBUG_LEVEL_ERROR    = 1,   /**< Errors only */
    DEBUG_LEVEL_WARNING  = 2,   /**< Errors + warnings */
    DEBUG_LEVEL_INFO     = 3,   /**< Errors + warnings + info */
    DEBUG_LEVEL_DEBUG    = 4,   /**< All messages */
    DEBUG_LEVEL_TRACE    = 5,   /**< Maximum verbosity */
} DebugLevel_t;

/*============================================================================
 * Debug Message Header
 *============================================================================*/

typedef struct __attribute__((packed)) {
    uint8_t  type;          /**< Message type (DebugMsgType_t) */
    uint8_t  flags;         /**< Flags (reserved) */
    uint16_t seq;           /**< Sequence number */
    uint32_t timestamp_us;  /**< Microsecond timestamp */
} DebugMsgHeader_t;

/*============================================================================
 * Debug Message Payloads
 *============================================================================*/

/** Text log message (variable length) */
typedef struct __attribute__((packed)) {
    DebugMsgHeader_t header;
    uint8_t  level;         /**< Log level */
    uint8_t  module_id;     /**< Module/subsystem ID */
    uint16_t line;          /**< Source line number */
    char     text[];        /**< Null-terminated text (variable) */
} DebugMsgLog_t;

/** Variable value (integer) */
typedef struct __attribute__((packed)) {
    DebugMsgHeader_t header;
    uint16_t var_id;        /**< Variable ID */
    uint16_t reserved;
    int32_t  value;         /**< Value */
} DebugMsgVarInt_t;

/** Variable value (float) */
typedef struct __attribute__((packed)) {
    DebugMsgHeader_t header;
    uint16_t var_id;        /**< Variable ID */
    uint16_t reserved;
    float    value;         /**< Value */
} DebugMsgVarFloat_t;

/** Channel state change */
typedef struct __attribute__((packed)) {
    DebugMsgHeader_t header;
    uint16_t channel_id;    /**< Channel ID */
    uint8_t  old_state;     /**< Previous state */
    uint8_t  new_state;     /**< New state */
    int32_t  value;         /**< Current value */
} DebugMsgChState_t;

/** Channel value update */
typedef struct __attribute__((packed)) {
    DebugMsgHeader_t header;
    uint16_t channel_id;    /**< Channel ID */
    uint16_t source_id;     /**< Source channel (if computed) */
    int32_t  old_value;     /**< Previous value */
    int32_t  new_value;     /**< New value */
} DebugMsgChValue_t;

/** Logic evaluation */
typedef struct __attribute__((packed)) {
    DebugMsgHeader_t header;
    uint16_t channel_id;    /**< Logic channel ID */
    uint8_t  op;            /**< Operation (AND/OR/XOR/etc.) */
    uint8_t  input_count;   /**< Number of inputs */
    uint8_t  inputs[8];     /**< Input values (bitmask per byte) */
    uint8_t  result;        /**< Result (0 or 1) */
    uint8_t  reserved[3];
} DebugMsgLogicEval_t;

/** Timer state */
typedef struct __attribute__((packed)) {
    DebugMsgHeader_t header;
    uint16_t channel_id;    /**< Timer channel ID */
    uint8_t  state;         /**< Timer state (idle/running/expired) */
    uint8_t  trigger;       /**< What triggered state change */
    uint32_t elapsed_ms;    /**< Elapsed time (ms) */
    uint32_t target_ms;     /**< Target time (ms) */
} DebugMsgTimerState_t;

/** Performance data */
typedef struct __attribute__((packed)) {
    DebugMsgHeader_t header;
    uint16_t cpu_percent;   /**< CPU usage (0.01% units) */
    uint16_t loop_time_us;  /**< Main loop time (us) */
    uint32_t free_heap;     /**< Free heap bytes */
    uint32_t min_stack;     /**< Minimum stack free */
} DebugMsgPerf_t;

/** CAN frame debug */
typedef struct __attribute__((packed)) {
    DebugMsgHeader_t header;
    uint8_t  bus;           /**< CAN bus number */
    uint8_t  flags;         /**< IDE, RTR, etc. */
    uint16_t reserved;
    uint32_t id;            /**< CAN ID */
    uint8_t  dlc;           /**< Data length */
    uint8_t  data[8];       /**< Data bytes */
} DebugMsgCan_t;

/*============================================================================
 * Debug Configuration Commands
 *============================================================================*/

/** Debug configuration (sent to device) */
typedef struct __attribute__((packed)) {
    uint8_t  level;         /**< Global debug level */
    uint8_t  channel_mask;  /**< Which debug channels to enable (bitmask) */
    uint16_t rate_limit_ms; /**< Minimum interval between messages */
    uint32_t module_mask;   /**< Which modules to debug (bitmask) */
} DebugConfig_t;

/*============================================================================
 * Debug Module IDs
 *============================================================================*/

typedef enum {
    DEBUG_MOD_SYSTEM    = 0,
    DEBUG_MOD_CHANNEL   = 1,
    DEBUG_MOD_LOGIC     = 2,
    DEBUG_MOD_TIMER     = 3,
    DEBUG_MOD_PROTOCOL  = 4,
    DEBUG_MOD_CAN       = 5,
    DEBUG_MOD_ADC       = 6,
    DEBUG_MOD_PROFET    = 7,
    DEBUG_MOD_HBRIDGE   = 8,
    DEBUG_MOD_LUA       = 9,
    DEBUG_MOD_CONFIG    = 10,
    DEBUG_MOD_TELEMETRY = 11,
    DEBUG_MOD_MAX       = 32
} DebugModule_t;

/*============================================================================
 * Constants
 *============================================================================*/

#define DEBUG_MAX_TEXT_LEN      128
#define DEBUG_MAX_VARS          64
#define DEBUG_BUFFER_SIZE       512

/*============================================================================
 * API Functions (for firmware)
 *============================================================================*/

#ifdef PMU_PLATFORM_EMBEDDED

/**
 * Initialize debug subsystem.
 */
void Debug_Init(void);

/**
 * Set debug configuration.
 */
void Debug_SetConfig(const DebugConfig_t* config);

/**
 * Log a text message.
 */
void Debug_Log(DebugLevel_t level, DebugModule_t module,
               uint16_t line, const char* fmt, ...);

/**
 * Log a variable value (integer).
 */
void Debug_VarInt(uint16_t var_id, int32_t value);

/**
 * Log a variable value (float).
 */
void Debug_VarFloat(uint16_t var_id, float value);

/**
 * Log channel state change.
 */
void Debug_ChannelState(uint16_t channel_id,
                        uint8_t old_state, uint8_t new_state,
                        int32_t value);

/**
 * Log logic evaluation.
 */
void Debug_LogicEval(uint16_t channel_id, uint8_t op,
                     const uint8_t* inputs, uint8_t count,
                     uint8_t result);

/**
 * Log timer state.
 */
void Debug_TimerState(uint16_t channel_id, uint8_t state,
                      uint32_t elapsed_ms, uint32_t target_ms);

/**
 * Log CAN frame.
 */
void Debug_CanFrame(uint8_t bus, bool is_rx,
                    uint32_t id, const uint8_t* data, uint8_t dlc);

/**
 * Convenience macros for logging.
 */
#define DBG_ERROR(mod, ...)   Debug_Log(DEBUG_LEVEL_ERROR, mod, __LINE__, __VA_ARGS__)
#define DBG_WARN(mod, ...)    Debug_Log(DEBUG_LEVEL_WARNING, mod, __LINE__, __VA_ARGS__)
#define DBG_INFO(mod, ...)    Debug_Log(DEBUG_LEVEL_INFO, mod, __LINE__, __VA_ARGS__)
#define DBG_DEBUG(mod, ...)   Debug_Log(DEBUG_LEVEL_DEBUG, mod, __LINE__, __VA_ARGS__)
#define DBG_TRACE(mod, ...)   Debug_Log(DEBUG_LEVEL_TRACE, mod, __LINE__, __VA_ARGS__)

#endif /* PMU_PLATFORM_EMBEDDED */

#ifdef __cplusplus
}
#endif

#endif /* PMU_DEBUG_PROTOCOL_H */
