/**
 ******************************************************************************
 * @file           : pmu_datalog.c
 * @brief          : High-Frequency Data Logger Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_datalog.h"
#include "pmu_channel.h"
#include "pmu_profet.h"
#include "pmu_adc.h"
#include <string.h>
#include <stdio.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/

/* Sample buffer entry (max size per sample) */
#define SAMPLE_MAX_SIZE     512

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/

/* Registered channels */
static PMU_DataLog_Channel_t s_channels[DATALOG_MAX_CHANNELS];
static uint16_t s_channel_count = 0;

/* Configuration */
static PMU_DataLog_Config_t s_config = {
    .sample_rate_hz = DATALOG_DEFAULT_RATE,
    .enable_file = false,
    .enable_streaming = true,
    .log_file_path = "datalog.plog",
    .session_name = "Session",
    .max_file_size_mb = 100,
    .buffer_size = DATALOG_BUFFER_SIZE,
};

/* State */
static PMU_DataLog_State_t s_state = DATALOG_STATE_IDLE;
static PMU_DataLog_Stats_t s_stats = {0};

/* Timing */
static uint32_t s_last_sample_tick = 0;
static uint32_t s_sample_interval_ms = 10;  /* 100 Hz default */
static uint32_t s_start_time = 0;

/* Sample buffer (circular) */
static uint8_t s_sample_buffer[DATALOG_BUFFER_SIZE * SAMPLE_MAX_SIZE];
static uint32_t s_buffer_head = 0;
static uint32_t s_buffer_tail = 0;
static uint32_t s_buffer_count = 0;

/* File handle */
static FILE* s_log_file = NULL;

/* Streaming callback */
static PMU_DataLog_Callback_t s_callback = NULL;

/* Initialization flag */
static bool s_initialized = false;

/* Current sample being built */
static uint8_t s_current_sample[SAMPLE_MAX_SIZE];
static uint16_t s_current_sample_len = 0;

/* Private function prototypes -----------------------------------------------*/
static void CollectSample(void);
static uint8_t GetTypeSize(PMU_DataLog_Type_t type);
static void WriteFileHeader(void);
static int32_t GetChannelRawValue(uint16_t channel_id);

/* External functions for data access */
extern uint32_t HAL_GetTick(void);

/* Exported functions --------------------------------------------------------*/

HAL_StatusTypeDef PMU_DataLog_Init(void)
{
    if (s_initialized) {
        return HAL_OK;
    }

    /* Clear channels */
    memset(s_channels, 0, sizeof(s_channels));
    s_channel_count = 0;

    /* Clear stats */
    memset(&s_stats, 0, sizeof(s_stats));

    /* Clear buffer */
    s_buffer_head = 0;
    s_buffer_tail = 0;
    s_buffer_count = 0;

    s_state = DATALOG_STATE_IDLE;
    s_initialized = true;

    return HAL_OK;
}

HAL_StatusTypeDef PMU_DataLog_DeInit(void)
{
    if (!s_initialized) {
        return HAL_OK;
    }

    PMU_DataLog_Stop();

    if (s_log_file) {
        fclose(s_log_file);
        s_log_file = NULL;
    }

    s_initialized = false;
    return HAL_OK;
}

HAL_StatusTypeDef PMU_DataLog_Configure(const PMU_DataLog_Config_t* config)
{
    if (!config) {
        return HAL_ERROR;
    }

    /* Validate rate */
    if (config->sample_rate_hz < DATALOG_MIN_RATE_HZ ||
        config->sample_rate_hz > DATALOG_MAX_RATE_HZ) {
        return HAL_ERROR;
    }

    memcpy(&s_config, config, sizeof(PMU_DataLog_Config_t));
    s_sample_interval_ms = 1000 / s_config.sample_rate_hz;

    return HAL_OK;
}

HAL_StatusTypeDef PMU_DataLog_GetConfig(PMU_DataLog_Config_t* config)
{
    if (!config) {
        return HAL_ERROR;
    }

    memcpy(config, &s_config, sizeof(PMU_DataLog_Config_t));
    return HAL_OK;
}

