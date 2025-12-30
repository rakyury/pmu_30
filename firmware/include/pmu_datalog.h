/**
 ******************************************************************************
 * @file           : pmu_datalog.h
 * @brief          : High-Frequency Data Logger Header
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module provides high-frequency data logging similar to professional
 * ECU data loggers (Link, Motec, etc.):
 * - Configurable sample rate (50-500 Hz)
 * - Binary format for efficiency
 * - Multiple data channels
 * - File and streaming output
 *
 ******************************************************************************
 */

#ifndef __PMU_DATALOG_H
#define __PMU_DATALOG_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Data channel type
 */
typedef enum {
    DATALOG_TYPE_BOOL = 0,      /* Boolean (1 bit packed) */
    DATALOG_TYPE_UINT8 = 1,     /* Unsigned 8-bit */
    DATALOG_TYPE_INT8 = 2,      /* Signed 8-bit */
    DATALOG_TYPE_UINT16 = 3,    /* Unsigned 16-bit */
    DATALOG_TYPE_INT16 = 4,     /* Signed 16-bit */
    DATALOG_TYPE_UINT32 = 5,    /* Unsigned 32-bit */
    DATALOG_TYPE_INT32 = 6,     /* Signed 32-bit */
    DATALOG_TYPE_FLOAT = 7,     /* 32-bit float */
} PMU_DataLog_Type_t;

/**
 * @brief Data channel category
 */
typedef enum {
    DATALOG_CAT_SYSTEM = 0,     /* System (voltage, temp, uptime) */
    DATALOG_CAT_OUTPUT = 1,     /* PROFET outputs */
    DATALOG_CAT_INPUT = 2,      /* Analog/digital inputs */
    DATALOG_CAT_HBRIDGE = 3,    /* H-Bridge motors */
    DATALOG_CAT_CAN = 4,        /* CAN data */
    DATALOG_CAT_LOGIC = 5,      /* Logic channels */
    DATALOG_CAT_PID = 6,        /* PID controllers */
    DATALOG_CAT_USER = 7,       /* User-defined */
} PMU_DataLog_Category_t;

/**
 * @brief Data channel definition
 */
typedef struct {
    uint16_t id;                /* Unique channel ID */
    char name[24];              /* Channel name */
    char unit[8];               /* Unit string (A, V, %, deg, etc.) */
    PMU_DataLog_Type_t type;    /* Data type */
    PMU_DataLog_Category_t category; /* Category for grouping */
    float scale;                /* Scale factor (value * scale = real) */
    float offset;               /* Offset (value * scale + offset = real) */
    float min_value;            /* Minimum expected value */
    float max_value;            /* Maximum expected value */
    uint8_t decimal_places;     /* Decimal places for display */
    uint8_t enabled;            /* Channel enabled for logging */
} PMU_DataLog_Channel_t;

/**
 * @brief Log sample (single timestamp data)
 */
typedef struct {
    uint32_t timestamp_ms;      /* Sample timestamp */
    uint16_t channel_count;     /* Number of channels in sample */
    uint8_t data[];             /* Variable length data */
} PMU_DataLog_Sample_t;

/**
 * @brief Log file header
 */
typedef struct {
    uint32_t magic;             /* Magic number 'PLOG' */
    uint16_t version;           /* File format version */
    uint16_t channel_count;     /* Number of channels */
    uint32_t sample_rate_hz;    /* Sample rate */
    uint32_t start_time;        /* Start timestamp */
    uint32_t sample_count;      /* Total samples */
    char device_name[32];       /* Device name */
    char session_name[32];      /* Session name */
} PMU_DataLog_FileHeader_t;

/**
 * @brief Logger configuration
 */
typedef struct {
    uint16_t sample_rate_hz;    /* Sample rate (50-500 Hz) */
    bool enable_file;           /* Write to file */
    bool enable_streaming;      /* Stream via protocol */
    char log_file_path[64];     /* Log file path */
    char session_name[32];      /* Session name */
    uint32_t max_file_size_mb;  /* Max file size before new file */
    uint16_t buffer_size;       /* Sample buffer size */
} PMU_DataLog_Config_t;

/**
 * @brief Logger state
 */
