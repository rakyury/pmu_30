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
/* v2.0 channel parsing */
static bool JSON_ParseChannels(cJSON* channels_array, PMU_JSON_LoadStats_t* stats);
static bool JSON_ParseDigitalInput(cJSON* channel_obj);
static bool JSON_ParseAnalogInput(cJSON* channel_obj);
static bool JSON_ParsePowerOutput(cJSON* channel_obj);
static bool JSON_ParseLogic(cJSON* channel_obj);
static bool JSON_ParseNumber(cJSON* channel_obj);
static bool JSON_ParseTimer(cJSON* channel_obj);
static bool JSON_ParseFilter(cJSON* channel_obj);
static bool JSON_ParseTable2D(cJSON* channel_obj);
static bool JSON_ParseTable3D(cJSON* channel_obj);
static bool JSON_ParseSwitch(cJSON* channel_obj);
static bool JSON_ParseEnum(cJSON* channel_obj);
static bool JSON_ParseCanRx(cJSON* channel_obj);
static bool JSON_ParseCanTx(cJSON* channel_obj);
static PMU_GPIOType_t JSON_ParseGPIOType(const char* type_str);

/* v1.0 legacy parsing */
static bool JSON_ParseInputs(cJSON* inputs_array);
static bool JSON_ParseOutputs(cJSON* outputs_array);
static bool JSON_ParseHBridges(cJSON* hbridges_array);
static bool JSON_ParseLogicFunctions(cJSON* logic_array);
static bool JSON_ParseVirtualChannels(cJSON* virtual_array);
static bool JSON_ParsePIDControllers(cJSON* pid_array);

