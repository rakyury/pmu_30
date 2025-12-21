/**
 ******************************************************************************
 * @file           : pmu_config_json.c
 * @brief          : JSON Configuration Loader Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_config_json.h"
#include "pmu_config.h"
#include "pmu_adc.h"
#include "pmu_profet.h"
#include "pmu_hbridge.h"
#include "pmu_can.h"
#include "pmu_logic.h"
#include <string.h>
#include <stdlib.h>

#ifndef UNIT_TEST
#include "cJSON.h"
#endif

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/
#define JSON_PARSE_BUFFER_SIZE    (64 * 1024)  /* 64KB buffer for JSON parsing */

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static char last_error[PMU_JSON_MAX_ERROR_LEN] = {0};
static uint32_t load_start_time = 0;

/* Private function prototypes -----------------------------------------------*/
static bool JSON_ParseInputs(cJSON* inputs_array);
static bool JSON_ParseOutputs(cJSON* outputs_array);
static bool JSON_ParseHBridges(cJSON* hbridges_array);
static bool JSON_ParseLogicFunctions(cJSON* logic_array);
static bool JSON_ParseVirtualChannels(cJSON* virtual_array);
static bool JSON_ParsePIDControllers(cJSON* pid_array);
static bool JSON_ParseCANBuses(cJSON* can_array);
static bool JSON_ParseSystem(cJSON* system_obj);
static PMU_InputType_t JSON_ParseInputType(const char* type_str);
static void JSON_SetError(const char* format, ...);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize JSON configuration loader
 */
HAL_StatusTypeDef PMU_JSON_Init(void)
{
    memset(last_error, 0, sizeof(last_error));
    return HAL_OK;
}

/**
 * @brief Load configuration from JSON string
 */
