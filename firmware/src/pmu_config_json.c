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
#include "pmu_handler.h"
#include "pmu_channel_ids.h"
#include "pmu_json_helpers.h"
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
static bool config_loading_phase = false;  /* Suppress warnings during initial load */

/* Storage for input configurations (persistent for PMU_ADC_SetConfig) */
static PMU_InputConfig_t input_config_storage[PMU30_NUM_ADC_INPUTS];

/* Storage for power output configurations (persistent for runtime control) */
static PMU_PowerOutputConfig_t power_output_storage[PMU30_NUM_OUTPUTS];
static uint8_t power_output_count = 0;

/* Storage for logic function configurations */
#define PMU_MAX_LOGIC_CHANNELS 64
typedef struct {
    PMU_LogicConfig_t config;
    uint16_t channel_id;          /* Assigned channel ID for telemetry */
    int32_t output_value;         /* Current output value (0 or 1000) */
    int32_t prev_input_value;     /* Previous input for edge detection */
    int32_t prev_input2_value;    /* Previous input2 for edge detection */
    uint32_t delay_start_ms;      /* Delay timer start */
    bool delay_active;            /* Delay timer running */
    bool latch_state;             /* For latching operations */
    uint32_t flash_last_toggle;   /* Last flash toggle time */
    bool flash_state;             /* Current flash state */
} PMU_LogicRuntime_t;
static PMU_LogicRuntime_t logic_storage[PMU_MAX_LOGIC_CHANNELS];
static uint8_t logic_count = 0;

/* Storage for number/math channel configurations */
#define PMU_MAX_NUMBER_CHANNELS 32
typedef struct {
    PMU_NumberConfig_t config;
    uint16_t channel_id;
    int32_t output_value;
} PMU_NumberRuntime_t;
static PMU_NumberRuntime_t number_storage[PMU_MAX_NUMBER_CHANNELS];
static uint8_t number_count = 0;

/* Storage for switch channel configurations */
#define PMU_MAX_SWITCH_CHANNELS 32
typedef struct {
    PMU_SwitchConfig_t config;
    uint16_t channel_id;
    int32_t output_value;
    int16_t current_state;
} PMU_SwitchRuntime_t;
static PMU_SwitchRuntime_t switch_storage[PMU_MAX_SWITCH_CHANNELS];
static uint8_t switch_count = 0;

/* Storage for filter channel configurations */
#define PMU_MAX_FILTER_CHANNELS 32
#define PMU_FILTER_WINDOW_MAX 16
typedef struct {
    PMU_FilterConfig_t config;
    uint16_t channel_id;
    int32_t output_value;
    int32_t window[PMU_FILTER_WINDOW_MAX];
    uint8_t window_index;
    uint8_t window_filled;
    int32_t ema_value;
} PMU_FilterRuntime_t;
static PMU_FilterRuntime_t filter_storage[PMU_MAX_FILTER_CHANNELS];
static uint8_t filter_count = 0;

/* Storage for timer channel configurations */
#define PMU_MAX_TIMER_CHANNELS 16
typedef struct {
    PMU_TimerConfig_t config;
    uint16_t channel_id;        /* Main channel - outputs running state (0/1000) */
    uint16_t elapsed_channel_id; /* Elapsed channel - outputs time in ms */
    int32_t output_value;       /* Current timer value in ms */
    uint32_t start_time_ms;     /* Time when timer started */
    bool running;               /* Timer is running */
    int32_t prev_start_value;   /* Previous start trigger value */
    int32_t prev_stop_value;    /* Previous stop trigger value */
} PMU_TimerRuntime_t;
static PMU_TimerRuntime_t timer_storage[PMU_MAX_TIMER_CHANNELS];
static uint8_t timer_count = 0;

/* Virtual channel ID allocator */
static uint16_t virtual_channel_id_next = PMU_CHANNEL_ID_VIRTUAL_START;

static uint16_t AllocateVirtualChannelID(void) {
    if (virtual_channel_id_next <= PMU_CHANNEL_ID_VIRTUAL_END) {
        return virtual_channel_id_next++;
    }
    return 0;
}

/* Mapping from JSON channel_id to runtime channel_id */
#define PMU_CHANNEL_ID_MAP_SIZE 256
typedef struct {
    uint16_t json_id;
    uint16_t runtime_id;
} PMU_ChannelIdMap_t;
static PMU_ChannelIdMap_t channel_id_map[PMU_CHANNEL_ID_MAP_SIZE];
static uint16_t channel_id_map_count = 0;

static void AddChannelIdMapping(uint16_t json_id, uint16_t runtime_id) {
    if (channel_id_map_count < PMU_CHANNEL_ID_MAP_SIZE) {
        channel_id_map[channel_id_map_count].json_id = json_id;
        channel_id_map[channel_id_map_count].runtime_id = runtime_id;
        channel_id_map_count++;
        printf("[MAP] JSON %d -> Runtime %d (count=%d)\n", json_id, runtime_id, channel_id_map_count);
        fflush(stdout);
    }
}

static uint16_t MapJsonIdToRuntimeId(uint16_t json_id) {
    for (uint16_t i = 0; i < channel_id_map_count; i++) {
        if (channel_id_map[i].json_id == json_id) {
            return channel_id_map[i].runtime_id;
        }
    }
    return json_id;  /* Return as-is if no mapping found */
}

/**
 * @brief Check if channel ID is already a known runtime ID (from a fixed range)
 *
 * IDs resolved from channel names are already runtime IDs and should not be mapped.
 * Only IDs from JSON channel_id fields (small sequential numbers) need mapping.
 */
static bool IsKnownRuntimeId(uint16_t channel_id) {
    /* Check all known fixed ID ranges from pmu_channel_ids.h */
    return PMU_CHID_IS_ANALOG(channel_id) ||
           PMU_CHID_IS_DIGITAL(channel_id) ||
           PMU_CHID_IS_OUTPUT(channel_id) ||
           PMU_CHID_IS_HBRIDGE(channel_id) ||
           PMU_CHID_IS_CAN_RX(channel_id) ||
           PMU_CHID_IS_CAN_TX(channel_id) ||
           PMU_CHID_IS_LOGIC(channel_id) ||
           PMU_CHID_IS_NUMBER(channel_id) ||
           PMU_CHID_IS_TIMER(channel_id) ||
           PMU_CHID_IS_FILTER(channel_id) ||
           PMU_CHID_IS_SWITCH(channel_id) ||
           PMU_CHID_IS_PID(channel_id);
}

/**
 * @brief Resolve channel ID to runtime ID (smart mapping)
 *
 * If the ID is already a known runtime ID (from name resolution), use it directly.
 * Otherwise, try to map it from JSON ID to runtime ID.
 */
static uint16_t ResolveToRuntimeId(uint16_t channel_id) {
    if (channel_id == 0) return 0;

    /* First try explicit JSON->Runtime mapping (has priority) */
    uint16_t mapped_id = MapJsonIdToRuntimeId(channel_id);
    if (mapped_id != channel_id) {
        /* Mapping found - use the mapped runtime ID */
        return mapped_id;
    }

    /* No mapping found - use as-is (it's either a runtime ID or unmapped JSON ID) */
    return channel_id;
}

/* Helper to get input channel value by ID (new, preferred) */
static int32_t GetInputChannelValueById(uint16_t channel_id) {
    if (channel_id == 0) return 0;

    /* Translate JSON channel_id to runtime channel_id */
    uint16_t runtime_id = MapJsonIdToRuntimeId(channel_id);

    const PMU_Channel_t* ch = PMU_Channel_GetInfo(runtime_id);
    if (!ch) {
        /* Only warn after initial config load is complete */
        if (!config_loading_phase) {
            static uint32_t warn_cnt_id = 0;
            if (++warn_cnt_id <= 5) {
                printf("[WARN] Channel ID %u (runtime=%u) not found!\n", channel_id, runtime_id);
            }
        }
        return 0;
    }

    return ch->value;
}

/* Helper to get input channel value by name (legacy, for backward compatibility) */
static int32_t GetInputChannelValue(const char* channel_name) {
    if (!channel_name || channel_name[0] == '\0') return 0;
    const PMU_Channel_t* ch = PMU_Channel_GetByName(channel_name);
    if (!ch) {
        /* Only warn after initial config load is complete */
        if (!config_loading_phase) {
            static uint32_t warn_cnt = 0;
            if (++warn_cnt <= 5) {
                printf("[WARN] Channel '%s' not found!\n", channel_name);
            }
        }
        return 0;
    }
    return ch->value;
}

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
static bool JSON_ParseCanRx(cJSON* channel_obj);
static bool JSON_ParseCanTx(cJSON* channel_obj);
static bool JSON_ParsePID(cJSON* channel_obj);
static bool JSON_ParseBlinkMarineKeypad(cJSON* channel_obj);
static bool JSON_ParseHandler(cJSON* channel_obj);

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
static uint16_t JSON_GetChannelRef(cJSON* obj, const char* key);  /* Get channel ID from field (supports numeric & string) */
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

    /* Clear all runtime storage for re-loading config */
    memset(logic_storage, 0, sizeof(logic_storage));
    logic_count = 0;

    memset(number_storage, 0, sizeof(number_storage));
    number_count = 0;

    memset(switch_storage, 0, sizeof(switch_storage));
    switch_count = 0;

    memset(filter_storage, 0, sizeof(filter_storage));
    filter_count = 0;

    memset(timer_storage, 0, sizeof(timer_storage));
    timer_count = 0;

    /* Clear channel ID mapping */
    memset(channel_id_map, 0, sizeof(channel_id_map));
    channel_id_map_count = 0;

    /* Reset virtual channel ID allocator */
    virtual_channel_id_next = PMU_CHANNEL_ID_VIRTUAL_START;

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

    /* Suppress channel lookup warnings during load (reset in case previous load failed) */
    config_loading_phase = true;

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

    /* End loading phase - warnings will now be shown for missing channels */
    config_loading_phase = false;

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

/* Enum maps for HBridge parsing */
static const JSON_EnumMap_t hbridge_mode_map[] = {
    {"coast", 0}, {"forward", 1}, {"reverse", 2}, {"brake", 3},
    {"wiper_park", 4}, {"pid_position", 5}, JSON_ENUM_MAP_END
};

static const JSON_EnumMap_t hbridge_pwm_mode_map[] = {
    {"fixed", PMU_HBRIDGE_PWM_FIXED},
    {"channel", PMU_HBRIDGE_PWM_CHANNEL},
    {"channel_offset", PMU_HBRIDGE_PWM_BIDIRECTIONAL},
    JSON_ENUM_MAP_END
};

static const JSON_EnumMap_t hbridge_failsafe_mode_map[] = {
    {"park", PMU_HBRIDGE_FAILSAFE_PARK},
    {"brake", PMU_HBRIDGE_FAILSAFE_BRAKE},
    {"coast", PMU_HBRIDGE_FAILSAFE_COAST},
    {"custom_position", PMU_HBRIDGE_FAILSAFE_CUSTOM},
    JSON_ENUM_MAP_END
};

