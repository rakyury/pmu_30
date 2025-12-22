/**
 ******************************************************************************
 * @file           : pmu_config_json.h
 * @brief          : JSON Configuration Loader Header
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module loads JSON configuration files matching the format used by
 * the PMU-30 Configurator application.
 *
 * JSON Structure v2.0 (unified channels):
 * {
 *   "version": "2.0",
 *   "device": { ... },
 *   "channels": [
 *     { "id": "...", "channel_type": "digital_input", ... },
 *     { "id": "...", "channel_type": "analog_input", ... },
 *     { "id": "...", "channel_type": "logic", ... },
 *     ...
 *   ],
 *   "can_buses": [ ... ],
 *   "system": { ... }
 * }
 *
 * Supported channel_type values:
 * - digital_input, analog_input, power_output
 * - can_rx, can_tx
 * - logic, number, filter
 * - table_2d, table_3d
 * - switch, timer, enum
 *
 * Legacy v1.0 format is also supported for backwards compatibility.
 *
 ******************************************************************************
 */

#ifndef PMU_CONFIG_JSON_H
#define PMU_CONFIG_JSON_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32h7xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief JSON configuration load result
 */
typedef enum {
    PMU_JSON_OK = 0,              /**< Configuration loaded successfully */
    PMU_JSON_ERROR_PARSE,         /**< JSON parsing error */
    PMU_JSON_ERROR_VALIDATION,    /**< Configuration validation error */
    PMU_JSON_ERROR_VERSION,       /**< Incompatible version */
    PMU_JSON_ERROR_MEMORY,        /**< Out of memory */
    PMU_JSON_ERROR_FILE           /**< File read error */
} PMU_JSON_Status_t;

/**
 * @brief Configuration load statistics (v2.0)
 */
typedef struct {
    uint32_t total_channels;      /**< Total channels loaded (v2.0) */
    uint32_t digital_inputs;      /**< Number of digital inputs */
    uint32_t analog_inputs;       /**< Number of analog inputs */
    uint32_t power_outputs;       /**< Number of power outputs */
    uint32_t logic_functions;     /**< Number of logic functions */
    uint32_t numbers;             /**< Number of math/number channels */
    uint32_t filters;             /**< Number of filters */
    uint32_t timers;              /**< Number of timers */
    uint32_t tables_2d;           /**< Number of 2D tables */
    uint32_t tables_3d;           /**< Number of 3D tables */
    uint32_t switches;            /**< Number of switches */
    uint32_t enums;               /**< Number of enumerations */
    uint32_t can_rx;              /**< Number of CAN RX channels */
    uint32_t can_tx;              /**< Number of CAN TX channels */
    uint32_t can_buses_loaded;    /**< Number of CAN buses loaded */
    uint32_t parse_time_ms;       /**< Parse time in milliseconds */
    /* Legacy v1.0 fields (for backwards compatibility) */
    uint32_t inputs_loaded;       /**< Number of inputs loaded (v1.0) */
    uint32_t outputs_loaded;      /**< Number of outputs loaded (v1.0) */
    uint32_t hbridges_loaded;     /**< Number of H-bridges loaded (v1.0) */
    uint32_t logic_functions_loaded;  /**< Number of logic functions loaded (v1.0) */
    uint32_t virtual_channels_loaded; /**< Number of virtual channels loaded (v1.0) */
    uint32_t pid_controllers_loaded;  /**< Number of PID controllers loaded (v1.0) */
} PMU_JSON_LoadStats_t;

/* Exported constants --------------------------------------------------------*/

#define PMU_JSON_MAX_ERROR_LEN    256   /**< Maximum error message length */
#define PMU_JSON_VERSION_1_0      "1.0" /**< Legacy configuration version */
#define PMU_JSON_VERSION_2_0      "2.0" /**< Current configuration version */

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize JSON configuration loader
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_JSON_Init(void);

/**
 * @brief Load configuration from JSON string
 * @param json_string Pointer to JSON string (null-terminated)
 * @param length Length of JSON string
 * @param stats Pointer to statistics structure (can be NULL)
 * @retval PMU_JSON_Status_t Load status
 */
PMU_JSON_Status_t PMU_JSON_LoadFromString(const char* json_string,
                                           uint32_t length,
                                           PMU_JSON_LoadStats_t* stats);

/**
 * @brief Load configuration from external flash
 * @param flash_address Flash address to read from
 * @param stats Pointer to statistics structure (can be NULL)
 * @retval PMU_JSON_Status_t Load status
 */
PMU_JSON_Status_t PMU_JSON_LoadFromFlash(uint32_t flash_address,
                                          PMU_JSON_LoadStats_t* stats);

/**
 * @brief Validate JSON configuration
 * @param json_string Pointer to JSON string
 * @param length Length of JSON string
 * @param error_msg Buffer to store error message (can be NULL)
 * @param error_msg_len Length of error message buffer
 * @retval true if valid, false otherwise
 */
bool PMU_JSON_Validate(const char* json_string,
                        uint32_t length,
                        char* error_msg,
                        uint32_t error_msg_len);

/**
 * @brief Get JSON configuration version from string
 * @param json_string Pointer to JSON string
 * @param length Length of JSON string
 * @param version_buf Buffer to store version string
 * @param version_buf_len Length of version buffer
 * @retval true if version extracted, false otherwise
 */
bool PMU_JSON_GetVersion(const char* json_string,
                          uint32_t length,
                          char* version_buf,
                          uint32_t version_buf_len);

/**
 * @brief Get last error message
 * @retval Pointer to error message string
 */
const char* PMU_JSON_GetLastError(void);

/**
 * @brief Clear configuration (reset to defaults)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_JSON_ClearConfig(void);

#ifdef __cplusplus
}
#endif

#endif /* PMU_CONFIG_JSON_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