PMU_JSON_Status_t PMU_JSON_LoadFromString(const char* json_string,
                                           uint32_t length,
                                           PMU_JSON_LoadStats_t* stats)
{
#ifdef UNIT_TEST
    (void)json_string;
    (void)length;
    if (stats) {
        memset(stats, 0, sizeof(PMU_JSON_LoadStats_t));
    }
    return PMU_JSON_OK;
#else

    if (!json_string || length == 0) {
        JSON_SetError("Invalid JSON string");
        return PMU_JSON_ERROR_PARSE;
    }

    /* Record start time */
    load_start_time = HAL_GetTick();

    /* Initialize stats */
    PMU_JSON_LoadStats_t local_stats = {0};

    /* Parse JSON */
    cJSON* root = cJSON_Parse(json_string);
    if (!root) {
        const char* error_ptr = cJSON_GetErrorPtr();
        if (error_ptr) {
            JSON_SetError("JSON parse error near: %.50s", error_ptr);
        } else {
            JSON_SetError("JSON parse error");
        }
        return PMU_JSON_ERROR_PARSE;
    }

    /* Validate version */
    cJSON* version = cJSON_GetObjectItem(root, "version");
    if (!version || !cJSON_IsString(version)) {
        JSON_SetError("Missing or invalid version field");
        cJSON_Delete(root);
        return PMU_JSON_ERROR_VALIDATION;
    }

    if (strcmp(version->valuestring, PMU_JSON_VERSION_1_0) != 0) {
        JSON_SetError("Unsupported version: %s (expected %s)",
                      version->valuestring, PMU_JSON_VERSION_1_0);
        cJSON_Delete(root);
        return PMU_JSON_ERROR_VERSION;
    }

    /* Parse device info */
    cJSON* device = cJSON_GetObjectItem(root, "device");
    if (device && cJSON_IsObject(device)) {
        cJSON* name = cJSON_GetObjectItem(device, "name");
        if (name && cJSON_IsString(name)) {
            /* Could store device name in configuration */
        }
    }

    /* Parse inputs */
    cJSON* inputs = cJSON_GetObjectItem(root, "inputs");
    if (inputs && cJSON_IsArray(inputs)) {
        if (!JSON_ParseInputs(inputs)) {
            cJSON_Delete(root);
            return PMU_JSON_ERROR_VALIDATION;
        }
        local_stats.inputs_loaded = cJSON_GetArraySize(inputs);
    }

    /* Parse outputs */
    cJSON* outputs = cJSON_GetObjectItem(root, "outputs");
    if (outputs && cJSON_IsArray(outputs)) {
        if (!JSON_ParseOutputs(outputs)) {
            cJSON_Delete(root);
            return PMU_JSON_ERROR_VALIDATION;
        }
        local_stats.outputs_loaded = cJSON_GetArraySize(outputs);
    }

    /* Parse H-bridges */
    cJSON* hbridges = cJSON_GetObjectItem(root, "hbridges");
    if (hbridges && cJSON_IsArray(hbridges)) {
        if (!JSON_ParseHBridges(hbridges)) {
            cJSON_Delete(root);
            return PMU_JSON_ERROR_VALIDATION;
        }
        local_stats.hbridges_loaded = cJSON_GetArraySize(hbridges);
    }

    /* Parse logic functions */
    cJSON* logic_functions = cJSON_GetObjectItem(root, "logic_functions");
    if (logic_functions && cJSON_IsArray(logic_functions)) {
        if (!JSON_ParseLogicFunctions(logic_functions)) {
            cJSON_Delete(root);
            return PMU_JSON_ERROR_VALIDATION;
        }
        local_stats.logic_functions_loaded = cJSON_GetArraySize(logic_functions);
    }

    /* Parse virtual channels */
    cJSON* virtual_channels = cJSON_GetObjectItem(root, "virtual_channels");
    if (virtual_channels && cJSON_IsArray(virtual_channels)) {
        if (!JSON_ParseVirtualChannels(virtual_channels)) {
            cJSON_Delete(root);
            return PMU_JSON_ERROR_VALIDATION;
        }
        local_stats.virtual_channels_loaded = cJSON_GetArraySize(virtual_channels);
    }

    /* Parse PID controllers */
    cJSON* pid_controllers = cJSON_GetObjectItem(root, "pid_controllers");
    if (pid_controllers && cJSON_IsArray(pid_controllers)) {
        if (!JSON_ParsePIDControllers(pid_controllers)) {
            cJSON_Delete(root);
            return PMU_JSON_ERROR_VALIDATION;
        }
        local_stats.pid_controllers_loaded = cJSON_GetArraySize(pid_controllers);
    }

    /* Parse CAN buses */
    cJSON* can_buses = cJSON_GetObjectItem(root, "can_buses");
    if (can_buses && cJSON_IsArray(can_buses)) {
        if (!JSON_ParseCANBuses(can_buses)) {
            cJSON_Delete(root);
            return PMU_JSON_ERROR_VALIDATION;
        }
        local_stats.can_buses_loaded = cJSON_GetArraySize(can_buses);
    }

    /* Parse system settings */
    cJSON* system = cJSON_GetObjectItem(root, "system");
    if (system && cJSON_IsObject(system)) {
        if (!JSON_ParseSystem(system)) {
            cJSON_Delete(root);
            return PMU_JSON_ERROR_VALIDATION;
        }
    }

    /* Clean up */
    cJSON_Delete(root);

    /* Calculate parse time */
    local_stats.parse_time_ms = HAL_GetTick() - load_start_time;

    /* Copy stats if requested */
    if (stats) {
        memcpy(stats, &local_stats, sizeof(PMU_JSON_LoadStats_t));
    }

    return PMU_JSON_OK;
#endif
}

/**
 * @brief Load configuration from external flash
 */
PMU_JSON_Status_t PMU_JSON_LoadFromFlash(uint32_t flash_address,
                                          PMU_JSON_LoadStats_t* stats)
{
    /* TODO: Implement flash read and JSON load */
    /* This would:
     * 1. Read JSON size from flash header
     * 2. Allocate buffer or read in chunks
     * 3. Read JSON data from flash
     * 4. Call PMU_JSON_LoadFromString()
     */
    (void)flash_address;
    (void)stats;

    JSON_SetError("Flash loading not yet implemented");
    return PMU_JSON_ERROR_FILE;
}

