/**
 ******************************************************************************
 * @file           : pmu_json_helpers.h
 * @brief          : JSON Field Extraction Helpers
 * @author         : R2 m-sport
 * @date           : 2025-12-29
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module provides additional helper functions for extracting typed values
 * from cJSON objects. These supplement the existing JSON_GetInt/Float/Bool/String
 * functions in pmu_config_json.c with typed integer variants and enum mapping.
 *
 ******************************************************************************
 */

#ifndef PMU_JSON_HELPERS_H
#define PMU_JSON_HELPERS_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* Forward declaration to avoid including cJSON.h in header */
struct cJSON;

/* Exported types ------------------------------------------------------------*/

/**
 * @brief String-to-enum mapping entry for JSON_GetEnum
 */
typedef struct {
    const char* name;   /**< JSON string value */
    int value;          /**< Corresponding enum/integer value */
} JSON_EnumMap_t;

/**
 * @brief Sentinel value to mark end of enum map array
 */
#define JSON_ENUM_MAP_END  { NULL, 0 }

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Get unsigned 8-bit integer from JSON object field
 * @param obj cJSON object to read from
 * @param field Field name
 * @param default_val Value to return if field missing or not a number
 * @return uint8_t value or default (clamped to 0-255)
 */
uint8_t JSON_GetUint8(const struct cJSON* obj, const char* field, uint8_t default_val);

/**
 * @brief Get unsigned 16-bit integer from JSON object field
 * @param obj cJSON object to read from
 * @param field Field name
 * @param default_val Value to return if field missing or not a number
 * @return uint16_t value or default (clamped to 0-65535)
 */
uint16_t JSON_GetUint16(const struct cJSON* obj, const char* field, uint16_t default_val);

/**
 * @brief Get signed 16-bit integer from JSON object field
 * @param obj cJSON object to read from
 * @param field Field name
 * @param default_val Value to return if field missing or not a number
 * @return int16_t value or default
 */
int16_t JSON_GetInt16(const struct cJSON* obj, const char* field, int16_t default_val);

/**
 * @brief Copy string value from JSON object field to destination buffer
 * @param obj cJSON object to read from
 * @param field Field name
 * @param dest Destination buffer
 * @param dest_size Size of destination buffer (includes null terminator)
 * @return true if string was copied, false if field missing or not a string
 * @note Always null-terminates dest, even on failure (sets to empty string)
 */
bool JSON_CopyString(const struct cJSON* obj, const char* field, char* dest, size_t dest_size);

/**
 * @brief Get enum value from JSON string field using mapping table
 * @param obj cJSON object to read from
 * @param field Field name
 * @param map Array of JSON_EnumMap_t entries, terminated with JSON_ENUM_MAP_END
 * @param default_val Value to return if field missing or string not in map
 * @return Mapped integer value or default
 *
 * Example:
 *   static const JSON_EnumMap_t mode_map[] = {
 *       { "coast", 0 }, { "forward", 1 }, { "reverse", 2 },
 *       JSON_ENUM_MAP_END
 *   };
 *   config.mode = JSON_GetEnum(obj, "mode", mode_map, 0);
 */
int JSON_GetEnum(const struct cJSON* obj, const char* field,
                 const JSON_EnumMap_t* map, int default_val);

#ifdef __cplusplus
}
#endif

#endif /* PMU_JSON_HELPERS_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