int16_t PMU_DataLog_RegisterChannel(const PMU_DataLog_Channel_t* channel)
{
    if (!channel || s_channel_count >= DATALOG_MAX_CHANNELS) {
        return -1;
    }

    /* Check for duplicate ID */
    for (uint16_t i = 0; i < s_channel_count; i++) {
        if (s_channels[i].id == channel->id) {
            return -1;
        }
    }

    s_channels[s_channel_count] = *channel;
    s_channel_count++;

    return channel->id;
}

HAL_StatusTypeDef PMU_DataLog_UnregisterChannel(uint16_t channel_id)
{
    for (uint16_t i = 0; i < s_channel_count; i++) {
        if (s_channels[i].id == channel_id) {
            /* Shift remaining channels */
            for (uint16_t j = i; j < s_channel_count - 1; j++) {
                s_channels[j] = s_channels[j + 1];
            }
            s_channel_count--;
            return HAL_OK;
        }
    }
    return HAL_ERROR;
}

const PMU_DataLog_Channel_t* PMU_DataLog_GetChannel(uint16_t channel_id)
{
    for (uint16_t i = 0; i < s_channel_count; i++) {
        if (s_channels[i].id == channel_id) {
            return &s_channels[i];
        }
    }
    return NULL;
}

uint16_t PMU_DataLog_GetChannelCount(void)
{
    return s_channel_count;
}

HAL_StatusTypeDef PMU_DataLog_SetChannelEnabled(uint16_t channel_id, bool enabled)
{
    for (uint16_t i = 0; i < s_channel_count; i++) {
        if (s_channels[i].id == channel_id) {
            s_channels[i].enabled = enabled ? 1 : 0;
            return HAL_OK;
        }
    }
    return HAL_ERROR;
}

HAL_StatusTypeDef PMU_DataLog_Start(void)
{
    if (!s_initialized) {
        return HAL_ERROR;
    }

    if (s_state == DATALOG_STATE_RUNNING) {
        return HAL_OK;  /* Already running */
    }

    /* Open file if enabled */
    if (s_config.enable_file) {
        s_log_file = fopen(s_config.log_file_path, "wb");
        if (s_log_file) {
            WriteFileHeader();
        }
    }

    /* Reset stats */
    s_stats.samples_logged = 0;
    s_stats.samples_dropped = 0;
    s_stats.bytes_written = 0;
    s_stats.duration_ms = 0;

    /* Clear buffer */
    s_buffer_head = 0;
    s_buffer_tail = 0;
    s_buffer_count = 0;

    s_start_time = HAL_GetTick();
    s_last_sample_tick = s_start_time;
    s_state = DATALOG_STATE_RUNNING;
    s_stats.state = s_state;

    return HAL_OK;
}

HAL_StatusTypeDef PMU_DataLog_Stop(void)
{
    if (s_state == DATALOG_STATE_IDLE) {
        return HAL_OK;
    }

    s_state = DATALOG_STATE_IDLE;
    s_stats.state = s_state;

    /* Flush and close file */
    if (s_log_file) {
        PMU_DataLog_Flush();
        fclose(s_log_file);
        s_log_file = NULL;
    }

    return HAL_OK;
}

HAL_StatusTypeDef PMU_DataLog_Pause(void)
{
    if (s_state != DATALOG_STATE_RUNNING) {
        return HAL_ERROR;
    }

    s_state = DATALOG_STATE_PAUSED;
    s_stats.state = s_state;
    return HAL_OK;
}

HAL_StatusTypeDef PMU_DataLog_Resume(void)
{
    if (s_state != DATALOG_STATE_PAUSED) {
        return HAL_ERROR;
    }

    s_state = DATALOG_STATE_RUNNING;
    s_stats.state = s_state;
    s_last_sample_tick = HAL_GetTick();
    return HAL_OK;
}

