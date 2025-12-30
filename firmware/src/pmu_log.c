/**
 ******************************************************************************
 * @file           : pmu_log.c
 * @brief          : Logging System Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_log.h"
#include <string.h>
#include <stdio.h>
#include <time.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/

/* Ring buffer for log entries */
static PMU_LogEntry_t s_log_buffer[PMU_LOG_BUFFER_SIZE];
static uint32_t s_buffer_head = 0;      /* Next write position */
static uint32_t s_buffer_count = 0;     /* Number of entries in buffer */

/* Configuration */
static PMU_LogConfig_t s_config = {
    .min_level = PMU_LOG_LEVEL_INFO,
    .enable_console = true,
    .enable_buffer = true,
    .enable_file = false,
    .enable_streaming = true,
    .log_file_path = PMU_LOG_DEFAULT_FILE,
    .max_file_size = PMU_LOG_DEFAULT_MAX_SIZE,
};

/* Statistics */
static PMU_LogStats_t s_stats = {0};

/* Callback for real-time streaming */
static PMU_LogCallback_t s_callback = NULL;

/* File handle for logging */
static FILE* s_log_file = NULL;

/* Initialization flag */
static bool s_initialized = false;

/* Mutex for thread safety (if available) */
#ifdef PMU_LOG_USE_MUTEX
static void* s_mutex = NULL;
#define LOG_LOCK()      /* Platform-specific lock */
#define LOG_UNLOCK()    /* Platform-specific unlock */
#else
#define LOG_LOCK()
#define LOG_UNLOCK()
#endif

/* Private function prototypes -----------------------------------------------*/
static uint32_t GetTimestamp(void);
static void WriteToConsole(const PMU_LogEntry_t* entry);
static void WriteToFile(const PMU_LogEntry_t* entry);

/* Exported functions --------------------------------------------------------*/

HAL_StatusTypeDef PMU_Log_Init(void)
{
    if (s_initialized) {
        return HAL_OK;
    }

    /* Clear buffer */
    memset(s_log_buffer, 0, sizeof(s_log_buffer));
    s_buffer_head = 0;
    s_buffer_count = 0;

    /* Clear statistics */
    memset(&s_stats, 0, sizeof(s_stats));
    s_stats.buffer_size = PMU_LOG_BUFFER_SIZE;

    s_initialized = true;

    PMU_LOG_INFO("Log", "Logging system initialized");

    return HAL_OK;
}

HAL_StatusTypeDef PMU_Log_DeInit(void)
{
    if (!s_initialized) {
        return HAL_OK;
    }

    /* Flush and close file */
    if (s_log_file) {
        fflush(s_log_file);
        fclose(s_log_file);
        s_log_file = NULL;
    }

    s_initialized = false;

    return HAL_OK;
}

HAL_StatusTypeDef PMU_Log_Configure(const PMU_LogConfig_t* config)
{
    if (!config) {
        return HAL_ERROR;
    }

    LOG_LOCK();

    /* Close existing file if path changed */
    if (s_log_file && strcmp(s_config.log_file_path, config->log_file_path) != 0) {
        fclose(s_log_file);
        s_log_file = NULL;
    }

    memcpy(&s_config, config, sizeof(PMU_LogConfig_t));

    /* Open new file if enabled */
    if (s_config.enable_file && !s_log_file) {
        s_log_file = fopen(s_config.log_file_path, "a");
    }

    LOG_UNLOCK();

    return HAL_OK;
}

HAL_StatusTypeDef PMU_Log_GetConfig(PMU_LogConfig_t* config)
{
    if (!config) {
        return HAL_ERROR;
    }

    LOG_LOCK();
    memcpy(config, &s_config, sizeof(PMU_LogConfig_t));
    LOG_UNLOCK();

    return HAL_OK;
}

void PMU_Log_SetLevel(PMU_LogLevel_t level)
{
    s_config.min_level = level;
}

PMU_LogLevel_t PMU_Log_GetLevel(void)
{
    return s_config.min_level;
}

