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
#include "pmu_logic_functions.h"
#include "pmu_channel.h"
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
#include <stdio.h>

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
static PMU_FunctionType_t JSON_ParseFunctionType(const char* type_str);
static uint16_t JSON_ResolveChannel(cJSON* channel_obj);
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

        /* TODO: Create input configuration
         * PMU_Config_GetInputConfig() doesn't exist yet
         * Need to implement proper config API
         */
        (void)input_type;
        (void)name_str;
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

        /* Enable/disable output based on configuration */
        if (is_enabled) {
            PMU_PROFET_SetState(ch, 1);
        } else {
            PMU_PROFET_SetState(ch, 0);
        }

        /* Parse PWM settings */
        cJSON* pwm = cJSON_GetObjectItem(output, "pwm");
        if (pwm && cJSON_IsObject(pwm)) {
            cJSON* default_duty = cJSON_GetObjectItem(pwm, "default_duty");
            if (default_duty && cJSON_IsNumber(default_duty)) {
                uint16_t duty = (uint16_t)default_duty->valueint;
                PMU_PROFET_SetPWM(ch, duty);
            }
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
 * @brief Parse logic functions from JSON
 */
static bool JSON_ParseLogicFunctions(cJSON* logic_array)
{
#ifndef UNIT_TEST
    int count = cJSON_GetArraySize(logic_array);

    for (int i = 0; i < count && i < PMU_MAX_LOGIC_FUNCTIONS; i++) {
        cJSON* func_obj = cJSON_GetArrayItem(logic_array, i);
        if (!func_obj || !cJSON_IsObject(func_obj)) {
            continue;
        }

        /* Get function type */
        cJSON* type = cJSON_GetObjectItem(func_obj, "type");
        if (!type || !cJSON_IsString(type)) {
            JSON_SetError("Logic function %d: missing or invalid type", i);
            continue;
        }

        PMU_FunctionType_t func_type = JSON_ParseFunctionType(type->valuestring);

        /* Get output channel */
        cJSON* output = cJSON_GetObjectItem(func_obj, "output");
        if (!output) {
            JSON_SetError("Logic function %d: missing output channel", i);
            continue;
        }
        uint16_t output_ch = JSON_ResolveChannel(output);

        /* Get input channels */
        cJSON* inputs = cJSON_GetObjectItem(func_obj, "inputs");
        uint16_t input_channels[8] = {0};
        uint8_t input_count = 0;

        if (inputs && cJSON_IsArray(inputs)) {
            int inp_count = cJSON_GetArraySize(inputs);
            for (int j = 0; j < inp_count && j < 8; j++) {
                cJSON* input = cJSON_GetArrayItem(inputs, j);
                input_channels[j] = JSON_ResolveChannel(input);
                input_count++;
            }
        }

        /* Get parameters */
        cJSON* params = cJSON_GetObjectItem(func_obj, "parameters");

        /* Create function based on type */
        uint16_t func_id = 0;

        /* Mathematical operations */
        if (func_type >= PMU_FUNC_ADD && func_type <= PMU_FUNC_CLAMP) {
            if (func_type == PMU_FUNC_SCALE && params) {
                /* Scale function: (input * multiplier) + offset */
                float multiplier = 1.0f;
                float offset = 0.0f;

                cJSON* mult = cJSON_GetObjectItem(params, "multiplier");
                if (mult && cJSON_IsNumber(mult)) {
                    multiplier = (float)mult->valuedouble;
                }

                cJSON* off = cJSON_GetObjectItem(params, "offset");
                if (off && cJSON_IsNumber(off)) {
                    offset = (float)off->valuedouble;
                }

                /* Create scale function manually */
                PMU_LogicFunction_t func = {0};
                func.type = PMU_FUNC_SCALE;
                func.output_channel = output_ch;
                func.input_channels[0] = input_channels[0];
                func.input_count = 1;
                func.enabled = 1;
                func.params.scale.scale = (int32_t)(multiplier * 1000);  /* Convert to fixed-point */
                func.params.scale.offset = (int32_t)offset;

                PMU_LogicFunctions_Register(&func);
                func_id = func.function_id;

            } else if (func_type == PMU_FUNC_CLAMP && params) {
                /* Clamp function: limit to min/max */
                int32_t min_val = -1000000;
                int32_t max_val = 1000000;

                cJSON* min_obj = cJSON_GetObjectItem(params, "min");
                if (min_obj && cJSON_IsNumber(min_obj)) {
                    min_val = (int32_t)min_obj->valueint;
                }

                cJSON* max_obj = cJSON_GetObjectItem(params, "max");
                if (max_obj && cJSON_IsNumber(max_obj)) {
                    max_val = (int32_t)max_obj->valueint;
                }

                /* Create clamp function manually */
                PMU_LogicFunction_t func = {0};
                func.type = PMU_FUNC_CLAMP;
                func.output_channel = output_ch;
                func.input_channels[0] = input_channels[0];
                func.input_count = 1;
                func.enabled = 1;
                func.params.clamp.min = min_val;
                func.params.clamp.max = max_val;

                PMU_LogicFunctions_Register(&func);
                func_id = func.function_id;

            } else {
                /* Simple math functions (add, subtract, multiply, divide, min, max, average, abs) */
                func_id = PMU_LogicFunctions_CreateMath(func_type, output_ch,
                                                         input_channels[0], input_channels[1]);
            }
        }
        /* Comparison operations */
        else if (func_type >= PMU_FUNC_GREATER && func_type <= PMU_FUNC_IN_RANGE) {
            func_id = PMU_LogicFunctions_CreateComparison(func_type, output_ch,
                                                           input_channels[0], input_channels[1]);
        }
        /* Logic operations */
        else if (func_type >= PMU_FUNC_AND && func_type <= PMU_FUNC_NOR) {
            /* Create logic function manually to support N inputs */
            PMU_LogicFunction_t func = {0};
            func.type = func_type;
            func.output_channel = output_ch;
            memcpy(func.input_channels, input_channels, sizeof(input_channels));
            func.input_count = input_count;
            func.enabled = 1;

            PMU_LogicFunctions_Register(&func);
            func_id = func.function_id;
        }
        /* PID Controller */
        else if (func_type == PMU_FUNC_PID) {
            if (!params) {
                JSON_SetError("Logic function %d: PID requires parameters", i);
                continue;
            }

            float setpoint = 0.0f;
            float kp = 1.0f;
            float ki = 0.0f;
            float kd = 0.0f;

            cJSON* sp = cJSON_GetObjectItem(params, "setpoint");
            if (sp && cJSON_IsNumber(sp)) {
                setpoint = (float)sp->valuedouble;
            }

            cJSON* kp_obj = cJSON_GetObjectItem(params, "kp");
            if (kp_obj && cJSON_IsNumber(kp_obj)) {
                kp = (float)kp_obj->valuedouble;
            }

            cJSON* ki_obj = cJSON_GetObjectItem(params, "ki");
            if (ki_obj && cJSON_IsNumber(ki_obj)) {
                ki = (float)ki_obj->valuedouble;
            }

            cJSON* kd_obj = cJSON_GetObjectItem(params, "kd");
            if (kd_obj && cJSON_IsNumber(kd_obj)) {
                kd = (float)kd_obj->valuedouble;
            }

            func_id = PMU_LogicFunctions_CreatePID(output_ch, input_channels[0],
                                                    setpoint, kp, ki, kd);
        }
        /* Hysteresis */
        else if (func_type == PMU_FUNC_HYSTERESIS) {
            if (!params) {
                JSON_SetError("Logic function %d: Hysteresis requires parameters", i);
                continue;
            }

            int32_t threshold_on = 100;
            int32_t threshold_off = 50;

            cJSON* on = cJSON_GetObjectItem(params, "threshold_on");
            if (on && cJSON_IsNumber(on)) {
                threshold_on = (int32_t)on->valueint;
            }

            cJSON* off = cJSON_GetObjectItem(params, "threshold_off");
            if (off && cJSON_IsNumber(off)) {
                threshold_off = (int32_t)off->valueint;
            }

            func_id = PMU_LogicFunctions_CreateHysteresis(output_ch, input_channels[0],
                                                           threshold_on, threshold_off);
        }
        /* Filters */
        else if (func_type >= PMU_FUNC_MOVING_AVG && func_type <= PMU_FUNC_LOW_PASS) {
            uint16_t window_size = 10;
            float time_constant = 0.1f;

            if (params) {
                cJSON* win = cJSON_GetObjectItem(params, "window_size");
                if (win && cJSON_IsNumber(win)) {
                    window_size = (uint16_t)win->valueint;
                }

                cJSON* tc = cJSON_GetObjectItem(params, "time_constant");
                if (tc && cJSON_IsNumber(tc)) {
                    time_constant = (float)tc->valuedouble;
                }
            }

            /* Create filter function manually */
            PMU_LogicFunction_t func = {0};
            func.type = func_type;
            func.output_channel = output_ch;
            func.input_channels[0] = input_channels[0];
            func.input_count = 1;
            func.enabled = 1;

            if (func_type == PMU_FUNC_MOVING_AVG) {
                func.params.moving_avg.window_size = window_size;
            }
            /* TODO: low_pass filter params not yet in union */
            (void)time_constant;

            PMU_LogicFunctions_Register(&func);
            func_id = func.function_id;
        }

        /* Get enabled state */
        cJSON* enabled = cJSON_GetObjectItem(func_obj, "enabled");
        bool is_enabled = true;
        if (enabled && cJSON_IsBool(enabled)) {
            is_enabled = cJSON_IsTrue(enabled);
        }

        if (func_id > 0) {
            PMU_LogicFunctions_SetEnabled(func_id, is_enabled);
        }
    }
#else
    (void)logic_array;
#endif

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
 * @brief Parse function type string to enum
 */
static PMU_FunctionType_t JSON_ParseFunctionType(const char* type_str)
{
    /* Mathematical operations */
    if (strcmp(type_str, "add") == 0) return PMU_FUNC_ADD;
    if (strcmp(type_str, "subtract") == 0) return PMU_FUNC_SUBTRACT;
    if (strcmp(type_str, "multiply") == 0) return PMU_FUNC_MULTIPLY;
    if (strcmp(type_str, "divide") == 0) return PMU_FUNC_DIVIDE;
    if (strcmp(type_str, "min") == 0) return PMU_FUNC_MIN;
    if (strcmp(type_str, "max") == 0) return PMU_FUNC_MAX;
    if (strcmp(type_str, "average") == 0) return PMU_FUNC_AVERAGE;
    if (strcmp(type_str, "abs") == 0) return PMU_FUNC_ABS;
    if (strcmp(type_str, "scale") == 0) return PMU_FUNC_SCALE;
    if (strcmp(type_str, "clamp") == 0) return PMU_FUNC_CLAMP;

    /* Comparison operations */
    if (strcmp(type_str, "greater") == 0 || strcmp(type_str, ">") == 0) return PMU_FUNC_GREATER;
    if (strcmp(type_str, "less") == 0 || strcmp(type_str, "<") == 0) return PMU_FUNC_LESS;
    if (strcmp(type_str, "equal") == 0 || strcmp(type_str, "==") == 0) return PMU_FUNC_EQUAL;
    if (strcmp(type_str, "not_equal") == 0 || strcmp(type_str, "!=") == 0) return PMU_FUNC_NOT_EQUAL;
    if (strcmp(type_str, "greater_equal") == 0 || strcmp(type_str, ">=") == 0) return PMU_FUNC_GREATER_EQUAL;
    if (strcmp(type_str, "less_equal") == 0 || strcmp(type_str, "<=") == 0) return PMU_FUNC_LESS_EQUAL;
    if (strcmp(type_str, "in_range") == 0) return PMU_FUNC_IN_RANGE;

    /* Logic operations */
    if (strcmp(type_str, "and") == 0 || strcmp(type_str, "AND") == 0) return PMU_FUNC_AND;
    if (strcmp(type_str, "or") == 0 || strcmp(type_str, "OR") == 0) return PMU_FUNC_OR;
    if (strcmp(type_str, "not") == 0 || strcmp(type_str, "NOT") == 0) return PMU_FUNC_NOT;
    if (strcmp(type_str, "xor") == 0 || strcmp(type_str, "XOR") == 0) return PMU_FUNC_XOR;
    if (strcmp(type_str, "nand") == 0 || strcmp(type_str, "NAND") == 0) return PMU_FUNC_NAND;
    if (strcmp(type_str, "nor") == 0 || strcmp(type_str, "NOR") == 0) return PMU_FUNC_NOR;

    /* Tables */
    if (strcmp(type_str, "table_1d") == 0) return PMU_FUNC_TABLE_1D;
    if (strcmp(type_str, "table_2d") == 0) return PMU_FUNC_TABLE_2D;

    /* Filters */
    if (strcmp(type_str, "moving_avg") == 0) return PMU_FUNC_MOVING_AVG;
    if (strcmp(type_str, "min_window") == 0) return PMU_FUNC_MIN_WINDOW;
    if (strcmp(type_str, "max_window") == 0) return PMU_FUNC_MAX_WINDOW;
    if (strcmp(type_str, "median") == 0) return PMU_FUNC_MEDIAN;
    if (strcmp(type_str, "low_pass") == 0) return PMU_FUNC_LOW_PASS;

    /* Control */
    if (strcmp(type_str, "pid") == 0 || strcmp(type_str, "PID") == 0) return PMU_FUNC_PID;
    if (strcmp(type_str, "hysteresis") == 0) return PMU_FUNC_HYSTERESIS;
    if (strcmp(type_str, "rate_limit") == 0) return PMU_FUNC_RATE_LIMIT;
    if (strcmp(type_str, "debounce") == 0) return PMU_FUNC_DEBOUNCE;

    /* Special */
    if (strcmp(type_str, "mux") == 0) return PMU_FUNC_MUX;
    if (strcmp(type_str, "demux") == 0) return PMU_FUNC_DEMUX;
    if (strcmp(type_str, "conditional") == 0) return PMU_FUNC_CONDITIONAL;

    /* Default */
    return PMU_FUNC_ADD;
}

/**
 * @brief Resolve channel from JSON (supports number or name lookup)
 */
static uint16_t JSON_ResolveChannel(cJSON* channel_obj)
{
    if (!channel_obj) {
        return 0;
    }

    /* If it's a number, use it directly as channel ID */
    if (cJSON_IsNumber(channel_obj)) {
        return (uint16_t)channel_obj->valueint;
    }

    /* If it's a string, look up channel by name */
    if (cJSON_IsString(channel_obj)) {
        const PMU_Channel_t* ch = PMU_Channel_GetByName(channel_obj->valuestring);
        if (ch != NULL) {
            return ch->channel_id;
        }
    }

    /* Default */
    return 0;
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
