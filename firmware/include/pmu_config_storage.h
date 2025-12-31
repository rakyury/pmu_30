/**
 ******************************************************************************
 * @file           : pmu_config_storage.h
 * @brief          : Configuration Storage Header - Persistent Settings for PMU-30
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module manages persistent configuration storage:
 * - Internal flash for critical settings (preserved across OTA updates)
 * - External flash for JSON configuration (larger storage)
 * - Wear leveling for flash longevity
 * - CRC validation for data integrity
 *
 * Storage Architecture:
 *
 * Internal Flash (64 KB @ 0x081F0000):
 * ┌─────────────────────────────────────┐
 * │ Header (256 bytes)                  │
 * │ - Magic, version, CRC               │
 * ├─────────────────────────────────────┤
 * │ System Config (4 KB)                │
 * │ - Device ID, calibration, etc.      │
 * ├─────────────────────────────────────┤
 * │ Channel Config Backup (56 KB)       │
 * │ - Compressed channel configuration  │
 * └─────────────────────────────────────┘
 *
 * External Flash (256 KB @ 0x00100000):
 * ┌─────────────────────────────────────┐
 * │ JSON Configuration Slot 0 (128 KB)  │
 * ├─────────────────────────────────────┤
 * │ JSON Configuration Slot 1 (128 KB)  │
 * └─────────────────────────────────────┘
 *
 ******************************************************************************
 */

#ifndef PMU_CONFIG_STORAGE_H
#define PMU_CONFIG_STORAGE_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "pmu_hal.h"
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Storage operation status
 */
typedef enum {
    PMU_STORAGE_OK = 0,           /**< Operation successful */
    PMU_STORAGE_ERROR,            /**< Generic error */
    PMU_STORAGE_ERROR_CRC,        /**< CRC check failed */
    PMU_STORAGE_ERROR_FLASH,      /**< Flash operation failed */
    PMU_STORAGE_ERROR_SIZE,       /**< Data too large */
    PMU_STORAGE_ERROR_NOT_FOUND,  /**< Configuration not found */
    PMU_STORAGE_ERROR_CORRUPT,    /**< Data corrupted */
    PMU_STORAGE_ERROR_VERSION     /**< Incompatible version */
} PMU_Storage_Status_t;

/**
 * @brief Configuration storage header
 */
typedef struct __attribute__((packed)) {
    uint32_t magic;               /**< Magic number (0x434F4E46 = "CONF") */
    uint16_t version_major;       /**< Major version */
    uint16_t version_minor;       /**< Minor version */
    uint32_t data_size;           /**< Size of configuration data */
    uint32_t data_crc32;          /**< CRC32 of configuration data */
    uint32_t write_count;         /**< Number of times written (wear leveling) */
    uint32_t timestamp;           /**< Last write timestamp */
    uint8_t  slot_active;         /**< Active slot (0 or 1) for external flash */
    uint8_t  reserved[3];         /**< Reserved for alignment */
    uint32_t header_crc32;        /**< CRC32 of header (excluding this field) */
} PMU_Config_Header_t;

/**
 * @brief System configuration (critical settings stored in internal flash)
 */