void PMU_Log_Write(PMU_LogLevel_t level, const char* source, const char* format, ...)
{
    va_list args;
    va_start(args, format);
    PMU_Log_WriteV(level, source, format, args);
    va_end(args);
}

void PMU_Log_WriteV(PMU_LogLevel_t level, const char* source, const char* format, va_list args)
{
    /* Check if logging is enabled for this level */
    if (level < s_config.min_level) {
        return;
    }

    if (!s_initialized) {
        /* Allow logging before init, just to console */
        char msg[PMU_LOG_MAX_MESSAGE];
        vsnprintf(msg, sizeof(msg), format, args);
        printf("[%s] %s: %s\n", PMU_Log_LevelName(level), source ? source : "???", msg);
        return;
    }

    LOG_LOCK();

    /* Create log entry */
    PMU_LogEntry_t entry;
    entry.timestamp_ms = GetTimestamp();
    entry.level = level;

    /* Copy source */
    if (source) {
        strncpy(entry.source, source, PMU_LOG_MAX_SOURCE - 1);
        entry.source[PMU_LOG_MAX_SOURCE - 1] = '\0';
    } else {
        strcpy(entry.source, "???");
    }

    /* Format message */
    vsnprintf(entry.message, PMU_LOG_MAX_MESSAGE, format, args);

    /* Update statistics */
    s_stats.total_entries++;
    switch (level) {
        case PMU_LOG_LEVEL_DEBUG: s_stats.debug_count++; break;
        case PMU_LOG_LEVEL_INFO:  s_stats.info_count++; break;
        case PMU_LOG_LEVEL_WARN:  s_stats.warn_count++; break;
        case PMU_LOG_LEVEL_ERROR: s_stats.error_count++; break;
        default: break;
    }

    /* Store in buffer */
    if (s_config.enable_buffer) {
        s_log_buffer[s_buffer_head] = entry;
        s_buffer_head = (s_buffer_head + 1) % PMU_LOG_BUFFER_SIZE;

        if (s_buffer_count < PMU_LOG_BUFFER_SIZE) {
            s_buffer_count++;
        } else {
            s_stats.dropped_count++;
        }
        s_stats.buffer_used = s_buffer_count;
    }

    /* Output to console */
    if (s_config.enable_console) {
        WriteToConsole(&entry);
    }

    /* Write to file */
    if (s_config.enable_file && s_log_file) {
        WriteToFile(&entry);
    }

    /* Call streaming callback */
    if (s_config.enable_streaming && s_callback) {
        s_callback(&entry);
    }

    LOG_UNLOCK();
}

void PMU_Log_SetCallback(PMU_LogCallback_t callback)
{
    s_callback = callback;
}

uint32_t PMU_Log_GetCount(void)
{
    return s_buffer_count;
}

bool PMU_Log_GetEntry(uint32_t index, PMU_LogEntry_t* entry)
{
    if (!entry || index >= s_buffer_count) {
        return false;
    }

    LOG_LOCK();

    /* Calculate actual buffer index (oldest first) */
    uint32_t buf_idx;
    if (s_buffer_count < PMU_LOG_BUFFER_SIZE) {
        buf_idx = index;
    } else {
        buf_idx = (s_buffer_head + index) % PMU_LOG_BUFFER_SIZE;
    }

    *entry = s_log_buffer[buf_idx];

    LOG_UNLOCK();

    return true;
}

uint32_t PMU_Log_GetRecent(PMU_LogEntry_t* entries, uint32_t max_count, PMU_LogLevel_t min_level)
{
    if (!entries || max_count == 0) {
        return 0;
    }

    LOG_LOCK();

    uint32_t retrieved = 0;

    /* Start from most recent and work backwards */
    for (uint32_t i = 0; i < s_buffer_count && retrieved < max_count; i++) {
        uint32_t idx = (s_buffer_head + s_buffer_count - 1 - i) % PMU_LOG_BUFFER_SIZE;

        if (s_log_buffer[idx].level >= min_level) {
            entries[retrieved++] = s_log_buffer[idx];
        }
    }

    LOG_UNLOCK();

    return retrieved;
}