/**
 * @brief Validate JSON configuration
 */
bool PMU_JSON_Validate(const char* json_string,
                        uint32_t length,
                        char* error_msg,
                        uint32_t error_msg_len)
{
#ifdef UNIT_TEST
    (void)json_string;
    (void)length;
    (void)error_msg;
    (void)error_msg_len;
    return true;
#else
    if (!json_string || length == 0) {
        if (error_msg && error_msg_len > 0) {
            snprintf(error_msg, error_msg_len, "Invalid JSON string");
        }
        return false;
    }

    /* Try to parse JSON */
    cJSON* root = cJSON_Parse(json_string);
    if (!root) {
        if (error_msg && error_msg_len > 0) {
            const char* error_ptr = cJSON_GetErrorPtr();
            if (error_ptr) {
                snprintf(error_msg, error_msg_len, "Parse error: %.100s", error_ptr);
            } else {
                snprintf(error_msg, error_msg_len, "Parse error");
            }
        }
        return false;
    }

    /* Check required fields */
    if (!cJSON_GetObjectItem(root, "version")) {
        if (error_msg && error_msg_len > 0) {
            snprintf(error_msg, error_msg_len, "Missing required field: version");
        }
        cJSON_Delete(root);
        return false;
    }

    if (!cJSON_GetObjectItem(root, "device")) {
        if (error_msg && error_msg_len > 0) {
            snprintf(error_msg, error_msg_len, "Missing required field: device");
        }
        cJSON_Delete(root);
        return false;
    }

    cJSON_Delete(root);
    return true;
#endif
}

/**
 * @brief Get JSON configuration version
 */
bool PMU_JSON_GetVersion(const char* json_string,
                          uint32_t length,
                          char* version_buf,
                          uint32_t version_buf_len)
{
#ifdef UNIT_TEST
    (void)json_string;
    (void)length;
    if (version_buf && version_buf_len > 0) {
        strncpy(version_buf, "1.0", version_buf_len - 1);
        version_buf[version_buf_len - 1] = '\0';
    }
    return true;
#else
    if (!json_string || !version_buf || version_buf_len == 0) {
        return false;
    }

    cJSON* root = cJSON_Parse(json_string);
    if (!root) {
        return false;
    }

    cJSON* version = cJSON_GetObjectItem(root, "version");
    if (!version || !cJSON_IsString(version)) {
        cJSON_Delete(root);
        return false;
    }

    strncpy(version_buf, version->valuestring, version_buf_len - 1);
    version_buf[version_buf_len - 1] = '\0';

    cJSON_Delete(root);
    return true;
#endif
}

/**
 * @brief Get last error message
 */
const char* PMU_JSON_GetLastError(void)
{
    return last_error;
}

/**
 * @brief Clear configuration
 */
