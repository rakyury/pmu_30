/**
 ******************************************************************************
 * @file           : pmu_handler.h
 * @brief          : Event Handler System Header
 * @author         : R2 m-sport
 * @date           : 2025-12-25
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module implements event handlers for the PMU-30.
 * Handlers react to system events and execute configurable actions:
 * - Write to virtual channels
 * - Send CAN/LIN messages
 * - Run Lua functions
 * - Set output states directly
 *
 ******************************************************************************
 */

#ifndef PMU_HANDLER_H
#define PMU_HANDLER_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "pmu_hal.h"
#include <stdint.h>
#include <stdbool.h>

/* Exported constants --------------------------------------------------------*/

#define PMU_HANDLER_MAX_HANDLERS      32   /**< Maximum number of event handlers */
#define PMU_HANDLER_EVENT_QUEUE_SIZE  16   /**< Event queue size */
#define PMU_HANDLER_ID_MAX_LEN        32   /**< Maximum handler ID length */
#define PMU_HANDLER_CHANNEL_MAX_LEN   32   /**< Maximum channel name length */
#define PMU_HANDLER_LUA_FUNC_MAX_LEN  32   /**< Maximum Lua function name length */

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Event types that can trigger handlers
 */
typedef enum {
    PMU_EVENT_NONE = 0,
    /* Channel state events */
    PMU_EVENT_CHANNEL_ON,           /**< Channel turned ON (rising edge) */
    PMU_EVENT_CHANNEL_OFF,          /**< Channel turned OFF (falling edge) */
    /* Fault events */
    PMU_EVENT_CHANNEL_FAULT,        /**< Channel entered fault state */
    PMU_EVENT_CHANNEL_CLEARED,      /**< Channel fault cleared */
    /* Threshold events (for analog inputs) */
    PMU_EVENT_THRESHOLD_HIGH,       /**< Input crossed threshold (rising) */
    PMU_EVENT_THRESHOLD_LOW,        /**< Input crossed threshold (falling) */
    /* System events */
    PMU_EVENT_SYSTEM_UNDERVOLT,     /**< System undervoltage */
    PMU_EVENT_SYSTEM_OVERVOLT,      /**< System overvoltage */
    PMU_EVENT_SYSTEM_OVERTEMP,      /**< System overtemperature */
    PMU_EVENT_MAX
} PMU_EventType_t;

/**
 * @brief Action types that handlers can execute
 */
typedef enum {
    PMU_ACTION_NONE = 0,
    PMU_ACTION_WRITE_CHANNEL,       /**< Write value to virtual channel */
    PMU_ACTION_SEND_CAN,            /**< Send CAN message */
    PMU_ACTION_SEND_LIN,            /**< Send LIN message */
    PMU_ACTION_RUN_LUA,             /**< Call Lua function */
    PMU_ACTION_SET_OUTPUT,          /**< Set output state directly */
    PMU_ACTION_MAX
} PMU_ActionType_t;

/**
 * @brief CAN/LIN message data for handler actions
 */
typedef struct {
    uint8_t bus;                    /**< CAN/LIN bus number (1-4) */
    uint32_t message_id;            /**< Message ID */
    uint8_t data[8];                /**< Message data (8 bytes) */
    uint8_t dlc;                    /**< Data length code */
} PMU_HandlerMessage_t;

/**
 * @brief Handler configuration structure
 */
typedef struct {
    char id[PMU_HANDLER_ID_MAX_LEN];                    /**< Handler ID */
    bool enabled;                                        /**< Handler enabled */

    /* Event configuration */
    PMU_EventType_t event;                               /**< Event type */
    char source_channel[PMU_HANDLER_CHANNEL_MAX_LEN];   /**< Source channel name */
    float threshold_value;                               /**< Threshold for THRESHOLD events */

    /* Condition (optional) */
    char condition_channel[PMU_HANDLER_CHANNEL_MAX_LEN]; /**< Condition channel (must be true) */

    /* Action configuration */
    PMU_ActionType_t action;                             /**< Action type */
    char target_channel[PMU_HANDLER_CHANNEL_MAX_LEN];   /**< Target channel */
    float value;                                         /**< Value to write */

    /* CAN/LIN message (for SEND_CAN/SEND_LIN) */
    PMU_HandlerMessage_t message;                        /**< Message config */

    /* Lua function (for RUN_LUA) */
    char lua_function[PMU_HANDLER_LUA_FUNC_MAX_LEN];    /**< Lua function name */

    /* Description */
    char description[64];                                /**< Optional description */

} PMU_HandlerConfig_t;