/* Enum maps for Logic operations */
static const JSON_EnumMap_t logic_operation_map[] = {
    {"is_true", PMU_LOGIC_IS_TRUE}, {"is_false", PMU_LOGIC_IS_FALSE},
    {"equal", PMU_LOGIC_EQUAL}, {"not_equal", PMU_LOGIC_NOT_EQUAL},
    {"less", PMU_LOGIC_LESS}, {"greater", PMU_LOGIC_GREATER},
    {"less_equal", PMU_LOGIC_LESS_EQUAL}, {"greater_equal", PMU_LOGIC_GREATER_EQUAL},
    {"and", PMU_LOGIC_AND}, {"or", PMU_LOGIC_OR}, {"xor", PMU_LOGIC_XOR},
    {"not", PMU_LOGIC_NOT}, {"nand", PMU_LOGIC_NAND}, {"nor", PMU_LOGIC_NOR},
    {"in_range", PMU_LOGIC_IN_RANGE}, {"changed", PMU_LOGIC_CHANGED},
    {"hysteresis", PMU_LOGIC_HYSTERESIS}, {"set_reset_latch", PMU_LOGIC_SET_RESET_LATCH},
    {"toggle", PMU_LOGIC_TOGGLE}, {"pulse", PMU_LOGIC_PULSE}, {"flash", PMU_LOGIC_FLASH},
    {"rising_edge", PMU_LOGIC_EDGE_RISING}, {"edge_rising", PMU_LOGIC_EDGE_RISING},
    {"falling_edge", PMU_LOGIC_EDGE_FALLING}, {"edge_falling", PMU_LOGIC_EDGE_FALLING},
    JSON_ENUM_MAP_END
};

static const JSON_EnumMap_t logic_polarity_map[] = {
    {"normal", PMU_POLARITY_NORMAL}, {"inverted", PMU_POLARITY_INVERTED},
    JSON_ENUM_MAP_END
};

static const JSON_EnumMap_t logic_edge_map[] = {
    {"rising", PMU_EDGE_RISING}, {"falling", PMU_EDGE_FALLING}, {"both", PMU_EDGE_BOTH},
    JSON_ENUM_MAP_END
};

static const JSON_EnumMap_t logic_default_state_map[] = {
    {"off", PMU_DEFAULT_STATE_OFF}, {"on", PMU_DEFAULT_STATE_ON},
    JSON_ENUM_MAP_END
};

/* Enum maps for Number/Math operations */
static const JSON_EnumMap_t number_operation_map[] = {
    {"constant", PMU_MATH_CONSTANT}, {"channel", PMU_MATH_CHANNEL},
    {"add", PMU_MATH_ADD}, {"subtract", PMU_MATH_SUBTRACT},
    {"multiply", PMU_MATH_MULTIPLY}, {"divide", PMU_MATH_DIVIDE},
    {"modulo", PMU_MATH_MODULO}, {"min", PMU_MATH_MIN}, {"max", PMU_MATH_MAX},
    {"clamp", PMU_MATH_CLAMP}, {"lookup2", PMU_MATH_LOOKUP2},
    {"lookup3", PMU_MATH_LOOKUP3}, {"lookup4", PMU_MATH_LOOKUP4},
    {"lookup5", PMU_MATH_LOOKUP5},
    JSON_ENUM_MAP_END
};

/* Enum maps for Timer */
static const JSON_EnumMap_t timer_edge_map[] = {
    {"rising", PMU_EDGE_RISING}, {"falling", PMU_EDGE_FALLING},
    {"both", PMU_EDGE_BOTH}, {"level", PMU_EDGE_LEVEL},
    JSON_ENUM_MAP_END
};

static const JSON_EnumMap_t timer_mode_map[] = {
    {"count_up", PMU_TIMER_MODE_COUNT_UP}, {"count_down", PMU_TIMER_MODE_COUNT_DOWN},
    JSON_ENUM_MAP_END
};

/* Enum maps for Filter */
static const JSON_EnumMap_t filter_type_map[] = {
    {"moving_avg", PMU_FILTER_MOVING_AVG}, {"low_pass", PMU_FILTER_LOW_PASS},
    {"min_window", PMU_FILTER_MIN_WINDOW}, {"max_window", PMU_FILTER_MAX_WINDOW},
    {"median", PMU_FILTER_MEDIAN},
    JSON_ENUM_MAP_END
};

/* Enum maps for CAN */
static const JSON_EnumMap_t can_data_type_map[] = {
    {"unsigned", PMU_CAN_DATA_TYPE_UNSIGNED}, {"signed", PMU_CAN_DATA_TYPE_SIGNED},
    {"float", PMU_CAN_DATA_TYPE_FLOAT},
    JSON_ENUM_MAP_END
};

static const JSON_EnumMap_t can_byte_order_map[] = {
    {"little_endian", 1}, {"big_endian", 0},
    JSON_ENUM_MAP_END
};

/* Combined data type+format map for CAN TX (encode: high nibble=type, low nibble=format) */
#define CAN_DTYPE(type, fmt) (((type) << 4) | (fmt))
static const JSON_EnumMap_t can_tx_dtype_map[] = {
    {"int8",   CAN_DTYPE(PMU_CAN_DATA_TYPE_SIGNED, PMU_CAN_DATA_FORMAT_8BIT)},
    {"uint8",  CAN_DTYPE(PMU_CAN_DATA_TYPE_UNSIGNED, PMU_CAN_DATA_FORMAT_8BIT)},
    {"int16",  CAN_DTYPE(PMU_CAN_DATA_TYPE_SIGNED, PMU_CAN_DATA_FORMAT_16BIT)},
    {"uint16", CAN_DTYPE(PMU_CAN_DATA_TYPE_UNSIGNED, PMU_CAN_DATA_FORMAT_16BIT)},
    {"int32",  CAN_DTYPE(PMU_CAN_DATA_TYPE_SIGNED, PMU_CAN_DATA_FORMAT_32BIT)},
    {"uint32", CAN_DTYPE(PMU_CAN_DATA_TYPE_UNSIGNED, PMU_CAN_DATA_FORMAT_32BIT)},
    JSON_ENUM_MAP_END
};

/* WiFi and Bluetooth configuration enum maps */
static const JSON_EnumMap_t wifi_mode_map[] = {
    {"ap", PMU_WIFI_MODE_AP}, {"sta", PMU_WIFI_MODE_STA}, {"ap_sta", PMU_WIFI_MODE_AP_STA},
    JSON_ENUM_MAP_END
};

static const JSON_EnumMap_t wifi_security_map[] = {
    {"open", PMU_WIFI_SEC_OPEN}, {"wpa", PMU_WIFI_SEC_WPA},
    {"wpa2", PMU_WIFI_SEC_WPA2}, {"wpa3", PMU_WIFI_SEC_WPA3},
    JSON_ENUM_MAP_END
};

static const JSON_EnumMap_t bt_mode_map[] = {
    {"ble", PMU_BT_MODE_BLE}, {"classic", PMU_BT_MODE_CLASSIC}, {"dual", PMU_BT_MODE_DUAL},
    JSON_ENUM_MAP_END
};

static const JSON_EnumMap_t bt_security_map[] = {
    {"none", PMU_BT_SEC_NONE}, {"pair", PMU_BT_SEC_PAIR_ONLY},
    {"auth", PMU_BT_SEC_AUTH}, {"secure", PMU_BT_SEC_SECURE},
    JSON_ENUM_MAP_END
};

/* LIN frame type enum maps */
static const JSON_EnumMap_t lin_frame_type_map[] = {
    {"unconditional", PMU_LIN_FRAME_TYPE_UNCONDITIONAL},
    {"event_triggered", PMU_LIN_FRAME_TYPE_EVENT_TRIGGERED},
    {"sporadic", PMU_LIN_FRAME_TYPE_SPORADIC},
    {"diagnostic", PMU_LIN_FRAME_TYPE_DIAGNOSTIC},
    JSON_ENUM_MAP_END
};

static const JSON_EnumMap_t lin_direction_map[] = {
    {"publish", PMU_LIN_DIR_PUBLISH}, {"subscribe", PMU_LIN_DIR_SUBSCRIBE},
    JSON_ENUM_MAP_END
};

static const JSON_EnumMap_t lin_checksum_map[] = {
    {"classic", PMU_LIN_CHECKSUM_CLASSIC}, {"enhanced", PMU_LIN_CHECKSUM_ENHANCED},
    JSON_ENUM_MAP_END
};

/**
 * @brief Parse H-bridges array from JSON
 */