PMU_DataLog_State_t PMU_DataLog_GetState(void)
{
    return s_state;
}

void PMU_DataLog_GetStats(PMU_DataLog_Stats_t* stats)
{
    if (!stats) {
        return;
    }

    s_stats.state = s_state;
    s_stats.buffer_usage_pct = (s_buffer_count * 100) / s_config.buffer_size;

    if (s_state == DATALOG_STATE_RUNNING) {
        s_stats.duration_ms = HAL_GetTick() - s_start_time;
        if (s_stats.duration_ms > 0) {
            s_stats.current_rate_hz = (s_stats.samples_logged * 1000) / s_stats.duration_ms;
        }
    }

    *stats = s_stats;
}

void PMU_DataLog_Update(void)
{
    if (s_state != DATALOG_STATE_RUNNING) {
        return;
    }

    uint32_t now = HAL_GetTick();
    uint32_t elapsed = now - s_last_sample_tick;

    if (elapsed >= s_sample_interval_ms) {
        s_last_sample_tick = now;
        CollectSample();
    }

    /* Update duration */
    s_stats.duration_ms = now - s_start_time;
}

void PMU_DataLog_SetCallback(PMU_DataLog_Callback_t callback)
{
    s_callback = callback;
}

uint16_t PMU_DataLog_RegisterDefaultChannels(void)
{
    uint16_t count = 0;
    PMU_DataLog_Channel_t ch;

    /* System channels */
    memset(&ch, 0, sizeof(ch));
    ch.id = 0x0001;
    strcpy(ch.name, "Battery Voltage");
    strcpy(ch.unit, "V");
    ch.type = DATALOG_TYPE_FLOAT;
    ch.category = DATALOG_CAT_SYSTEM;
    ch.scale = 0.001f;
    ch.min_value = 0;
    ch.max_value = 30;
    ch.decimal_places = 2;
    ch.enabled = 1;
    if (PMU_DataLog_RegisterChannel(&ch) >= 0) count++;

    ch.id = 0x0002;
    strcpy(ch.name, "Board Temp");
    strcpy(ch.unit, "C");
    ch.type = DATALOG_TYPE_INT16;
    ch.min_value = -40;
    ch.max_value = 125;
    ch.scale = 1.0f;
    if (PMU_DataLog_RegisterChannel(&ch) >= 0) count++;

    /* PROFET outputs (30 channels) */
    for (int i = 0; i < 30; i++) {
        /* Output state */
        ch.id = 0x0100 + i * 2;
        snprintf(ch.name, sizeof(ch.name), "OUT%d State", i + 1);
        strcpy(ch.unit, "");
        ch.type = DATALOG_TYPE_UINT8;
        ch.category = DATALOG_CAT_OUTPUT;
        ch.scale = 1.0f;
        ch.min_value = 0;
        ch.max_value = 1;
        ch.decimal_places = 0;
        ch.enabled = 1;
        if (PMU_DataLog_RegisterChannel(&ch) >= 0) count++;

        /* Output current */
        ch.id = 0x0100 + i * 2 + 1;
        snprintf(ch.name, sizeof(ch.name), "OUT%d Current", i + 1);
        strcpy(ch.unit, "A");
        ch.type = DATALOG_TYPE_FLOAT;
        ch.scale = 0.001f;
        ch.min_value = 0;
        ch.max_value = 30;
        ch.decimal_places = 2;
        if (PMU_DataLog_RegisterChannel(&ch) >= 0) count++;
    }

    /* Analog inputs (20 channels) */
    for (int i = 0; i < 20; i++) {
        ch.id = 0x0200 + i;
        snprintf(ch.name, sizeof(ch.name), "AIN%d", i + 1);
        strcpy(ch.unit, "V");
        ch.type = DATALOG_TYPE_FLOAT;
        ch.category = DATALOG_CAT_INPUT;
        ch.scale = 1.0f;
        ch.min_value = 0;
        ch.max_value = 5;
        ch.decimal_places = 3;
        ch.enabled = 1;
        if (PMU_DataLog_RegisterChannel(&ch) >= 0) count++;
    }

    /* H-Bridge channels (4 bridges) */
    for (int i = 0; i < 4; i++) {
        /* Position */
        ch.id = 0x0300 + i * 4;
        snprintf(ch.name, sizeof(ch.name), "HB%d Position", i + 1);
        strcpy(ch.unit, "%");
        ch.type = DATALOG_TYPE_INT16;
        ch.category = DATALOG_CAT_HBRIDGE;
        ch.scale = 0.1f;
        ch.min_value = 0;
        ch.max_value = 100;
        ch.decimal_places = 1;
        ch.enabled = 1;
        if (PMU_DataLog_RegisterChannel(&ch) >= 0) count++;

        /* Current */
        ch.id = 0x0300 + i * 4 + 1;
        snprintf(ch.name, sizeof(ch.name), "HB%d Current", i + 1);
        strcpy(ch.unit, "A");
        ch.type = DATALOG_TYPE_FLOAT;
        ch.scale = 1.0f;
        ch.min_value = -30;
        ch.max_value = 30;
        ch.decimal_places = 2;
        if (PMU_DataLog_RegisterChannel(&ch) >= 0) count++;

        /* PWM Duty */
        ch.id = 0x0300 + i * 4 + 2;
        snprintf(ch.name, sizeof(ch.name), "HB%d PWM", i + 1);
        strcpy(ch.unit, "%");
        ch.type = DATALOG_TYPE_UINT16;
        ch.scale = 0.1f;
        ch.min_value = 0;
        ch.max_value = 100;
        ch.decimal_places = 1;
        if (PMU_DataLog_RegisterChannel(&ch) >= 0) count++;

        /* Mode */
        ch.id = 0x0300 + i * 4 + 3;
        snprintf(ch.name, sizeof(ch.name), "HB%d Mode", i + 1);
        strcpy(ch.unit, "");
        ch.type = DATALOG_TYPE_UINT8;
        ch.scale = 1.0f;
        ch.min_value = 0;
        ch.max_value = 5;
        ch.decimal_places = 0;
        if (PMU_DataLog_RegisterChannel(&ch) >= 0) count++;
    }

    return count;
}