/**
 * @brief Event instance pushed to queue
 */
typedef struct {
    PMU_EventType_t type;           /**< Event type */
    uint16_t source_channel_id;     /**< Source channel ID that triggered event */
    int32_t value;                  /**< Event value (e.g., fault code) */
    uint32_t timestamp_ms;          /**< Event timestamp */
} PMU_Event_t;

/**
 * @brief Handler runtime state
 */
typedef struct {
    PMU_HandlerConfig_t config;     /**< Handler configuration */
    bool active;                    /**< Handler slot is active */

    /* Resolved channel IDs */
    uint16_t source_channel_id;     /**< Resolved source channel ID */
    uint16_t condition_channel_id;  /**< Resolved condition channel ID */
    uint16_t target_channel_id;     /**< Resolved target channel ID */

    /* Edge detection state */
    int32_t prev_source_value;      /**< Previous source value for edge detection */
    bool prev_threshold_state;      /**< Previous threshold state */

    /* Statistics */
    uint32_t trigger_count;         /**< Number of times triggered */
    uint32_t last_trigger_ms;       /**< Last trigger timestamp */

} PMU_HandlerState_t;

/**
 * @brief Handler system statistics
 */
typedef struct {
    uint8_t total_handlers;         /**< Total configured handlers */
    uint8_t enabled_handlers;       /**< Currently enabled handlers */
    uint32_t events_processed;      /**< Total events processed */
    uint32_t actions_executed;      /**< Total actions executed */
} PMU_HandlerStats_t;

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize handler subsystem
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Handler_Init(void);

/**
 * @brief Add or update a handler configuration
 * @param config Pointer to handler configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Handler_AddHandler(const PMU_HandlerConfig_t* config);

/**
 * @brief Remove a handler by ID
 * @param id Handler ID string
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Handler_RemoveHandler(const char* id);

/**
 * @brief Clear all handlers
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Handler_ClearAll(void);

/**
 * @brief Push an event to the event queue
 * @param type Event type
 * @param source_channel_id Source channel ID
 * @param value Event value
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Handler_PushEvent(PMU_EventType_t type,
                                         uint16_t source_channel_id,
                                         int32_t value);

/**
 * @brief Push a system event (no source channel)
 * @param type System event type
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Handler_PushSystemEvent(PMU_EventType_t type);

/**
 * @brief Update handler system (call from main loop at 100Hz+)
 * Processes event queue and executes matching handlers
 * @retval None
 */
void PMU_Handler_Update(void);

/**
 * @brief Enable or disable a handler
 * @param id Handler ID
 * @param enabled Enable state
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Handler_SetEnabled(const char* id, bool enabled);

/**
 * @brief Check if a handler is enabled
 * @param id Handler ID
 * @retval true if enabled
 */
bool PMU_Handler_IsEnabled(const char* id);

/**
 * @brief Get handler state
 * @param id Handler ID
 * @retval Pointer to state (or NULL if not found)
 */
const PMU_HandlerState_t* PMU_Handler_GetState(const char* id);

/**
 * @brief Get handler system statistics
 * @retval Pointer to statistics structure
 */
const PMU_HandlerStats_t* PMU_Handler_GetStats(void);

/**
 * @brief List all handlers
 * @param configs Array to fill with configurations
 * @param max_count Maximum number to return
 * @retval Number of handlers returned
 */
uint8_t PMU_Handler_ListHandlers(PMU_HandlerConfig_t* configs, uint8_t max_count);

/**
 * @brief Convert event type to string
 * @param type Event type
 * @retval String representation
 */
const char* PMU_Handler_EventTypeToString(PMU_EventType_t type);

/**
 * @brief Convert action type to string
 * @param type Action type
 * @retval String representation
 */
const char* PMU_Handler_ActionTypeToString(PMU_ActionType_t type);

#ifdef __cplusplus
}
#endif

#endif /* PMU_HANDLER_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