static bool JSON_ParseHBridges(cJSON* hbridges_array)
{
    int count = cJSON_GetArraySize(hbridges_array);
    if (count > PMU30_NUM_HBRIDGES) {
        count = PMU30_NUM_HBRIDGES;
    }

    for (int i = 0; i < count; i++) {
        cJSON* hb = cJSON_GetArrayItem(hbridges_array, i);
        if (!hb || !cJSON_IsObject(hb)) continue;

        PMU_HBridgeConfig_t config = {0};

        /* Basic settings */
        JSON_CopyString(hb, "name", config.name, sizeof(config.name));
        config.bridge = JSON_GetUint8(hb, "bridge_number", 0);
        config.enabled = true;  /* Channels always enabled */
        config.mode = JSON_GetEnum(hb, "mode", hbridge_mode_map, 0);
        JSON_CopyString(hb, "motor_preset", config.motor_preset, sizeof(config.motor_preset));

        /* Control sources */
        config.source_channel_id = JSON_GetChannelRef(hb, "source_channel");
        config.direction_source_channel_id = JSON_GetChannelRef(hb, "direction_source_channel");
        config.invert_direction = JSON_GetBool(hb, "invert_direction", false);

        /* PWM control */
        config.pwm_mode = JSON_GetEnum(hb, "pwm_mode", hbridge_pwm_mode_map, PMU_HBRIDGE_PWM_FIXED);
        config.pwm_frequency = JSON_GetUint16(hb, "pwm_frequency", 1000);
        config.pwm_value = JSON_GetUint8(hb, "pwm_value", 255);
        config.pwm_source_channel_id = JSON_GetChannelRef(hb, "pwm_source_channel");
        config.duty_limit_percent = JSON_GetUint8(hb, "duty_limit_percent", 100);

        /* Position control */
        config.position_feedback_enabled = JSON_GetBool(hb, "position_feedback_enabled", false);
        config.position_source_channel_id = JSON_GetChannelRef(hb, "position_source_channel");
        config.target_position = JSON_GetUint16(hb, "target_position", 0);
        config.target_source_channel_id = JSON_GetChannelRef(hb, "target_source_channel");
        config.position_min = JSON_GetUint16(hb, "position_min", 0);
        config.position_max = JSON_GetUint16(hb, "position_max", 65535);
        config.position_deadband = JSON_GetUint16(hb, "position_deadband", 50);
        config.position_park = JSON_GetFloat(hb, "position_park", 0.0f);

        /* Valid voltage range */
        config.valid_voltage_min = JSON_GetFloat(hb, "valid_voltage_min", 0.2f);
        config.valid_voltage_max = JSON_GetFloat(hb, "valid_voltage_max", 4.8f);

        /* Position margins */
        config.lower_margin = JSON_GetUint16(hb, "lower_margin", 50);
        config.upper_margin = JSON_GetUint16(hb, "upper_margin", 50);

        /* PID control */
        config.pid_kp = JSON_GetFloat(hb, "pid_kp", 1.0f);
        config.pid_ki = JSON_GetFloat(hb, "pid_ki", 0.0f);
        config.pid_kd = JSON_GetFloat(hb, "pid_kd", 0.0f);
        config.pid_kd_filter = JSON_GetFloat(hb, "pid_kd_filter", 0.1f);
        config.pid_output_min = JSON_GetInt16(hb, "pid_output_min", -255);
        config.pid_output_max = JSON_GetInt16(hb, "pid_output_max", 255);

        /* Current protection */
        config.current_limit_a = JSON_GetFloat(hb, "current_limit_a", 10.0f);
        config.inrush_current_a = JSON_GetFloat(hb, "inrush_current_a", 30.0f);
        config.inrush_time_ms = JSON_GetUint16(hb, "inrush_time_ms", 500);
        config.retry_count = JSON_GetUint8(hb, "retry_count", 3);
        config.retry_delay_ms = JSON_GetUint16(hb, "retry_delay_ms", 1000);

        /* Stall detection */
        config.stall_detection_enabled = JSON_GetBool(hb, "stall_detection_enabled", true);
        config.stall_current_threshold_a = JSON_GetFloat(hb, "stall_current_threshold_a", 5.0f);
        config.stall_time_threshold_ms = JSON_GetUint16(hb, "stall_time_threshold_ms", 500);
        config.overtemperature_threshold_c = JSON_GetInt16(hb, "overtemperature_threshold_c", 120);

        /* Signal loss failsafe */
        config.failsafe_enabled = JSON_GetBool(hb, "failsafe_enabled", true);
        config.signal_timeout_ms = JSON_GetUint16(hb, "signal_timeout_ms", 100);
        config.failsafe_mode = JSON_GetEnum(hb, "failsafe_mode", hbridge_failsafe_mode_map, PMU_HBRIDGE_FAILSAFE_PARK);
        config.failsafe_position = JSON_GetUint16(hb, "failsafe_position", 0);
        config.failsafe_pwm = JSON_GetUint8(hb, "failsafe_pwm", 100);
        config.auto_recovery = JSON_GetBool(hb, "auto_recovery", true);

        /* Store the configuration */
        if (config.bridge < PMU30_NUM_HBRIDGES) {
            /* TODO: Store to actual config structure or call PMU_HBridge_Configure() */
        }
    }

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
        wifi_config.mode = JSON_GetEnum(wifi, "mode", wifi_mode_map, PMU_WIFI_MODE_AP);

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
            wifi_config.ap.security = JSON_GetEnum(ap, "security", wifi_security_map, PMU_WIFI_SEC_WPA2);
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
        printf("[JSON] WiFi configured: mode=%d enabled=%d\n",
               wifi_config.mode, wifi_config.enabled);
    }

    /* Parse Bluetooth configuration */
    cJSON* bt = cJSON_GetObjectItem(settings_obj, "bluetooth");
    if (bt && cJSON_IsObject(bt)) {
        PMU_BT_Config_t bt_config;
        PMU_BT_SetDefaultConfig(&bt_config);

        bt_config.enabled = JSON_GetBool(bt, "enabled", false);
        bt_config.mode = JSON_GetEnum(bt, "mode", bt_mode_map, PMU_BT_MODE_BLE);

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
            bt_config.classic.security = JSON_GetEnum(classic, "security", bt_security_map, PMU_BT_SEC_AUTH);
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
            bt_config.ble.security = JSON_GetEnum(ble, "security", bt_security_map, PMU_BT_SEC_PAIR_ONLY);
        }

        /* Telemetry service configuration */
        cJSON* telem = cJSON_GetObjectItem(bt, "telemetry");
        if (telem && cJSON_IsObject(telem)) {
            bt_config.telemetry.enabled = JSON_GetBool(telem, "enabled", true);
            bt_config.telemetry.update_rate_ms = (uint16_t)JSON_GetInt(telem, "update_rate_ms", 100);
            bt_config.telemetry.notify_changes = JSON_GetBool(telem, "notify_changes", false) ? 1 : 0;
        }

        PMU_BT_ApplyConfig(&bt_config);
        printf("[JSON] Bluetooth configured: mode=%d enabled=%d\n",
               bt_config.mode, bt_config.enabled);
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

        /* Parse message name - use 'name' field as both id and display name */
        const char* name = JSON_GetString(msg, "name", "");
        if (strlen(name) == 0) {
            JSON_SetError("CAN message missing required 'name' field");
            continue;
        }
        strncpy(config.id, name, PMU_CHANNEL_ID_LEN - 1);
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
        config.enabled = true;  /* Channels always enabled */

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

        /* Parse frame name - use 'name' field as both id and display name */
        const char* name = JSON_GetString(frame, "name", "");
        if (strlen(name) == 0) {
            JSON_SetError("LIN frame missing required 'name' field");
            continue;
        }
        strncpy(config.id, name, PMU_LIN_ID_LEN - 1);
        strncpy(config.name, name, PMU_LIN_ID_LEN - 1);

        /* Parse LIN bus (1 or 2) */
        int bus_val = JSON_GetInt(frame, "bus", 1);
        config.bus = (bus_val >= 2) ? PMU_LIN_BUS_2 : PMU_LIN_BUS_1;

        /* Parse frame ID (0-63) */
        config.frame_id = (uint8_t)JSON_GetInt(frame, "frame_id", 0) & 0x3F;

        /* Parse frame type, direction, and checksum using enum maps */
        config.frame_type = JSON_GetEnum(frame, "frame_type", lin_frame_type_map, PMU_LIN_FRAME_TYPE_UNCONDITIONAL);
        config.direction = JSON_GetEnum(frame, "direction", lin_direction_map, PMU_LIN_DIR_SUBSCRIBE);
        config.checksum = JSON_GetEnum(frame, "checksum", lin_checksum_map, PMU_LIN_CHECKSUM_ENHANCED);

        /* Parse other properties */
        config.length = (uint8_t)JSON_GetInt(frame, "length", 8);
        if (config.length > 8) config.length = 8;

        config.timeout_ms = (uint16_t)JSON_GetInt(frame, "timeout_ms", 100);
        config.enabled = true;  /* Frames always enabled */

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
            printf("[JSON] LIN frame '%s': bus=%d, id=0x%02X, dir=%d, type=%d\n",
                   config.id, config.bus, config.frame_id,
                   config.direction, config.frame_type);

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
    const char* id = JSON_GetString(channel, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("LIN RX channel missing required 'name' field");
        return false;
    }
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
    const char* id = JSON_GetString(channel, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("LIN TX channel missing required 'name' field");
        return false;
    }
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
 * @brief Get channel reference from JSON field (supports both numeric ID and string name)
 * @param obj Parent JSON object
 * @param key Field name
 * @return Channel ID (0 if not found or empty)
 */