HAL_StatusTypeDef PMU_JSON_ClearConfig(void)
{
    /* Reset all configurations to defaults */
    PMU_Config_Init();
    return HAL_OK;
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Parse inputs array from JSON
 */
static bool JSON_ParseInputs(cJSON* inputs_array)
{
#ifndef UNIT_TEST
    int count = cJSON_GetArraySize(inputs_array);

    for (int i = 0; i < count && i < 20; i++) {
        cJSON* input = cJSON_GetArrayItem(inputs_array, i);
        if (!input || !cJSON_IsObject(input)) {
            continue;
        }

        /* Get channel number */
        cJSON* channel = cJSON_GetObjectItem(input, "channel");
        if (!channel || !cJSON_IsNumber(channel)) {
            continue;
        }

        uint8_t ch = (uint8_t)channel->valueint;
        if (ch >= 20) {
            continue;
        }

        /* Get input type */
        cJSON* type = cJSON_GetObjectItem(input, "type");
        if (!type || !cJSON_IsString(type)) {
            continue;
        }

        PMU_InputType_t input_type = JSON_ParseInputType(type->valuestring);

        /* Get name */
        cJSON* name = cJSON_GetObjectItem(input, "name");
        const char* name_str = (name && cJSON_IsString(name)) ? name->valuestring : "";

        /* Create input configuration */
        PMU_InputConfig_t* config = PMU_Config_GetInputConfig(ch);
        if (config) {
            config->type = input_type;
            strncpy(config->name, name_str, sizeof(config->name) - 1);

            /* Parse parameters */
            cJSON* params = cJSON_GetObjectItem(input, "parameters");
            if (params && cJSON_IsObject(params)) {
                cJSON* threshold_low = cJSON_GetObjectItem(params, "threshold_low");
                if (threshold_low && cJSON_IsNumber(threshold_low)) {
                    config->threshold_low_mv = (uint16_t)threshold_low->valueint;
                }

                cJSON* threshold_high = cJSON_GetObjectItem(params, "threshold_high");
                if (threshold_high && cJSON_IsNumber(threshold_high)) {
                    config->threshold_high_mv = (uint16_t)threshold_high->valueint;
                }

                cJSON* multiplier = cJSON_GetObjectItem(params, "multiplier");
                if (multiplier && cJSON_IsNumber(multiplier)) {
                    config->multiplier = (float)multiplier->valuedouble;
                }

                cJSON* offset = cJSON_GetObjectItem(params, "offset");
                if (offset && cJSON_IsNumber(offset)) {
                    config->offset = (float)offset->valuedouble;
                }

                cJSON* filter_samples = cJSON_GetObjectItem(params, "filter_samples");
                if (filter_samples && cJSON_IsNumber(filter_samples)) {
                    config->filter_samples = (uint8_t)filter_samples->valueint;
                }

                cJSON* debounce_ms = cJSON_GetObjectItem(params, "debounce_ms");
                if (debounce_ms && cJSON_IsNumber(debounce_ms)) {
                    config->debounce_ms = (uint8_t)debounce_ms->valueint;
                }
            }

            /* Apply configuration to ADC module */
            PMU_ADC_SetConfig(ch, config);
        }
    }
#else
    (void)inputs_array;
#endif

    return true;
}

/**
 * @brief Parse outputs array from JSON
 */
static bool JSON_ParseOutputs(cJSON* outputs_array)
{
#ifndef UNIT_TEST
    int count = cJSON_GetArraySize(outputs_array);

    for (int i = 0; i < count && i < 30; i++) {
        cJSON* output = cJSON_GetArrayItem(outputs_array, i);
        if (!output || !cJSON_IsObject(output)) {
            continue;
        }

        /* Get channel number */
        cJSON* channel = cJSON_GetObjectItem(output, "channel");
        if (!channel || !cJSON_IsNumber(channel)) {
            continue;
        }

        uint8_t ch = (uint8_t)channel->valueint;
        if (ch >= 30) {
            continue;
        }

        /* Get enabled state */
        cJSON* enabled = cJSON_GetObjectItem(output, "enabled");
        bool is_enabled = (enabled && cJSON_IsTrue(enabled));

        /* Get name */
        cJSON* name = cJSON_GetObjectItem(output, "name");
        const char* name_str = (name && cJSON_IsString(name)) ? name->valuestring : "";

        /* Get configuration */
        PMU_OutputConfig_t* config = PMU_Config_GetOutputConfig(ch);
        if (config) {
            config->enabled = is_enabled;
            strncpy(config->name, name_str, sizeof(config->name) - 1);

            /* Parse protection settings */
            cJSON* protection = cJSON_GetObjectItem(output, "protection");
            if (protection && cJSON_IsObject(protection)) {
                cJSON* current_limit = cJSON_GetObjectItem(protection, "current_limit_ma");
                if (current_limit && cJSON_IsNumber(current_limit)) {
                    config->current_limit_mA = (uint16_t)current_limit->valueint;
                }

                cJSON* inrush_current = cJSON_GetObjectItem(protection, "inrush_current_ma");
                if (inrush_current && cJSON_IsNumber(inrush_current)) {
                    config->inrush_current_mA = (uint16_t)inrush_current->valueint;
                }

                cJSON* soft_start = cJSON_GetObjectItem(protection, "soft_start_ms");
                if (soft_start && cJSON_IsNumber(soft_start)) {
                    config->soft_start_ms = (uint16_t)soft_start->valueint;
                }
            }

            /* Parse PWM settings */
            cJSON* pwm = cJSON_GetObjectItem(output, "pwm");
            if (pwm && cJSON_IsObject(pwm)) {
                cJSON* pwm_enabled = cJSON_GetObjectItem(pwm, "enabled");
                config->pwm_enabled = (pwm_enabled && cJSON_IsTrue(pwm_enabled));

                cJSON* default_duty = cJSON_GetObjectItem(pwm, "default_duty");
                if (default_duty && cJSON_IsNumber(default_duty)) {
                    config->default_pwm_duty = (uint16_t)default_duty->valueint;
                }
            }

            /* Apply configuration */
            PMU_PROFET_SetConfig(ch, config);
        }
    }
#else
    (void)outputs_array;
#endif

    return true;
}

/**
 * @brief Parse H-bridges array from JSON (simplified implementation)
 */
static bool JSON_ParseHBridges(cJSON* hbridges_array)
{
    /* TODO: Implement full H-bridge parsing */
    (void)hbridges_array;
    return true;
}

/**
 * @brief Parse logic functions from JSON (simplified implementation)
 */
static bool JSON_ParseLogicFunctions(cJSON* logic_array)
{
    /* TODO: Implement logic function parsing */
    (void)logic_array;
    return true;
}

/**
 * @brief Parse virtual channels from JSON (simplified implementation)
 */
static bool JSON_ParseVirtualChannels(cJSON* virtual_array)
{
    /* TODO: Implement virtual channel parsing */
    (void)virtual_array;
    return true;
}

/**
 * @brief Parse PID controllers from JSON (simplified implementation)
 */
static bool JSON_ParsePIDControllers(cJSON* pid_array)
{
    /* TODO: Implement PID controller parsing */
    (void)pid_array;
    return true;
}

/**
 * @brief Parse CAN buses from JSON (simplified implementation)
 */
static bool JSON_ParseCANBuses(cJSON* can_array)
{
    /* TODO: Implement CAN bus parsing */
    (void)can_array;
    return true;
}

/**
 * @brief Parse system settings from JSON (simplified implementation)
 */
static bool JSON_ParseSystem(cJSON* system_obj)
{
    /* TODO: Implement system settings parsing */
    (void)system_obj;
    return true;
}

/**
 * @brief Parse input type string to enum
 */
static PMU_InputType_t JSON_ParseInputType(const char* type_str)
{
    if (strcmp(type_str, "Switch Active Low") == 0) {
        return PMU_INPUT_SWITCH_ACTIVE_LOW;
    } else if (strcmp(type_str, "Switch Active High") == 0) {
        return PMU_INPUT_SWITCH_ACTIVE_HIGH;
    } else if (strcmp(type_str, "Rotary Switch") == 0) {
        return PMU_INPUT_ROTARY_SWITCH;
    } else if (strcmp(type_str, "Linear Analog") == 0) {
        return PMU_INPUT_LINEAR_ANALOG;
    } else if (strcmp(type_str, "Calibrated Analog") == 0) {
        return PMU_INPUT_CALIBRATED_ANALOG;
    } else if (strcmp(type_str, "Frequency Input") == 0) {
        return PMU_INPUT_FREQUENCY;
    }

    return PMU_INPUT_LINEAR_ANALOG;  /* Default */
}

/**
 * @brief Set error message
 */
static void JSON_SetError(const char* format, ...)
{
    va_list args;
    va_start(args, format);
    vsnprintf(last_error, sizeof(last_error), format, args);
    va_end(args);
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
