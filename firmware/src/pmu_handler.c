/**
 ******************************************************************************
 * @file           : pmu_handler.c
 * @brief          : Event Handler System Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-25
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_handler.h"
#include "pmu_channel.h"
#include "pmu_profet.h"
#include "pmu_can.h"
#include <string.h>
#include <stdio.h>

/* Private defines -----------------------------------------------------------*/

/* Private types -------------------------------------------------------------*/

/**
 * @brief Circular event queue
 */
typedef struct {
    PMU_Event_t events[PMU_HANDLER_EVENT_QUEUE_SIZE];
    uint8_t head;           /**< Next write position */
    uint8_t tail;           /**< Next read position */
    uint8_t count;          /**< Number of events in queue */
} EventQueue_t;

/* Private variables ---------------------------------------------------------*/

/** Handler storage */
static PMU_HandlerState_t handlers[PMU_HANDLER_MAX_HANDLERS];
static uint8_t handler_count = 0;

/** Event queue */
static EventQueue_t event_queue = {0};

/** Statistics */
static PMU_HandlerStats_t stats = {0};

/* Private function prototypes -----------------------------------------------*/
static PMU_HandlerState_t* Handler_FindById(const char* id);
static PMU_HandlerState_t* Handler_FindFreeSlot(void);
static void Handler_ResolveChannelIds(PMU_HandlerState_t* handler);
static bool Handler_EventMatches(const PMU_HandlerState_t* handler, const PMU_Event_t* event);
static bool Handler_CheckCondition(const PMU_HandlerState_t* handler);
static void Handler_ExecuteAction(PMU_HandlerState_t* handler);
static void Handler_ExecuteWriteChannel(const PMU_HandlerState_t* handler);
static void Handler_ExecuteSetOutput(const PMU_HandlerState_t* handler);
static void Handler_ExecuteSendCAN(const PMU_HandlerState_t* handler);
static void Handler_ExecuteSendLIN(const PMU_HandlerState_t* handler);
static void Handler_ExecuteRunLua(const PMU_HandlerState_t* handler);
static bool Queue_Push(const PMU_Event_t* event);
static bool Queue_Pop(PMU_Event_t* event);
static void Handler_ProcessThresholds(void);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize handler subsystem
 */
HAL_StatusTypeDef PMU_Handler_Init(void)
{
    /* Clear all handlers */
    memset(handlers, 0, sizeof(handlers));
    handler_count = 0;

    /* Clear event queue */
    memset(&event_queue, 0, sizeof(event_queue));

    /* Clear statistics */
    memset(&stats, 0, sizeof(stats));

    return HAL_OK;
}

/**
 * @brief Add or update a handler
 */
HAL_StatusTypeDef PMU_Handler_AddHandler(const PMU_HandlerConfig_t* config)
{
    if (!config || config->id[0] == '\0') {
        return HAL_ERROR;
    }

    /* Check if handler with this ID already exists */
    PMU_HandlerState_t* existing = Handler_FindById(config->id);
    if (existing) {
        /* Update existing handler */
        memcpy(&existing->config, config, sizeof(PMU_HandlerConfig_t));
        existing->prev_source_value = 0;
        existing->prev_threshold_state = false;
        Handler_ResolveChannelIds(existing);
        return HAL_OK;
    }

    /* Find free slot */
    PMU_HandlerState_t* slot = Handler_FindFreeSlot();
    if (!slot) {
        return HAL_ERROR;  /* No free slots */
    }

    /* Initialize new handler */
    memset(slot, 0, sizeof(PMU_HandlerState_t));
    memcpy(&slot->config, config, sizeof(PMU_HandlerConfig_t));
    slot->active = true;

    /* Resolve channel IDs */
    Handler_ResolveChannelIds(slot);

    handler_count++;
    stats.total_handlers = handler_count;
    if (config->enabled) {
        stats.enabled_handlers++;
    }

    return HAL_OK;
}

/**
 * @brief Remove a handler by ID
 */
HAL_StatusTypeDef PMU_Handler_RemoveHandler(const char* id)
{
    PMU_HandlerState_t* handler = Handler_FindById(id);
    if (!handler) {
        return HAL_ERROR;
    }

    if (handler->config.enabled) {
        stats.enabled_handlers--;
    }

    handler->active = false;
    handler_count--;
    stats.total_handlers = handler_count;

    return HAL_OK;
}

