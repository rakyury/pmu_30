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
#include "pmu_lin.h"
#include "pmu_logic.h"
#include "pmu_logic_functions.h"
#include "pmu_channel.h"
#include "pmu_can_stream.h"
#include "pmu_pid.h"
#include "pmu_blinkmarine.h"
#include "pmu_wifi.h"
#include "pmu_bluetooth.h"
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
#include <stdio.h>

/* Enable cJSON for real hardware and emulator, but not unit tests */
#if !defined(UNIT_TEST) || defined(PMU_EMULATOR)
#include "cJSON.h"
#define JSON_PARSING_ENABLED 1
#endif

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/
#define JSON_PARSE_BUFFER_SIZE    (64 * 1024)  /* 64KB buffer for JSON parsing */

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static char last_error[PMU_JSON_MAX_ERROR_LEN] = {0};
static uint32_t load_start_time = 0;

/* Storage for input configurations (persistent for PMU_ADC_SetConfig) */
static PMU_InputConfig_t input_config_storage[PMU30_NUM_ADC_INPUTS];

/* Storage for power output configurations (persistent for runtime control) */
static PMU_PowerOutputConfig_t power_output_storage[PMU30_NUM_OUTPUTS];
static uint8_t power_output_count = 0;

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
static bool JSON_ParsePID(cJSON* channel_obj);
static bool JSON_ParseBlinkMarineKeypad(cJSON* channel_obj);
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
static bool JSON_ParseSettings(cJSON* settings_obj, PMU_JSON_LoadStats_t* stats);
static bool JSON_ParseCanMessages(cJSON* messages_array, PMU_JSON_LoadStats_t* stats);
static bool JSON_ParseLinFrameObjects(cJSON* frames_array, PMU_JSON_LoadStats_t* stats);
static bool JSON_ParseLinRx(cJSON* channel);
static bool JSON_ParseLinTx(cJSON* channel);
static bool JSON_ParseLuaScripts(cJSON* scripts_array, PMU_JSON_LoadStats_t* stats);
static PMU_LegacyInputType_t JSON_ParseInputType(const char* type_str);
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
#ifndef JSON_PARSING_ENABLED
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

    bool is_v3 = (strcmp(version->valuestring, PMU_JSON_VERSION_3_0) == 0);
    bool is_v2 = (strcmp(version->valuestring, PMU_JSON_VERSION_2_0) == 0);
    bool is_v1 = (strcmp(version->valuestring, PMU_JSON_VERSION_1_0) == 0);

    if (!is_v1 && !is_v2 && !is_v3) {
        JSON_SetError("Unsupported version: %s (expected %s, %s, or %s)",
                      version->valuestring, PMU_JSON_VERSION_1_0, PMU_JSON_VERSION_2_0, PMU_JSON_VERSION_3_0);
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
     * v2.0/v3.0 Format: Unified channels array
     * ======================================== */
    if (is_v2 || is_v3) {
        cJSON* channels = cJSON_GetObjectItem(root, "channels");
        if (channels && cJSON_IsArray(channels)) {
            if (!JSON_ParseChannels(channels, &local_stats)) {
                cJSON_Delete(root);
                return PMU_JSON_ERROR_VALIDATION;
            }
        }

        /* Parse CAN messages (Level 1 - v3.0) */
        cJSON* can_messages = cJSON_GetObjectItem(root, "can_messages");
        if (can_messages && cJSON_IsArray(can_messages)) {
            if (!JSON_ParseCanMessages(can_messages, &local_stats)) {
                cJSON_Delete(root);
                return PMU_JSON_ERROR_VALIDATION;
            }
        }

        /* Parse LIN frame objects (Level 1 - v3.0) */
        cJSON* lin_frame_objects = cJSON_GetObjectItem(root, "lin_frame_objects");
        if (lin_frame_objects && cJSON_IsArray(lin_frame_objects)) {
            if (!JSON_ParseLinFrameObjects(lin_frame_objects, &local_stats)) {
                cJSON_Delete(root);
                return PMU_JSON_ERROR_VALIDATION;
            }
        }

        /* Parse Lua scripts */
        cJSON* lua_scripts = cJSON_GetObjectItem(root, "lua_scripts");
        if (lua_scripts && cJSON_IsArray(lua_scripts)) {
            if (!JSON_ParseLuaScripts(lua_scripts, &local_stats)) {
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

    /* Parse settings (v3.0 - includes standard_can_stream, can_a, can_b, power, safety) */
    cJSON* settings = cJSON_GetObjectItem(root, "settings");
    if (settings && cJSON_IsObject(settings)) {
        if (!JSON_ParseSettings(settings, &local_stats)) {
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
#ifndef JSON_PARSING_ENABLED
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
#ifndef JSON_PARSING_ENABLED
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
    /* Clear power output storage */
    PMU_PowerOutput_ClearConfig();
    return HAL_OK;
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Parse inputs array from JSON
 */
static bool JSON_ParseInputs(cJSON* inputs_array)
{
#ifdef JSON_PARSING_ENABLED
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

        PMU_LegacyInputType_t input_type = JSON_ParseInputType(type->valuestring);

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
#ifdef JSON_PARSING_ENABLED
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
#ifdef JSON_PARSING_ENABLED
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
 * @brief Parse system settings from JSON
 *
 * Handles: control_frequency_hz, logic_frequency_hz, can1_baudrate, can2_baudrate
 */
static bool JSON_ParseSystem(cJSON* system_obj)
{
#ifdef JSON_PARSING_ENABLED
    /* Parse and log system settings */
    int control_freq = JSON_GetInt(system_obj, "control_frequency_hz", 1000);
    int logic_freq = JSON_GetInt(system_obj, "logic_frequency_hz", 500);
    int can1_baud = JSON_GetInt(system_obj, "can1_baudrate", 500000);
    int can2_baud = JSON_GetInt(system_obj, "can2_baudrate", 500000);

    printf("[JSON] System: control=%dHz, logic=%dHz, CAN1=%d, CAN2=%d\n",
           control_freq, logic_freq, can1_baud, can2_baud);

    /* TODO: Apply these settings to hardware when infrastructure is ready */

#else
    (void)system_obj;
#endif

    return true;
}

/**
 * @brief Parse settings section from JSON (v3.0)
 *
 * Handles: can_a, can_b, standard_can_stream, power, safety, system
 */
static bool JSON_ParseSettings(cJSON* settings_obj, PMU_JSON_LoadStats_t* stats)
{
#ifdef JSON_PARSING_ENABLED
    /* Parse Standard CAN Stream configuration */
    cJSON* stream = cJSON_GetObjectItem(settings_obj, "standard_can_stream");
    if (stream && cJSON_IsObject(stream)) {
        PMU_CanStreamConfig_t stream_config = {0};

        stream_config.enabled = JSON_GetBool(stream, "enabled", false);
        stream_config.can_bus = (uint8_t)JSON_GetInt(stream, "can_bus", 1);

        /* Parse base_id (can be hex string "0x600" or integer 1536) */
        cJSON* base_id = cJSON_GetObjectItem(stream, "base_id");
        if (base_id) {
            if (cJSON_IsString(base_id)) {
                /* Parse hex string like "0x600" */
                stream_config.base_id = (uint32_t)strtoul(base_id->valuestring, NULL, 0);
            } else if (cJSON_IsNumber(base_id)) {
                stream_config.base_id = (uint32_t)base_id->valueint;
            } else {
                stream_config.base_id = PMU_CAN_STREAM_DEFAULT_BASE_ID;
            }
        } else {
            stream_config.base_id = PMU_CAN_STREAM_DEFAULT_BASE_ID;
        }

        stream_config.is_extended = JSON_GetBool(stream, "is_extended", false);
        stream_config.include_extended = JSON_GetBool(stream, "include_extended", true);

        /* Apply configuration */
        PMU_CanStream_Configure(&stream_config);
        PMU_CanStream_SetEnabled(stream_config.enabled);

        if (stats) {
            stats->stream_enabled = stream_config.enabled;
        }
    }

    /* Parse CAN A bus configuration */
    cJSON* can_a = cJSON_GetObjectItem(settings_obj, "can_a");
    if (can_a && cJSON_IsObject(can_a)) {
        PMU_CAN_BusConfig_t bus_config = {0};

        bus_config.bitrate = (uint32_t)JSON_GetInt(can_a, "bitrate", 500000);
        bus_config.fd_bitrate = (uint32_t)JSON_GetInt(can_a, "fd_bitrate", 2000000);
        bus_config.enable_fd = JSON_GetBool(can_a, "fd_enabled", false) ? 1 : 0;
        bus_config.enable_termination = JSON_GetBool(can_a, "termination", true) ? 1 : 0;

        PMU_CAN_ConfigureBus(PMU_CAN_BUS_1, &bus_config);
    }

    /* Parse CAN B bus configuration */
    cJSON* can_b = cJSON_GetObjectItem(settings_obj, "can_b");
    if (can_b && cJSON_IsObject(can_b)) {
        PMU_CAN_BusConfig_t bus_config = {0};

        bus_config.bitrate = (uint32_t)JSON_GetInt(can_b, "bitrate", 500000);
        bus_config.fd_bitrate = (uint32_t)JSON_GetInt(can_b, "fd_bitrate", 2000000);
        bus_config.enable_fd = JSON_GetBool(can_b, "fd_enabled", false) ? 1 : 0;
        bus_config.enable_termination = JSON_GetBool(can_b, "termination", true) ? 1 : 0;

        PMU_CAN_ConfigureBus(PMU_CAN_BUS_2, &bus_config);
    }

    /* Parse WiFi configuration */
    cJSON* wifi = cJSON_GetObjectItem(settings_obj, "wifi");
    if (wifi && cJSON_IsObject(wifi)) {
        PMU_WiFi_Config_t wifi_config;
        PMU_WiFi_SetDefaultAPConfig(&wifi_config);

        wifi_config.enabled = JSON_GetBool(wifi, "enabled", false);

        /* Mode: "ap", "sta", "ap_sta" */
        const char* mode_str = JSON_GetString(wifi, "mode", "ap");
        if (strcmp(mode_str, "sta") == 0) {
            wifi_config.mode = PMU_WIFI_MODE_STA;
        } else if (strcmp(mode_str, "ap_sta") == 0) {
            wifi_config.mode = PMU_WIFI_MODE_AP_STA;
        } else {
            wifi_config.mode = PMU_WIFI_MODE_AP;
        }

        /* Hostname */
        const char* hostname = JSON_GetString(wifi, "hostname", "pmu30");
        strncpy(wifi_config.hostname, hostname, PMU_WIFI_HOSTNAME_MAX_LEN);

        /* AP configuration */
        cJSON* ap = cJSON_GetObjectItem(wifi, "ap");
        if (ap && cJSON_IsObject(ap)) {
            const char* ssid = JSON_GetString(ap, "ssid", PMU_WIFI_DEFAULT_AP_SSID);
            const char* pass = JSON_GetString(ap, "password", PMU_WIFI_DEFAULT_AP_PASS);
            strncpy(wifi_config.ap.ssid, ssid, PMU_WIFI_SSID_MAX_LEN);
            strncpy(wifi_config.ap.password, pass, PMU_WIFI_PASS_MAX_LEN);
            wifi_config.ap.channel = (uint8_t)JSON_GetInt(ap, "channel", 6);
            wifi_config.ap.hidden = JSON_GetBool(ap, "hidden", false) ? 1 : 0;
            wifi_config.ap.max_clients = (uint8_t)JSON_GetInt(ap, "max_clients", 4);

            const char* sec = JSON_GetString(ap, "security", "wpa2");
            if (strcmp(sec, "open") == 0) wifi_config.ap.security = PMU_WIFI_SEC_OPEN;
            else if (strcmp(sec, "wpa") == 0) wifi_config.ap.security = PMU_WIFI_SEC_WPA;
            else if (strcmp(sec, "wpa3") == 0) wifi_config.ap.security = PMU_WIFI_SEC_WPA3;
            else wifi_config.ap.security = PMU_WIFI_SEC_WPA2;
        }

        /* STA configuration */
        cJSON* sta = cJSON_GetObjectItem(wifi, "sta");
        if (sta && cJSON_IsObject(sta)) {
            const char* ssid = JSON_GetString(sta, "ssid", "");
            const char* pass = JSON_GetString(sta, "password", "");
            strncpy(wifi_config.sta.ssid, ssid, PMU_WIFI_SSID_MAX_LEN);
            strncpy(wifi_config.sta.password, pass, PMU_WIFI_PASS_MAX_LEN);
            wifi_config.sta.auto_reconnect = JSON_GetBool(sta, "auto_reconnect", true) ? 1 : 0;
            wifi_config.sta.dhcp = JSON_GetBool(sta, "dhcp", true) ? 1 : 0;

            /* Static IP (if DHCP disabled) */
            if (!wifi_config.sta.dhcp) {
                const char* ip = JSON_GetString(sta, "ip", "192.168.1.100");
                const char* gw = JSON_GetString(sta, "gateway", "192.168.1.1");
                const char* nm = JSON_GetString(sta, "netmask", "255.255.255.0");
                /* TODO: Parse IP strings to uint32_t */
                (void)ip; (void)gw; (void)nm;
            }
        }

        /* Web server configuration */
        cJSON* web = cJSON_GetObjectItem(wifi, "web");
        if (web && cJSON_IsObject(web)) {
            wifi_config.web.enabled = JSON_GetBool(web, "enabled", true);
            wifi_config.web.http_port = (uint16_t)JSON_GetInt(web, "http_port", 80);
            wifi_config.web.ws_port = (uint16_t)JSON_GetInt(web, "ws_port", 81);
            wifi_config.web.auth_enabled = JSON_GetBool(web, "auth_enabled", false) ? 1 : 0;

            if (wifi_config.web.auth_enabled) {
                const char* user = JSON_GetString(web, "username", "admin");
                const char* pass = JSON_GetString(web, "password", "");
                strncpy(wifi_config.web.username, user, 31);
                strncpy(wifi_config.web.password, pass, 31);
            }
        }

        PMU_WiFi_ApplyConfig(&wifi_config);
        printf("[JSON] WiFi configured: mode=%s enabled=%d\n",
               mode_str, wifi_config.enabled);
    }

    /* Parse Bluetooth configuration */
    cJSON* bt = cJSON_GetObjectItem(settings_obj, "bluetooth");
    if (bt && cJSON_IsObject(bt)) {
        PMU_BT_Config_t bt_config;
        PMU_BT_SetDefaultConfig(&bt_config);

        bt_config.enabled = JSON_GetBool(bt, "enabled", false);

        /* Mode: "classic", "ble", "dual" */
        const char* bt_mode_str = JSON_GetString(bt, "mode", "ble");
        if (strcmp(bt_mode_str, "classic") == 0) {
            bt_config.mode = PMU_BT_MODE_CLASSIC;
        } else if (strcmp(bt_mode_str, "dual") == 0) {
            bt_config.mode = PMU_BT_MODE_DUAL;
        } else {
            bt_config.mode = PMU_BT_MODE_BLE;
        }

        /* Classic configuration */
        cJSON* classic = cJSON_GetObjectItem(bt, "classic");
        if (classic && cJSON_IsObject(classic)) {
            const char* name = JSON_GetString(classic, "device_name", PMU_BT_DEFAULT_DEVICE_NAME);
            const char* pin = JSON_GetString(classic, "pin", PMU_BT_DEFAULT_PIN);
            strncpy(bt_config.classic.device_name, name, sizeof(bt_config.classic.device_name) - 1);
            strncpy(bt_config.classic.pin, pin, sizeof(bt_config.classic.pin) - 1);
            bt_config.classic.discoverable = JSON_GetBool(classic, "discoverable", true) ? 1 : 0;
            bt_config.classic.connectable = JSON_GetBool(classic, "connectable", true) ? 1 : 0;
            bt_config.classic.max_connections = (uint8_t)JSON_GetInt(classic, "max_connections", 1);

            const char* sec = JSON_GetString(classic, "security", "auth");
            if (strcmp(sec, "none") == 0) bt_config.classic.security = PMU_BT_SEC_NONE;
            else if (strcmp(sec, "pair") == 0) bt_config.classic.security = PMU_BT_SEC_PAIR_ONLY;
            else if (strcmp(sec, "secure") == 0) bt_config.classic.security = PMU_BT_SEC_SECURE;
            else bt_config.classic.security = PMU_BT_SEC_AUTH;
        }

        /* BLE configuration */
        cJSON* ble = cJSON_GetObjectItem(bt, "ble");
        if (ble && cJSON_IsObject(ble)) {
            const char* name = JSON_GetString(ble, "device_name", PMU_BT_DEFAULT_DEVICE_NAME);
            strncpy(bt_config.ble.device_name, name, sizeof(bt_config.ble.device_name) - 1);
            bt_config.ble.advertising_enabled = JSON_GetBool(ble, "advertising", true) ? 1 : 0;
            bt_config.ble.adv_interval_ms = (uint16_t)JSON_GetInt(ble, "adv_interval_ms", 100);
            bt_config.ble.conn_interval_min = (uint16_t)JSON_GetInt(ble, "conn_interval_min", 20);
            bt_config.ble.conn_interval_max = (uint16_t)JSON_GetInt(ble, "conn_interval_max", 40);
            bt_config.ble.supervision_timeout = (uint16_t)JSON_GetInt(ble, "supervision_timeout", 400);
            bt_config.ble.require_bonding = JSON_GetBool(ble, "require_bonding", false) ? 1 : 0;

            const char* sec = JSON_GetString(ble, "security", "pair");
            if (strcmp(sec, "none") == 0) bt_config.ble.security = PMU_BT_SEC_NONE;
            else if (strcmp(sec, "auth") == 0) bt_config.ble.security = PMU_BT_SEC_AUTH;
            else if (strcmp(sec, "secure") == 0) bt_config.ble.security = PMU_BT_SEC_SECURE;
            else bt_config.ble.security = PMU_BT_SEC_PAIR_ONLY;
        }

        /* Telemetry service configuration */
        cJSON* telem = cJSON_GetObjectItem(bt, "telemetry");
        if (telem && cJSON_IsObject(telem)) {
            bt_config.telemetry.enabled = JSON_GetBool(telem, "enabled", true);
            bt_config.telemetry.update_rate_ms = (uint16_t)JSON_GetInt(telem, "update_rate_ms", 100);
            bt_config.telemetry.notify_changes = JSON_GetBool(telem, "notify_changes", false) ? 1 : 0;
        }

        PMU_BT_ApplyConfig(&bt_config);
        printf("[JSON] Bluetooth configured: mode=%s enabled=%d\n",
               bt_mode_str, bt_config.enabled);
    }

    /* TODO: Parse power settings */
    /* TODO: Parse safety settings */

#else
    (void)settings_obj;
    (void)stats;
#endif

    return true;
}

/**
 * @brief Parse CAN messages array (Level 1 - v3.0)
 *
 * CAN messages define the base message properties that CAN RX channels reference.
 */
static bool JSON_ParseCanMessages(cJSON* messages_array, PMU_JSON_LoadStats_t* stats)
{
#ifdef JSON_PARSING_ENABLED
    int count = cJSON_GetArraySize(messages_array);

    for (int i = 0; i < count && i < PMU_MAX_CAN_MESSAGES; i++) {
        cJSON* msg = cJSON_GetArrayItem(messages_array, i);
        if (!msg || !cJSON_IsObject(msg)) {
            continue;
        }

        PMU_CanMessageConfig_t config = {0};

        /* Parse message ID and name */
        const char* id = JSON_GetString(msg, "id", "");
        strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

        const char* name = JSON_GetString(msg, "name", "");
        strncpy(config.name, name, sizeof(config.name) - 1);

        /* Parse CAN bus and ID */
        config.can_bus = (uint8_t)JSON_GetInt(msg, "can_bus", 1);

        /* Parse base_id (can be hex string or integer) */
        cJSON* base_id = cJSON_GetObjectItem(msg, "base_id");
        if (base_id) {
            if (cJSON_IsString(base_id)) {
                config.base_id = (uint32_t)strtoul(base_id->valuestring, NULL, 0);
            } else if (cJSON_IsNumber(base_id)) {
                config.base_id = (uint32_t)base_id->valueint;
            }
        }

        config.is_extended = JSON_GetBool(msg, "is_extended", false);

        /* Parse message type */
        const char* msg_type = JSON_GetString(msg, "message_type", "normal");
        if (strcmp(msg_type, "compound") == 0 || strcmp(msg_type, "multiplexed") == 0) {
            config.message_type = PMU_CAN_MSG_TYPE_COMPOUND;
        } else {
            config.message_type = PMU_CAN_MSG_TYPE_NORMAL;
        }

        config.frame_count = (uint8_t)JSON_GetInt(msg, "frame_count", 1);
        config.dlc = (uint8_t)JSON_GetInt(msg, "dlc", 8);
        config.timeout_ms = (uint16_t)JSON_GetInt(msg, "timeout_ms", 500);
        config.enabled = JSON_GetBool(msg, "enabled", true);

        /* TODO: Register message with CAN subsystem */
        /* PMU_CAN_RegisterMessage(&config); */

        printf("[JSON] CAN message '%s': bus=%d, id=0x%X, type=%s\n",
               config.id, config.can_bus, (unsigned)config.base_id, msg_type);

        if (stats) {
            stats->can_messages++;
        }
    }

#else
    (void)messages_array;
    (void)stats;
#endif

    return true;
}

/**
 * @brief Parse LIN frame objects array (Level 1 - v3.0)
 *
 * LIN frame objects define the base frame properties that LIN RX/TX channels reference.
 * Similar to CAN messages, this is the two-level architecture for LIN.
 *
 * JSON format:
 * {
 *   "id": "frame_motor_control",
 *   "name": "Motor Control Frame",
 *   "bus": 0,
 *   "frame_id": 16,
 *   "frame_type": "unconditional",
 *   "direction": "subscribe",
 *   "checksum": "enhanced",
 *   "length": 8,
 *   "timeout_ms": 100,
 *   "enabled": true
 * }
 */
static bool JSON_ParseLinFrameObjects(cJSON* frames_array, PMU_JSON_LoadStats_t* stats)
{
#ifdef JSON_PARSING_ENABLED
    int count = cJSON_GetArraySize(frames_array);

    for (int i = 0; i < count && i < PMU_LIN_MAX_FRAME_OBJECTS; i++) {
        cJSON* frame = cJSON_GetArrayItem(frames_array, i);
        if (!frame || !cJSON_IsObject(frame)) {
            continue;
        }

        PMU_LIN_FrameObject_t config = {0};

        /* Parse frame ID and name */
        const char* id = JSON_GetString(frame, "id", "");
        strncpy(config.id, id, PMU_LIN_ID_LEN - 1);

        const char* name = JSON_GetString(frame, "name", "");
        strncpy(config.name, name, PMU_LIN_ID_LEN - 1);

        /* Parse LIN bus (1 or 2) */
        int bus_val = JSON_GetInt(frame, "bus", 1);
        config.bus = (bus_val >= 2) ? PMU_LIN_BUS_2 : PMU_LIN_BUS_1;

        /* Parse frame ID (0-63) */
        config.frame_id = (uint8_t)JSON_GetInt(frame, "frame_id", 0) & 0x3F;

        /* Parse frame type */
        const char* frame_type = JSON_GetString(frame, "frame_type", "unconditional");
        if (strcmp(frame_type, "unconditional") == 0) {
            config.frame_type = PMU_LIN_FRAME_TYPE_UNCONDITIONAL;
        } else if (strcmp(frame_type, "event_triggered") == 0) {
            config.frame_type = PMU_LIN_FRAME_TYPE_EVENT_TRIGGERED;
        } else if (strcmp(frame_type, "sporadic") == 0) {
            config.frame_type = PMU_LIN_FRAME_TYPE_SPORADIC;
        } else if (strcmp(frame_type, "diagnostic") == 0) {
            config.frame_type = PMU_LIN_FRAME_TYPE_DIAGNOSTIC;
        } else {
            config.frame_type = PMU_LIN_FRAME_TYPE_UNCONDITIONAL;
        }

        /* Parse direction */
        const char* direction = JSON_GetString(frame, "direction", "subscribe");
        if (strcmp(direction, "publish") == 0) {
            config.direction = PMU_LIN_DIR_PUBLISH;
        } else {
            config.direction = PMU_LIN_DIR_SUBSCRIBE;
        }

        /* Parse checksum type */
        const char* checksum = JSON_GetString(frame, "checksum", "enhanced");
        if (strcmp(checksum, "classic") == 0) {
            config.checksum = PMU_LIN_CHECKSUM_CLASSIC;
        } else {
            config.checksum = PMU_LIN_CHECKSUM_ENHANCED;
        }

        /* Parse other properties */
        config.length = (uint8_t)JSON_GetInt(frame, "length", 8);
        if (config.length > 8) config.length = 8;

        config.timeout_ms = (uint16_t)JSON_GetInt(frame, "timeout_ms", 100);
        config.enabled = JSON_GetBool(frame, "enabled", true);

        /* Parse default data if provided */
        cJSON* default_data = cJSON_GetObjectItem(frame, "default_data");
        if (default_data && cJSON_IsArray(default_data)) {
            int data_count = cJSON_GetArraySize(default_data);
            for (int j = 0; j < data_count && j < 8; j++) {
                cJSON* byte_val = cJSON_GetArrayItem(default_data, j);
                if (byte_val && cJSON_IsNumber(byte_val)) {
                    config.data[j] = (uint8_t)byte_val->valueint;
                }
            }
        }

        /* Register frame object with LIN subsystem */
        if (PMU_LIN_AddFrameObject(&config) == HAL_OK) {
            printf("[JSON] LIN frame '%s': bus=%d, id=0x%02X, dir=%s, type=%s\n",
                   config.id, config.bus, config.frame_id,
                   direction, frame_type);

            if (stats) {
                stats->lin_frame_objects++;
            }
        } else {
            printf("[JSON] Failed to add LIN frame '%s'\n", config.id);
        }
    }

#else
    (void)frames_array;
    (void)stats;
#endif

    return true;
}

/**
 * @brief Parse LIN RX channel (Level 2 - v3.0)
 *
 * LIN RX channels extract signals from LIN frame objects.
 *
 * JSON format:
 * {
 *   "id": "lin_motor_speed",
 *   "name": "Motor Speed",
 *   "type": "lin_rx",
 *   "frame_ref": "frame_motor_control",
 *   "data_type": "unsigned",
 *   "start_bit": 0,
 *   "bit_length": 16,
 *   "byte_order": "little",
 *   "multiplier": 0.1,
 *   "divider": 1.0,
 *   "offset": 0.0,
 *   "default_value": 0.0,
 *   "timeout_behavior": "hold",
 *   "enabled": true
 * }
 */
static bool JSON_ParseLinRx(cJSON* channel)
{
#ifdef JSON_PARSING_ENABLED
    const char* id = JSON_GetString(channel, "id", "");
    const char* frame_ref = JSON_GetString(channel, "frame_ref", "");

    PMU_LIN_Input_t input = {0};

    strncpy(input.id, id, PMU_LIN_ID_LEN - 1);
    strncpy(input.frame_ref, frame_ref, PMU_LIN_ID_LEN - 1);

    /* Parse data type */
    const char* data_type = JSON_GetString(channel, "data_type", "unsigned");
    if (strcmp(data_type, "signed") == 0) {
        input.data_type = PMU_LIN_DATA_TYPE_SIGNED;
    } else if (strcmp(data_type, "boolean") == 0 || strcmp(data_type, "bool") == 0) {
        input.data_type = PMU_LIN_DATA_TYPE_BOOL;
    } else {
        input.data_type = PMU_LIN_DATA_TYPE_UNSIGNED;
    }

    /* Parse bit position and length */
    input.start_bit = (uint8_t)JSON_GetInt(channel, "start_bit", 0);
    input.bit_length = (uint8_t)JSON_GetInt(channel, "bit_length", 8);

    /* Parse byte order */
    const char* byte_order = JSON_GetString(channel, "byte_order", "little");
    input.byte_order = (strcmp(byte_order, "big") == 0) ? 1 : 0;

    /* Parse scaling */
    input.multiplier = JSON_GetFloat(channel, "multiplier", 1.0f);
    input.divider = JSON_GetFloat(channel, "divider", 1.0f);
    input.offset = JSON_GetFloat(channel, "offset", 0.0f);
    input.default_value = JSON_GetFloat(channel, "default_value", 0.0f);

    /* Parse timeout behavior */
    const char* timeout_beh = JSON_GetString(channel, "timeout_behavior", "hold");
    if (strcmp(timeout_beh, "zero") == 0) {
        input.timeout_behavior = PMU_LIN_TIMEOUT_SET_ZERO;
    } else if (strcmp(timeout_beh, "default") == 0) {
        input.timeout_behavior = PMU_LIN_TIMEOUT_USE_DEFAULT;
    } else {
        input.timeout_behavior = PMU_LIN_TIMEOUT_HOLD_LAST;
    }

    /* Register input with LIN subsystem */
    if (PMU_LIN_AddInput(&input) == HAL_OK) {
        printf("[JSON] LIN RX '%s' -> frame='%s', bits=%d:%d, scale=%.3f/%.3f+%.3f\n",
               id, frame_ref, input.start_bit, input.bit_length,
               (double)input.multiplier, (double)input.divider, (double)input.offset);
        return true;
    }

    printf("[JSON] Failed to add LIN RX '%s'\n", id);
    return false;

#else
    (void)channel;
    return true;
#endif
}

/**
 * @brief Parse LIN TX channel (Level 2 - v3.0)
 *
 * LIN TX channels pack signals into LIN frame objects for transmission.
 *
 * JSON format:
 * {
 *   "id": "lin_motor_command",
 *   "name": "Motor Command",
 *   "type": "lin_tx",
 *   "frame_ref": "frame_motor_control",
 *   "source": "channel_ref",
 *   "data_type": "unsigned",
 *   "start_bit": 0,
 *   "bit_length": 16,
 *   "byte_order": "little",
 *   "multiplier": 1.0,
 *   "divider": 0.1,
 *   "offset": 0.0,
 *   "enabled": true
 * }
 */
static bool JSON_ParseLinTx(cJSON* channel)
{
#ifdef JSON_PARSING_ENABLED
    const char* id = JSON_GetString(channel, "id", "");
    const char* frame_ref = JSON_GetString(channel, "frame_ref", "");
    const char* source = JSON_GetString(channel, "source", "");

    PMU_LIN_Output_t output = {0};

    strncpy(output.id, id, PMU_LIN_ID_LEN - 1);
    strncpy(output.frame_ref, frame_ref, PMU_LIN_ID_LEN - 1);
    strncpy(output.source_channel, source, PMU_LIN_ID_LEN - 1);

    /* Parse data type */
    const char* data_type = JSON_GetString(channel, "data_type", "unsigned");
    if (strcmp(data_type, "signed") == 0) {
        output.data_type = PMU_LIN_DATA_TYPE_SIGNED;
    } else if (strcmp(data_type, "boolean") == 0 || strcmp(data_type, "bool") == 0) {
        output.data_type = PMU_LIN_DATA_TYPE_BOOL;
    } else {
        output.data_type = PMU_LIN_DATA_TYPE_UNSIGNED;
    }

    /* Parse bit position and length */
    output.start_bit = (uint8_t)JSON_GetInt(channel, "start_bit", 0);
    output.bit_length = (uint8_t)JSON_GetInt(channel, "bit_length", 8);

    /* Parse byte order */
    const char* byte_order = JSON_GetString(channel, "byte_order", "little");
    output.byte_order = (strcmp(byte_order, "big") == 0) ? 1 : 0;

    /* Parse scaling (inverse of RX for TX) */
    output.multiplier = JSON_GetFloat(channel, "multiplier", 1.0f);
    output.divider = JSON_GetFloat(channel, "divider", 1.0f);
    output.offset = JSON_GetFloat(channel, "offset", 0.0f);

    /* Register output with LIN subsystem */
    if (PMU_LIN_AddOutput(&output) == HAL_OK) {
        printf("[JSON] LIN TX '%s' <- src='%s' -> frame='%s', bits=%d:%d\n",
               id, source, frame_ref, output.start_bit, output.bit_length);
        return true;
    }

    printf("[JSON] Failed to add LIN TX '%s'\n", id);
    return false;

#else
    (void)channel;
    return true;
#endif
}

/**
 * @brief Parse Lua scripts array
 */
static bool JSON_ParseLuaScripts(cJSON* scripts_array, PMU_JSON_LoadStats_t* stats)
{
#ifdef JSON_PARSING_ENABLED
    int count = cJSON_GetArraySize(scripts_array);

    for (int i = 0; i < count; i++) {
        cJSON* script = cJSON_GetArrayItem(scripts_array, i);
        if (!script || !cJSON_IsObject(script)) {
            continue;
        }

        const char* name = JSON_GetString(script, "name", "unnamed");
        const char* code = JSON_GetString(script, "code", "");
        bool enabled = JSON_GetBool(script, "enabled", true);
        bool auto_run = JSON_GetBool(script, "auto_run", false);

        if (strlen(code) > 0 && enabled) {
#ifdef PMU_LUA_ENABLED
            /* Load script into Lua engine */
            HAL_StatusTypeDef result = PMU_Lua_LoadScript(name, code, strlen(code));
            if (result == HAL_OK) {
                printf("[JSON] Lua script '%s' loaded (%zu bytes)\n", name, strlen(code));

                /* Enable auto-run if specified */
                if (auto_run) {
                    PMU_Lua_EnableScript(name, true);
                }

                if (stats) {
                    stats->lua_scripts++;
                }
            } else {
                printf("[JSON] Failed to load Lua script '%s'\n", name);
            }
#else
            /* Lua not available - just log */
            printf("[JSON] Lua script '%s' (%zu bytes, auto_run=%d) - Lua disabled\n",
                   name, strlen(code), auto_run);
            if (stats) {
                stats->lua_scripts++;
            }
#endif
        }
    }

#else
    (void)scripts_array;
    (void)stats;
#endif

    return true;
}

/**
 * @brief Parse input type string to enum (legacy format)
 */
static PMU_LegacyInputType_t JSON_ParseInputType(const char* type_str)
{
    if (strcmp(type_str, "Switch Active Low") == 0) {
        return PMU_LEGACY_INPUT_SWITCH_ACTIVE_LOW;
    } else if (strcmp(type_str, "Switch Active High") == 0) {
        return PMU_LEGACY_INPUT_SWITCH_ACTIVE_HIGH;
    } else if (strcmp(type_str, "Rotary Switch") == 0) {
        return PMU_LEGACY_INPUT_ROTARY_SWITCH;
    } else if (strcmp(type_str, "Linear Analog") == 0) {
        return PMU_LEGACY_INPUT_LINEAR_ANALOG;
    } else if (strcmp(type_str, "Calibrated Analog") == 0) {
        return PMU_LEGACY_INPUT_CALIBRATED_ANALOG;
    } else if (strcmp(type_str, "Frequency Input") == 0) {
        return PMU_LEGACY_INPUT_FREQUENCY;
    }

    return PMU_LEGACY_INPUT_LINEAR_ANALOG;  /* Default */
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
    if (strcmp(type_str, "lin_rx") == 0) return PMU_CHANNEL_TYPE_LIN_RX;
    if (strcmp(type_str, "lin_tx") == 0) return PMU_CHANNEL_TYPE_LIN_TX;
    if (strcmp(type_str, "logic") == 0) return PMU_CHANNEL_TYPE_LOGIC;
    if (strcmp(type_str, "number") == 0) return PMU_CHANNEL_TYPE_NUMBER;
    if (strcmp(type_str, "table_2d") == 0) return PMU_CHANNEL_TYPE_TABLE_2D;
    if (strcmp(type_str, "table_3d") == 0) return PMU_CHANNEL_TYPE_TABLE_3D;
    if (strcmp(type_str, "switch") == 0) return PMU_CHANNEL_TYPE_SWITCH;
    if (strcmp(type_str, "timer") == 0) return PMU_CHANNEL_TYPE_TIMER;
    if (strcmp(type_str, "filter") == 0) return PMU_CHANNEL_TYPE_FILTER;
    if (strcmp(type_str, "enum") == 0) return PMU_CHANNEL_TYPE_ENUM;
    if (strcmp(type_str, "lua_script") == 0) return PMU_CHANNEL_TYPE_LUA_SCRIPT;
    if (strcmp(type_str, "pid") == 0) return PMU_CHANNEL_TYPE_PID;
    if (strcmp(type_str, "blinkmarine_keypad") == 0) return PMU_CHANNEL_TYPE_BLINKMARINE_KEYPAD;
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
#ifdef JSON_PARSING_ENABLED
    int count = cJSON_GetArraySize(channels_array);

    for (int i = 0; i < count; i++) {
        cJSON* channel = cJSON_GetArrayItem(channels_array, i);
        if (!channel || !cJSON_IsObject(channel)) {
            continue;
        }

        /* Get channel ID and type */
        /* Try "id" first, then "name" as fallback */
        const char* id = JSON_GetString(channel, "id", "");
        if (strlen(id) == 0) {
            id = JSON_GetString(channel, "name", "");
        }

        /* Support both "channel_type" (v2.0) and "gpio_type" (legacy) */
        const char* channel_type_str = JSON_GetString(channel, "channel_type", "");
        if (strlen(channel_type_str) == 0) {
            channel_type_str = JSON_GetString(channel, "gpio_type", "");  /* Fallback */
        }

        if (strlen(channel_type_str) == 0) {
            JSON_SetError("Channel %d: missing channel_type", i);
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

            case PMU_CHANNEL_TYPE_LIN_RX:
                success = JSON_ParseLinRx(channel);
                if (success && stats) stats->lin_rx++;
                break;

            case PMU_CHANNEL_TYPE_LIN_TX:
                success = JSON_ParseLinTx(channel);
                if (success && stats) stats->lin_tx++;
                break;

            case PMU_CHANNEL_TYPE_PID:
                success = JSON_ParsePID(channel);
                if (success && stats) stats->pid_controllers++;
                break;

            case PMU_CHANNEL_TYPE_BLINKMARINE_KEYPAD:
                success = JSON_ParseBlinkMarineKeypad(channel);
                if (success && stats) stats->blinkmarine_keypads++;
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
#ifdef JSON_PARSING_ENABLED
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
#ifdef JSON_PARSING_ENABLED
    PMU_AnalogInputConfig_t config = {0};

    /* Copy ID */
    const char* id = JSON_GetString(channel_obj, "id", "");
    printf("[CONFIG] Parsing analog input: id='%s'\n", id);
    fflush(stdout);
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

    /* Register the analog input with ADC system */
    uint8_t pin = config.input_pin;
    if (pin < PMU30_NUM_ADC_INPUTS) {
        uint8_t adc_channel = pin;  /* input_pin is already 0-based */

        /* Create PMU_InputConfig_t from PMU_AnalogInputConfig_t */
        PMU_InputConfig_t* adc_config = &input_config_storage[adc_channel];
        memset(adc_config, 0, sizeof(PMU_InputConfig_t));

        adc_config->channel = pin + 1;  /* Display as 1-based (A1, A2, ...) */
        strncpy(adc_config->name, config.id, sizeof(adc_config->name) - 1);

        /* Map subtype to legacy input type */
        switch (config.subtype) {
            case PMU_AI_SUBTYPE_SWITCH_ACTIVE_LOW:
                adc_config->type = PMU_LEGACY_INPUT_SWITCH_ACTIVE_LOW;
                break;
            case PMU_AI_SUBTYPE_SWITCH_ACTIVE_HIGH:
                adc_config->type = PMU_LEGACY_INPUT_SWITCH_ACTIVE_HIGH;
                break;
            case PMU_AI_SUBTYPE_ROTARY_SWITCH:
                adc_config->type = PMU_LEGACY_INPUT_ROTARY_SWITCH;
                break;
            case PMU_AI_SUBTYPE_LINEAR:
                adc_config->type = PMU_LEGACY_INPUT_LINEAR_ANALOG;
                break;
            case PMU_AI_SUBTYPE_CALIBRATED:
                adc_config->type = PMU_LEGACY_INPUT_CALIBRATED_ANALOG;
                break;
            default:
                adc_config->type = PMU_LEGACY_INPUT_LINEAR_ANALOG;
                break;
        }

        /* Copy threshold values */
        adc_config->threshold_high_mv = config.threshold_high_mv;
        adc_config->threshold_low_mv = config.threshold_low_mv;
        adc_config->debounce_ms = config.debounce_ms;

        /* Copy scaling values */
        if (config.max_voltage_mv > config.min_voltage_mv) {
            float voltage_range = (config.max_voltage_mv - config.min_voltage_mv) / 1000.0f;
            float value_range = config.max_value - config.min_value;
            adc_config->multiplier = value_range / voltage_range;
            adc_config->offset = config.min_value - (config.min_voltage_mv / 1000.0f) * adc_config->multiplier;
        } else {
            adc_config->multiplier = 1.0f;
            adc_config->offset = 0.0f;
        }

        adc_config->decimal_places = config.decimal_places;
        adc_config->filter_samples = 4;  /* Default filter size */

        /* Copy calibration points for calibrated analog inputs */
        adc_config->calibration_count = config.calibration_count;
        for (int i = 0; i < config.calibration_count && i < PMU_MAX_CALIBRATION_POINTS; i++) {
            adc_config->calibration[i].voltage = config.calibration[i].voltage;
            adc_config->calibration[i].value = config.calibration[i].value;
        }

        /* Configure ADC channel */
        HAL_StatusTypeDef adc_result = PMU_ADC_SetConfig(adc_channel, adc_config);
        printf("[CONFIG] ADC ch%d: type=%d thresh_hi=%dmV thresh_lo=%dmV result=%d\n",
               adc_channel, adc_config->type, adc_config->threshold_high_mv,
               adc_config->threshold_low_mv, adc_result);
        fflush(stdout);

        /* Register channel with channel system */
        PMU_Channel_t channel = {0};
        channel.channel_id = adc_channel;  /* Input channels use 0-19 */
        strncpy(channel.name, config.id, sizeof(channel.name) - 1);

        /* Determine hw_class based on subtype */
        switch (config.subtype) {
            case PMU_AI_SUBTYPE_SWITCH_ACTIVE_LOW:
            case PMU_AI_SUBTYPE_SWITCH_ACTIVE_HIGH:
                channel.hw_class = PMU_CHANNEL_CLASS_INPUT_SWITCH;
                channel.min_value = 0;
                channel.max_value = 1;
                break;
            case PMU_AI_SUBTYPE_ROTARY_SWITCH:
                channel.hw_class = PMU_CHANNEL_CLASS_INPUT_ROTARY;
                channel.min_value = 0;
                channel.max_value = config.positions > 0 ? config.positions - 1 : 7;
                break;
            default:
                channel.hw_class = PMU_CHANNEL_CLASS_INPUT_ANALOG;
                channel.min_value = (int32_t)config.min_value;
                channel.max_value = (int32_t)config.max_value;
                break;
        }

        channel.physical_index = adc_channel;
        channel.flags = PMU_CHANNEL_FLAG_ENABLED;

        HAL_StatusTypeDef ch_result = PMU_Channel_Register(&channel);
        printf("[CONFIG] Channel ch%d '%s' class=0x%02X result=%d\n",
               adc_channel, config.id, channel.hw_class, ch_result);
        fflush(stdout);
    }
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse power output channel
 *
 * Supports both schema format and dialog format:
 * Schema: output_pins, source_channel, pwm_enabled, duty_fixed
 * Dialog: pins, control_function, pwm.enabled, pwm.duty_value
 */
static bool JSON_ParsePowerOutput(cJSON* channel_obj)
{
#ifdef JSON_PARSING_ENABLED
    PMU_PowerOutputConfig_t config = {0};

    const char* id = JSON_GetString(channel_obj, "id", "");
    if (strlen(id) == 0) {
        /* Try to use name as id if id is not present */
        id = JSON_GetString(channel_obj, "name", "unnamed");
    }
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    /* Parse output pins array - try "output_pins" first, then "pins" */
    cJSON* pins = cJSON_GetObjectItem(channel_obj, "output_pins");
    if (!pins || !cJSON_IsArray(pins)) {
        pins = cJSON_GetObjectItem(channel_obj, "pins");
    }
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

    /* Source channel - try "source_channel" then "control_function" */
    const char* source = JSON_GetString(channel_obj, "source_channel", "");
    if (strlen(source) == 0) {
        source = JSON_GetString(channel_obj, "control_function", "");
    }
    strncpy(config.source_channel, source, PMU_CHANNEL_ID_LEN - 1);

    /* PWM settings - try flat format first, then nested "pwm" object */
    cJSON* pwm_obj = cJSON_GetObjectItem(channel_obj, "pwm");
    if (pwm_obj && cJSON_IsObject(pwm_obj)) {
        /* Dialog nested format: pwm.enabled, pwm.frequency, pwm.duty_value */
        config.pwm_enabled = JSON_GetBool(pwm_obj, "enabled", false);
        config.pwm_frequency_hz = (uint16_t)JSON_GetInt(pwm_obj, "frequency", 1000);
        config.duty_fixed = JSON_GetFloat(pwm_obj, "duty_value", 100.0f);
        config.soft_start_ms = JSON_GetBool(pwm_obj, "soft_start_enabled", false) ?
                               (uint16_t)JSON_GetInt(pwm_obj, "soft_start_duration_ms", 0) : 0;
        const char* duty_ch = JSON_GetString(pwm_obj, "duty_function", "");
        strncpy(config.duty_channel, duty_ch, PMU_CHANNEL_ID_LEN - 1);
    } else {
        /* Schema flat format: pwm_enabled, pwm_frequency_hz, duty_fixed */
        config.pwm_enabled = JSON_GetBool(channel_obj, "pwm_enabled", false);
        config.pwm_frequency_hz = (uint16_t)JSON_GetInt(channel_obj, "pwm_frequency_hz", 1000);
        config.duty_fixed = JSON_GetFloat(channel_obj, "duty_fixed", 100.0f);
        config.soft_start_ms = (uint16_t)JSON_GetInt(channel_obj, "soft_start_ms", 0);
        const char* duty_ch = JSON_GetString(channel_obj, "duty_channel", "");
        strncpy(config.duty_channel, duty_ch, PMU_CHANNEL_ID_LEN - 1);
    }

    /* Protection settings - try flat format first, then nested "protection" object */
    cJSON* prot_obj = cJSON_GetObjectItem(channel_obj, "protection");
    if (prot_obj && cJSON_IsObject(prot_obj)) {
        /* Dialog nested format */
        config.current_limit_a = JSON_GetFloat(prot_obj, "current_limit", 25.0f);
        config.inrush_current_a = JSON_GetFloat(prot_obj, "inrush_current", 50.0f);
        config.inrush_time_ms = (uint16_t)JSON_GetInt(prot_obj, "inrush_time_ms", 100);
        config.retry_count = (uint8_t)JSON_GetInt(prot_obj, "retry_count", 3);
        config.retry_forever = JSON_GetBool(prot_obj, "retry_forever", false);
    } else {
        /* Schema flat format */
        config.current_limit_a = JSON_GetFloat(channel_obj, "current_limit_a", 25.0f);
        config.inrush_current_a = JSON_GetFloat(channel_obj, "inrush_current_a", 50.0f);
        config.inrush_time_ms = (uint16_t)JSON_GetInt(channel_obj, "inrush_time_ms", 100);
        config.retry_count = (uint8_t)JSON_GetInt(channel_obj, "retry_count", 3);
        config.retry_forever = JSON_GetBool(channel_obj, "retry_forever", false);
    }

    /* Check if output is enabled (for "always on" mode) */
    bool enabled = JSON_GetBool(channel_obj, "enabled", false);

    /* Apply configuration to PROFET channels */
    for (int i = 0; i < config.output_pin_count; i++) {
        uint8_t pin = config.output_pins[i];
        if (pin < 30) {
            /* Set channel state based on enabled flag */
            if (!enabled) {
                /* Disabled channel - turn OFF and skip PWM setup */
                PMU_PROFET_SetState(pin, 0);
                continue;
            }

            /* Channel is enabled */
            /* When source_channel is empty, it means "always on" mode */
            if (strlen(config.source_channel) == 0) {
                PMU_PROFET_SetState(pin, 1);
            }

            /* Set PWM duty cycle (only for enabled channels) */
            if (config.pwm_enabled) {
                /* duty_fixed is 0-100%, convert to 0-1000 per-mille */
                uint16_t duty_permille = (uint16_t)(config.duty_fixed * 10.0f);
                PMU_PROFET_SetPWM(pin, duty_permille);
            } else {
                /* No PWM, full duty (100%) */
                PMU_PROFET_SetPWM(pin, 1000);
            }
        }
    }

    /* Print debug info */
    printf("[JSON] Power output '%s': pins=[", id);
    for (int i = 0; i < config.output_pin_count; i++) {
        printf("%d%s", config.output_pins[i], (i < config.output_pin_count - 1) ? "," : "");
    }
    printf("], enabled=%d, source='%s', pwm=%d, duty=%.1f%%\n",
           enabled, config.source_channel, config.pwm_enabled, config.duty_fixed);

    /* Store configuration for runtime control */
    if (power_output_count < PMU30_NUM_OUTPUTS) {
        memcpy(&power_output_storage[power_output_count], &config, sizeof(PMU_PowerOutputConfig_t));
        power_output_count++;
    }

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
#ifdef JSON_PARSING_ENABLED
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
#ifdef JSON_PARSING_ENABLED
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
#ifdef JSON_PARSING_ENABLED
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
#ifdef JSON_PARSING_ENABLED
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
#ifdef JSON_PARSING_ENABLED
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
#ifdef JSON_PARSING_ENABLED
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
#ifdef JSON_PARSING_ENABLED
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
#ifdef JSON_PARSING_ENABLED
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
#ifdef JSON_PARSING_ENABLED
    PMU_CanRxConfig_t config = {0};

    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    config.can_bus = (uint8_t)JSON_GetInt(channel_obj, "can_bus", 1);
    config.message_id = (uint32_t)JSON_GetInt(channel_obj, "message_id", 0);
    config.is_extended = JSON_GetBool(channel_obj, "is_extended", false);
    config.start_bit = (uint8_t)JSON_GetInt(channel_obj, "start_bit", 0);
    config.bit_length = (uint8_t)JSON_GetInt(channel_obj, "length", 8);

    const char* order = JSON_GetString(channel_obj, "byte_order", "little_endian");
    config.little_endian = (strcmp(order, "little_endian") == 0);

    const char* vtype = JSON_GetString(channel_obj, "value_type", "unsigned");
    if (strcmp(vtype, "float") == 0) {
        config.data_type = PMU_CAN_DATA_TYPE_FLOAT;
    } else if (strcmp(vtype, "signed") == 0) {
        config.data_type = PMU_CAN_DATA_TYPE_SIGNED;
    } else {
        config.data_type = PMU_CAN_DATA_TYPE_UNSIGNED;
    }

    config.multiplier = JSON_GetFloat(channel_obj, "factor", 1.0f);
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
#ifdef JSON_PARSING_ENABLED
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

/**
 * @brief Parse PID controller channel
 */
static bool JSON_ParsePID(cJSON* channel_obj)
{
#ifdef JSON_PARSING_ENABLED
    PMU_PIDConfig_t config = {0};

    /* Copy ID */
    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    /* Input/Output channels */
    const char* setpoint_ch = JSON_GetString(channel_obj, "setpoint_channel", "");
    strncpy(config.setpoint_channel, setpoint_ch, PMU_CHANNEL_ID_LEN - 1);

    const char* process_ch = JSON_GetString(channel_obj, "process_channel", "");
    strncpy(config.process_channel, process_ch, PMU_CHANNEL_ID_LEN - 1);

    const char* output_ch = JSON_GetString(channel_obj, "output_channel", "");
    strncpy(config.output_channel, output_ch, PMU_CHANNEL_ID_LEN - 1);

    /* PID parameters */
    config.kp = JSON_GetFloat(channel_obj, "kp", 1.0f);
    config.ki = JSON_GetFloat(channel_obj, "ki", 0.0f);
    config.kd = JSON_GetFloat(channel_obj, "kd", 0.0f);

    /* Setpoint value (used if setpoint_channel is empty) */
    config.setpoint_value = JSON_GetFloat(channel_obj, "setpoint_value", 0.0f);

    /* Output limits */
    config.output_min = JSON_GetFloat(channel_obj, "output_min", 0.0f);
    config.output_max = JSON_GetFloat(channel_obj, "output_max", 100.0f);

    /* Advanced settings */
    config.sample_time_ms = (uint16_t)JSON_GetInt(channel_obj, "sample_time_ms", 100);
    config.anti_windup = JSON_GetBool(channel_obj, "anti_windup", true);
    config.derivative_filter = JSON_GetBool(channel_obj, "derivative_filter", true);
    config.derivative_filter_coeff = JSON_GetFloat(channel_obj, "derivative_filter_coeff", 0.1f);

    /* Control options */
    config.enabled = JSON_GetBool(channel_obj, "enabled", true);
    config.reversed = JSON_GetBool(channel_obj, "reversed", false);

    /* Register PID controller */
    HAL_StatusTypeDef status = PMU_PID_AddController(&config);
    if (status != HAL_OK) {
        JSON_SetError("Failed to add PID controller '%s'", id);
        return false;
    }

    printf("[JSON] Parsed PID: %s Kp=%.2f Ki=%.2f Kd=%.2f\n",
           id, config.kp, config.ki, config.kd);
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse BlinkMarine keypad channel
 */
static bool JSON_ParseBlinkMarineKeypad(cJSON* channel_obj)
{
#ifdef JSON_PARSING_ENABLED
    PMU_BlinkMarine_Keypad_t keypad = {0};

    /* Copy ID and name */
    const char* id = JSON_GetString(channel_obj, "id", "");
    strncpy(keypad.id, id, sizeof(keypad.id) - 1);

    const char* name = JSON_GetString(channel_obj, "name", id);
    strncpy(keypad.name, name, sizeof(keypad.name) - 1);

    /* Keypad type */
    const char* type_str = JSON_GetString(channel_obj, "keypad_type", "2x6");
    if (strcmp(type_str, "2x8") == 0) {
        keypad.type = PMU_BLINKMARINE_2X8;
    } else {
        keypad.type = PMU_BLINKMARINE_2X6;
    }

    /* CAN configuration */
    keypad.can_bus = (PMU_CAN_Bus_t)JSON_GetInt(channel_obj, "can_bus", 1);
    keypad.rx_base_id = (uint32_t)JSON_GetInt(channel_obj, "rx_base_id", PMU_BM_DEFAULT_RX_ID);
    keypad.tx_base_id = (uint32_t)JSON_GetInt(channel_obj, "tx_base_id", PMU_BM_DEFAULT_TX_ID);
    keypad.enabled = JSON_GetBool(channel_obj, "enabled", true);

    /* LED mode - default for all buttons */
    int led_mode = JSON_GetInt(channel_obj, "led_mode", 0);

    /* Parse buttons configuration */
    cJSON* buttons_array = cJSON_GetObjectItem(channel_obj, "buttons");
    if (buttons_array && cJSON_IsArray(buttons_array)) {
        int button_count = cJSON_GetArraySize(buttons_array);
        uint8_t max_buttons = PMU_BlinkMarine_GetButtonCount(keypad.type);

        for (int i = 0; i < button_count && i < max_buttons; i++) {
            cJSON* button = cJSON_GetArrayItem(buttons_array, i);
            if (!button || !cJSON_IsObject(button)) continue;

            PMU_BM_ButtonConfig_t* btn = &keypad.buttons[i];

            /* Button channel mapping */
            const char* channel_id = JSON_GetString(button, "channel_id", "");
            strncpy(btn->channel_id, channel_id, sizeof(btn->channel_id) - 1);
            btn->enabled = JSON_GetBool(button, "enabled", true);

            /* LED colors */
            btn->led_on_color = (PMU_BM_LedColor_t)JSON_GetInt(button, "led_on_color", PMU_BM_LED_GREEN);
            btn->led_off_color = (PMU_BM_LedColor_t)JSON_GetInt(button, "led_off_color", PMU_BM_LED_OFF);
            btn->led_mode = (PMU_BM_LedCtrlMode_t)led_mode;

            /* Button-specific LED mode override */
            if (cJSON_HasObjectItem(button, "led_mode")) {
                btn->led_mode = (PMU_BM_LedCtrlMode_t)JSON_GetInt(button, "led_mode", led_mode);
            }
        }
    }

    /* Add keypad */
    HAL_StatusTypeDef status = PMU_BlinkMarine_AddKeypad(&keypad);
    if (status != HAL_OK) {
        JSON_SetError("Failed to add BlinkMarine keypad '%s'", id);
        return false;
    }

    printf("[JSON] Parsed BlinkMarine keypad: %s type=%s CAN%d RX:0x%03X TX:0x%03X\n",
           id, type_str, keypad.can_bus, (unsigned int)keypad.rx_base_id, (unsigned int)keypad.tx_base_id);
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Update power outputs based on their source channels
 * Call this function at 100Hz or faster in the control loop
 */
void PMU_PowerOutput_Update(void)
{
#ifdef JSON_PARSING_ENABLED
    for (uint8_t i = 0; i < power_output_count; i++) {
        PMU_PowerOutputConfig_t* cfg = &power_output_storage[i];

        /* Skip outputs without source_channel (always on or disabled) */
        if (strlen(cfg->source_channel) == 0) {
            continue;
        }

        /* Resolve source channel to value */
        const PMU_Channel_t* source_ch = PMU_Channel_GetByName(cfg->source_channel);
        if (!source_ch) {
            /* Source channel not found - skip */
            continue;
        }

        int32_t source_value = source_ch->value;
        bool output_active = (source_value > 0);

        /* Apply to all configured pins */
        for (int p = 0; p < cfg->output_pin_count; p++) {
            uint8_t pin = cfg->output_pins[p];
            if (pin >= 30) continue;

            /* Skip if manual override is set */
            if (PMU_PROFET_HasManualOverride(pin)) {
                continue;
            }

            if (output_active) {
                if (cfg->pwm_enabled) {
                    /* Use fixed duty or resolve duty_channel */
                    float duty = cfg->duty_fixed;
                    if (strlen(cfg->duty_channel) > 0) {
                        const PMU_Channel_t* duty_ch = PMU_Channel_GetByName(cfg->duty_channel);
                        if (duty_ch) {
                            duty = (float)duty_ch->value / 10.0f; /* Assume 0-1000 -> 0-100% */
                        }
                    }
                    uint16_t duty_permille = (uint16_t)(duty * 10.0f);
                    PMU_PROFET_SetPWM(pin, duty_permille);
                } else {
                    PMU_PROFET_SetState(pin, 1);
                }
            } else {
                PMU_PROFET_SetState(pin, 0);
            }
        }
    }
#endif
}

/**
 * @brief Clear power output storage (call before reloading config)
 */
void PMU_PowerOutput_ClearConfig(void)
{
    memset(power_output_storage, 0, sizeof(power_output_storage));
    power_output_count = 0;
}

/**
 * @brief Get power output configuration count
 */
uint8_t PMU_PowerOutput_GetCount(void)
{
    return power_output_count;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
