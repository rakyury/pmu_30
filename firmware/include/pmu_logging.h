/**
 ******************************************************************************
 * @file           : pmu_logging.h
 * @brief          : Data Logging System Header
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 ******************************************************************************
 */

#ifndef __PMU_LOGGING_H
#define __PMU_LOGGING_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Logging status
 */
typedef enum {
    PMU_LOG_STATUS_IDLE = 0,
    PMU_LOG_STATUS_RECORDING,
    PMU_LOG_STATUS_PAUSED,
    PMU_LOG_STATUS_FULL,
    PMU_LOG_STATUS_ERROR
} PMU_Logging_Status_t;

/**
 * @brief Log channel configuration
 */
typedef struct {
    uint16_t channel_id;        /* Source channel (input/output/virtual) */
    uint8_t channel_type;       /* 0=Input, 1=Output, 2=Virtual, 3=CAN */
    uint8_t enabled;            /* Enable/disable this channel */
    uint16_t sample_rate;       /* Sample rate in Hz (1-500) */
    char name[32];              /* Channel name */
} PMU_LogChannel_t;

/**
 * @brief Logging configuration
 */
typedef struct {
    uint16_t sample_rate;       /* Base sample rate in Hz (default 500Hz) */
    uint8_t trigger_mode;       /* 0=Always, 1=On input, 2=Manual */
    uint16_t trigger_channel;   /* Trigger channel if applicable */
    uint32_t pre_trigger_ms;    /* Pre-trigger buffer time in ms */
    uint32_t post_trigger_ms;   /* Post-trigger recording time in ms */
    PMU_LogChannel_t channels[64]; /* Up to 64 channels */
    uint8_t channel_count;      /* Number of active channels */
} PMU_LogConfig_t;

/**
 * @brief Logging session info
 */
typedef struct {
    uint32_t session_id;        /* Unique session ID */
    uint32_t start_time;        /* Start timestamp (seconds since boot) */
    uint32_t duration_ms;       /* Recording duration in milliseconds */
    uint32_t sample_count;      /* Total samples recorded */
    uint32_t bytes_used;        /* Flash bytes used */
    PMU_Logging_Status_t status; /* Current status */
} PMU_LogSession_t;

/**
 * @brief Flash statistics
 */
typedef struct {
    uint32_t total_bytes;       /* Total flash size (512MB) */
    uint32_t used_bytes;        /* Bytes used */
    uint32_t free_bytes;        /* Bytes available */
    uint16_t session_count;     /* Number of sessions stored */
    uint32_t write_errors;      /* Flash write error count */
    uint8_t health_percent;     /* Flash health 0-100% */
} PMU_FlashStats_t;

/* Exported constants --------------------------------------------------------*/

/* Flash size (W25Q512JV) */
#define PMU_LOG_FLASH_SIZE          (512UL * 1024 * 1024)  /* 512 MB */
#define PMU_LOG_FLASH_SECTOR_SIZE   (4096)                 /* 4 KB sector */

/* Sample rates */
#define PMU_LOG_RATE_MIN            1       /* 1 Hz */
#define PMU_LOG_RATE_DEFAULT        100     /* 100 Hz */
#define PMU_LOG_RATE_MAX            500     /* 500 Hz */

/* Channel limits */
#define PMU_LOG_MAX_CHANNELS        64
#define PMU_LOG_MAX_SESSIONS        1000

/* Pre-allocated buffer sizes */
#define PMU_LOG_BUFFER_SIZE         (8192)  /* 8KB RAM buffer */

/* Trigger modes */
#define PMU_LOG_TRIGGER_ALWAYS      0
#define PMU_LOG_TRIGGER_ON_INPUT    1
#define PMU_LOG_TRIGGER_MANUAL      2

/* Exported macro ------------------------------------------------------------*/

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize logging system
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_Init(void);

/**
 * @brief Update logging system (call at 500Hz)
 * @retval None
 */
void PMU_Logging_Update(void);

/**
 * @brief Configure logging channels and settings
 * @param config Logging configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_Configure(PMU_LogConfig_t* config);

/**
 * @brief Start recording session
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_Start(void);

/**
 * @brief Stop recording session
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_Stop(void);

/**
 * @brief Pause recording (can be resumed)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_Pause(void);

/**
 * @brief Resume recording
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_Resume(void);

/**
 * @brief Get current logging status
 * @retval Current status
 */
PMU_Logging_Status_t PMU_Logging_GetStatus(void);

/**
 * @brief Get current session info
 * @retval Pointer to session info
 */
PMU_LogSession_t* PMU_Logging_GetSessionInfo(void);

/**
 * @brief Get flash statistics
 * @retval Pointer to flash statistics
 */
PMU_FlashStats_t* PMU_Logging_GetFlashStats(void);

/**
 * @brief Erase all logged data
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_EraseAll(void);

/**
 * @brief Erase specific session
 * @param session_id Session to erase
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_EraseSession(uint32_t session_id);

/**
 * @brief Get list of stored sessions
 * @param sessions Array to fill with session info
 * @param max_count Maximum sessions to retrieve
 * @retval Number of sessions found
 */
uint16_t PMU_Logging_GetSessionList(PMU_LogSession_t* sessions, uint16_t max_count);

/**
 * @brief Download session data
 * @param session_id Session to download
 * @param buffer Buffer to write data
 * @param offset Offset in session data
 * @param length Bytes to read
 * @retval Bytes read
 */
uint32_t PMU_Logging_DownloadSession(uint32_t session_id, uint8_t* buffer,
                                      uint32_t offset, uint32_t length);

/**
 * @brief Trigger manual recording
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_Trigger(void);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_LOGGING_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