/**
 * @brief Clear all handlers
 */
HAL_StatusTypeDef PMU_Handler_ClearAll(void)
{
    memset(handlers, 0, sizeof(handlers));
    handler_count = 0;
    stats.total_handlers = 0;
    stats.enabled_handlers = 0;

    return HAL_OK;
}

/**
 * @brief Push an event to the queue
 */
HAL_StatusTypeDef PMU_Handler_PushEvent(PMU_EventType_t type,
                                         uint16_t source_channel_id,
                                         int32_t value)
{
    PMU_Event_t event = {
        .type = type,
        .source_channel_id = source_channel_id,
        .value = value,
        .timestamp_ms = HAL_GetTick()
    };

    if (Queue_Push(&event)) {
        return HAL_OK;
    }
    return HAL_ERROR;  /* Queue full */
}

/**
 * @brief Push a system event
 */
HAL_StatusTypeDef PMU_Handler_PushSystemEvent(PMU_EventType_t type)
{
    return PMU_Handler_PushEvent(type, 0, 0);
}

/**
 * @brief Update handler system - process events and execute handlers
 */
void PMU_Handler_Update(void)
{
    PMU_Event_t event;

    /* Process threshold crossings (edge detection for analog inputs) */
    Handler_ProcessThresholds();

    /* Process all events in queue */
    while (Queue_Pop(&event)) {
        stats.events_processed++;

        /* Check each handler */
        for (uint8_t i = 0; i < PMU_HANDLER_MAX_HANDLERS; i++) {
            PMU_HandlerState_t* handler = &handlers[i];

            if (!handler->active || !handler->config.enabled) {
                continue;
            }

            /* Check if event matches handler */
            if (!Handler_EventMatches(handler, &event)) {
                continue;
            }

            /* Check condition (if specified) */
            if (!Handler_CheckCondition(handler)) {
                continue;
            }

            /* Execute action */
            Handler_ExecuteAction(handler);

            /* Update statistics */
            handler->trigger_count++;
            handler->last_trigger_ms = HAL_GetTick();
            stats.actions_executed++;
        }
    }
}

/**
 * @brief Enable or disable a handler
 */
HAL_StatusTypeDef PMU_Handler_SetEnabled(const char* id, bool enabled)
{
    PMU_HandlerState_t* handler = Handler_FindById(id);
    if (!handler) {
        return HAL_ERROR;
    }

    if (handler->config.enabled != enabled) {
        handler->config.enabled = enabled;
        if (enabled) {
            stats.enabled_handlers++;
        } else {
            stats.enabled_handlers--;
        }
    }

    return HAL_OK;
}

/**
 * @brief Check if handler is enabled
 */
bool PMU_Handler_IsEnabled(const char* id)
{
    PMU_HandlerState_t* handler = Handler_FindById(id);
    if (!handler) {
        return false;
    }
    return handler->config.enabled;
}

/**
 * @brief Get handler state
 */
const PMU_HandlerState_t* PMU_Handler_GetState(const char* id)
{
    return Handler_FindById(id);
}

/**
 * @brief Get statistics
 */
const PMU_HandlerStats_t* PMU_Handler_GetStats(void)
{
    return &stats;
}

/**
 * @brief List all handlers
 */
uint8_t PMU_Handler_ListHandlers(PMU_HandlerConfig_t* configs, uint8_t max_count)
{
    uint8_t count = 0;

    for (uint8_t i = 0; i < PMU_HANDLER_MAX_HANDLERS && count < max_count; i++) {
        if (handlers[i].active) {
            memcpy(&configs[count], &handlers[i].config, sizeof(PMU_HandlerConfig_t));
            count++;
        }
    }

    return count;
}

/**
 * @brief Convert event type to string
 */
const char* PMU_Handler_EventTypeToString(PMU_EventType_t type)
{
    switch (type) {
        case PMU_EVENT_CHANNEL_ON:      return "channel_on";
        case PMU_EVENT_CHANNEL_OFF:     return "channel_off";
        case PMU_EVENT_CHANNEL_FAULT:   return "channel_fault";
        case PMU_EVENT_CHANNEL_CLEARED: return "channel_cleared";
        case PMU_EVENT_THRESHOLD_HIGH:  return "threshold_high";
        case PMU_EVENT_THRESHOLD_LOW:   return "threshold_low";
        case PMU_EVENT_SYSTEM_UNDERVOLT: return "system_undervolt";
        case PMU_EVENT_SYSTEM_OVERVOLT:  return "system_overvolt";
        case PMU_EVENT_SYSTEM_OVERTEMP:  return "system_overtemp";
        default:                         return "unknown";
    }
}