/* Common */
static bool JSON_ParseCANBuses(cJSON* can_array);
static bool JSON_ParseSystem(cJSON* system_obj);
static PMU_InputType_t JSON_ParseInputType(const char* type_str);
static PMU_FunctionType_t JSON_ParseFunctionType(const char* type_str);
static uint16_t JSON_ResolveChannel(cJSON* channel_obj);
static void JSON_SetError(const char* format, ...);
static const char* JSON_GetString(cJSON* obj, const char* key, const char* default_val);
static float JSON_GetFloat(cJSON* obj, const char* key, float default_val);
static int JSON_GetInt(cJSON* obj, const char* key, int default_val);
static bool JSON_GetBool(cJSON* obj, const char* key, bool default_val);

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

    bool is_v2 = (strcmp(version->valuestring, PMU_JSON_VERSION_2_0) == 0);
    bool is_v1 = (strcmp(version->valuestring, PMU_JSON_VERSION_1_0) == 0);

    if (!is_v1 && !is_v2) {
        JSON_SetError("Unsupported version: %s (expected %s or %s)",
                      version->valuestring, PMU_JSON_VERSION_1_0, PMU_JSON_VERSION_2_0);
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

    /* ========================================
     * v2.0 Format: Unified channels array
     * ======================================== */
    if (is_v2) {
        cJSON* channels = cJSON_GetObjectItem(root, "channels");
        if (channels && cJSON_IsArray(channels)) {
            if (!JSON_ParseChannels(channels, &local_stats)) {
                cJSON_Delete(root);
                return PMU_JSON_ERROR_VALIDATION;
            }
        }
    }
    /* ========================================
     * v1.0 Format: Legacy separate arrays
     * ======================================== */
    else {
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
    }

    /* Parse CAN buses (common for v1.0 and v2.0) */
    cJSON* can_buses = cJSON_GetObjectItem(root, "can_buses");
    if (can_buses && cJSON_IsArray(can_buses)) {
        if (!JSON_ParseCANBuses(can_buses)) {
            cJSON_Delete(root);
            return PMU_JSON_ERROR_VALIDATION;
        }
        local_stats.can_buses_loaded = cJSON_GetArraySize(can_buses);
    }

    /* Parse system settings (common for v1.0 and v2.0) */
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

/* ============================================================================
 * v2.0 Helper Functions
 * ============================================================================ */

/**
 * @brief Get string from JSON object with default value
 */
static const char* JSON_GetString(cJSON* obj, const char* key, const char* default_val)
{
    cJSON* item = cJSON_GetObjectItem(obj, key);
    if (item && cJSON_IsString(item)) {
        return item->valuestring;
    }
    return default_val;
}

/**
 * @brief Get float from JSON object with default value
 */
static float JSON_GetFloat(cJSON* obj, const char* key, float default_val)
{
    cJSON* item = cJSON_GetObjectItem(obj, key);
    if (item && cJSON_IsNumber(item)) {
        return (float)item->valuedouble;
    }
    return default_val;
}

/**
 * @brief Get int from JSON object with default value
 */
static int JSON_GetInt(cJSON* obj, const char* key, int default_val)
{
    cJSON* item = cJSON_GetObjectItem(obj, key);
    if (item && cJSON_IsNumber(item)) {
        return item->valueint;
    }
    return default_val;
}

/**
 * @brief Get bool from JSON object with default value
 */
static bool JSON_GetBool(cJSON* obj, const char* key, bool default_val)
{
    cJSON* item = cJSON_GetObjectItem(obj, key);
    if (item && cJSON_IsBool(item)) {
        return cJSON_IsTrue(item);
    }
    return default_val;
}

/**
 * @brief Parse channel type string to enum
 */
static PMU_ChannelType_t JSON_ParseChannelType(const char* type_str)
{
    if (strcmp(type_str, "digital_input") == 0) return PMU_CHANNEL_TYPE_DIGITAL_INPUT;
    if (strcmp(type_str, "analog_input") == 0) return PMU_CHANNEL_TYPE_ANALOG_INPUT;
    if (strcmp(type_str, "power_output") == 0) return PMU_CHANNEL_TYPE_POWER_OUTPUT;
    if (strcmp(type_str, "can_rx") == 0) return PMU_CHANNEL_TYPE_CAN_RX;
    if (strcmp(type_str, "can_tx") == 0) return PMU_CHANNEL_TYPE_CAN_TX;
    if (strcmp(type_str, "logic") == 0) return PMU_CHANNEL_TYPE_LOGIC;
    if (strcmp(type_str, "number") == 0) return PMU_CHANNEL_TYPE_NUMBER;
    if (strcmp(type_str, "table_2d") == 0) return PMU_CHANNEL_TYPE_TABLE_2D;
    if (strcmp(type_str, "table_3d") == 0) return PMU_CHANNEL_TYPE_TABLE_3D;
    if (strcmp(type_str, "switch") == 0) return PMU_CHANNEL_TYPE_SWITCH;
    if (strcmp(type_str, "timer") == 0) return PMU_CHANNEL_TYPE_TIMER;
    if (strcmp(type_str, "filter") == 0) return PMU_CHANNEL_TYPE_FILTER;
    if (strcmp(type_str, "enum") == 0) return PMU_CHANNEL_TYPE_ENUM;
    return PMU_CHANNEL_TYPE_COUNT; /* Invalid */
}

/* ============================================================================
 * v2.0 Channel Parsing Functions
 * ============================================================================ */

/**
 * @brief Parse unified channels array (v2.0)
 */
static bool JSON_ParseChannels(cJSON* channels_array, PMU_JSON_LoadStats_t* stats)
{
#ifndef UNIT_TEST
    int count = cJSON_GetArraySize(channels_array);

    for (int i = 0; i < count; i++) {
        cJSON* channel = cJSON_GetArrayItem(channels_array, i);
        if (!channel || !cJSON_IsObject(channel)) {
            continue;
        }

        /* Get channel ID and type */
        const char* id = JSON_GetString(channel, "id", "");
        /* Support both "channel_type" (v2.0) and "gpio_type" (legacy) */
        const char* channel_type_str = JSON_GetString(channel, "channel_type", "");
        if (strlen(channel_type_str) == 0) {
            channel_type_str = JSON_GetString(channel, "gpio_type", "");  /* Fallback */
        }

        if (strlen(id) == 0 || strlen(channel_type_str) == 0) {
            JSON_SetError("Channel %d: missing id or channel_type", i);
            continue;
        }

        PMU_ChannelType_t channel_type = JSON_ParseChannelType(channel_type_str);
        bool success = false;

        /* Dispatch to type-specific parser */
        switch (channel_type) {
            case PMU_CHANNEL_TYPE_DIGITAL_INPUT:
                success = JSON_ParseDigitalInput(channel);
                if (success && stats) stats->digital_inputs++;
                break;

            case PMU_CHANNEL_TYPE_ANALOG_INPUT:
                success = JSON_ParseAnalogInput(channel);
                if (success && stats) stats->analog_inputs++;
                break;

            case PMU_CHANNEL_TYPE_POWER_OUTPUT:
                success = JSON_ParsePowerOutput(channel);
                if (success && stats) stats->power_outputs++;
                break;

            case PMU_CHANNEL_TYPE_LOGIC:
                success = JSON_ParseLogic(channel);
                if (success && stats) stats->logic_functions++;
                break;

            case PMU_CHANNEL_TYPE_NUMBER:
                success = JSON_ParseNumber(channel);
                if (success && stats) stats->numbers++;
                break;

            case PMU_CHANNEL_TYPE_TIMER:
                success = JSON_ParseTimer(channel);
                if (success && stats) stats->timers++;
                break;

            case PMU_CHANNEL_TYPE_FILTER:
                success = JSON_ParseFilter(channel);
                if (success && stats) stats->filters++;
                break;

            case PMU_CHANNEL_TYPE_TABLE_2D:
                success = JSON_ParseTable2D(channel);
                if (success && stats) stats->tables_2d++;
                break;

            case PMU_CHANNEL_TYPE_TABLE_3D:
                success = JSON_ParseTable3D(channel);
                if (success && stats) stats->tables_3d++;
                break;

            case PMU_CHANNEL_TYPE_SWITCH:
                success = JSON_ParseSwitch(channel);
                if (success && stats) stats->switches++;
                break;

            case PMU_CHANNEL_TYPE_ENUM:
                success = JSON_ParseEnum(channel);
                if (success && stats) stats->enums++;
                break;

            case PMU_CHANNEL_TYPE_CAN_RX:
                success = JSON_ParseCanRx(channel);
                if (success && stats) stats->can_rx++;
                break;

            case PMU_CHANNEL_TYPE_CAN_TX:
                success = JSON_ParseCanTx(channel);
                if (success && stats) stats->can_tx++;
                break;

            default:
                JSON_SetError("Channel %s: unknown channel_type '%s'", id, channel_type_str);
                continue;
        }

        if (success && stats) {
            stats->total_channels++;
        }
    }
#else
    (void)channels_array;
    (void)stats;
#endif

    return true;
}

/**
 * @brief Parse digital input channel
 */
static bool JSON_ParseDigitalInput(cJSON* channel_obj)
{
#ifndef UNIT_TEST
    PMU_DigitalInputConfig_t config = {0};

    /* Copy ID */
    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    /* Parse subtype */
    const char* subtype = JSON_GetString(channel_obj, "subtype", "switch_active_low");
    if (strcmp(subtype, "switch_active_low") == 0) config.subtype = PMU_DI_SUBTYPE_SWITCH_ACTIVE_LOW;
    else if (strcmp(subtype, "switch_active_high") == 0) config.subtype = PMU_DI_SUBTYPE_SWITCH_ACTIVE_HIGH;
    else if (strcmp(subtype, "frequency") == 0) config.subtype = PMU_DI_SUBTYPE_FREQUENCY;
    else if (strcmp(subtype, "rpm") == 0) config.subtype = PMU_DI_SUBTYPE_RPM;
    else if (strcmp(subtype, "flex_fuel") == 0) config.subtype = PMU_DI_SUBTYPE_FLEX_FUEL;
    else if (strcmp(subtype, "beacon") == 0) config.subtype = PMU_DI_SUBTYPE_BEACON;
    else if (strcmp(subtype, "puls_oil_sensor") == 0) config.subtype = PMU_DI_SUBTYPE_PULS_OIL_SENSOR;

    /* Common fields */
    config.input_pin = (uint8_t)JSON_GetInt(channel_obj, "input_pin", 0);
    config.enable_pullup = JSON_GetBool(channel_obj, "enable_pullup", false);
    config.threshold_mv = (uint16_t)(JSON_GetFloat(channel_obj, "threshold_voltage", 2.5f) * 1000);
    config.debounce_ms = (uint16_t)JSON_GetInt(channel_obj, "debounce_ms", 50);

    /* Frequency/RPM specific */
    const char* edge = JSON_GetString(channel_obj, "trigger_edge", "rising");
    if (strcmp(edge, "rising") == 0) config.trigger_edge = PMU_EDGE_RISING;
    else if (strcmp(edge, "falling") == 0) config.trigger_edge = PMU_EDGE_FALLING;
    else if (strcmp(edge, "both") == 0) config.trigger_edge = PMU_EDGE_BOTH;

    config.multiplier = JSON_GetFloat(channel_obj, "multiplier", 1.0f);
    config.divider = JSON_GetFloat(channel_obj, "divider", 1.0f);
    config.timeout_ms = (uint16_t)JSON_GetInt(channel_obj, "timeout_ms", 1000);
    config.number_of_teeth = (uint16_t)JSON_GetInt(channel_obj, "number_of_teeth", 1);

    /* TODO: Register digital input channel */
    (void)config;
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse analog input channel
 */
static bool JSON_ParseAnalogInput(cJSON* channel_obj)
{
#ifndef UNIT_TEST
    PMU_AnalogInputConfig_t config = {0};

    /* Copy ID */
    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    /* Parse subtype */
    const char* subtype = JSON_GetString(channel_obj, "subtype", "linear");
    if (strcmp(subtype, "switch_active_low") == 0) config.subtype = PMU_AI_SUBTYPE_SWITCH_ACTIVE_LOW;
    else if (strcmp(subtype, "switch_active_high") == 0) config.subtype = PMU_AI_SUBTYPE_SWITCH_ACTIVE_HIGH;
    else if (strcmp(subtype, "rotary_switch") == 0) config.subtype = PMU_AI_SUBTYPE_ROTARY_SWITCH;
    else if (strcmp(subtype, "linear") == 0) config.subtype = PMU_AI_SUBTYPE_LINEAR;
    else if (strcmp(subtype, "calibrated") == 0) config.subtype = PMU_AI_SUBTYPE_CALIBRATED;

    /* Common fields */
    config.input_pin = (uint8_t)JSON_GetInt(channel_obj, "input_pin", 0);
    config.decimal_places = (uint8_t)JSON_GetInt(channel_obj, "decimal_places", 0);

    /* Parse pullup option */
    const char* pullup = JSON_GetString(channel_obj, "pullup_option", "1m_down");
    if (strcmp(pullup, "none") == 0) config.pullup_option = PMU_PULLUP_NONE;
    else if (strcmp(pullup, "1m_down") == 0) config.pullup_option = PMU_PULLUP_1M_DOWN;
    else if (strcmp(pullup, "10k_up") == 0) config.pullup_option = PMU_PULLUP_10K_UP;
    else if (strcmp(pullup, "10k_down") == 0) config.pullup_option = PMU_PULLUP_10K_DOWN;
    else if (strcmp(pullup, "100k_up") == 0) config.pullup_option = PMU_PULLUP_100K_UP;
    else if (strcmp(pullup, "100k_down") == 0) config.pullup_option = PMU_PULLUP_100K_DOWN;

    /* Switch mode fields */
    config.threshold_high_mv = (uint16_t)(JSON_GetFloat(channel_obj, "threshold_high", 2.5f) * 1000);
    config.threshold_high_time_ms = (uint16_t)JSON_GetInt(channel_obj, "threshold_high_time_ms", 50);
    config.threshold_low_mv = (uint16_t)(JSON_GetFloat(channel_obj, "threshold_low", 1.5f) * 1000);
    config.threshold_low_time_ms = (uint16_t)JSON_GetInt(channel_obj, "threshold_low_time_ms", 50);

    /* Rotary switch fields */
    config.positions = (uint8_t)JSON_GetInt(channel_obj, "positions", 4);
    config.debounce_ms = (uint16_t)JSON_GetInt(channel_obj, "debounce_ms", 50);

    /* Linear mode fields */
    config.min_voltage_mv = (uint16_t)(JSON_GetFloat(channel_obj, "min_voltage", 0.0f) * 1000);
    config.max_voltage_mv = (uint16_t)(JSON_GetFloat(channel_obj, "max_voltage", 5.0f) * 1000);
    config.min_value = JSON_GetFloat(channel_obj, "min_value", 0.0f);
    config.max_value = JSON_GetFloat(channel_obj, "max_value", 100.0f);

    /* Calibration points */
    cJSON* calib_points = cJSON_GetObjectItem(channel_obj, "calibration_points");
    if (calib_points && cJSON_IsArray(calib_points)) {
        int calib_count = cJSON_GetArraySize(calib_points);
        config.calibration_count = (calib_count > PMU_MAX_CALIBRATION_POINTS) ?
                                    PMU_MAX_CALIBRATION_POINTS : (uint8_t)calib_count;

        for (int i = 0; i < config.calibration_count; i++) {
            cJSON* point = cJSON_GetArrayItem(calib_points, i);
            if (point && cJSON_IsObject(point)) {
                config.calibration[i].voltage = JSON_GetFloat(point, "voltage", 0.0f);
                config.calibration[i].value = JSON_GetFloat(point, "value", 0.0f);
            }
        }
    }

    /* TODO: Register analog input channel */
    (void)config;
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse power output channel
 */
static bool JSON_ParsePowerOutput(cJSON* channel_obj)
{
#ifndef UNIT_TEST
    PMU_PowerOutputConfig_t config = {0};

    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    /* Parse output pins array */
    cJSON* pins = cJSON_GetObjectItem(channel_obj, "output_pins");
    if (pins && cJSON_IsArray(pins)) {
        int pin_count = cJSON_GetArraySize(pins);
        config.output_pin_count = (pin_count > PMU_MAX_OUTPUT_PINS) ?
                                   PMU_MAX_OUTPUT_PINS : (uint8_t)pin_count;
        for (int i = 0; i < config.output_pin_count; i++) {
            cJSON* pin = cJSON_GetArrayItem(pins, i);
            if (pin && cJSON_IsNumber(pin)) {
                config.output_pins[i] = (uint8_t)pin->valueint;
            }
        }
    }

    /* Source channel */
    const char* source = JSON_GetString(channel_obj, "source_channel", "");
    strncpy(config.source_channel, source, PMU_CHANNEL_ID_LEN - 1);

    /* PWM settings */
    config.pwm_enabled = JSON_GetBool(channel_obj, "pwm_enabled", false);
    config.pwm_frequency_hz = (uint16_t)JSON_GetInt(channel_obj, "pwm_frequency_hz", 1000);
    const char* duty_ch = JSON_GetString(channel_obj, "duty_channel", "");
    strncpy(config.duty_channel, duty_ch, PMU_CHANNEL_ID_LEN - 1);
    config.duty_fixed = JSON_GetFloat(channel_obj, "duty_fixed", 100.0f);
    config.soft_start_ms = (uint16_t)JSON_GetInt(channel_obj, "soft_start_ms", 0);

    /* Protection settings */
    config.current_limit_a = JSON_GetFloat(channel_obj, "current_limit_a", 25.0f);
    config.inrush_current_a = JSON_GetFloat(channel_obj, "inrush_current_a", 50.0f);
    config.inrush_time_ms = (uint16_t)JSON_GetInt(channel_obj, "inrush_time_ms", 100);
    config.retry_count = (uint8_t)JSON_GetInt(channel_obj, "retry_count", 3);
    config.retry_forever = JSON_GetBool(channel_obj, "retry_forever", false);

    /* TODO: Register power output channel */
    (void)config;
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse logic function channel
 */
static bool JSON_ParseLogic(cJSON* channel_obj)
{
#ifndef UNIT_TEST
    PMU_LogicConfig_t config = {0};

    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    /* Parse operation */
    const char* op = JSON_GetString(channel_obj, "operation", "is_true");
    if (strcmp(op, "is_true") == 0) config.operation = PMU_LOGIC_IS_TRUE;
    else if (strcmp(op, "is_false") == 0) config.operation = PMU_LOGIC_IS_FALSE;
    else if (strcmp(op, "equal") == 0) config.operation = PMU_LOGIC_EQUAL;
    else if (strcmp(op, "not_equal") == 0) config.operation = PMU_LOGIC_NOT_EQUAL;
    else if (strcmp(op, "less") == 0) config.operation = PMU_LOGIC_LESS;
    else if (strcmp(op, "greater") == 0) config.operation = PMU_LOGIC_GREATER;
    else if (strcmp(op, "less_equal") == 0) config.operation = PMU_LOGIC_LESS_EQUAL;
    else if (strcmp(op, "greater_equal") == 0) config.operation = PMU_LOGIC_GREATER_EQUAL;
    else if (strcmp(op, "and") == 0) config.operation = PMU_LOGIC_AND;
    else if (strcmp(op, "or") == 0) config.operation = PMU_LOGIC_OR;
    else if (strcmp(op, "xor") == 0) config.operation = PMU_LOGIC_XOR;
    else if (strcmp(op, "changed") == 0) config.operation = PMU_LOGIC_CHANGED;
    else if (strcmp(op, "hysteresis") == 0) config.operation = PMU_LOGIC_HYSTERESIS;
    else if (strcmp(op, "set_reset_latch") == 0) config.operation = PMU_LOGIC_SET_RESET_LATCH;
    else if (strcmp(op, "toggle") == 0) config.operation = PMU_LOGIC_TOGGLE;
    else if (strcmp(op, "pulse") == 0) config.operation = PMU_LOGIC_PULSE;
    else if (strcmp(op, "flash") == 0) config.operation = PMU_LOGIC_FLASH;

    /* Channel inputs */
    const char* ch = JSON_GetString(channel_obj, "channel", "");
    strncpy(config.channel, ch, PMU_CHANNEL_ID_LEN - 1);
    const char* ch2 = JSON_GetString(channel_obj, "channel_2", "");
    strncpy(config.channel_2, ch2, PMU_CHANNEL_ID_LEN - 1);

    /* Delays */
    config.true_delay_s = JSON_GetFloat(channel_obj, "true_delay_s", 0.0f);
    config.false_delay_s = JSON_GetFloat(channel_obj, "false_delay_s", 0.0f);

    /* Constant for comparison */
    config.constant = JSON_GetFloat(channel_obj, "constant", 0.0f);

    /* Changed operation */
    config.threshold = JSON_GetFloat(channel_obj, "threshold", 0.0f);
    config.time_on_s = JSON_GetFloat(channel_obj, "time_on_s", 0.0f);

    /* Hysteresis */
    const char* pol = JSON_GetString(channel_obj, "polarity", "normal");
    config.polarity = (strcmp(pol, "inverted") == 0) ? PMU_POLARITY_INVERTED : PMU_POLARITY_NORMAL;
    config.upper_value = JSON_GetFloat(channel_obj, "upper_value", 100.0f);
    config.lower_value = JSON_GetFloat(channel_obj, "lower_value", 0.0f);

    /* Set/Reset latch */
    const char* set_ch = JSON_GetString(channel_obj, "set_channel", "");
    strncpy(config.set_channel, set_ch, PMU_CHANNEL_ID_LEN - 1);
    const char* reset_ch = JSON_GetString(channel_obj, "reset_channel", "");
    strncpy(config.reset_channel, reset_ch, PMU_CHANNEL_ID_LEN - 1);
    const char* def = JSON_GetString(channel_obj, "default_state", "off");
    config.default_state = (strcmp(def, "on") == 0) ? PMU_DEFAULT_STATE_ON : PMU_DEFAULT_STATE_OFF;

    /* Toggle/Pulse */
    const char* edge = JSON_GetString(channel_obj, "edge", "rising");
    if (strcmp(edge, "rising") == 0) config.edge = PMU_EDGE_RISING;
    else if (strcmp(edge, "falling") == 0) config.edge = PMU_EDGE_FALLING;
    else if (strcmp(edge, "both") == 0) config.edge = PMU_EDGE_BOTH;

    const char* toggle_ch = JSON_GetString(channel_obj, "toggle_channel", "");
    strncpy(config.toggle_channel, toggle_ch, PMU_CHANNEL_ID_LEN - 1);
    config.pulse_count = (uint8_t)JSON_GetInt(channel_obj, "pulse_count", 1);
    config.retrigger = JSON_GetBool(channel_obj, "retrigger", false);

    /* Flash */
    config.time_off_s = JSON_GetFloat(channel_obj, "time_off_s", 0.5f);

    /* TODO: Register logic channel */
    (void)config;
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse number/math channel
 */
static bool JSON_ParseNumber(cJSON* channel_obj)
{
#ifndef UNIT_TEST
    PMU_NumberConfig_t config = {0};

    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    /* Parse operation */
    const char* op = JSON_GetString(channel_obj, "operation", "constant");
    if (strcmp(op, "constant") == 0) config.operation = PMU_MATH_CONSTANT;
    else if (strcmp(op, "channel") == 0) config.operation = PMU_MATH_CHANNEL;
    else if (strcmp(op, "add") == 0) config.operation = PMU_MATH_ADD;
    else if (strcmp(op, "subtract") == 0) config.operation = PMU_MATH_SUBTRACT;
    else if (strcmp(op, "multiply") == 0) config.operation = PMU_MATH_MULTIPLY;
    else if (strcmp(op, "divide") == 0) config.operation = PMU_MATH_DIVIDE;
    else if (strcmp(op, "modulo") == 0) config.operation = PMU_MATH_MODULO;
    else if (strcmp(op, "min") == 0) config.operation = PMU_MATH_MIN;
    else if (strcmp(op, "max") == 0) config.operation = PMU_MATH_MAX;
    else if (strcmp(op, "clamp") == 0) config.operation = PMU_MATH_CLAMP;
    else if (strcmp(op, "lookup2") == 0) config.operation = PMU_MATH_LOOKUP2;
    else if (strcmp(op, "lookup3") == 0) config.operation = PMU_MATH_LOOKUP3;
    else if (strcmp(op, "lookup4") == 0) config.operation = PMU_MATH_LOOKUP4;
    else if (strcmp(op, "lookup5") == 0) config.operation = PMU_MATH_LOOKUP5;

    /* Inputs array */
    cJSON* inputs = cJSON_GetObjectItem(channel_obj, "inputs");
    if (inputs && cJSON_IsArray(inputs)) {
        int inp_count = cJSON_GetArraySize(inputs);
        config.input_count = (inp_count > PMU_MAX_NUMBER_INPUTS) ?
                              PMU_MAX_NUMBER_INPUTS : (uint8_t)inp_count;
        for (int i = 0; i < config.input_count; i++) {
            cJSON* inp = cJSON_GetArrayItem(inputs, i);
            if (inp && cJSON_IsString(inp)) {
                strncpy(config.inputs[i], inp->valuestring, PMU_CHANNEL_ID_LEN - 1);
            }
        }
    }

    config.constant_value = JSON_GetFloat(channel_obj, "constant_value", 0.0f);
    config.clamp_min = JSON_GetFloat(channel_obj, "clamp_min", 0.0f);
    config.clamp_max = JSON_GetFloat(channel_obj, "clamp_max", 100.0f);
    config.decimal_places = (uint8_t)JSON_GetInt(channel_obj, "decimal_places", 2);

    /* Lookup values */
    cJSON* lookup = cJSON_GetObjectItem(channel_obj, "lookup_values");
    if (lookup && cJSON_IsArray(lookup)) {
        int lookup_count = cJSON_GetArraySize(lookup);
        for (int i = 0; i < lookup_count && i < PMU_MAX_NUMBER_INPUTS; i++) {
            cJSON* val = cJSON_GetArrayItem(lookup, i);
            if (val && cJSON_IsNumber(val)) {
                config.lookup_values[i] = (float)val->valuedouble;
            }
        }
    }

    /* TODO: Register number channel */
    (void)config;
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse timer channel
 */
static bool JSON_ParseTimer(cJSON* channel_obj)
{
#ifndef UNIT_TEST
    PMU_TimerConfig_t config = {0};

    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    const char* start = JSON_GetString(channel_obj, "start_channel", "");
    strncpy(config.start_channel, start, PMU_CHANNEL_ID_LEN - 1);

    const char* start_edge = JSON_GetString(channel_obj, "start_edge", "rising");
    if (strcmp(start_edge, "rising") == 0) config.start_edge = PMU_EDGE_RISING;
    else if (strcmp(start_edge, "falling") == 0) config.start_edge = PMU_EDGE_FALLING;
    else if (strcmp(start_edge, "both") == 0) config.start_edge = PMU_EDGE_BOTH;

    const char* stop = JSON_GetString(channel_obj, "stop_channel", "");
    strncpy(config.stop_channel, stop, PMU_CHANNEL_ID_LEN - 1);

    const char* stop_edge = JSON_GetString(channel_obj, "stop_edge", "rising");
    if (strcmp(stop_edge, "rising") == 0) config.stop_edge = PMU_EDGE_RISING;
    else if (strcmp(stop_edge, "falling") == 0) config.stop_edge = PMU_EDGE_FALLING;
    else if (strcmp(stop_edge, "both") == 0) config.stop_edge = PMU_EDGE_BOTH;

    const char* mode = JSON_GetString(channel_obj, "mode", "count_up");
    config.mode = (strcmp(mode, "count_down") == 0) ? PMU_TIMER_MODE_COUNT_DOWN : PMU_TIMER_MODE_COUNT_UP;

    config.limit_hours = (uint16_t)JSON_GetInt(channel_obj, "limit_hours", 0);
    config.limit_minutes = (uint8_t)JSON_GetInt(channel_obj, "limit_minutes", 0);
    config.limit_seconds = (uint8_t)JSON_GetInt(channel_obj, "limit_seconds", 0);

    /* TODO: Register timer channel */
    (void)config;
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse filter channel
 */
static bool JSON_ParseFilter(cJSON* channel_obj)
{
#ifndef UNIT_TEST
    PMU_FilterConfig_t config = {0};

    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    const char* type = JSON_GetString(channel_obj, "filter_type", "moving_avg");
    if (strcmp(type, "moving_avg") == 0) config.filter_type = PMU_FILTER_MOVING_AVG;
    else if (strcmp(type, "low_pass") == 0) config.filter_type = PMU_FILTER_LOW_PASS;
    else if (strcmp(type, "min_window") == 0) config.filter_type = PMU_FILTER_MIN_WINDOW;
    else if (strcmp(type, "max_window") == 0) config.filter_type = PMU_FILTER_MAX_WINDOW;
    else if (strcmp(type, "median") == 0) config.filter_type = PMU_FILTER_MEDIAN;

    const char* input = JSON_GetString(channel_obj, "input_channel", "");
    strncpy(config.input_channel, input, PMU_CHANNEL_ID_LEN - 1);

    config.window_size = (uint16_t)JSON_GetInt(channel_obj, "window_size", 10);
    config.time_constant = JSON_GetFloat(channel_obj, "time_constant", 0.1f);

    /* TODO: Register filter channel */
    (void)config;
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse 2D table channel
 */
static bool JSON_ParseTable2D(cJSON* channel_obj)
{
#ifndef UNIT_TEST
    PMU_Table2DConfig_t config = {0};

    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    const char* x_ch = JSON_GetString(channel_obj, "x_axis_channel", "");
    strncpy(config.x_axis_channel, x_ch, PMU_CHANNEL_ID_LEN - 1);

    config.x_min = JSON_GetFloat(channel_obj, "x_min", 0.0f);
    config.x_max = JSON_GetFloat(channel_obj, "x_max", 100.0f);
    config.x_step = JSON_GetFloat(channel_obj, "x_step", 10.0f);
    config.decimal_places = (uint8_t)JSON_GetInt(channel_obj, "decimal_places", 0);

    /* X values */
    cJSON* x_vals = cJSON_GetObjectItem(channel_obj, "x_values");
    if (x_vals && cJSON_IsArray(x_vals)) {
        int x_count = cJSON_GetArraySize(x_vals);
        config.x_count = (x_count > PMU_MAX_TABLE_SIZE) ? PMU_MAX_TABLE_SIZE : (uint8_t)x_count;
        for (int i = 0; i < config.x_count; i++) {
            cJSON* val = cJSON_GetArrayItem(x_vals, i);
            if (val && cJSON_IsNumber(val)) {
                config.x_values[i] = (float)val->valuedouble;
            }
        }
    }

    /* Output values */
    cJSON* out_vals = cJSON_GetObjectItem(channel_obj, "output_values");
    if (out_vals && cJSON_IsArray(out_vals)) {
        for (int i = 0; i < config.x_count; i++) {
            cJSON* val = cJSON_GetArrayItem(out_vals, i);
            if (val && cJSON_IsNumber(val)) {
                config.output_values[i] = (float)val->valuedouble;
            }
        }
    }

    /* TODO: Register table 2d channel */
    (void)config;
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse 3D table channel
 */
static bool JSON_ParseTable3D(cJSON* channel_obj)
{
#ifndef UNIT_TEST
    PMU_Table3DConfig_t config = {0};

    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    const char* x_ch = JSON_GetString(channel_obj, "x_axis_channel", "");
    strncpy(config.x_axis_channel, x_ch, PMU_CHANNEL_ID_LEN - 1);

    const char* y_ch = JSON_GetString(channel_obj, "y_axis_channel", "");
    strncpy(config.y_axis_channel, y_ch, PMU_CHANNEL_ID_LEN - 1);

    config.x_min = JSON_GetFloat(channel_obj, "x_min", 0.0f);
    config.x_max = JSON_GetFloat(channel_obj, "x_max", 100.0f);
    config.x_step = JSON_GetFloat(channel_obj, "x_step", 10.0f);
    config.y_min = JSON_GetFloat(channel_obj, "y_min", 0.0f);
    config.y_max = JSON_GetFloat(channel_obj, "y_max", 100.0f);
    config.y_step = JSON_GetFloat(channel_obj, "y_step", 10.0f);
    config.decimal_places = (uint8_t)JSON_GetInt(channel_obj, "decimal_places", 0);

    /* X and Y values */
    cJSON* x_vals = cJSON_GetObjectItem(channel_obj, "x_values");
    if (x_vals && cJSON_IsArray(x_vals)) {
        int x_count = cJSON_GetArraySize(x_vals);
        config.x_count = (x_count > PMU_MAX_TABLE_SIZE) ? PMU_MAX_TABLE_SIZE : (uint8_t)x_count;
        for (int i = 0; i < config.x_count; i++) {
            cJSON* val = cJSON_GetArrayItem(x_vals, i);
            if (val && cJSON_IsNumber(val)) {
                config.x_values[i] = (float)val->valuedouble;
            }
        }
    }

    cJSON* y_vals = cJSON_GetObjectItem(channel_obj, "y_values");
    if (y_vals && cJSON_IsArray(y_vals)) {
        int y_count = cJSON_GetArraySize(y_vals);
        config.y_count = (y_count > PMU_MAX_TABLE_SIZE) ? PMU_MAX_TABLE_SIZE : (uint8_t)y_count;
        for (int i = 0; i < config.y_count; i++) {
            cJSON* val = cJSON_GetArrayItem(y_vals, i);
            if (val && cJSON_IsNumber(val)) {
                config.y_values[i] = (float)val->valuedouble;
            }
        }
    }

    /* Data matrix */
    cJSON* data = cJSON_GetObjectItem(channel_obj, "data");
    if (data && cJSON_IsArray(data)) {
        for (int y = 0; y < config.y_count; y++) {
            cJSON* row = cJSON_GetArrayItem(data, y);
            if (row && cJSON_IsArray(row)) {
                for (int x = 0; x < config.x_count; x++) {
                    cJSON* val = cJSON_GetArrayItem(row, x);
                    if (val && cJSON_IsNumber(val)) {
                        config.data[y][x] = (float)val->valuedouble;
                    }
                }
            }
        }
    }

    /* TODO: Register table 3d channel */
    (void)config;
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse switch channel
 */
static bool JSON_ParseSwitch(cJSON* channel_obj)
{
#ifndef UNIT_TEST
    PMU_SwitchConfig_t config = {0};

    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    const char* type = JSON_GetString(channel_obj, "switch_type", "latching");
    strncpy(config.switch_type, type, sizeof(config.switch_type) - 1);

    const char* up_ch = JSON_GetString(channel_obj, "input_up_channel", "");
    strncpy(config.input_up_channel, up_ch, PMU_CHANNEL_ID_LEN - 1);

    const char* up_edge = JSON_GetString(channel_obj, "input_up_edge", "rising");
    if (strcmp(up_edge, "rising") == 0) config.input_up_edge = PMU_EDGE_RISING;
    else if (strcmp(up_edge, "falling") == 0) config.input_up_edge = PMU_EDGE_FALLING;
    else if (strcmp(up_edge, "both") == 0) config.input_up_edge = PMU_EDGE_BOTH;

    const char* down_ch = JSON_GetString(channel_obj, "input_down_channel", "");
    strncpy(config.input_down_channel, down_ch, PMU_CHANNEL_ID_LEN - 1);

    const char* down_edge = JSON_GetString(channel_obj, "input_down_edge", "rising");
    if (strcmp(down_edge, "rising") == 0) config.input_down_edge = PMU_EDGE_RISING;
    else if (strcmp(down_edge, "falling") == 0) config.input_down_edge = PMU_EDGE_FALLING;
    else if (strcmp(down_edge, "both") == 0) config.input_down_edge = PMU_EDGE_BOTH;

    config.state_first = (int16_t)JSON_GetInt(channel_obj, "state_first", 0);
    config.state_last = (int16_t)JSON_GetInt(channel_obj, "state_last", 10);
    config.state_default = (int16_t)JSON_GetInt(channel_obj, "state_default", 0);

    /* TODO: Register switch channel */
    (void)config;
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse enum channel
 */
static bool JSON_ParseEnum(cJSON* channel_obj)
{
#ifndef UNIT_TEST
    PMU_EnumConfig_t config = {0};

    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    config.is_bitfield = JSON_GetBool(channel_obj, "is_bitfield", false);

    /* Items array */
    cJSON* items = cJSON_GetObjectItem(channel_obj, "items");
    if (items && cJSON_IsArray(items)) {
        int item_count = cJSON_GetArraySize(items);
        config.item_count = (item_count > PMU_MAX_ENUM_ITEMS) ?
                             PMU_MAX_ENUM_ITEMS : (uint8_t)item_count;

        for (int i = 0; i < config.item_count; i++) {
            cJSON* item = cJSON_GetArrayItem(items, i);
            if (item && cJSON_IsObject(item)) {
                config.items[i].value = (int16_t)JSON_GetInt(item, "value", 0);
                const char* text = JSON_GetString(item, "text", "");
                strncpy(config.items[i].text, text, sizeof(config.items[i].text) - 1);

                /* Parse color (hex string like "#FF0000") */
                const char* color = JSON_GetString(item, "color", "#FFFFFF");
                if (color[0] == '#' && strlen(color) >= 7) {
                    config.items[i].color = (uint32_t)strtoul(color + 1, NULL, 16);
                }
            }
        }
    }

    /* TODO: Register enum channel */
    (void)config;
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse CAN RX channel
 */
static bool JSON_ParseCanRx(cJSON* channel_obj)
{
#ifndef UNIT_TEST
    PMU_CanRxConfig_t config = {0};

    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    config.can_bus = (uint8_t)JSON_GetInt(channel_obj, "can_bus", 1);
    config.message_id = (uint32_t)JSON_GetInt(channel_obj, "message_id", 0);
    config.is_extended = JSON_GetBool(channel_obj, "is_extended", false);
    config.start_bit = (uint8_t)JSON_GetInt(channel_obj, "start_bit", 0);
    config.length = (uint8_t)JSON_GetInt(channel_obj, "length", 8);

    const char* order = JSON_GetString(channel_obj, "byte_order", "little_endian");
    config.little_endian = (strcmp(order, "little_endian") == 0);

    const char* vtype = JSON_GetString(channel_obj, "value_type", "unsigned");
    config.is_signed = (strcmp(vtype, "signed") == 0);
    config.is_float = (strcmp(vtype, "float") == 0);

    config.factor = JSON_GetFloat(channel_obj, "factor", 1.0f);
    config.offset = JSON_GetFloat(channel_obj, "offset", 0.0f);
    config.timeout_ms = (uint16_t)JSON_GetInt(channel_obj, "timeout_ms", 1000);

    /* TODO: Register CAN RX channel */
    (void)config;
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse CAN TX channel
 */
static bool JSON_ParseCanTx(cJSON* channel_obj)
{
#ifndef UNIT_TEST
    PMU_CanTxConfig_t config = {0};

    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    config.can_bus = (uint8_t)JSON_GetInt(channel_obj, "can_bus", 1);
    config.message_id = (uint32_t)JSON_GetInt(channel_obj, "message_id", 0);
    config.is_extended = JSON_GetBool(channel_obj, "is_extended", false);
    config.cycle_time_ms = (uint16_t)JSON_GetInt(channel_obj, "cycle_time_ms", 100);

    /* Signals array */
    cJSON* signals = cJSON_GetObjectItem(channel_obj, "signals");
    if (signals && cJSON_IsArray(signals)) {
        int sig_count = cJSON_GetArraySize(signals);
        config.signal_count = (sig_count > PMU_MAX_CAN_TX_SIGNALS) ?
                               PMU_MAX_CAN_TX_SIGNALS : (uint8_t)sig_count;

        for (int i = 0; i < config.signal_count; i++) {
            cJSON* sig = cJSON_GetArrayItem(signals, i);
            if (sig && cJSON_IsObject(sig)) {
                const char* src = JSON_GetString(sig, "source_channel", "");
                strncpy(config.signals[i].source_channel, src, PMU_CHANNEL_ID_LEN - 1);

                config.signals[i].start_bit = (uint8_t)JSON_GetInt(sig, "start_bit", 0);
                config.signals[i].length = (uint8_t)JSON_GetInt(sig, "length", 8);

                const char* order = JSON_GetString(sig, "byte_order", "little_endian");
                config.signals[i].little_endian = (strcmp(order, "little_endian") == 0);

                config.signals[i].factor = JSON_GetFloat(sig, "factor", 1.0f);
                config.signals[i].offset = JSON_GetFloat(sig, "offset", 0.0f);
            }
        }
    }

    /* TODO: Register CAN TX channel */
    (void)config;
#else
    (void)channel_obj;
#endif
    return true;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
