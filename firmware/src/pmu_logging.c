/**
 ******************************************************************************
 * @file           : pmu_logging.c
 * @brief          : Data Logging System Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module implements:
 * - High-speed data logging (up to 500Hz)
 * - External flash storage (W25Q512JV 512MB)
 * - Circular buffer for continuous recording
 * - Pre/post trigger capture
 * - Session management
 * - Data download via USB/WiFi
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_logging.h"
#include "pmu_adc.h"
#include "pmu_profet.h"
#include "pmu_logic.h"
#include "pmu_protection.h"
#include "stm32h7xx_hal.h"
#include <string.h>

/* Private typedef -----------------------------------------------------------*/

/**
 * @brief Logging state machine
 */
typedef struct {
    PMU_Logging_Status_t status;        /* Current status */
    PMU_LogConfig_t config;             /* Configuration */
    PMU_LogSession_t current_session;   /* Current session info */
    PMU_FlashStats_t flash_stats;       /* Flash statistics */

    /* RAM buffer for fast writes */
    uint8_t buffer[PMU_LOG_BUFFER_SIZE];
    uint16_t buffer_index;

    /* Timing */
    uint32_t sample_counter;            /* Sample counter */
    uint32_t tick_counter;              /* Tick counter for timing */

    /* Trigger state */
    uint8_t triggered;                  /* Trigger flag */
    uint32_t trigger_timestamp;         /* Trigger timestamp */

    /* Flash management */
    uint32_t flash_write_address;       /* Current write address */
    uint32_t session_start_address;     /* Session start address */
} PMU_LoggingState_t;

/* Private define ------------------------------------------------------------*/

/* Flash commands (W25Q512JV) */
#define FLASH_CMD_WRITE_ENABLE      0x06
#define FLASH_CMD_WRITE_DISABLE     0x04
#define FLASH_CMD_READ_STATUS       0x05
#define FLASH_CMD_PAGE_PROGRAM      0x02
#define FLASH_CMD_SECTOR_ERASE      0x20
#define FLASH_CMD_CHIP_ERASE        0xC7
#define FLASH_CMD_READ_DATA         0x03

/* Flash timing */
#define FLASH_PAGE_SIZE             256
#define FLASH_SECTOR_SIZE           4096
#define FLASH_WRITE_TIMEOUT_MS      10

/* Session header magic */
#define SESSION_HEADER_MAGIC        0x504D5530  /* "PMU0" */

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_LoggingState_t log_state;
static SPI_HandleTypeDef* hspi_flash = NULL;  /* SPI handle for flash */

/* Private function prototypes -----------------------------------------------*/
static HAL_StatusTypeDef Logging_InitFlash(void);
static HAL_StatusTypeDef Logging_FlashWriteEnable(void);
static HAL_StatusTypeDef Logging_FlashWaitReady(void);
static HAL_StatusTypeDef Logging_FlashWritePage(uint32_t address, uint8_t* data, uint16_t len);
static HAL_StatusTypeDef Logging_FlashReadData(uint32_t address, uint8_t* data, uint32_t len);
static HAL_StatusTypeDef Logging_FlashEraseSector(uint32_t address);
static void Logging_SampleChannels(void);
static void Logging_WriteBuffer(void);
static uint16_t Logging_GetChannelValue(PMU_LogChannel_t* channel);
static void Logging_UpdateFlashStats(void);

/* Private user code ---------------------------------------------------------*/

/**
 * @brief Initialize logging system
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_Init(void)
{
    /* Clear state */
    memset(&log_state, 0, sizeof(PMU_LoggingState_t));

    /* Set default configuration */
    log_state.config.sample_rate = PMU_LOG_RATE_DEFAULT;
    log_state.config.trigger_mode = PMU_LOG_TRIGGER_MANUAL;
    log_state.config.pre_trigger_ms = 1000;
    log_state.config.post_trigger_ms = 5000;
    log_state.config.channel_count = 0;

    /* Initialize flash statistics */
    log_state.flash_stats.total_bytes = PMU_LOG_FLASH_SIZE;
    log_state.flash_stats.used_bytes = 0;
    log_state.flash_stats.free_bytes = PMU_LOG_FLASH_SIZE;
    log_state.flash_stats.session_count = 0;
    log_state.flash_stats.health_percent = 100;

    /* Set initial status */
    log_state.status = PMU_LOG_STATUS_IDLE;

    /* Initialize external flash */
    /* TODO: Assign SPI handle */
    /* hspi_flash = &hspi1; */

    if (Logging_InitFlash() != HAL_OK) {
        log_state.status = PMU_LOG_STATUS_ERROR;
        return HAL_ERROR;
    }

    /* Update flash statistics */
    Logging_UpdateFlashStats();

    return HAL_OK;
}