HAL_StatusTypeDef PMU_DataLog_Flush(void)
{
    if (s_log_file) {
        fflush(s_log_file);
    }
    return HAL_OK;
}

/* Private functions ---------------------------------------------------------*/

static void CollectSample(void)
{
    /* Build sample: timestamp + channel values */
    s_current_sample_len = 0;

    /* Timestamp (4 bytes) */
    uint32_t timestamp = HAL_GetTick() - s_start_time;
    memcpy(&s_current_sample[s_current_sample_len], &timestamp, 4);
    s_current_sample_len += 4;

    /* Collect enabled channels */
    for (uint16_t i = 0; i < s_channel_count; i++) {
        if (!s_channels[i].enabled) {
            continue;
        }

        int32_t raw_value = GetChannelRawValue(s_channels[i].id);
        uint8_t type_size = GetTypeSize(s_channels[i].type);

        /* Bounds check */
        if (s_current_sample_len + type_size > SAMPLE_MAX_SIZE) {
            break;
        }

        /* Copy value based on type */
        switch (s_channels[i].type) {
            case DATALOG_TYPE_BOOL:
            case DATALOG_TYPE_UINT8:
            case DATALOG_TYPE_INT8:
                s_current_sample[s_current_sample_len] = (uint8_t)raw_value;
                break;

            case DATALOG_TYPE_UINT16:
            case DATALOG_TYPE_INT16: {
                int16_t val16 = (int16_t)raw_value;
                memcpy(&s_current_sample[s_current_sample_len], &val16, 2);
                break;
            }

            case DATALOG_TYPE_UINT32:
            case DATALOG_TYPE_INT32:
                memcpy(&s_current_sample[s_current_sample_len], &raw_value, 4);
                break;

            case DATALOG_TYPE_FLOAT: {
                float valf = (float)raw_value * s_channels[i].scale + s_channels[i].offset;
                memcpy(&s_current_sample[s_current_sample_len], &valf, 4);
                break;
            }

            default:
                break;
        }

        s_current_sample_len += type_size;
    }

    s_stats.samples_logged++;

    /* Write to file */
    if (s_config.enable_file && s_log_file) {
        /* Write sample length + data */
        uint16_t len = s_current_sample_len;
        fwrite(&len, 2, 1, s_log_file);
        fwrite(s_current_sample, 1, s_current_sample_len, s_log_file);
        s_stats.bytes_written += 2 + s_current_sample_len;
    }

    /* Stream via callback */
    if (s_config.enable_streaming && s_callback) {
        s_callback(s_current_sample, s_current_sample_len);
    }
}