typedef struct __attribute__((packed)) {
    /* Device identification */
    uint32_t device_id;           /**< Unique device ID */
    char     serial_number[32];   /**< Device serial number */
    char     device_name[64];     /**< User-defined device name */

    /* Hardware configuration */
    uint8_t  hw_revision;         /**< Hardware revision */
    uint8_t  profet_count;        /**< Number of PROFET channels enabled */
    uint8_t  hbridge_count;       /**< Number of H-bridge channels enabled */
    uint8_t  analog_input_count;  /**< Number of analog inputs enabled */
    uint8_t  digital_input_count; /**< Number of digital inputs enabled */
    uint8_t  can_bus_count;       /**< Number of CAN buses enabled */
    uint8_t  reserved_hw[2];      /**< Reserved */

    /* ADC calibration */
    int16_t  adc_offset[20];      /**< ADC offset calibration per channel */
    uint16_t adc_gain[20];        /**< ADC gain calibration (×1000) */
    uint16_t vbat_calibration;    /**< Battery voltage calibration factor */
    int16_t  temp_offset;         /**< Temperature sensor offset */

    /* Protection thresholds */
    uint16_t voltage_min_mv;      /**< Minimum voltage threshold */
    uint16_t voltage_max_mv;      /**< Maximum voltage threshold */
    int16_t  temp_warning_c;      /**< Temperature warning threshold */
    int16_t  temp_critical_c;     /**< Temperature critical threshold */
    uint32_t max_current_ma;      /**< Maximum total current */

    /* System settings */
    uint16_t update_rate_hz;      /**< Control loop update rate */
    uint16_t logging_rate_hz;     /**< Data logging rate */
    uint8_t  can1_bitrate_idx;    /**< CAN1 bitrate index */
    uint8_t  can2_bitrate_idx;    /**< CAN2 bitrate index */
    uint8_t  can1_fd_enabled;     /**< CAN1 FD mode enabled */
    uint8_t  can2_fd_enabled;     /**< CAN2 FD mode enabled */

    /* Statistics */
    uint32_t power_on_count;      /**< Number of power-on cycles */
    uint32_t runtime_hours;       /**< Total runtime in hours */
    uint32_t fault_count;         /**< Total number of faults */
    uint32_t last_fault_code;     /**< Last fault code */

    /* Reserved for future use */
    uint8_t  reserved[128];
} PMU_System_Config_t;

/**
 * @brief Storage statistics
 */
typedef struct {
    uint32_t read_count;          /**< Number of read operations */
    uint32_t write_count;         /**< Number of write operations */
    uint32_t error_count;         /**< Number of errors */
    uint32_t internal_writes;     /**< Internal flash write count */
    uint32_t external_writes;     /**< External flash write count */
} PMU_Storage_Stats_t;

/* Exported constants --------------------------------------------------------*/

/* Internal flash configuration region */
#define PMU_CONFIG_INT_ADDRESS    0x081F0000UL
#define PMU_CONFIG_INT_SIZE       (64 * 1024)         /* 64 KB */
#define PMU_CONFIG_HEADER_SIZE    256                 /* Header size */
#define PMU_CONFIG_SYSTEM_SIZE    (4 * 1024)          /* System config size */
#define PMU_CONFIG_BACKUP_SIZE    (56 * 1024)         /* Backup config size */

/* External flash configuration region */
#define PMU_CONFIG_EXT_ADDRESS    0x00100000UL
#define PMU_CONFIG_EXT_SIZE       (256 * 1024)        /* 256 KB total */
#define PMU_CONFIG_SLOT_SIZE      (128 * 1024)        /* 128 KB per slot */
#define PMU_CONFIG_SLOT_0         PMU_CONFIG_EXT_ADDRESS
#define PMU_CONFIG_SLOT_1         (PMU_CONFIG_EXT_ADDRESS + PMU_CONFIG_SLOT_SIZE)

/* Magic numbers */
#define PMU_CONFIG_MAGIC          0x434F4E46UL        /* "CONF" */
#define PMU_JSON_MAGIC            0x4A534F4EUL        /* "JSON" */

/* Version */
#define PMU_CONFIG_VERSION_MAJOR  2
#define PMU_CONFIG_VERSION_MINOR  0

/* CRC polynomial */
#define PMU_CONFIG_CRC_POLY       0xEDB88320UL
#define PMU_CONFIG_CRC_INIT       0xFFFFFFFFUL

/* Maximum JSON configuration size */
#define PMU_CONFIG_JSON_MAX_SIZE  (120 * 1024)        /* 120 KB max JSON */

/* Exported functions --------------------------------------------------------*/

/*---------------------------------------------------------------------------*/
/* Initialization                                                             */
/*---------------------------------------------------------------------------*/

/**
 * @brief Initialize configuration storage
 * @retval Storage status
 */
PMU_Storage_Status_t PMU_Storage_Init(void);

/**
 * @brief Check if storage contains valid configuration
 * @retval true if valid configuration exists
 */
bool PMU_Storage_HasValidConfig(void);