/**
 * @brief Convert action type to string
 */
const char* PMU_Handler_ActionTypeToString(PMU_ActionType_t type)
{
    switch (type) {
        case PMU_ACTION_WRITE_CHANNEL: return "write_channel";
        case PMU_ACTION_SEND_CAN:      return "send_can";
        case PMU_ACTION_SEND_LIN:      return "send_lin";
        case PMU_ACTION_RUN_LUA:       return "run_lua";
        case PMU_ACTION_SET_OUTPUT:    return "set_output";
        default:                       return "unknown";
    }
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Find handler by ID
 */
static PMU_HandlerState_t* Handler_FindById(const char* id)
{
    for (uint8_t i = 0; i < PMU_HANDLER_MAX_HANDLERS; i++) {
        if (handlers[i].active &&
            strncmp(handlers[i].config.id, id, PMU_HANDLER_ID_MAX_LEN) == 0) {
            return &handlers[i];
        }
    }
    return NULL;
}

/**
 * @brief Find free handler slot
 */
static PMU_HandlerState_t* Handler_FindFreeSlot(void)
{
    for (uint8_t i = 0; i < PMU_HANDLER_MAX_HANDLERS; i++) {
        if (!handlers[i].active) {
            return &handlers[i];
        }
    }
    return NULL;
}

/**
 * @brief Resolve channel names to IDs
 */
static void Handler_ResolveChannelIds(PMU_HandlerState_t* handler)
{
    handler->source_channel_id = 0;
    handler->condition_channel_id = 0;
    handler->target_channel_id = 0;

    /* Resolve source channel */
    if (handler->config.source_channel[0] != '\0') {
        handler->source_channel_id = PMU_Channel_GetIndexByID(handler->config.source_channel);
    }

    /* Resolve condition channel */
    if (handler->config.condition_channel[0] != '\0') {
        handler->condition_channel_id = PMU_Channel_GetIndexByID(handler->config.condition_channel);
    }

    /* Resolve target channel */
    if (handler->config.target_channel[0] != '\0') {
        handler->target_channel_id = PMU_Channel_GetIndexByID(handler->config.target_channel);
    }
}

/**
 * @brief Check if event matches handler configuration
 */
static bool Handler_EventMatches(const PMU_HandlerState_t* handler, const PMU_Event_t* event)
{
    /* Event type must match */
    if (handler->config.event != event->type) {
        return false;
    }

    /* For system events, no source channel check needed */
    if (event->type == PMU_EVENT_SYSTEM_UNDERVOLT ||
        event->type == PMU_EVENT_SYSTEM_OVERVOLT ||
        event->type == PMU_EVENT_SYSTEM_OVERTEMP) {
        return true;
    }

    /* For channel events, source must match */
    if (handler->source_channel_id != 0 &&
        handler->source_channel_id == event->source_channel_id) {
        return true;
    }

    return false;
}

/**
 * @brief Check if condition channel is true
 */
static bool Handler_CheckCondition(const PMU_HandlerState_t* handler)
{
    /* No condition = always pass */
    if (handler->condition_channel_id == 0) {
        return true;
    }

    /* Get condition channel value */
    int32_t value = PMU_Channel_GetValue(handler->condition_channel_id);
    return (value != 0);
}

/**
 * @brief Execute handler action
 */
static void Handler_ExecuteAction(PMU_HandlerState_t* handler)
{
    switch (handler->config.action) {
        case PMU_ACTION_WRITE_CHANNEL:
            Handler_ExecuteWriteChannel(handler);
            break;
        case PMU_ACTION_SET_OUTPUT:
            Handler_ExecuteSetOutput(handler);
            break;
        case PMU_ACTION_SEND_CAN:
            Handler_ExecuteSendCAN(handler);
            break;
        case PMU_ACTION_SEND_LIN:
            Handler_ExecuteSendLIN(handler);
            break;
        case PMU_ACTION_RUN_LUA:
            Handler_ExecuteRunLua(handler);
            break;
        default:
            break;
    }
}

/**
 * @brief Execute WRITE_CHANNEL action
 */
static void Handler_ExecuteWriteChannel(const PMU_HandlerState_t* handler)
{
    if (handler->target_channel_id != 0) {
        PMU_Channel_SetValue(handler->target_channel_id, (int32_t)handler->config.value);
    }
}

/**
 * @brief Execute SET_OUTPUT action
 */
static void Handler_ExecuteSetOutput(const PMU_HandlerState_t* handler)
{
    if (handler->target_channel_id != 0) {
        /* Get physical output index from channel */
        uint8_t output_idx = handler->target_channel_id;
        if (output_idx < PMU30_NUM_OUTPUTS) {
            int state = (handler->config.value != 0) ? 1 : 0;
            PMU_PROFET_SetState(output_idx, state);
        }
    }
}

/**
 * @brief Execute SEND_CAN action
 */
static void Handler_ExecuteSendCAN(const PMU_HandlerState_t* handler)
{
    /* Build CAN message structure */
    PMU_CAN_Message_t msg;
    msg.id = handler->config.message.message_id;
    msg.dlc = handler->config.message.dlc > 0 ? handler->config.message.dlc : 8;
    msg.frame_type = PMU_CAN_FRAME_CLASSIC;
    msg.id_type = PMU_CAN_ID_STANDARD;
    msg.rtr = 0;
    memcpy(msg.data, handler->config.message.data, msg.dlc);

    /* Send CAN message */
    PMU_CAN_SendMessage((PMU_CAN_Bus_t)handler->config.message.bus, &msg);
}

/**
 * @brief Execute SEND_LIN action
 */
static void Handler_ExecuteSendLIN(const PMU_HandlerState_t* handler)
{
    /* TODO: Implement LIN message sending */
    (void)handler;
}

/**
 * @brief Execute RUN_LUA action
 */
static void Handler_ExecuteRunLua(const PMU_HandlerState_t* handler)
{
    /* TODO: Implement Lua function call */
    /* Will call PMU_Lua_CallFunction(handler->config.lua_function) */
    (void)handler;
}

/**
 * @brief Process threshold crossings for analog inputs
 */
static void Handler_ProcessThresholds(void)
{
    for (uint8_t i = 0; i < PMU_HANDLER_MAX_HANDLERS; i++) {
        PMU_HandlerState_t* handler = &handlers[i];

        if (!handler->active || !handler->config.enabled) {
            continue;
        }

        /* Only process threshold events */
        if (handler->config.event != PMU_EVENT_THRESHOLD_HIGH &&
            handler->config.event != PMU_EVENT_THRESHOLD_LOW) {
            continue;
        }

        /* Get current source value */
        if (handler->source_channel_id == 0) {
            continue;
        }

        int32_t value = PMU_Channel_GetValue(handler->source_channel_id);

        /* Check threshold crossing */
        float threshold = handler->config.threshold_value;
        bool above_threshold = ((float)value >= threshold);

        if (handler->config.event == PMU_EVENT_THRESHOLD_HIGH) {
            /* Rising edge: was below, now above */
            if (!handler->prev_threshold_state && above_threshold) {
                PMU_Handler_PushEvent(PMU_EVENT_THRESHOLD_HIGH,
                                      handler->source_channel_id, value);
            }
        } else {
            /* Falling edge: was above, now below */
            if (handler->prev_threshold_state && !above_threshold) {
                PMU_Handler_PushEvent(PMU_EVENT_THRESHOLD_LOW,
                                      handler->source_channel_id, value);
            }
        }

        handler->prev_threshold_state = above_threshold;
    }
}

/**
 * @brief Push event to queue
 */
static bool Queue_Push(const PMU_Event_t* event)
{
    if (event_queue.count >= PMU_HANDLER_EVENT_QUEUE_SIZE) {
        return false;  /* Queue full */
    }

    memcpy(&event_queue.events[event_queue.head], event, sizeof(PMU_Event_t));
    event_queue.head = (event_queue.head + 1) % PMU_HANDLER_EVENT_QUEUE_SIZE;
    event_queue.count++;

    return true;
}

/**
 * @brief Pop event from queue
 */
static bool Queue_Pop(PMU_Event_t* event)
{
    if (event_queue.count == 0) {
        return false;  /* Queue empty */
    }

    memcpy(event, &event_queue.events[event_queue.tail], sizeof(PMU_Event_t));
    event_queue.tail = (event_queue.tail + 1) % PMU_HANDLER_EVENT_QUEUE_SIZE;
    event_queue.count--;

    return true;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