typedef enum {
    DATALOG_STATE_IDLE = 0,     /* Not logging */
    DATALOG_STATE_RUNNING = 1,  /* Logging active */
    DATALOG_STATE_PAUSED = 2,   /* Logging paused */
    DATALOG_STATE_ERROR = 3,    /* Error occurred */
} PMU_DataLog_State_t;

/**
 * @brief Logger statistics
 */
typedef struct {
    PMU_DataLog_State_t state;  /* Current state */
    uint32_t samples_logged;    /* Total samples logged */
    uint32_t samples_dropped;   /* Samples dropped (overflow) */
    uint32_t bytes_written;     /* Bytes written to file */
    uint32_t duration_ms;       /* Logging duration */
    uint16_t current_rate_hz;   /* Actual sample rate achieved */
    uint8_t buffer_usage_pct;   /* Buffer usage percentage */
} PMU_DataLog_Stats_t;

/**
 * @brief Sample callback for streaming
 */
typedef void (*PMU_DataLog_Callback_t)(const uint8_t* data, uint16_t len);

/* Exported constants --------------------------------------------------------*/

/* File format magic */
#define DATALOG_MAGIC           0x474F4C50  /* 'PLOG' */

/* File format version */
#define DATALOG_VERSION         0x0100      /* 1.0 */

/* Limits */
#define DATALOG_MAX_CHANNELS    128
#define DATALOG_MIN_RATE_HZ     10
#define DATALOG_MAX_RATE_HZ     500
#define DATALOG_DEFAULT_RATE    100

/* Default buffer size (samples) */
#define DATALOG_BUFFER_SIZE     1024

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize data logger
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_DataLog_Init(void);

/**
 * @brief Deinitialize data logger
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_DataLog_DeInit(void);

/**
 * @brief Configure data logger
 * @param config Configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_DataLog_Configure(const PMU_DataLog_Config_t* config);

/**
 * @brief Get current configuration
 * @param config Buffer to receive configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_DataLog_GetConfig(PMU_DataLog_Config_t* config);

/**
 * @brief Register a data channel
 * @param channel Channel definition
 * @retval Channel ID or -1 on error
 */
int16_t PMU_DataLog_RegisterChannel(const PMU_DataLog_Channel_t* channel);

/**
 * @brief Unregister a channel
 * @param channel_id Channel ID
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_DataLog_UnregisterChannel(uint16_t channel_id);

/**
 * @brief Get channel by ID
 * @param channel_id Channel ID
 * @retval Pointer to channel or NULL
 */
const PMU_DataLog_Channel_t* PMU_DataLog_GetChannel(uint16_t channel_id);

/**
 * @brief Get channel count
 * @retval Number of registered channels
 */
uint16_t PMU_DataLog_GetChannelCount(void);

/**
 * @brief Enable/disable channel for logging
 * @param channel_id Channel ID
 * @param enabled Enable state
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_DataLog_SetChannelEnabled(uint16_t channel_id, bool enabled);

/**
 * @brief Start logging
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_DataLog_Start(void);

/**
 * @brief Stop logging
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_DataLog_Stop(void);

/**
 * @brief Pause logging
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_DataLog_Pause(void);

/**
 * @brief Resume logging
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_DataLog_Resume(void);

/**
 * @brief Get logger state
 * @retval Current state
 */
PMU_DataLog_State_t PMU_DataLog_GetState(void);

/**
 * @brief Get logger statistics
 * @param stats Buffer to receive stats
 */
void PMU_DataLog_GetStats(PMU_DataLog_Stats_t* stats);

/**
 * @brief Update logger (call at system tick rate)
 * Called automatically by system tick.
 */
void PMU_DataLog_Update(void);

/**
 * @brief Set streaming callback
 * @param callback Callback function
 */
void PMU_DataLog_SetCallback(PMU_DataLog_Callback_t callback);

/**
 * @brief Register default PMU channels (outputs, inputs, system)
 * @retval Number of channels registered
 */
uint16_t PMU_DataLog_RegisterDefaultChannels(void);

/**
 * @brief Flush pending data to file
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_DataLog_Flush(void);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_DATALOG_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
