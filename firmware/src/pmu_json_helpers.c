/**
 ******************************************************************************
 * @file           : pmu_json_helpers.c
 * @brief          : JSON Field Extraction Helpers Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-29
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_json_helpers.h"

/* Enable cJSON for real hardware and emulator, but not unit tests */
#if !defined(UNIT_TEST) || defined(PMU_EMULATOR)
#include "cJSON.h"
#define JSON_HELPERS_ENABLED 1
#endif

#include <string.h>

/* Private functions ---------------------------------------------------------*/

#ifdef JSON_HELPERS_ENABLED

/**
 * @brief Get unsigned 8-bit integer from JSON object field
 */
uint8_t JSON_GetUint8(const cJSON* obj, const char* field, uint8_t default_val)
{
    if (!obj || !field) return default_val;

    cJSON* item = cJSON_GetObjectItem(obj, field);
    if (item && cJSON_IsNumber(item)) {
        int val = item->valueint;
        if (val < 0) return 0;
        if (val > 255) return 255;
        return (uint8_t)val;
    }
    return default_val;
}

/**
 * @brief Get unsigned 16-bit integer from JSON object field
 */
uint16_t JSON_GetUint16(const cJSON* obj, const char* field, uint16_t default_val)
{
    if (!obj || !field) return default_val;

    cJSON* item = cJSON_GetObjectItem(obj, field);
    if (item && cJSON_IsNumber(item)) {
        int val = item->valueint;
        if (val < 0) return 0;
        if (val > 65535) return 65535;
        return (uint16_t)val;
    }
    return default_val;
}

/**
 * @brief Get signed 16-bit integer from JSON object field
 */
int16_t JSON_GetInt16(const cJSON* obj, const char* field, int16_t default_val)
{
    if (!obj || !field) return default_val;

    cJSON* item = cJSON_GetObjectItem(obj, field);
    if (item && cJSON_IsNumber(item)) {
        int val = item->valueint;
        if (val < -32768) return -32768;
        if (val > 32767) return 32767;
        return (int16_t)val;
    }
    return default_val;
}

/**
 * @brief Copy string value from JSON object field to destination buffer
 */
bool JSON_CopyString(const cJSON* obj, const char* field, char* dest, size_t dest_size)
{
    if (!dest || dest_size == 0) return false;

    /* Always null-terminate, even on failure */
    dest[0] = '\0';

    if (!obj || !field) return false;

    cJSON* item = cJSON_GetObjectItem(obj, field);
    if (item && cJSON_IsString(item) && item->valuestring) {
        strncpy(dest, item->valuestring, dest_size - 1);
        dest[dest_size - 1] = '\0';
        return true;
    }
    return false;
}

/**
 * @brief Get enum value from JSON string field using mapping table
 */
int JSON_GetEnum(const cJSON* obj, const char* field,
                 const JSON_EnumMap_t* map, int default_val)
{
    if (!obj || !field || !map) return default_val;

    cJSON* item = cJSON_GetObjectItem(obj, field);
    if (!item || !cJSON_IsString(item) || !item->valuestring) {
        return default_val;
    }

    /* Search mapping table */
    for (const JSON_EnumMap_t* entry = map; entry->name != NULL; entry++) {
        if (strcmp(item->valuestring, entry->name) == 0) {
            return entry->value;
        }
    }

    return default_val;
}

#else /* JSON_HELPERS_ENABLED */

/* Stub implementations for unit tests without cJSON */

uint8_t JSON_GetUint8(const void* obj, const char* field, uint8_t default_val) { return default_val; }
uint16_t JSON_GetUint16(const void* obj, const char* field, uint16_t default_val) { return default_val; }
int16_t JSON_GetInt16(const void* obj, const char* field, int16_t default_val) { return default_val; }
bool JSON_CopyString(const void* obj, const char* field, char* dest, size_t dest_size) {
    if (dest && dest_size > 0) dest[0] = '\0';
    return false;
}
int JSON_GetEnum(const void* obj, const char* field, const JSON_EnumMap_t* map, int default_val) { return default_val; }

#endif /* JSON_HELPERS_ENABLED */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