static uint16_t JSON_GetChannelRef(cJSON* obj, const char* key)
{
    if (!obj || !key) return 0;
    cJSON* field = cJSON_GetObjectItem(obj, key);
    return JSON_ResolveChannel(field);
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

        /* Get channel name - required field */
        const char* id = JSON_GetString(channel, "channel_name", "");
        if (strlen(id) == 0) {
            JSON_SetError("Channel %d: missing required 'channel_name' field", i);
            continue;
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

            case PMU_CHANNEL_TYPE_HANDLER:
                success = JSON_ParseHandler(channel);
                if (success && stats) stats->handlers++;
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

    /* Get JSON channel_id for mapping */
    uint16_t json_channel_id = (uint16_t)JSON_GetInt(channel_obj, "channel_id", 0);

    /* Get channel name - required field */
    const char* id = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("Digital input missing required 'name' field");
        return false;
    }
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
/* Button function mode (ECUMaster compatible) */
    const char* btn_mode = JSON_GetString(channel_obj, "button_mode", "none");
    if (strcmp(btn_mode, "none") == 0) config.button_mode = PMU_BUTTON_MODE_DIRECT;
    else if (strcmp(btn_mode, "long_press") == 0) config.button_mode = PMU_BUTTON_MODE_LONG_PRESS;
    else if (strcmp(btn_mode, "double_click") == 0) config.button_mode = PMU_BUTTON_MODE_DOUBLE_CLICK;
    else if (strcmp(btn_mode, "toggle") == 0) config.button_mode = PMU_BUTTON_MODE_TOGGLE;
    else if (strcmp(btn_mode, "latching") == 0) config.button_mode = PMU_BUTTON_MODE_LATCHING;
    else if (strcmp(btn_mode, "press_hold") == 0) config.button_mode = PMU_BUTTON_MODE_PRESS_AND_HOLD;
    else config.button_mode = PMU_BUTTON_MODE_DIRECT;

    config.long_press_ms = (uint16_t)JSON_GetInt(channel_obj, "long_press_ms", 500);
    config.long_press_output_id = JSON_GetChannelRef(channel_obj, "long_press_output");
    config.double_click_ms = (uint16_t)JSON_GetInt(channel_obj, "double_click_ms", 300);
    config.double_click_output_id = JSON_GetChannelRef(channel_obj, "double_click_output");
    config.hold_start_ms = (uint16_t)JSON_GetInt(channel_obj, "hold_start_ms", 500);
    config.hold_full_ms = (uint16_t)JSON_GetInt(channel_obj, "hold_full_ms", 2000);
    config.reset_channel_id = JSON_GetChannelRef(channel_obj, "reset_channel");

    /* Register digital input channel */
    uint8_t pin = config.input_pin;
    if (pin < PMU30_NUM_ADC_INPUTS) {
        printf("[CONFIG] Parsing digital input: id='%s' pin=%d\n", id, pin);
        fflush(stdout);

        /* Configure as digital input in ADC system */
        PMU_InputConfig_t* adc_config = &input_config_storage[pin];
        memset(adc_config, 0, sizeof(PMU_InputConfig_t));

        adc_config->channel = pin + 1;  /* Display as 1-based */
        strncpy(adc_config->name, config.id, sizeof(adc_config->name) - 1);

        /* Map subtype to legacy input type */
        switch (config.subtype) {
            case PMU_DI_SUBTYPE_SWITCH_ACTIVE_LOW:
                adc_config->type = PMU_LEGACY_INPUT_SWITCH_ACTIVE_LOW;
                break;
            case PMU_DI_SUBTYPE_SWITCH_ACTIVE_HIGH:
                adc_config->type = PMU_LEGACY_INPUT_SWITCH_ACTIVE_HIGH;
                break;
            case PMU_DI_SUBTYPE_FREQUENCY:
            case PMU_DI_SUBTYPE_RPM:
                adc_config->type = PMU_LEGACY_INPUT_FREQUENCY;
                break;
            default:
                adc_config->type = PMU_LEGACY_INPUT_SWITCH_ACTIVE_HIGH;
                break;
        }

        adc_config->threshold_high_mv = config.threshold_mv;
        adc_config->threshold_low_mv = config.threshold_mv / 2;
        adc_config->debounce_ms = config.debounce_ms;
        adc_config->multiplier = config.multiplier;
        adc_config->offset = 0.0f;

        PMU_ADC_SetConfig(pin, adc_config);

        /* Register channel with channel system */
        /* Digital inputs use channel_id 50-69 to avoid conflict with analog inputs (0-19) */
        PMU_Channel_t channel = {0};
        channel.channel_id = 50 + pin;
        strncpy(channel.name, config.id, sizeof(channel.name) - 1);
        channel.hw_class = PMU_CHANNEL_CLASS_INPUT_SWITCH;
        channel.min_value = 0;
        channel.max_value = 1;
        channel.physical_index = pin;
        channel.flags = PMU_CHANNEL_FLAG_ENABLED;

        HAL_StatusTypeDef ch_result = PMU_Channel_Register(&channel);
        printf("[CONFIG] Digital input ch%d '%s' (ID=%d) result=%d\n", pin, config.id, channel.channel_id, ch_result);
        fflush(stdout);

        /* Set channel_id in ADC system for PMU_Channel_SetValue sync */
        PMU_ADC_SetChannelId(pin, channel.channel_id);

        /* Add mapping from JSON channel_id to runtime channel_id */
        if (json_channel_id != 0) {
            AddChannelIdMapping(json_channel_id, channel.channel_id);
        }
    }
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

    /* Get JSON channel_id for mapping */
    uint16_t json_channel_id = (uint16_t)JSON_GetInt(channel_obj, "channel_id", 0);

    /* Get channel name - required field */
    const char* id = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("Analog input missing required 'name' field");
        return false;
    }
    printf("[CONFIG] Parsing analog input: id='%s'\n", id);
    fflush(stdout);
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    /* Check if analog input is enabled - skip ADC config if disabled */
    bool enabled = JSON_GetBool(channel_obj, "enabled", false);
    if (!enabled) {
        printf("[CONFIG] Analog input '%s' is disabled, skipping ADC config\n", id);
        fflush(stdout);
        return true;  /* Return true to not break parsing, just skip this channel */
    }

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

        /* Add mapping from JSON channel_id to runtime channel_id */
        if (json_channel_id != 0) {
            AddChannelIdMapping(json_channel_id, channel.channel_id);
        }
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

    /* Get channel name - required field */
    const char* id = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("Power output missing required 'name' field");
        return false;
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

    /* Source channel (numeric ID only) */
    config.source_channel_id = JSON_GetChannelRef(channel_obj, "source_channel");
    if (config.source_channel_id == 0) {
        config.source_channel_id = JSON_GetChannelRef(channel_obj, "control_function");
    }

    /* PWM settings - try flat format first, then nested "pwm" object */
    cJSON* pwm_obj = cJSON_GetObjectItem(channel_obj, "pwm");
    if (pwm_obj && cJSON_IsObject(pwm_obj)) {
        /* Dialog nested format: pwm.enabled, pwm.frequency, pwm.duty_value */
        config.pwm_enabled = JSON_GetBool(pwm_obj, "enabled", false);
        config.pwm_frequency_hz = (uint16_t)JSON_GetInt(pwm_obj, "frequency", 1000);
        config.duty_fixed = JSON_GetFloat(pwm_obj, "duty_value", 100.0f);
        config.soft_start_ms = JSON_GetBool(pwm_obj, "soft_start_enabled", false) ?
                               (uint16_t)JSON_GetInt(pwm_obj, "soft_start_duration_ms", 0) : 0;
        config.duty_channel_id = JSON_GetChannelRef(pwm_obj, "duty_function");
    } else {
        /* Schema flat format: pwm_enabled, pwm_frequency_hz, duty_fixed */
        config.pwm_enabled = JSON_GetBool(channel_obj, "pwm_enabled", false);
        config.pwm_frequency_hz = (uint16_t)JSON_GetInt(channel_obj, "pwm_frequency_hz", 1000);
        config.duty_fixed = JSON_GetFloat(channel_obj, "duty_fixed", 100.0f);
        config.soft_start_ms = (uint16_t)JSON_GetInt(channel_obj, "soft_start_ms", 0);
        config.duty_channel_id = JSON_GetChannelRef(channel_obj, "duty_channel");
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
            if (config.source_channel_id == 0) {
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
    if (config.source_channel_id != 0) {
        printf("], enabled=%d, source_id=%d, pwm=%d, duty=%.1f%%\n",
               enabled, config.source_channel_id, config.pwm_enabled, config.duty_fixed);
    } else {
        printf("], enabled=%d, source=%d, pwm=%d, duty=%.1f%%\n",
               enabled, config.source_channel_id, config.pwm_enabled, config.duty_fixed);
    }

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

    /* Get channel name - required field */
    const char* id = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("Logic function missing required 'name' field");
        return false;
    }
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    /* Get JSON channel_id for mapping */
    uint16_t json_channel_id = (uint16_t)JSON_GetInt(channel_obj, "channel_id", 0);

    /* Parse operation using enum map */
    config.operation = JSON_GetEnum(channel_obj, "operation", logic_operation_map, PMU_LOGIC_IS_TRUE);

    /* Channel inputs (supports both numeric ID and string name for backward compat) */
    config.channel_id = JSON_GetChannelRef(channel_obj, "channel");
    config.channel_2_id = JSON_GetChannelRef(channel_obj, "channel_2");

    /* Delays */
    config.true_delay_s = JSON_GetFloat(channel_obj, "true_delay_s", 0.0f);
    config.false_delay_s = JSON_GetFloat(channel_obj, "false_delay_s", 0.0f);

    /* Constant for comparison */
    config.constant = JSON_GetFloat(channel_obj, "constant", 0.0f);

    /* Changed operation */
    config.threshold = JSON_GetFloat(channel_obj, "threshold", 0.0f);
    config.time_on_s = JSON_GetFloat(channel_obj, "time_on_s", 0.0f);

    /* Hysteresis */
    config.polarity = JSON_GetEnum(channel_obj, "polarity", logic_polarity_map, PMU_POLARITY_NORMAL);
    config.upper_value = JSON_GetFloat(channel_obj, "upper_value", 100.0f);
    config.lower_value = JSON_GetFloat(channel_obj, "lower_value", 0.0f);

    /* Set/Reset latch */
    config.set_channel_id = JSON_GetChannelRef(channel_obj, "set_channel");
    config.reset_channel_id = JSON_GetChannelRef(channel_obj, "reset_channel");
    config.default_state = JSON_GetEnum(channel_obj, "default_state", logic_default_state_map, PMU_DEFAULT_STATE_OFF);

    /* Toggle/Pulse */
    config.edge = JSON_GetEnum(channel_obj, "edge", logic_edge_map, PMU_EDGE_RISING);

    config.toggle_channel_id = JSON_GetChannelRef(channel_obj, "toggle_channel");
    config.pulse_count = (uint8_t)JSON_GetInt(channel_obj, "pulse_count", 1);
    config.retrigger = JSON_GetBool(channel_obj, "retrigger", false);

    /* Flash */
    config.time_off_s = JSON_GetFloat(channel_obj, "time_off_s", 0.5f);

    /* Store in runtime storage */
    if (logic_count >= PMU_MAX_LOGIC_CHANNELS) {
        JSON_SetError("Too many logic channels (max %d)", PMU_MAX_LOGIC_CHANNELS);
        return false;
    }

    PMU_LogicRuntime_t* rt = &logic_storage[logic_count];
    memcpy(&rt->config, &config, sizeof(PMU_LogicConfig_t));
    rt->output_value = 0;
    rt->prev_input_value = 0;
    rt->prev_input2_value = 0;
    rt->delay_active = false;
    rt->latch_state = (config.default_state == PMU_DEFAULT_STATE_ON);
    rt->flash_state = false;

    /* Allocate virtual channel ID */
    rt->channel_id = AllocateVirtualChannelID();
    if (rt->channel_id == 0) {
        JSON_SetError("Failed to allocate channel ID for logic '%s'", id);
        return false;
    }

    /* Add mapping from JSON channel_id to runtime channel_id */
    if (json_channel_id != 0) {
        AddChannelIdMapping(json_channel_id, rt->channel_id);
    }

    /* Register channel */
    PMU_Channel_t channel = {0};
    channel.channel_id = rt->channel_id;
    channel.hw_class = PMU_CHANNEL_CLASS_OUTPUT_FUNCTION;
    channel.direction = PMU_CHANNEL_DIR_VIRTUAL;
    channel.format = PMU_CHANNEL_FORMAT_BOOLEAN;
    channel.flags = PMU_CHANNEL_FLAG_ENABLED;
    channel.value = 0;
    channel.min_value = 0;
    channel.max_value = 1000;
    strncpy(channel.name, id, sizeof(channel.name) - 1);
    PMU_Channel_Register(&channel);

    logic_count++;
    printf("[JSON] Parsed logic channel: %s (JSON_ID=%d, RT_ID=%d, op=%d)\n",
           id, json_channel_id, rt->channel_id, config.operation);
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

    /* Get channel name - required field */
    const char* id = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("Number channel missing required 'name' field");
        return false;
    }
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    /* Get JSON channel_id for mapping */
    uint16_t json_channel_id = (uint16_t)JSON_GetInt(channel_obj, "channel_id", 0);

    /* Parse operation using enum map */
    config.operation = JSON_GetEnum(channel_obj, "operation", number_operation_map, PMU_MATH_CONSTANT);

    /* Inputs array (supports both numeric IDs and string names) */
    cJSON* inputs = cJSON_GetObjectItem(channel_obj, "inputs");
    if (inputs && cJSON_IsArray(inputs)) {
        int inp_count = cJSON_GetArraySize(inputs);
        config.input_count = (inp_count > PMU_MAX_NUMBER_INPUTS) ?
                              PMU_MAX_NUMBER_INPUTS : (uint8_t)inp_count;
        for (int i = 0; i < config.input_count; i++) {
            cJSON* inp = cJSON_GetArrayItem(inputs, i);
            config.input_ids[i] = JSON_ResolveChannel(inp);
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

    /* Store in runtime storage */
    if (number_count >= PMU_MAX_NUMBER_CHANNELS) {
        JSON_SetError("Too many number channels (max %d)", PMU_MAX_NUMBER_CHANNELS);
        return false;
    }

    PMU_NumberRuntime_t* rt = &number_storage[number_count];
    memcpy(&rt->config, &config, sizeof(PMU_NumberConfig_t));
    rt->output_value = 0;

    /* Allocate virtual channel ID */
    rt->channel_id = AllocateVirtualChannelID();
    if (rt->channel_id == 0) {
        JSON_SetError("Failed to allocate channel ID for number '%s'", id);
        return false;
    }

    /* Add mapping from JSON channel_id to runtime channel_id */
    if (json_channel_id != 0) {
        AddChannelIdMapping(json_channel_id, rt->channel_id);
    }

    /* Register channel */
    PMU_Channel_t channel = {0};
    channel.channel_id = rt->channel_id;
    channel.hw_class = PMU_CHANNEL_CLASS_OUTPUT_NUMBER;
    channel.direction = PMU_CHANNEL_DIR_VIRTUAL;
    channel.format = PMU_CHANNEL_FORMAT_INT;
    channel.flags = PMU_CHANNEL_FLAG_ENABLED;
    channel.value = 0;
    channel.min_value = (int32_t)(config.clamp_min * 1000);
    channel.max_value = (int32_t)(config.clamp_max * 1000);
    strncpy(channel.name, id, sizeof(channel.name) - 1);
    PMU_Channel_Register(&channel);

    number_count++;
    printf("[JSON] Parsed number channel: %s (JSON_ID=%d, RT_ID=%d, op=%d)\n",
           id, json_channel_id, rt->channel_id, config.operation);
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

    /* Get channel name - required field */
    const char* id = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("Timer missing required 'name' field");
        return false;
    }
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    /* Get JSON channel_id for mapping */
    uint16_t json_channel_id = (uint16_t)JSON_GetInt(channel_obj, "channel_id", 0);

    config.start_channel_id = JSON_GetChannelRef(channel_obj, "start_channel");
    config.start_edge = JSON_GetEnum(channel_obj, "start_edge", timer_edge_map, PMU_EDGE_RISING);

    config.stop_channel_id = JSON_GetChannelRef(channel_obj, "stop_channel");
    config.stop_edge = JSON_GetEnum(channel_obj, "stop_edge", timer_edge_map, PMU_EDGE_RISING);

    config.mode = JSON_GetEnum(channel_obj, "mode", timer_mode_map, PMU_TIMER_MODE_COUNT_UP);

    config.limit_hours = (uint16_t)JSON_GetInt(channel_obj, "limit_hours", 0);
    config.limit_minutes = (uint8_t)JSON_GetInt(channel_obj, "limit_minutes", 0);
    config.limit_seconds = (uint8_t)JSON_GetInt(channel_obj, "limit_seconds", 0);

    /* Store in runtime storage and register channel */
    if (timer_count >= PMU_MAX_TIMER_CHANNELS) {
        JSON_SetError("Too many timer channels (max %d)", PMU_MAX_TIMER_CHANNELS);
        return false;
    }
    PMU_TimerRuntime_t* rt = &timer_storage[timer_count];
    memcpy(&rt->config, &config, sizeof(PMU_TimerConfig_t));
    rt->channel_id = AllocateVirtualChannelID();
    if (rt->channel_id == 0) {
        JSON_SetError("Failed to allocate virtual channel ID for timer '%s'", id);
        return false;
    }
    /* Allocate elapsed channel ID */
    rt->elapsed_channel_id = AllocateVirtualChannelID();
    if (rt->elapsed_channel_id == 0) {
        JSON_SetError("Failed to allocate elapsed channel ID for timer '%s'", id);
        return false;
    }

    rt->output_value = 0;
    rt->start_time_ms = 0;
    rt->running = false;
    rt->prev_start_value = 0;
    rt->prev_stop_value = 0;

    /* Add mapping from JSON channel_id to runtime channel_id */
    if (json_channel_id != 0) {
        AddChannelIdMapping(json_channel_id, rt->channel_id);
    }

    /* Register the main timer channel (outputs running state 0/1000) */
    PMU_Channel_t channel = {0};
    channel.channel_id = rt->channel_id;
    channel.hw_class = PMU_CHANNEL_CLASS_OUTPUT_FUNCTION;
    channel.direction = PMU_CHANNEL_DIR_VIRTUAL;
    channel.format = PMU_CHANNEL_FORMAT_BOOLEAN;
    channel.flags = PMU_CHANNEL_FLAG_ENABLED;
    channel.min_value = 0;
    channel.max_value = 1000;
    strncpy(channel.name, id, sizeof(channel.name) - 1);
    channel.value = 0;
    PMU_Channel_Register(&channel);

    /* Register the elapsed channel (outputs time in ms) */
    char elapsed_name[32];
    snprintf(elapsed_name, sizeof(elapsed_name), "%s_Elapsed", id);
    channel.channel_id = rt->elapsed_channel_id;
    channel.format = PMU_CHANNEL_FORMAT_INT;
    channel.min_value = 0;
    channel.max_value = 0x7FFFFFFF;
    strncpy(channel.name, elapsed_name, sizeof(channel.name) - 1);
    channel.value = 0;
    PMU_Channel_Register(&channel);

    timer_count++;
    printf("[JSON] Parsed timer channel: %s (JSON_ID=%d, RT_ID=%d, ELAPSED_ID=%d)\n",
           id, json_channel_id, rt->channel_id, rt->elapsed_channel_id);
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

    /* Get channel name - required field */
    const char* id = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("Filter missing required 'name' field");
        return false;
    }
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    /* Get JSON channel_id for mapping */
    uint16_t json_channel_id = (uint16_t)JSON_GetInt(channel_obj, "channel_id", 0);

    config.filter_type = JSON_GetEnum(channel_obj, "filter_type", filter_type_map, PMU_FILTER_MOVING_AVG);

    config.input_channel_id = JSON_GetChannelRef(channel_obj, "input_channel");

    config.window_size = (uint16_t)JSON_GetInt(channel_obj, "window_size", 10);
    config.time_constant = JSON_GetFloat(channel_obj, "time_constant", 0.1f);

    /* Store in runtime storage and register channel */
    if (filter_count >= PMU_MAX_FILTER_CHANNELS) {
        JSON_SetError("Too many filter channels (max %d)", PMU_MAX_FILTER_CHANNELS);
        return false;
    }
    PMU_FilterRuntime_t* rt = &filter_storage[filter_count];
    memcpy(&rt->config, &config, sizeof(PMU_FilterConfig_t));
    rt->channel_id = AllocateVirtualChannelID();
    if (rt->channel_id == 0) {
        JSON_SetError("Failed to allocate virtual channel ID for filter '%s'", id);
        return false;
    }
    rt->output_value = 0;
    rt->window_index = 0;
    rt->window_filled = 0;
    rt->ema_value = 0;
    memset(rt->window, 0, sizeof(rt->window));

    /* Add mapping from JSON channel_id to runtime channel_id */
    if (json_channel_id != 0) {
        AddChannelIdMapping(json_channel_id, rt->channel_id);
    }

    /* Register the channel */
    PMU_Channel_t channel = {0};
    channel.channel_id = rt->channel_id;
    channel.hw_class = PMU_CHANNEL_CLASS_INPUT_CALCULATED;
    channel.direction = PMU_CHANNEL_DIR_VIRTUAL;
    channel.format = PMU_CHANNEL_FORMAT_INT;
    channel.flags = PMU_CHANNEL_FLAG_ENABLED;
    strncpy(channel.name, id, sizeof(channel.name) - 1);
    channel.value = 0;
    PMU_Channel_Register(&channel);
    filter_count++;
    printf("[JSON] Parsed filter channel: %s (JSON_ID=%d, RT_ID=%d)\n",
           id, json_channel_id, rt->channel_id);
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

    /* Get channel name - required field */
    const char* id = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("Table2D missing required 'name' field");
        return false;
    }
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    config.x_axis_channel_id = JSON_GetChannelRef(channel_obj, "x_axis_channel");

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

    /* Get channel name - required field */
    const char* id = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("Table3D missing required 'name' field");
        return false;
    }
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    config.x_axis_channel_id = JSON_GetChannelRef(channel_obj, "x_axis_channel");
    config.y_axis_channel_id = JSON_GetChannelRef(channel_obj, "y_axis_channel");

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

    /* Get channel name - required field */
    const char* id = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("Switch missing required 'name' field");
        return false;
    }
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    /* Get JSON channel_id for mapping */
    uint16_t json_channel_id = (uint16_t)JSON_GetInt(channel_obj, "channel_id", 0);

    const char* type = JSON_GetString(channel_obj, "switch_type", "latching");
    strncpy(config.switch_type, type, sizeof(config.switch_type) - 1);

    config.input_up_channel_id = JSON_GetChannelRef(channel_obj, "input_up_channel");
    config.input_up_edge = JSON_GetEnum(channel_obj, "input_up_edge", logic_edge_map, PMU_EDGE_RISING);

    config.input_down_channel_id = JSON_GetChannelRef(channel_obj, "input_down_channel");
    config.input_down_edge = JSON_GetEnum(channel_obj, "input_down_edge", logic_edge_map, PMU_EDGE_RISING);

    config.state_first = (int16_t)JSON_GetInt(channel_obj, "state_first", 0);
    config.state_last = (int16_t)JSON_GetInt(channel_obj, "state_last", 10);
    config.state_default = (int16_t)JSON_GetInt(channel_obj, "state_default", 0);

    /* Store in runtime storage and register channel */
    if (switch_count >= PMU_MAX_SWITCH_CHANNELS) {
        JSON_SetError("Too many switch channels (max %d)", PMU_MAX_SWITCH_CHANNELS);
        return false;
    }
    PMU_SwitchRuntime_t* rt = &switch_storage[switch_count];
    memcpy(&rt->config, &config, sizeof(PMU_SwitchConfig_t));
    rt->channel_id = AllocateVirtualChannelID();
    if (rt->channel_id == 0) {
        JSON_SetError("Failed to allocate virtual channel ID for switch '%s'", id);
        return false;
    }
    rt->current_state = config.state_default;
    rt->output_value = config.state_default * 1000;

    /* Add mapping from JSON channel_id to runtime channel_id */
    if (json_channel_id != 0) {
        AddChannelIdMapping(json_channel_id, rt->channel_id);
    }

    /* Register the channel */
    PMU_Channel_t channel = {0};
    channel.channel_id = rt->channel_id;
    channel.hw_class = PMU_CHANNEL_CLASS_INPUT_CALCULATED;
    channel.direction = PMU_CHANNEL_DIR_VIRTUAL;
    channel.format = PMU_CHANNEL_FORMAT_INT;
    channel.flags = PMU_CHANNEL_FLAG_ENABLED;
    strncpy(channel.name, id, sizeof(channel.name) - 1);
    channel.value = rt->current_state * 1000; /* Scaled format */
    PMU_Channel_Register(&channel);
    switch_count++;
    printf("[JSON] Parsed switch channel: %s (JSON_ID=%d, RT_ID=%d)\n",
           id, json_channel_id, rt->channel_id);
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

    /* Get channel name - required field */
    const char* id = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("CAN RX missing required 'name' field");
        return false;
    }
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    config.can_bus = (uint8_t)JSON_GetInt(channel_obj, "can_bus", 1);
    config.message_id = (uint32_t)JSON_GetInt(channel_obj, "message_id", 0);
    config.is_extended = JSON_GetBool(channel_obj, "is_extended", false);
    config.start_bit = (uint8_t)JSON_GetInt(channel_obj, "start_bit", 0);
    config.bit_length = (uint8_t)JSON_GetInt(channel_obj, "length", 8);

    config.little_endian = JSON_GetEnum(channel_obj, "byte_order", can_byte_order_map, 1);
    config.data_type = JSON_GetEnum(channel_obj, "value_type", can_data_type_map, PMU_CAN_DATA_TYPE_UNSIGNED);

    config.multiplier = JSON_GetFloat(channel_obj, "factor", 1.0f);
    config.offset = JSON_GetFloat(channel_obj, "offset", 0.0f);
    config.timeout_ms = (uint16_t)JSON_GetInt(channel_obj, "timeout_ms", 1000);

    /* Register CAN RX channel */
    static uint16_t can_rx_count = 0;
    uint16_t channel_id = 100 + can_rx_count;  /* CAN RX channels start at 100 */

    PMU_Channel_t channel = {0};
    channel.channel_id = channel_id;
    strncpy(channel.name, config.id, sizeof(channel.name) - 1);
    channel.hw_class = PMU_CHANNEL_CLASS_INPUT_CAN;
    channel.format = PMU_CHANNEL_FORMAT_SIGNED;
    channel.min_value = -1000000;
    channel.max_value = 1000000;
    channel.physical_index = can_rx_count;
    channel.flags = PMU_CHANNEL_FLAG_ENABLED;

    PMU_Channel_Register(&channel);
    can_rx_count++;

    printf("[JSON] Registered CAN RX channel: %s (ID=%d)\n", config.id, channel_id);
    fflush(stdout);
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

    /* Get channel name - required field */
    const char* id = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("CAN TX missing required 'channel_name' field");
        return false;
    }
    strncpy(config.id, id, PMU_CHANNEL_ID_LEN - 1);

    config.can_bus = (uint8_t)JSON_GetInt(channel_obj, "can_bus", 1);
    config.message_id = (uint32_t)JSON_GetInt(channel_obj, "message_id", 0);
    config.is_extended = JSON_GetBool(channel_obj, "is_extended", false);
        /* Trigger channel for triggered mode */
    config.trigger_channel_id = JSON_GetChannelRef(channel_obj, "trigger_channel");

    /* Signals array (v3.0 format with numeric channel IDs) */
    cJSON* signals = cJSON_GetObjectItem(channel_obj, "signals");
    if (signals && cJSON_IsArray(signals)) {
        int sig_count = cJSON_GetArraySize(signals);
        config.signal_count = (sig_count > PMU_MAX_CAN_TX_SIGNALS) ?
                               PMU_MAX_CAN_TX_SIGNALS : (uint8_t)sig_count;

        for (int i = 0; i < config.signal_count; i++) {
            cJSON* sig = cJSON_GetArrayItem(signals, i);
            if (sig && cJSON_IsObject(sig)) {
                /* Use numeric channel ID (v3.0) */
                config.signals_v3[i].source_channel_id = JSON_GetChannelRef(sig, "source_channel");
                config.signals_v3[i].byte_offset = (uint8_t)JSON_GetInt(sig, "byte_offset", 0);
                config.signals_v3[i].multiplier = JSON_GetFloat(sig, "multiplier", 1.0f);

                config.signals_v3[i].little_endian = JSON_GetEnum(sig, "byte_order", can_byte_order_map, 1);

                /* Data type (signed/unsigned) and format (size) - combined lookup */
                int dtype = JSON_GetEnum(sig, "data_type", can_tx_dtype_map,
                                         CAN_DTYPE(PMU_CAN_DATA_TYPE_SIGNED, PMU_CAN_DATA_FORMAT_16BIT));
                config.signals_v3[i].data_type = (dtype >> 4) & 0x0F;
                config.signals_v3[i].data_format = dtype & 0x0F;

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

    /* Get channel name - required field */
    const char* id = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(id) == 0) {
        JSON_SetError("PID missing required 'channel_name' field");
        return false;
    }
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
    config.enabled = true;  /* Channels always enabled */
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
 * @brief Parse BlinkMarine keypad channel (J1939 protocol)
 * Supports PKP-2600-SI (12 buttons) and PKP-2800-SI (16 buttons)
 */
static bool JSON_ParseBlinkMarineKeypad(cJSON* channel_obj)
{
#ifdef JSON_PARSING_ENABLED
    PMU_BlinkMarine_Keypad_t keypad = {0};

    /* Get channel name - required field */
    const char* name = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(name) == 0) {
        JSON_SetError("BlinkMarine keypad missing required 'channel_name' field");
        return false;
    }
    strncpy(keypad.name, name, sizeof(keypad.name) - 1);

    /* Keypad type (integer: 0=PKP2600SI, 1=PKP2800SI) */
    keypad.type = (PMU_BlinkMarine_Type_t)JSON_GetInt(channel_obj, "type", PMU_BLINKMARINE_PKP2600SI);

    /* J1939 CAN configuration */
    keypad.can_bus = (PMU_CAN_Bus_t)JSON_GetInt(channel_obj, "can_bus", 1);
    keypad.source_address = (uint8_t)JSON_GetInt(channel_obj, "source_address", PMU_BM_DEFAULT_SRC_ADDR);
    keypad.keypad_identifier = (uint8_t)JSON_GetInt(channel_obj, "keypad_identifier", PMU_BM_DEFAULT_KEYPAD_ID);
    keypad.destination_address = (uint8_t)JSON_GetInt(channel_obj, "destination_address", PMU_BM_DEFAULT_DEST_ADDR);
    keypad.use_extended_id = JSON_GetBool(channel_obj, "use_extended_id", true);
    keypad.timeout_ms = (uint16_t)JSON_GetInt(channel_obj, "timeout_ms", PMU_BM_DEFAULT_TIMEOUT_MS);
    keypad.enabled = true;  /* Keypads always enabled */

    /* Brightness settings (0-63) */
    keypad.led_brightness = (uint8_t)JSON_GetInt(channel_obj, "led_brightness", 0x3F);
    keypad.backlight_brightness = (uint8_t)JSON_GetInt(channel_obj, "backlight_brightness", 0x20);
    keypad.backlight_color = (PMU_BM_LedColor_t)JSON_GetInt(channel_obj, "backlight_color", PMU_BM_LED_WHITE);

    /* Parse buttons configuration */
    cJSON* buttons_array = cJSON_GetObjectItem(channel_obj, "buttons");
    if (buttons_array && cJSON_IsArray(buttons_array)) {
        int button_count = cJSON_GetArraySize(buttons_array);
        uint8_t max_buttons = PMU_BlinkMarine_GetButtonCount(keypad.type);

        for (int i = 0; i < button_count && i < max_buttons; i++) {
            cJSON* button = cJSON_GetArrayItem(buttons_array, i);
            if (!button || !cJSON_IsObject(button)) continue;

            PMU_BM_ButtonConfig_t* btn = &keypad.buttons[i];

            /* Button enabled */
            btn->enabled = true;  /* Buttons always enabled */

            /* LED colors (indexes into PMU_BM_LedColor_t enum) */
            btn->led_on_color = (PMU_BM_LedColor_t)JSON_GetInt(button, "led_on_color", PMU_BM_LED_GREEN);
            btn->led_off_color = (PMU_BM_LedColor_t)JSON_GetInt(button, "led_off_color", PMU_BM_LED_OFF);
            btn->led_secondary = (PMU_BM_LedColor_t)JSON_GetInt(button, "led_secondary", PMU_BM_LED_RED);

            /* LED control mode */
            btn->led_ctrl_mode = (PMU_BM_LedCtrlMode_t)JSON_GetInt(button, "led_ctrl_mode", PMU_BM_LED_CTRL_FOLLOW);

            /* LED channel name for channel-controlled mode */
            const char* led_channel = JSON_GetString(button, "led_channel_name", "");
            strncpy(btn->led_channel_name, led_channel, sizeof(btn->led_channel_name) - 1);
        }
    }

    /* Add keypad */
    HAL_StatusTypeDef status = PMU_BlinkMarine_AddKeypad(&keypad);
    if (status != HAL_OK) {
        JSON_SetError("Failed to add BlinkMarine keypad '%s'", name);
        return false;
    }

    const char* type_names[] = { "PKP2600SI", "PKP2800SI" };
    printf("[JSON] Parsed BlinkMarine keypad: %s type=%s CAN%d SA:0x%02X KID:0x%02X\n",
           name, type_names[keypad.type], keypad.can_bus,
           keypad.source_address, keypad.keypad_identifier);
#else
    (void)channel_obj;
#endif
    return true;
}

/**
 * @brief Parse handler channel (stub - handlers configured via pmu_handler.c)
 */
static bool JSON_ParseHandler(cJSON* channel_obj)
{
    /* TODO: Implement handler parsing - for now just log and return success */
#ifdef JSON_PARSING_ENABLED
    const char* name = JSON_GetString(channel_obj, "channel_name", "");
    if (strlen(name) == 0) {
        JSON_SetError("Handler missing required 'channel_name' field");
        return false;
    }
    printf("[JSON] Handler '%s' parsing not yet implemented\n", name);
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
    static uint32_t call_counter = 0;
    call_counter++;
    if (call_counter % 5000 == 1) {
        printf("[PWR_UPDATE] Called, count=%d\n", call_counter);
        fflush(stdout);
    }

#ifdef JSON_PARSING_ENABLED
    static uint32_t debug_counter = 0;
    debug_counter++;

    /* Debug every 5 seconds */
    if (debug_counter % 5000 == 1) {
        printf("[PWR_UPD] power_output_count=%d\n", power_output_count);
        fflush(stdout);
    }

    for (uint8_t i = 0; i < power_output_count; i++) {
        PMU_PowerOutputConfig_t* cfg = &power_output_storage[i];

        /* Skip outputs without source_channel (always on or disabled) */
        if (cfg->source_channel_id == 0) {
            continue;
        }

        /* Resolve source channel to value
         * source_channel_id may be:
         * - A runtime ID (50-69 for digital inputs) if resolved from string name
         * - A JSON ID (small number like 6) if parsed from numeric field
         * ResolveToRuntimeId handles both cases correctly.
         */
        const PMU_Channel_t* source_ch = NULL;
        if (cfg->source_channel_id != 0) {
            /* Smart resolve: use directly if known runtime ID, otherwise map */
            uint16_t runtime_id = ResolveToRuntimeId(cfg->source_channel_id);
            source_ch = PMU_Channel_GetInfo(runtime_id);

            /* Debug output every 1000 calls (~1 second at 1kHz) */
            if (debug_counter % 1000 == 1) {
                printf("[PWR_OUT] '%s': src_id=%d, runtime=%d, ch=%p\n",
                       cfg->id, cfg->source_channel_id, runtime_id, (void*)source_ch);
                if (source_ch) {
                    printf("  -> src_name='%s', value=%d\n", source_ch->name, source_ch->value);
                }
                fflush(stdout);
            }
        }
        /* source_ch already resolved by ID */
        if (!source_ch) {
            /* Source channel not found - skip */
            continue;
        }

        int32_t source_value = source_ch->value;
        bool output_active = (source_value > 0);

        /* Debug output every 1000 calls */
        if (debug_counter % 1000 == 1) {
            printf("  -> value=%d, active=%d, pins=%d\n", source_value, output_active, cfg->output_pin_count);
            fflush(stdout);
        }

        /* Apply to all configured pins */
        for (int p = 0; p < cfg->output_pin_count; p++) {
            uint8_t pin = cfg->output_pins[p];
            if (pin >= 30) continue;

            /* Skip if manual override is set */
            if (PMU_PROFET_HasManualOverride(pin)) {
                if (debug_counter % 1000 == 1) {
                    printf("  -> pin %d has MANUAL OVERRIDE!\n", pin);
                    fflush(stdout);
                }
                continue;
            }

            if (output_active) {
                if (cfg->pwm_enabled) {
                    /* Use fixed duty or resolve duty_channel */
                    float duty = cfg->duty_fixed;
                    if (cfg->duty_channel_id != 0) {
                        const PMU_Channel_t* duty_ch = PMU_Channel_GetInfo(cfg->duty_channel_id);
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


/* ============================================================================
 * Logic Channel Runtime Functions
 * ============================================================================ */

/**
 * @brief Update all logic channels - call from main loop at ~100-500Hz
 */
void PMU_LogicChannel_Update(void)
{
#ifdef JSON_PARSING_ENABLED
    for (uint8_t i = 0; i < logic_count; i++) {
        PMU_LogicRuntime_t* rt = &logic_storage[i];
        PMU_LogicConfig_t* cfg = &rt->config;

        int32_t input1 = GetInputChannelValueById(cfg->channel_id);
        int32_t input2 = GetInputChannelValueById(cfg->channel_2_id);

        bool result = false;

        uint32_t now = HAL_GetTick();

        switch (cfg->operation) {
            /* Basic boolean operations - C-style cast: value > 0 = true */
            case PMU_LOGIC_IS_TRUE:
                result = (input1 > 0);
                break;
            case PMU_LOGIC_IS_FALSE:
                result = (input1 <= 0);
                break;

            /* Two-input logic operations */
            case PMU_LOGIC_AND:
                result = (input1 > 0) && (input2 > 0);
                break;
            case PMU_LOGIC_OR:
                result = (input1 > 0) || (input2 > 0);
                break;
            case PMU_LOGIC_XOR:
                result = ((input1 > 0) != (input2 > 0));
                break;
            case PMU_LOGIC_NOT:
                result = (input1 <= 0);  /* Same as IS_FALSE */
                break;
            case PMU_LOGIC_NAND:
                result = !((input1 > 0) && (input2 > 0));
                break;
            case PMU_LOGIC_NOR:
                result = !((input1 > 0) || (input2 > 0));
                break;

            /* Comparison operations - constant in same units as channel */
            case PMU_LOGIC_EQUAL:
                result = (input1 == (int32_t)cfg->constant);
                break;
            case PMU_LOGIC_NOT_EQUAL:
                result = (input1 != (int32_t)cfg->constant);
                break;
            case PMU_LOGIC_LESS:
                result = (input1 < (int32_t)cfg->constant);
                break;
            case PMU_LOGIC_GREATER:
                result = (input1 > (int32_t)cfg->constant);
                break;
            case PMU_LOGIC_LESS_EQUAL:
                result = (input1 <= (int32_t)cfg->constant);
                break;
            case PMU_LOGIC_GREATER_EQUAL:
                result = (input1 >= (int32_t)cfg->constant);
                break;

            /* IN_RANGE: True when lower <= input <= upper */
            case PMU_LOGIC_IN_RANGE: {
                int32_t lower = (int32_t)cfg->lower_value;
                int32_t upper = (int32_t)cfg->upper_value;
                result = (input1 >= lower && input1 <= upper);
                break;
            }

            /* CHANGED: Output true when input changes by threshold amount */
            case PMU_LOGIC_CHANGED: {
                int32_t diff = input1 - rt->prev_input_value;
                if (diff < 0) diff = -diff;  /* abs */
                if (diff >= (int32_t)cfg->threshold) {
                    /* Value changed by threshold - start output timer */
                    rt->delay_start_ms = now;
                    rt->delay_active = true;
                }
                /* Output stays true for time_on_s after change detected */
                if (rt->delay_active) {
                    uint32_t time_on_ms = (uint32_t)(cfg->time_on_s * 1000);
                    if (now - rt->delay_start_ms < time_on_ms) {
                        result = true;
                    } else {
                        rt->delay_active = false;
                    }
                }
                break;
            }

            /* HYSTERESIS: Turn on above upper, off below lower */
            case PMU_LOGIC_HYSTERESIS: {
                int32_t upper = (int32_t)cfg->upper_value;
                int32_t lower = (int32_t)cfg->lower_value;
                if (cfg->polarity == PMU_POLARITY_NORMAL) {
                    /* Normal: output ON when input >= upper, OFF when input <= lower */
                    if (input1 >= upper) {
                        rt->latch_state = true;
                    } else if (input1 <= lower) {
                        rt->latch_state = false;
                    }
                } else {
                    /* Inverted: output OFF when input >= upper, ON when input <= lower */
                    if (input1 >= upper) {
                        rt->latch_state = false;
                    } else if (input1 <= lower) {
                        rt->latch_state = true;
                    }
                }
                result = rt->latch_state;
                break;
            }

            /* SET_RESET_LATCH: SR flip-flop */
            case PMU_LOGIC_SET_RESET_LATCH: {
                int32_t set_val = GetInputChannelValueById(cfg->set_channel_id);
                int32_t reset_val = GetInputChannelValueById(cfg->reset_channel_id);
                /* Set has priority over reset */
                if (set_val > 0 && rt->prev_input_value <= 0) {
                    /* Rising edge on set */
                    rt->latch_state = true;
                } else if (reset_val > 0 && rt->prev_input2_value <= 0) {
                    /* Rising edge on reset */
                    rt->latch_state = false;
                }
                result = rt->latch_state;
                /* Store set/reset for edge detection */
                rt->prev_input_value = set_val;
                rt->prev_input2_value = reset_val;
                break;
            }

            /* TOGGLE: Toggle output on edge of toggle channel */
            case PMU_LOGIC_TOGGLE: {
                int32_t toggle_val = GetInputChannelValueById(cfg->toggle_channel_id);
                int32_t set_val = GetInputChannelValueById(cfg->set_channel_id);
                int32_t reset_val = GetInputChannelValueById(cfg->reset_channel_id);

                /* Check for set/reset override */
                if (set_val > 0) {
                    rt->latch_state = true;
                } else if (reset_val > 0) {
                    rt->latch_state = false;
                } else {
                    /* Check for toggle edge */
                    bool edge_detected = false;
                    if (cfg->edge == PMU_EDGE_RISING) {
                        edge_detected = (toggle_val > 0 && rt->prev_input_value <= 0);
                    } else {
                        edge_detected = (toggle_val <= 0 && rt->prev_input_value > 0);
                    }
                    if (edge_detected) {
                        rt->latch_state = !rt->latch_state;
                    }
                }
                result = rt->latch_state;
                rt->prev_input_value = toggle_val;
                break;
            }

            /* PULSE: Generate pulse(s) on trigger edge */
            case PMU_LOGIC_PULSE: {
                bool edge_detected = false;
                if (cfg->edge == PMU_EDGE_RISING) {
                    edge_detected = (input1 > 0 && rt->prev_input_value <= 0);
                } else {
                    edge_detected = (input1 <= 0 && rt->prev_input_value > 0);
                }

                if (edge_detected) {
                    if (!rt->delay_active || cfg->retrigger) {
                        rt->delay_start_ms = now;
                        rt->delay_active = true;
                    }
                }

                if (rt->delay_active) {
                    uint32_t time_on_ms = (uint32_t)(cfg->time_on_s * 1000);
                    uint32_t total_time = time_on_ms * cfg->pulse_count;
                    uint32_t elapsed = now - rt->delay_start_ms;

                    if (elapsed < total_time) {
                        /* Which pulse are we in? */
                        uint32_t pulse_idx = elapsed / time_on_ms;
                        /* First half of each pulse is ON */
                        uint32_t within_pulse = elapsed % time_on_ms;
                        result = (within_pulse < time_on_ms / 2);
                    } else {
                        rt->delay_active = false;
                    }
                }
                break;
            }

            /* FLASH: Periodic on/off when input is true */
            case PMU_LOGIC_FLASH: {
                if (input1 > 0) {
                    uint32_t time_on_ms = (uint32_t)(cfg->time_on_s * 1000);
                    uint32_t time_off_ms = (uint32_t)(cfg->time_off_s * 1000);
                    uint32_t period = time_on_ms + time_off_ms;

                    if (period > 0) {
                        uint32_t elapsed = now - rt->flash_last_toggle;
                        uint32_t threshold = rt->flash_state ? time_on_ms : time_off_ms;

                        if (elapsed >= threshold) {
                            rt->flash_state = !rt->flash_state;
                            rt->flash_last_toggle = now;
                        }
                        result = rt->flash_state;
                    }
                } else {
                    rt->flash_state = false;
                    rt->flash_last_toggle = now;
                }
                break;
            }

            /* EDGE_RISING: One-shot pulse on 0->1 transition */
            case PMU_LOGIC_EDGE_RISING:
                result = (input1 > 0 && rt->prev_input_value <= 0);
                break;

            /* EDGE_FALLING: One-shot pulse on 1->0 transition */
            case PMU_LOGIC_EDGE_FALLING:
                result = (input1 <= 0 && rt->prev_input_value > 0);
                break;

            default:
                result = false;
                break;
        }

        int32_t new_value = result ? 1000 : 0;
        rt->output_value = new_value;
        PMU_Channel_SetValue(rt->channel_id, new_value);

        /* Store prev values for operations that don't override them */
        if (cfg->operation != PMU_LOGIC_SET_RESET_LATCH &&
            cfg->operation != PMU_LOGIC_TOGGLE) {
            rt->prev_input_value = input1;
            rt->prev_input2_value = input2;
        }
    }
#endif
}

/* ============================================================================
 * Number Channel Runtime Functions
 * ============================================================================ */

/**
 * @brief Update all number channels
 */
void PMU_NumberChannel_Update(void)
{
#ifdef JSON_PARSING_ENABLED
    for (uint8_t i = 0; i < number_count; i++) {
        PMU_NumberRuntime_t* rt = &number_storage[i];
        PMU_NumberConfig_t* cfg = &rt->config;

        int32_t result = 0;
        switch (cfg->operation) {
            case PMU_MATH_CONSTANT:
                result = (int32_t)(cfg->constant_value * 1000);
                break;
            case PMU_MATH_CHANNEL:
                if (cfg->input_count > 0) {
                    result = GetInputChannelValueById(cfg->input_ids[0]);
                }
                break;
            case PMU_MATH_ADD:
                for (uint8_t j = 0; j < cfg->input_count; j++) {
                    result += GetInputChannelValueById(cfg->input_ids[j]);
                }
                break;
            case PMU_MATH_SUBTRACT:
                if (cfg->input_count > 0) {
                    result = GetInputChannelValueById(cfg->input_ids[0]);
                    for (uint8_t j = 1; j < cfg->input_count; j++) {
                        result -= GetInputChannelValueById(cfg->input_ids[j]);
                    }
                }
                break;
            case PMU_MATH_MULTIPLY:
                result = 1000;
                for (uint8_t j = 0; j < cfg->input_count; j++) {
                    result = (result * GetInputChannelValueById(cfg->input_ids[j])) / 1000;
                }
                break;
            case PMU_MATH_DIVIDE:
                if (cfg->input_count >= 2) {
                    int32_t divisor = GetInputChannelValueById(cfg->input_ids[1]);
                    if (divisor != 0) {
                        result = (GetInputChannelValueById(cfg->input_ids[0]) * 1000) / divisor;
                    }
                }
                break;
            case PMU_MATH_MIN:
                if (cfg->input_count > 0) {
                    result = GetInputChannelValueById(cfg->input_ids[0]);
                    for (uint8_t j = 1; j < cfg->input_count; j++) {
                        int32_t val = GetInputChannelValueById(cfg->input_ids[j]);
                        if (val < result) result = val;
                    }
                }
                break;
            case PMU_MATH_MAX:
                if (cfg->input_count > 0) {
                    result = GetInputChannelValueById(cfg->input_ids[0]);
                    for (uint8_t j = 1; j < cfg->input_count; j++) {
                        int32_t val = GetInputChannelValueById(cfg->input_ids[j]);
                        if (val > result) result = val;
                    }
                }
                break;
            default:
                break;
        }

        /* Apply clamp */
        int32_t clamp_min = (int32_t)(cfg->clamp_min * 1000);
        int32_t clamp_max = (int32_t)(cfg->clamp_max * 1000);
        if (clamp_max > clamp_min) {
            if (result < clamp_min) result = clamp_min;
            if (result > clamp_max) result = clamp_max;
        }

        rt->output_value = result;
        PMU_Channel_SetValue(rt->channel_id, result);
    }
#endif
}

/* ============================================================================
 * Switch Channel Runtime Functions
 * ============================================================================ */

/**
 * @brief Update all switch channels
 */
void PMU_SwitchChannel_Update(void)
{
#ifdef JSON_PARSING_ENABLED
    for (uint8_t i = 0; i < switch_count; i++) {
        PMU_SwitchRuntime_t* rt = &switch_storage[i];
        PMU_SwitchConfig_t* cfg = &rt->config;

        int32_t up_val = GetInputChannelValueById(cfg->input_up_channel_id);
        int32_t down_val = GetInputChannelValueById(cfg->input_down_channel_id);

        /* Simple edge detection for up/down */
        static int32_t prev_up[PMU_MAX_SWITCH_CHANNELS] = {0};
        static int32_t prev_down[PMU_MAX_SWITCH_CHANNELS] = {0};

        bool up_edge = (up_val > 0) && (prev_up[i] <= 0);
        bool down_edge = (down_val > 0) && (prev_down[i] <= 0);

        prev_up[i] = up_val;
        prev_down[i] = down_val;

        if (up_edge && rt->current_state < cfg->state_last) {
            rt->current_state++;
        }
        if (down_edge && rt->current_state > cfg->state_first) {
            rt->current_state--;
        }

        rt->output_value = rt->current_state * 1000;
        PMU_Channel_SetValue(rt->channel_id, rt->output_value);
    }
#endif
}

/* ============================================================================
 * Filter Channel Runtime Functions
 * ============================================================================ */

/**
 * @brief Update all filter channels
 */
void PMU_FilterChannel_Update(void)
{
#ifdef JSON_PARSING_ENABLED
    for (uint8_t i = 0; i < filter_count; i++) {
        PMU_FilterRuntime_t* rt = &filter_storage[i];
        PMU_FilterConfig_t* cfg = &rt->config;

        int32_t input_val = GetInputChannelValueById(cfg->input_channel_id);
        int32_t result = input_val;

        switch (cfg->filter_type) {
            case PMU_FILTER_LOW_PASS: {
                /* Low pass filter (exponential moving average) */
                /* time_constant is in seconds, higher = slower response */
                int32_t alpha = (int32_t)(1000.0f / (1.0f + cfg->time_constant * 100.0f));
                if (alpha < 10) alpha = 10;    /* Min 1% */
                if (alpha > 1000) alpha = 1000; /* Max 100% */
                rt->ema_value = ((alpha * input_val) + ((1000 - alpha) * rt->ema_value)) / 1000;
                result = rt->ema_value;
                break;
            }
            case PMU_FILTER_MOVING_AVG: {
                /* Simple moving average */
                rt->window[rt->window_index] = input_val;
                rt->window_index = (rt->window_index + 1) % cfg->window_size;
                if (rt->window_filled < cfg->window_size) rt->window_filled++;

                int32_t sum = 0;
                uint8_t count = rt->window_filled;
                for (uint8_t j = 0; j < count; j++) {
                    sum += rt->window[j];
                }
                result = count > 0 ? sum / count : input_val;
                break;
            }
            case PMU_FILTER_MEDIAN: {
                /* Median filter */
                rt->window[rt->window_index] = input_val;
                rt->window_index = (rt->window_index + 1) % cfg->window_size;
                if (rt->window_filled < cfg->window_size) rt->window_filled++;

                /* Sort and find median */
                int32_t sorted[PMU_FILTER_WINDOW_MAX];
                uint8_t count = rt->window_filled;
                for (uint8_t j = 0; j < count; j++) sorted[j] = rt->window[j];
                /* Bubble sort */
                for (uint8_t j = 0; j < count - 1; j++) {
                    for (uint8_t k = 0; k < count - j - 1; k++) {
                        if (sorted[k] > sorted[k+1]) {
                            int32_t temp = sorted[k];
                            sorted[k] = sorted[k+1];
                            sorted[k+1] = temp;
                        }
                    }
                }
                result = sorted[count / 2];
                break;
            }
            default:
                break;
        }

        rt->output_value = result;
        PMU_Channel_SetValue(rt->channel_id, result);
    }
#endif
}

/* ============================================================================
 * Timer Channel Runtime Functions
 * ============================================================================ */

/**
 * @brief Update all timer channels - call from main loop at ~100-500Hz
 */
void PMU_TimerChannel_Update(void)
{
#ifdef JSON_PARSING_ENABLED
    uint32_t now = HAL_GetTick();

    for (uint8_t i = 0; i < timer_count; i++) {
        PMU_TimerRuntime_t* rt = &timer_storage[i];
        PMU_TimerConfig_t* cfg = &rt->config;

        /* Get start trigger value */
        int32_t start_val = GetInputChannelValueById(cfg->start_channel_id);
        int32_t stop_val = GetInputChannelValueById(cfg->stop_channel_id);

        /* Edge detection for start */
        bool start_edge = false;
        if (cfg->start_edge == PMU_EDGE_RISING) {
            start_edge = (start_val > 0 && rt->prev_start_value <= 0);
        } else if (cfg->start_edge == PMU_EDGE_FALLING) {
            start_edge = (start_val <= 0 && rt->prev_start_value > 0);
        } else if (cfg->start_edge == PMU_EDGE_BOTH) {
            start_edge = ((start_val > 0) != (rt->prev_start_value > 0));
        } else if (cfg->start_edge == PMU_EDGE_LEVEL) {
            /* Level trigger - start when input is high */
            start_edge = (start_val > 0 && !rt->running);
        }

        /* Edge detection for stop */
        bool stop_edge = false;
        if (cfg->stop_channel_id != 0) {
            if (cfg->stop_edge == PMU_EDGE_RISING) {
                stop_edge = (stop_val > 0 && rt->prev_stop_value <= 0);
            } else if (cfg->stop_edge == PMU_EDGE_FALLING) {
                stop_edge = (stop_val <= 0 && rt->prev_stop_value > 0);
            } else if (cfg->stop_edge == PMU_EDGE_BOTH) {
                stop_edge = ((stop_val > 0) != (rt->prev_stop_value > 0));
            } else if (cfg->stop_edge == PMU_EDGE_LEVEL) {
                stop_edge = (stop_val > 0 && rt->running);
            }
        }

        /* Start timer on edge */
        if (start_edge && !rt->running) {
            rt->running = true;
            rt->start_time_ms = now;
            rt->output_value = 0;
        }

        /* Stop timer on edge or limit */
        if (stop_edge && rt->running) {
            rt->running = false;
        }

        /* Update timer value if running */
        if (rt->running) {
            uint32_t elapsed_ms = now - rt->start_time_ms;
            uint32_t limit_ms = ((uint32_t)cfg->limit_hours * 3600 +
                                 (uint32_t)cfg->limit_minutes * 60 +
                                 (uint32_t)cfg->limit_seconds) * 1000;

            if (cfg->mode == PMU_TIMER_MODE_COUNT_UP) {
                rt->output_value = (int32_t)elapsed_ms;
                /* Check limit */
                if (limit_ms > 0 && elapsed_ms >= limit_ms) {
                    rt->output_value = (int32_t)limit_ms;
                    rt->running = false;
                }
            } else {
                /* Count down */
                if (elapsed_ms >= limit_ms) {
                    rt->output_value = 0;
                    rt->running = false;
                } else {
                    rt->output_value = (int32_t)(limit_ms - elapsed_ms);
                }
            }
        }

        /* Update channel values */
        /* Main channel outputs running state (1000 when running, 0 when stopped) */
        PMU_Channel_SetValue(rt->channel_id, rt->running ? 1000 : 0);
        /* Elapsed channel outputs time in milliseconds */
        PMU_Channel_SetValue(rt->elapsed_channel_id, rt->output_value);

        rt->prev_start_value = start_val;
        rt->prev_stop_value = stop_val;
    }
#endif
}

/**
 * @brief Clear timer storage
 */
void PMU_TimerChannel_ClearConfig(void)
{
    memset(timer_storage, 0, sizeof(timer_storage));
    timer_count = 0;
}

/**
 * @brief Get timer channel count
 */
uint8_t PMU_TimerChannel_GetCount(void)
{
    return timer_count;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