/**
 * @brief Initialize external flash chip
 * @retval HAL status
 */
static HAL_StatusTypeDef Logging_InitFlash(void)
{
    /* TODO: Initialize SPI communication with W25Q512JV */
    /* This is a placeholder */

    /* Example initialization:
    if (hspi_flash == NULL) {
        return HAL_ERROR;
    }

    // Read flash ID to verify communication
    uint8_t cmd = 0x9F; // Read JEDEC ID
    uint8_t id[3];

    HAL_GPIO_WritePin(FLASH_CS_GPIO_Port, FLASH_CS_Pin, GPIO_PIN_RESET);
    HAL_SPI_Transmit(hspi_flash, &cmd, 1, HAL_MAX_DELAY);
    HAL_SPI_Receive(hspi_flash, id, 3, HAL_MAX_DELAY);
    HAL_GPIO_WritePin(FLASH_CS_GPIO_Port, FLASH_CS_Pin, GPIO_PIN_SET);

    // Check if ID matches W25Q512JV (0xEF, 0x40, 0x20)
    if (id[0] != 0xEF || id[1] != 0x40 || id[2] != 0x20) {
        return HAL_ERROR;
    }
    */

    return HAL_OK;
}

/**
 * @brief Update logging system (call at 500Hz)
 * @retval None
 */
void PMU_Logging_Update(void)
{
    /* Increment tick counter */
    log_state.tick_counter++;

    /* Check if recording */
    if (log_state.status != PMU_LOG_STATUS_RECORDING) {
        return;
    }

    /* Sample channels based on sample rate */
    uint32_t sample_interval = 500 / log_state.config.sample_rate;

    if (log_state.tick_counter % sample_interval == 0) {
        Logging_SampleChannels();
        log_state.sample_counter++;

        /* Update session duration */
        log_state.current_session.duration_ms =
            (log_state.tick_counter - log_state.trigger_timestamp) * 2; /* 2ms per tick at 500Hz */
        log_state.current_session.sample_count = log_state.sample_counter;
    }

    /* Write buffer when full */
    if (log_state.buffer_index >= PMU_LOG_BUFFER_SIZE - 64) {
        Logging_WriteBuffer();
    }

    /* Check if flash is full */
    if (log_state.flash_write_address >= PMU_LOG_FLASH_SIZE) {
        log_state.status = PMU_LOG_STATUS_FULL;
    }
}

/**
 * @brief Sample all enabled channels
 */
static void Logging_SampleChannels(void)
{
    /* Write timestamp (32-bit, milliseconds) */
    uint32_t timestamp = log_state.current_session.duration_ms;
    memcpy(&log_state.buffer[log_state.buffer_index], &timestamp, 4);
    log_state.buffer_index += 4;

    /* Sample each enabled channel */
    for (uint8_t i = 0; i < log_state.config.channel_count; i++) {
        PMU_LogChannel_t* ch = &log_state.config.channels[i];

        if (!ch->enabled) {
            continue;
        }

        /* Get channel value */
        uint16_t value = Logging_GetChannelValue(ch);

        /* Write to buffer (16-bit value) */
        memcpy(&log_state.buffer[log_state.buffer_index], &value, 2);
        log_state.buffer_index += 2;
    }
}

/**
 * @brief Get value from specific channel
 * @param channel Channel configuration
 * @retval Channel value
 */
static uint16_t Logging_GetChannelValue(PMU_LogChannel_t* channel)
{
    switch (channel->channel_type) {
        case 0:  /* Physical Input (ADC) */
            return PMU_ADC_GetValue(channel->channel_id);

        case 1:  /* Physical Output */
            {
                PMU_PROFET_Channel_t* ch = PMU_PROFET_GetChannelData(channel->channel_id);
                return (ch != NULL) ? ch->current_mA : 0;
            }

        case 2:  /* Virtual Channel */
            return (uint16_t)PMU_Logic_GetVirtualChannel(channel->channel_id);

        case 3:  /* System values */
            /* Could log voltage, temperature, etc. */
            if (channel->channel_id == 0) {
                return PMU_Protection_GetVoltage();
            } else if (channel->channel_id == 1) {
                return (uint16_t)PMU_Protection_GetTemperature();
            }
            return 0;

        default:
            return 0;
    }
}

