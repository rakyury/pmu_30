/**
 ******************************************************************************
 * @file           : pmu_log.h
 * @brief          : Logging System Header
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module provides a centralized logging system with:
 * - Multiple log levels (DEBUG, INFO, WARN, ERROR)
 * - Ring buffer storage for recent logs
 * - File output support
 * - Real-time streaming via protocol
 * - Source/module tagging
 *
 ******************************************************************************
 */

#ifndef __PMU_LOG_H
#define __PMU_LOG_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include <stdint.h>
#include <stdbool.h>
#include <stdarg.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Log levels
 */
typedef enum {
    PMU_LOG_LEVEL_DEBUG = 0,    /* Detailed debug information */
    PMU_LOG_LEVEL_INFO = 1,     /* General information */
    PMU_LOG_LEVEL_WARN = 2,     /* Warning conditions */
    PMU_LOG_LEVEL_ERROR = 3,    /* Error conditions */
    PMU_LOG_LEVEL_NONE = 4,     /* Logging disabled */
} PMU_LogLevel_t;

/**
 * @brief Single log entry
 */
typedef struct {
    uint32_t timestamp_ms;      /* Timestamp in milliseconds */
    PMU_LogLevel_t level;       /* Log level */
    char source[16];            /* Source module name */
    char message[128];          /* Log message */
} PMU_LogEntry_t;

/**
 * @brief Log callback function type
 * Called for each new log entry (for real-time streaming)
 */
typedef void (*PMU_LogCallback_t)(const PMU_LogEntry_t* entry);

/**
 * @brief Log configuration
 */
typedef struct {
    PMU_LogLevel_t min_level;       /* Minimum level to log */
    bool enable_console;            /* Output to console/UART */
    bool enable_buffer;             /* Store in ring buffer */
    bool enable_file;               /* Write to file */
    bool enable_streaming;          /* Enable real-time callbacks */
    char log_file_path[64];         /* Log file path */
    uint32_t max_file_size;         /* Max file size before rotation (bytes) */
} PMU_LogConfig_t;

/**
 * @brief Log statistics
 */
typedef struct {
    uint32_t total_entries;         /* Total log entries ever */
    uint32_t debug_count;           /* Debug entries */
    uint32_t info_count;            /* Info entries */
    uint32_t warn_count;            /* Warning entries */
    uint32_t error_count;           /* Error entries */
    uint32_t dropped_count;         /* Entries dropped (buffer full) */
    uint32_t buffer_used;           /* Current buffer usage */
    uint32_t buffer_size;           /* Buffer capacity */
} PMU_LogStats_t;

/* Exported constants --------------------------------------------------------*/

/* Log buffer size (number of entries) */
#define PMU_LOG_BUFFER_SIZE         256

/* Maximum message length */
#define PMU_LOG_MAX_MESSAGE         128

/* Maximum source name length */
#define PMU_LOG_MAX_SOURCE          16

/* Default log file path */
#define PMU_LOG_DEFAULT_FILE        "pmu_log.txt"

/* Default max file size (1 MB) */
#define PMU_LOG_DEFAULT_MAX_SIZE    (1024 * 1024)

/* Exported macros -----------------------------------------------------------*/

/* Convenience logging macros */
#define PMU_LOG_DEBUG(src, fmt, ...)   PMU_Log_Write(PMU_LOG_LEVEL_DEBUG, src, fmt, ##__VA_ARGS__)
#define PMU_LOG_INFO(src, fmt, ...)    PMU_Log_Write(PMU_LOG_LEVEL_INFO, src, fmt, ##__VA_ARGS__)
#define PMU_LOG_WARN(src, fmt, ...)    PMU_Log_Write(PMU_LOG_LEVEL_WARN, src, fmt, ##__VA_ARGS__)
#define PMU_LOG_ERROR(src, fmt, ...)   PMU_Log_Write(PMU_LOG_LEVEL_ERROR, src, fmt, ##__VA_ARGS__)

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize logging system
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Log_Init(void);

/**
 * @brief Deinitialize logging system
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Log_DeInit(void);

/**
 * @brief Apply log configuration
 * @param config Configuration to apply
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Log_Configure(const PMU_LogConfig_t* config);

/**
 * @brief Get current log configuration
 * @param config Buffer to receive configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Log_GetConfig(PMU_LogConfig_t* config);

/**
 * @brief Set minimum log level
 * @param level Minimum level to log
 */
void PMU_Log_SetLevel(PMU_LogLevel_t level);

/**
 * @brief Get current minimum log level
 * @retval Current minimum level
 */
PMU_LogLevel_t PMU_Log_GetLevel(void);

/**
 * @brief Write a log entry
 * @param level Log level
 * @param source Source module name
 * @param format Printf-style format string
 * @param ... Format arguments
 */
void PMU_Log_Write(PMU_LogLevel_t level, const char* source, const char* format, ...);

/**
 * @brief Write a log entry with va_list
 * @param level Log level
 * @param source Source module name
 * @param format Printf-style format string
 * @param args Format arguments
 */
void PMU_Log_WriteV(PMU_LogLevel_t level, const char* source, const char* format, va_list args);

/**
 * @brief Register callback for real-time log streaming
 * @param callback Callback function (NULL to unregister)
 */
void PMU_Log_SetCallback(PMU_LogCallback_t callback);

/**
 * @brief Get number of entries in buffer
 * @retval Number of entries
 */
uint32_t PMU_Log_GetCount(void);

/**
 * @brief Get log entry from buffer
 * @param index Index (0 = oldest)
 * @param entry Buffer to receive entry
 * @retval true if entry exists
 */
bool PMU_Log_GetEntry(uint32_t index, PMU_LogEntry_t* entry);

/**
 * @brief Get recent entries from buffer
 * @param entries Array to receive entries
 * @param max_count Maximum entries to retrieve
 * @param min_level Minimum level filter (or PMU_LOG_LEVEL_DEBUG for all)
 * @retval Number of entries retrieved
 */
uint32_t PMU_Log_GetRecent(PMU_LogEntry_t* entries, uint32_t max_count, PMU_LogLevel_t min_level);

/**
 * @brief Clear log buffer
 */
void PMU_Log_Clear(void);

/**
 * @brief Get log statistics
 * @param stats Buffer to receive statistics
 */
void PMU_Log_GetStats(PMU_LogStats_t* stats);

/**
 * @brief Flush logs to file
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Log_Flush(void);

/**
 * @brief Get level name string
 * @param level Log level
 * @retval Level name string
 */
const char* PMU_Log_LevelName(PMU_LogLevel_t level);

/**
 * @brief Parse level from string
 * @param name Level name
 * @retval Log level or PMU_LOG_LEVEL_INFO on error
 */
PMU_LogLevel_t PMU_Log_ParseLevel(const char* name);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_LOG_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