void PMU_Log_Clear(void)
{
    LOG_LOCK();

    s_buffer_head = 0;
    s_buffer_count = 0;
    s_stats.buffer_used = 0;

    LOG_UNLOCK();
}

void PMU_Log_GetStats(PMU_LogStats_t* stats)
{
    if (!stats) {
        return;
    }

    LOG_LOCK();
    *stats = s_stats;
    LOG_UNLOCK();
}

HAL_StatusTypeDef PMU_Log_Flush(void)
{
    if (s_log_file) {
        fflush(s_log_file);
    }
    return HAL_OK;
}

const char* PMU_Log_LevelName(PMU_LogLevel_t level)
{
    switch (level) {
        case PMU_LOG_LEVEL_DEBUG: return "DEBUG";
        case PMU_LOG_LEVEL_INFO:  return "INFO";
        case PMU_LOG_LEVEL_WARN:  return "WARN";
        case PMU_LOG_LEVEL_ERROR: return "ERROR";
        default: return "???";
    }
}

PMU_LogLevel_t PMU_Log_ParseLevel(const char* name)
{
    if (!name) return PMU_LOG_LEVEL_INFO;

    if (strcmp(name, "DEBUG") == 0 || strcmp(name, "debug") == 0) {
        return PMU_LOG_LEVEL_DEBUG;
    } else if (strcmp(name, "INFO") == 0 || strcmp(name, "info") == 0) {
        return PMU_LOG_LEVEL_INFO;
    } else if (strcmp(name, "WARN") == 0 || strcmp(name, "warn") == 0 ||
               strcmp(name, "WARNING") == 0 || strcmp(name, "warning") == 0) {
        return PMU_LOG_LEVEL_WARN;
    } else if (strcmp(name, "ERROR") == 0 || strcmp(name, "error") == 0) {
        return PMU_LOG_LEVEL_ERROR;
    }

    return PMU_LOG_LEVEL_INFO;
}

/* Private functions ---------------------------------------------------------*/

static uint32_t GetTimestamp(void)
{
#ifdef HAL_GetTick
    return HAL_GetTick();
#else
    /* For emulator or systems without HAL */
    static uint32_t s_start_time = 0;
    if (s_start_time == 0) {
        s_start_time = (uint32_t)time(NULL);
    }
    return ((uint32_t)time(NULL) - s_start_time) * 1000;
#endif
}

static void WriteToConsole(const PMU_LogEntry_t* entry)
{
    /* ANSI color codes for different levels */
    const char* color = "";
    const char* reset = "\033[0m";

    switch (entry->level) {
        case PMU_LOG_LEVEL_DEBUG:
            color = "\033[90m";  /* Gray */
            break;
        case PMU_LOG_LEVEL_INFO:
            color = "\033[37m";  /* White */
            break;
        case PMU_LOG_LEVEL_WARN:
            color = "\033[33m";  /* Yellow */
            break;
        case PMU_LOG_LEVEL_ERROR:
            color = "\033[31m";  /* Red */
            break;
        default:
            break;
    }

    printf("%s[%u.%03u] [%s] %s: %s%s\n",
           color,
           entry->timestamp_ms / 1000,
           entry->timestamp_ms % 1000,
           PMU_Log_LevelName(entry->level),
           entry->source,
           entry->message,
           reset);
}

static void WriteToFile(const PMU_LogEntry_t* entry)
{
    if (!s_log_file) {
        return;
    }

    fprintf(s_log_file, "%u,%s,%s,%s\n",
            entry->timestamp_ms,
            PMU_Log_LevelName(entry->level),
            entry->source,
            entry->message);

    /* Check file size for rotation */
    if (s_config.max_file_size > 0) {
        long pos = ftell(s_log_file);
        if (pos > 0 && (uint32_t)pos >= s_config.max_file_size) {
            /* Rotate log file */
            fclose(s_log_file);

            /* Rename current file */
            char backup_path[80];
            snprintf(backup_path, sizeof(backup_path), "%s.1", s_config.log_file_path);
            remove(backup_path);
            rename(s_config.log_file_path, backup_path);

            /* Open new file */
            s_log_file = fopen(s_config.log_file_path, "w");
        }
    }
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