static uint8_t GetTypeSize(PMU_DataLog_Type_t type)
{
    switch (type) {
        case DATALOG_TYPE_BOOL:
        case DATALOG_TYPE_UINT8:
        case DATALOG_TYPE_INT8:
            return 1;
        case DATALOG_TYPE_UINT16:
        case DATALOG_TYPE_INT16:
            return 2;
        case DATALOG_TYPE_UINT32:
        case DATALOG_TYPE_INT32:
        case DATALOG_TYPE_FLOAT:
            return 4;
        default:
            return 0;
    }
}

static void WriteFileHeader(void)
{
    if (!s_log_file) {
        return;
    }

    PMU_DataLog_FileHeader_t header;
    memset(&header, 0, sizeof(header));

    header.magic = DATALOG_MAGIC;
    header.version = DATALOG_VERSION;
    header.channel_count = s_channel_count;
    header.sample_rate_hz = s_config.sample_rate_hz;
    header.start_time = HAL_GetTick();
    header.sample_count = 0;  /* Updated on close */
    strncpy(header.device_name, "PMU-30", sizeof(header.device_name) - 1);
    strncpy(header.session_name, s_config.session_name, sizeof(header.session_name) - 1);

    fwrite(&header, sizeof(header), 1, s_log_file);
    s_stats.bytes_written += sizeof(header);

    /* Write channel definitions */
    for (uint16_t i = 0; i < s_channel_count; i++) {
        fwrite(&s_channels[i], sizeof(PMU_DataLog_Channel_t), 1, s_log_file);
        s_stats.bytes_written += sizeof(PMU_DataLog_Channel_t);
    }
}

static int32_t GetChannelRawValue(uint16_t channel_id)
{
    /* System channels */
    if (channel_id == 0x0001) {
        /* Battery voltage (mV) */
        return 12000;  /* TODO: Get from protection module */
    }
    if (channel_id == 0x0002) {
        /* Board temp */
        return 25;  /* TODO: Get from protection module */
    }

    /* Output channels 0x0100 - 0x01FF */
    if (channel_id >= 0x0100 && channel_id < 0x0200) {
        uint8_t out_idx = (channel_id - 0x0100) / 2;
        uint8_t is_current = (channel_id - 0x0100) % 2;

        PMU_PROFET_Channel_t* profet = PMU_PROFET_GetChannelData(out_idx);
        if (profet) {
            if (is_current) {
                return profet->current_mA;
            } else {
                return profet->state;
            }
        }
        return 0;
    }

    /* Analog inputs 0x0200 - 0x02FF */
    if (channel_id >= 0x0200 && channel_id < 0x0300) {
        uint8_t ain_idx = channel_id - 0x0200;
        /* TODO: Get from ADC module */
        (void)ain_idx;
        return 0;
    }

    /* H-Bridge channels 0x0300 - 0x03FF */
    if (channel_id >= 0x0300 && channel_id < 0x0400) {
        /* TODO: Get from H-Bridge module */
        return 0;
    }

    return 0;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