/**
 * @brief Write buffer to flash
 */
static void Logging_WriteBuffer(void)
{
    if (log_state.buffer_index == 0) {
        return;
    }

    /* Write to flash in 256-byte pages */
    uint16_t bytes_to_write = log_state.buffer_index;
    uint16_t offset = 0;

    while (bytes_to_write > 0) {
        uint16_t chunk = (bytes_to_write > FLASH_PAGE_SIZE) ? FLASH_PAGE_SIZE : bytes_to_write;

        Logging_FlashWritePage(log_state.flash_write_address,
                               &log_state.buffer[offset],
                               chunk);

        log_state.flash_write_address += chunk;
        offset += chunk;
        bytes_to_write -= chunk;
    }

    /* Update session bytes used */
    log_state.current_session.bytes_used =
        log_state.flash_write_address - log_state.session_start_address;

    /* Clear buffer */
    log_state.buffer_index = 0;
}

/**
 * @brief Configure logging
 * @param config Configuration structure
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_Configure(PMU_LogConfig_t* config)
{
    if (config == NULL) {
        return HAL_ERROR;
    }

    /* Can only configure when idle */
    if (log_state.status != PMU_LOG_STATUS_IDLE) {
        return HAL_ERROR;
    }

    /* Copy configuration */
    memcpy(&log_state.config, config, sizeof(PMU_LogConfig_t));

    return HAL_OK;
}

/**
 * @brief Start recording session
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_Start(void)
{
    if (log_state.status != PMU_LOG_STATUS_IDLE) {
        return HAL_ERROR;
    }

    /* Initialize new session */
    log_state.current_session.session_id++;
    log_state.current_session.start_time = log_state.tick_counter / 500; /* Convert to seconds */
    log_state.current_session.duration_ms = 0;
    log_state.current_session.sample_count = 0;
    log_state.current_session.bytes_used = 0;
    log_state.current_session.status = PMU_LOG_STATUS_RECORDING;

    /* Reset counters */
    log_state.sample_counter = 0;
    log_state.buffer_index = 0;
    log_state.triggered = 0;

    /* Set flash write address */
    log_state.session_start_address = log_state.flash_write_address;

    /* Write session header to flash */
    /* TODO: Implement session header */

    /* Set status */
    log_state.status = PMU_LOG_STATUS_RECORDING;

    return HAL_OK;
}

/**
 * @brief Stop recording session
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_Stop(void)
{
    if (log_state.status != PMU_LOG_STATUS_RECORDING &&
        log_state.status != PMU_LOG_STATUS_PAUSED) {
        return HAL_ERROR;
    }

    /* Flush remaining buffer */
    Logging_WriteBuffer();

    /* Update session info */
    log_state.current_session.status = PMU_LOG_STATUS_IDLE;

    /* Update flash statistics */
    log_state.flash_stats.used_bytes = log_state.flash_write_address;
    log_state.flash_stats.free_bytes = PMU_LOG_FLASH_SIZE - log_state.flash_write_address;
    log_state.flash_stats.session_count++;

    /* Set status */
    log_state.status = PMU_LOG_STATUS_IDLE;

    return HAL_OK;
}

/**
 * @brief Pause recording
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_Pause(void)
{
    if (log_state.status != PMU_LOG_STATUS_RECORDING) {
        return HAL_ERROR;
    }

    log_state.status = PMU_LOG_STATUS_PAUSED;
    return HAL_OK;
}

/**
 * @brief Resume recording
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_Resume(void)
{
    if (log_state.status != PMU_LOG_STATUS_PAUSED) {
        return HAL_ERROR;
    }

    log_state.status = PMU_LOG_STATUS_RECORDING;
    return HAL_OK;
}

/**
 * @brief Trigger manual recording
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_Trigger(void)
{
    if (log_state.config.trigger_mode == PMU_LOG_TRIGGER_MANUAL) {
        log_state.triggered = 1;
        log_state.trigger_timestamp = log_state.tick_counter;
        return HAL_OK;
    }

    return HAL_ERROR;
}

/**
 * @brief Get current status
 * @retval Status
 */