/*---------------------------------------------------------------------------*/
/* System Configuration (Internal Flash)                                      */
/*---------------------------------------------------------------------------*/

/**
 * @brief Load system configuration from internal flash
 * @param config Pointer to configuration structure
 * @retval Storage status
 */
PMU_Storage_Status_t PMU_Storage_LoadSystemConfig(PMU_System_Config_t* config);

/**
 * @brief Save system configuration to internal flash
 * @param config Pointer to configuration structure
 * @retval Storage status
 */
PMU_Storage_Status_t PMU_Storage_SaveSystemConfig(const PMU_System_Config_t* config);

/**
 * @brief Reset system configuration to defaults
 * @retval Storage status
 */
PMU_Storage_Status_t PMU_Storage_ResetSystemConfig(void);

/**
 * @brief Get pointer to current system configuration
 * @retval Pointer to system configuration (read-only)
 */
const PMU_System_Config_t* PMU_Storage_GetSystemConfig(void);

/*---------------------------------------------------------------------------*/
/* JSON Configuration (External Flash)                                        */
/*---------------------------------------------------------------------------*/

/**
 * @brief Load JSON configuration from external flash
 * @param buffer Output buffer for JSON data
 * @param buffer_size Buffer size
 * @param actual_size Actual JSON size (output)
 * @retval Storage status
 */
PMU_Storage_Status_t PMU_Storage_LoadJSON(char* buffer, uint32_t buffer_size, uint32_t* actual_size);

/**
 * @brief Save JSON configuration to external flash
 * @param json JSON string to save
 * @param json_size Size of JSON string
 * @retval Storage status
 */
PMU_Storage_Status_t PMU_Storage_SaveJSON(const char* json, uint32_t json_size);

/**
 * @brief Get JSON configuration size without loading
 * @param size Output for JSON size
 * @retval Storage status
 */
PMU_Storage_Status_t PMU_Storage_GetJSONSize(uint32_t* size);

/**
 * @brief Clear JSON configuration
 * @retval Storage status
 */
PMU_Storage_Status_t PMU_Storage_ClearJSON(void);

/*---------------------------------------------------------------------------*/
/* Factory Reset                                                              */
/*---------------------------------------------------------------------------*/

/**
 * @brief Perform factory reset (clear all configuration)
 * @param keep_calibration If true, preserve ADC calibration
 * @retval Storage status
 */
PMU_Storage_Status_t PMU_Storage_FactoryReset(bool keep_calibration);

/**
 * @brief Export configuration to external buffer
 * @param buffer Output buffer
 * @param buffer_size Buffer size
 * @param actual_size Actual export size (output)
 * @retval Storage status
 */
PMU_Storage_Status_t PMU_Storage_ExportConfig(uint8_t* buffer, uint32_t buffer_size, uint32_t* actual_size);

/**
 * @brief Import configuration from buffer
 * @param buffer Configuration data
 * @param buffer_size Buffer size
 * @retval Storage status
 */
PMU_Storage_Status_t PMU_Storage_ImportConfig(const uint8_t* buffer, uint32_t buffer_size);

/*---------------------------------------------------------------------------*/
/* Statistics and Utilities                                                   */
/*---------------------------------------------------------------------------*/

/**
 * @brief Get storage statistics
 * @retval Pointer to statistics structure
 */
PMU_Storage_Stats_t* PMU_Storage_GetStats(void);

/**
 * @brief Increment power-on counter
 * @note Called automatically at startup
 */
void PMU_Storage_IncrementPowerOn(void);

/**
 * @brief Update runtime counter
 * @note Called periodically (e.g., every hour)
 */
void PMU_Storage_UpdateRuntime(void);

/**
 * @brief Log a fault event
 * @param fault_code Fault code to log
 */
void PMU_Storage_LogFault(uint32_t fault_code);

/**
 * @brief Calculate CRC32 of data
 * @param data Data pointer
 * @param length Data length
 * @retval CRC32 value
 */
uint32_t PMU_Storage_CalculateCRC32(const uint8_t* data, uint32_t length);

#ifdef __cplusplus
}
#endif

#endif /* PMU_CONFIG_STORAGE_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