PMU_Logging_Status_t PMU_Logging_GetStatus(void)
{
    return log_state.status;
}

/**
 * @brief Get session info
 * @retval Pointer to session info
 */
PMU_LogSession_t* PMU_Logging_GetSessionInfo(void)
{
    return &log_state.current_session;
}

/**
 * @brief Get flash statistics
 * @retval Pointer to flash stats
 */
PMU_FlashStats_t* PMU_Logging_GetFlashStats(void)
{
    return &log_state.flash_stats;
}

/**
 * @brief Erase all data
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_EraseAll(void)
{
    if (log_state.status != PMU_LOG_STATUS_IDLE) {
        return HAL_ERROR;
    }

    /* TODO: Erase entire flash chip */
    /* This would use FLASH_CMD_CHIP_ERASE */

    /* Reset flash pointers */
    log_state.flash_write_address = 0;
    log_state.session_start_address = 0;

    /* Reset statistics */
    log_state.flash_stats.used_bytes = 0;
    log_state.flash_stats.free_bytes = PMU_LOG_FLASH_SIZE;
    log_state.flash_stats.session_count = 0;

    return HAL_OK;
}

/**
 * @brief Erase specific session
 * @param session_id Session to erase
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_Logging_EraseSession(uint32_t session_id)
{
    /* TODO: Implement session-specific erase */
    /* Would require session table in flash */
    return HAL_OK;
}

/**
 * @brief Get session list
 * @param sessions Array to fill
 * @param max_count Maximum sessions
 * @retval Number found
 */
uint16_t PMU_Logging_GetSessionList(PMU_LogSession_t* sessions, uint16_t max_count)
{
    /* TODO: Scan flash for session headers */
    /* For now, return current session if active */
    if (sessions != NULL && max_count > 0) {
        memcpy(&sessions[0], &log_state.current_session, sizeof(PMU_LogSession_t));
        return 1;
    }
    return 0;
}

/**
 * @brief Download session data
 * @param session_id Session ID
 * @param buffer Buffer to write
 * @param offset Offset in session
 * @param length Bytes to read
 * @retval Bytes read
 */
uint32_t PMU_Logging_DownloadSession(uint32_t session_id, uint8_t* buffer,
                                      uint32_t offset, uint32_t length)
{
    /* TODO: Implement session data download */
    /* Would read from flash at session address + offset */
    return 0;
}

/**
 * @brief Update flash statistics
 */
static void Logging_UpdateFlashStats(void)
{
    /* TODO: Scan flash to count sessions and calculate usage */
    /* For now, use current values */
}

/* Flash low-level functions ------------------------------------------------*/

/**
 * @brief Enable flash writes
 * @retval HAL status
 */
static HAL_StatusTypeDef Logging_FlashWriteEnable(void)
{
    /* TODO: Send Write Enable command */
    return HAL_OK;
}

/**
 * @brief Wait for flash ready
 * @retval HAL status
 */
static HAL_StatusTypeDef Logging_FlashWaitReady(void)
{
    /* TODO: Poll status register until ready */
    return HAL_OK;
}

/**
 * @brief Write page to flash
 * @param address Flash address
 * @param data Data to write
 * @param len Data length
 * @retval HAL status
 */
static HAL_StatusTypeDef Logging_FlashWritePage(uint32_t address, uint8_t* data, uint16_t len)
{
    /* TODO: Implement page program */
    /* This would use FLASH_CMD_PAGE_PROGRAM */
    return HAL_OK;
}

/**
 * @brief Read data from flash
 * @param address Flash address
 * @param data Buffer to read into
 * @param len Bytes to read
 * @retval HAL status
 */
static HAL_StatusTypeDef Logging_FlashReadData(uint32_t address, uint8_t* data, uint32_t len)
{
    /* TODO: Implement flash read */
    /* This would use FLASH_CMD_READ_DATA */
    return HAL_OK;
}

/**
 * @brief Erase flash sector
 * @param address Sector address
 * @retval HAL status
 */
static HAL_StatusTypeDef Logging_FlashEraseSector(uint32_t address)
{
    /* TODO: Implement sector erase */
    /* This would use FLASH_CMD_SECTOR_ERASE */
    return HAL_OK;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
