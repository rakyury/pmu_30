/**
 ******************************************************************************
 * @file           : pmu_min_port.c
 * @brief          : MIN Protocol Port Adapter for STM32
 ******************************************************************************
 *
 * Implements MIN protocol callbacks for Nucleo-F446RE USART2.
 * Provides reliable communication with automatic retransmission.
 *
 ******************************************************************************
 */

#include "min_config.h"
#include "min.h"
#include "pmu_min_port.h"
#include <string.h>

#ifdef NUCLEO_F446RE
#include "stm32f4xx_hal.h"

/* External references */
extern UART_HandleTypeDef huart2;
extern uint32_t HAL_GetTick(void);
extern IWDG_HandleTypeDef hiwdg;

/* ============================================================================
 * Flash Storage for Config Persistence (STM32F446RE Sector 3)
 * ============================================================================
 * Using Sector 3 (16KB) instead of Sector 7 (128KB) for faster erase time:
 * - Sector 7 (128KB): 1-2 seconds erase time, triggers IWDG timeout
 * - Sector 3 (16KB):  ~200ms erase time, safe for IWDG
 *
 * STM32F446RE Flash layout:
 * - Sector 0-3: 16KB each (0x08000000 - 0x0800FFFF)
 * - Sector 4: 64KB (0x08010000 - 0x0801FFFF)
 * - Sector 5-7: 128KB each (0x08020000 - 0x0807FFFF)
 *
 * Firmware is ~30KB, so Sector 3 (0x0800C000) is safe for config storage.
 *
 * Format: [magic:4][size:2][crc16:2][data...]
 * ============================================================================ */
#define CONFIG_FLASH_ADDR    0x0800C000UL  /* Sector 3: 16KB */
#define CONFIG_FLASH_SECTOR  FLASH_SECTOR_3
#define CONFIG_FLASH_MAGIC   0x434F4E46UL  /* "CONF" */

typedef struct __attribute__((packed)) {
    uint32_t magic;
    uint16_t size;
    uint16_t crc16;
} ConfigFlashHeader_t;

/* MIN context for USART2 */
static struct min_context g_min_ctx;

/* TX buffer for batching frame bytes - atomic send eliminates race conditions */
#define MIN_TX_BUFFER_SIZE 600
static uint8_t min_tx_buffer[MIN_TX_BUFFER_SIZE];
static uint16_t min_tx_len = 0;
static volatile bool min_tx_in_progress = false;

/* RX buffer for bytes received during TX - prevents byte loss
 * At 115200 baud with 200-byte TX packets (~17ms), we could receive
 * up to ~200 bytes during a single TX. 256 bytes gives margin. */
#define MIN_RX_BUFFER_SIZE 256
static uint8_t min_rx_buffer[MIN_RX_BUFFER_SIZE];
static volatile uint16_t min_rx_head = 0;  /* Write position */
static volatile uint16_t min_rx_tail = 0;  /* Read position */
static volatile bool min_rx_processing = false;  /* Prevent recursive processing */

/* Config buffer - copy of loaded config for GET_CONFIG */
#define MIN_CONFIG_BUFFER_SIZE 2048
static uint8_t min_config_buffer[MIN_CONFIG_BUFFER_SIZE];
static uint16_t min_config_len = 0;

/* Stream state */
static bool min_stream_active = false;
static uint32_t min_stream_period_ms = 100;  /* 10 Hz default */
static uint32_t min_last_stream_time = 0;
static uint32_t min_stream_counter = 0;

/* ============================================================================
 * MIN Protocol Callbacks (required by min.c)
 * ============================================================================ */

void min_tx_start(uint8_t port)
{
    (void)port;
    /* Don't start new TX if one is in progress (prevents nested calls from
     * command handlers triggered during TX polling) */
    if (min_tx_in_progress) {
        return;
    }
    min_tx_len = 0;
    min_tx_in_progress = true;
}

void min_tx_byte(uint8_t port, uint8_t byte)
{
    (void)port;
    /* Only write if TX is in progress (started by min_tx_start) */
    if (min_tx_in_progress && min_tx_len < MIN_TX_BUFFER_SIZE) {
        min_tx_buffer[min_tx_len++] = byte;
    }
}

void min_tx_finished(uint8_t port)
{
    (void)port;
    if (min_tx_len > 0) {
        /* Send frame while buffering any received bytes.
         * We can't process RX immediately (would cause reentrancy), but we
         * must not lose bytes. Buffer them now, process after TX completes. */
        for (uint16_t i = 0; i < min_tx_len; i++) {
            /* Wait for TX empty, but poll RX while waiting */
            while (!(USART2->SR & USART_SR_TXE)) {
                /* Check for RX data and buffer it */
                if (USART2->SR & USART_SR_RXNE) {
                    uint8_t rx_byte = (uint8_t)(USART2->DR & 0xFF);
                    uint16_t next_head = (min_rx_head + 1) % MIN_RX_BUFFER_SIZE;
                    if (next_head != min_rx_tail) {  /* Not full */
                        min_rx_buffer[min_rx_head] = rx_byte;
                        min_rx_head = next_head;
                    }
                }
            }
            USART2->DR = min_tx_buffer[i];
        }
        /* Wait for transmission complete, still buffering RX */
        while (!(USART2->SR & USART_SR_TC)) {
            if (USART2->SR & USART_SR_RXNE) {
                uint8_t rx_byte = (uint8_t)(USART2->DR & 0xFF);
                uint16_t next_head = (min_rx_head + 1) % MIN_RX_BUFFER_SIZE;
                if (next_head != min_rx_tail) {
                    min_rx_buffer[min_rx_head] = rx_byte;
                    min_rx_head = next_head;
                }
            }
        }
    }
    min_tx_in_progress = false;

    /* Process any buffered RX bytes now that TX is complete.
     * Guard against recursion: if a command triggers another TX,
     * that TX's completion will try to process RX again. */
    if (!min_rx_processing) {
        min_rx_processing = true;
        while (min_rx_tail != min_rx_head) {
            uint8_t byte = min_rx_buffer[min_rx_tail];
            min_rx_tail = (min_rx_tail + 1) % MIN_RX_BUFFER_SIZE;
            min_poll(&g_min_ctx, &byte, 1);
        }
        min_rx_processing = false;
    }
}

uint16_t min_tx_space(uint8_t port)
{
    (void)port;
    return MIN_TX_BUFFER_SIZE - min_tx_len;
}

uint32_t min_time_ms(void)
{
    return HAL_GetTick();
}

/* ============================================================================
 * External Functions
 * ============================================================================ */

/* Channel executor */
extern int PMU_ChannelExec_LoadConfig(const uint8_t* data, uint16_t size);
extern void PMU_ChannelExec_Clear(void);
extern uint16_t PMU_ChannelExec_GetChannelCount(void);
extern bool PMU_ChannelExec_GetChannelInfo(uint16_t index, uint16_t* channel_id, int32_t* value);

/* Output control */
extern void PMU_PROFET_SetState(uint8_t channel, bool state);
extern uint8_t PMU_PROFET_GetState(uint8_t channel);

/* ADC */
extern uint16_t PMU_ADC_GetValue(uint8_t channel);

/* Digital inputs from main loop */
extern uint8_t g_digital_inputs[8];

/* ============================================================================
 * Flash Storage Helper Functions
 * ============================================================================ */

static uint16_t Config_CRC16(const uint8_t* data, uint16_t length)
{
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < length; i++) {
        crc ^= ((uint16_t)data[i]) << 8;
        for (uint8_t j = 0; j < 8; j++) {
            crc = (crc & 0x8000) ? ((crc << 1) ^ 0x1021) : (crc << 1);
        }
    }
    return crc;
}

static bool Config_SaveToFlash(void)
{
    if (min_config_len == 0 || min_config_len > MIN_CONFIG_BUFFER_SIZE) {
        return false;
    }

    /* Prepare header */
    ConfigFlashHeader_t header;
    header.magic = CONFIG_FLASH_MAGIC;
    header.size = min_config_len;
    header.crc16 = Config_CRC16(min_config_buffer, min_config_len);

    /* Refresh IWDG before flash erase (128KB sector takes 1-2 seconds) */
    HAL_IWDG_Refresh(&hiwdg);

    /* Unlock flash */
    HAL_FLASH_Unlock();

    /* Erase Sector 7 */
    FLASH_EraseInitTypeDef erase_init;
    uint32_t sector_error = 0;
    erase_init.TypeErase = FLASH_TYPEERASE_SECTORS;
    erase_init.Sector = CONFIG_FLASH_SECTOR;
    erase_init.NbSectors = 1;
    erase_init.VoltageRange = FLASH_VOLTAGE_RANGE_3;

    if (HAL_FLASHEx_Erase(&erase_init, &sector_error) != HAL_OK) {
        HAL_FLASH_Lock();
        return false;
    }

    /* Refresh IWDG after erase */
    HAL_IWDG_Refresh(&hiwdg);

    /* Write header (8 bytes = 2 words) */
    uint32_t addr = CONFIG_FLASH_ADDR;
    uint32_t* header_ptr = (uint32_t*)&header;
    for (int i = 0; i < 2; i++) {
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, addr, header_ptr[i]) != HAL_OK) {
            HAL_FLASH_Lock();
            return false;
        }
        addr += 4;
    }

    /* Write config data (word-aligned) */
    uint32_t words = (min_config_len + 3) / 4;
    uint32_t* data_ptr = (uint32_t*)min_config_buffer;
    for (uint32_t i = 0; i < words; i++) {
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, addr, data_ptr[i]) != HAL_OK) {
            HAL_FLASH_Lock();
            return false;
        }
        addr += 4;
    }

    HAL_FLASH_Lock();
    return true;
}

static bool Config_LoadFromFlash(void)
{
    ConfigFlashHeader_t* header = (ConfigFlashHeader_t*)CONFIG_FLASH_ADDR;

    /* Check magic */
    if (header->magic != CONFIG_FLASH_MAGIC) {
        return false;
    }

    /* Check size */
    if (header->size == 0 || header->size > MIN_CONFIG_BUFFER_SIZE) {
        return false;
    }

    /* Read config data */
    uint8_t* flash_data = (uint8_t*)(CONFIG_FLASH_ADDR + sizeof(ConfigFlashHeader_t));
    memcpy(min_config_buffer, flash_data, header->size);
    min_config_len = header->size;

    /* Verify CRC */
    uint16_t calc_crc = Config_CRC16(min_config_buffer, min_config_len);
    if (calc_crc != header->crc16) {
        min_config_len = 0;
        return false;
    }

    return true;
}

/* ============================================================================
 * Command Handlers
 * ============================================================================ */

static void handle_ping(void)
{
    /* PONG is unreliable - if lost, client will retry PING
     * Using min_send_frame avoids infinite retransmits when client doesn't ACK */
    min_send_frame(&g_min_ctx, MIN_CMD_PONG, NULL, 0);
}

static void handle_reset(void)
{
    /* Send ACK before reset (may not arrive - client should retry after timeout) */
    uint8_t ack[1] = {MIN_CMD_RESET};
    min_send_frame(&g_min_ctx, MIN_CMD_ACK, ack, 1);

    /* Wait for TX to complete */
    while (!(USART2->SR & USART_SR_TC)) {}

    /* Trigger full system reset */
    NVIC_SystemReset();
    /* Never returns */
}

static void handle_get_config(void)
{
    if (min_config_len == 0) {
        uint8_t response[6] = {0, 0, 1, 0, 0, 0};
        min_send_frame(&g_min_ctx, MIN_CMD_CONFIG_DATA, response, 6);  /* Unreliable */
        return;
    }

    /* Send config with chunk header */
    uint8_t response[260];
    response[0] = 0;  /* chunk_idx */
    response[1] = 0;
    response[2] = 1;  /* total_chunks */
    response[3] = 0;

    uint16_t copy_len = (min_config_len > 251) ? 251 : min_config_len;
    memcpy(response + 4, min_config_buffer, copy_len);

    /* Unreliable - if lost, client retries GET_CONFIG */
    min_send_frame(&g_min_ctx, MIN_CMD_CONFIG_DATA, response, 4 + copy_len);
}

static void handle_load_binary_config(uint8_t const *payload, uint8_t len)
{
    if (len < 4) {
        uint8_t nack[2] = {MIN_CMD_LOAD_BINARY, 0x02};
        min_send_frame(&g_min_ctx, MIN_CMD_NACK, nack, 2);  /* Unreliable NACK */
        return;
    }

    min_stream_active = false;

    /* Skip 4-byte chunk header */
    uint16_t config_len = len - 4;
    const uint8_t* config_data = payload + 4;

    /* Store config for persistence */
    if (config_len <= MIN_CONFIG_BUFFER_SIZE) {
        memcpy(min_config_buffer, config_data, config_len);
        min_config_len = config_len;
    }

    /* Load via channel executor */
    int result = PMU_ChannelExec_LoadConfig(config_data, config_len);
    /* result is the number of loaded channels (including output links) */
    uint16_t channels_loaded = (result >= 0) ? (uint16_t)result : 0;

    uint8_t ack[4];
    ack[0] = (result >= 0) ? 1 : 0;
    ack[1] = 0;
    ack[2] = channels_loaded & 0xFF;
    ack[3] = (channels_loaded >> 8) & 0xFF;

    /* Unreliable ACK - if lost, client retries and we reload config */
    min_send_frame(&g_min_ctx, MIN_CMD_BINARY_ACK, ack, 4);
}

static void handle_save_config(void)
{
    bool success = Config_SaveToFlash();
    uint8_t ack[1] = {success ? 1 : 0};
    min_send_frame(&g_min_ctx, MIN_CMD_FLASH_ACK, ack, 1);
}

static void handle_clear_config(void)
{
    PMU_ChannelExec_Clear();
    min_config_len = 0;

    /* Refresh IWDG before flash erase (128KB sector takes 1-2 seconds) */
    HAL_IWDG_Refresh(&hiwdg);

    /* Erase flash sector to prevent loading on next boot */
    HAL_FLASH_Unlock();
    FLASH_EraseInitTypeDef erase_init = {
        .TypeErase = FLASH_TYPEERASE_SECTORS,
        .Sector = CONFIG_FLASH_SECTOR,
        .NbSectors = 1,
        .VoltageRange = FLASH_VOLTAGE_RANGE_3
    };
    uint32_t sector_error = 0;
    HAL_FLASHEx_Erase(&erase_init, &sector_error);
    HAL_FLASH_Lock();

    /* Refresh IWDG after erase */
    HAL_IWDG_Refresh(&hiwdg);

    uint8_t ack[1] = {1};
    min_send_frame(&g_min_ctx, MIN_CMD_CLEAR_CONFIG_ACK, ack, 1);
}

static void handle_start_stream(uint8_t const *payload, uint8_t len)
{
    uint16_t rate_hz = 10;
    if (len >= 2) {
        rate_hz = payload[0] | (payload[1] << 8);
        if (rate_hz == 0) rate_hz = 10;
        if (rate_hz > 100) rate_hz = 100;
    }

    min_stream_period_ms = 1000 / rate_hz;
    min_stream_active = true;
    min_last_stream_time = min_time_ms();

    uint8_t ack[1] = {MIN_CMD_START_STREAM};
    min_send_frame(&g_min_ctx, MIN_CMD_ACK, ack, 1);  /* Unreliable ACK */
}

static void handle_stop_stream(void)
{
    min_stream_active = false;
    uint8_t ack[1] = {MIN_CMD_STOP_STREAM};
    min_send_frame(&g_min_ctx, MIN_CMD_ACK, ack, 1);  /* Unreliable ACK */
}

static void handle_set_output(uint8_t const *payload, uint8_t len)
{
    if (len < 2) {
        uint8_t nack[2] = {MIN_CMD_SET_OUTPUT, 0x02};
        min_send_frame(&g_min_ctx, MIN_CMD_NACK, nack, 2);  /* Unreliable NACK */
        return;
    }

    PMU_PROFET_SetState(payload[0], payload[1] != 0);

    uint8_t ack[2] = {payload[0], payload[1]};
    min_send_frame(&g_min_ctx, MIN_CMD_OUTPUT_ACK, ack, 2);  /* Unreliable ACK */
}

static void handle_get_capabilities(void)
{
    /* Device capabilities response:
     * [0]    device_type (0=PMU-30, 1=PMU-30 Pro, 2=PMU-16 Mini)
     * [1]    fw_version_major
     * [2]    fw_version_minor
     * [3]    fw_version_patch
     * [4]    output_count
     * [5]    analog_input_count
     * [6]    digital_input_count
     * [7]    hbridge_count
     * [8]    can_bus_count
     * [9]    reserved (0)
     */
    uint8_t caps[10] = {
        PMU_DEVICE_TYPE,
        PMU_FW_VERSION_MAJOR,
        PMU_FW_VERSION_MINOR,
        PMU_FW_VERSION_PATCH,
        PMU_OUTPUT_COUNT,
        PMU_ANALOG_INPUT_COUNT,
        PMU_DIGITAL_INPUT_COUNT,
        PMU_HBRIDGE_COUNT,
        PMU_CAN_BUS_COUNT,
        0  /* reserved */
    };
    min_send_frame(&g_min_ctx, MIN_CMD_CAPABILITIES, caps, 10);
}

/**
 * @brief MIN application frame handler - routes commands
 */
void min_application_handler(uint8_t min_id, uint8_t const *min_payload,
                             uint8_t len_payload, uint8_t port)
{
    (void)port;

    switch (min_id) {
        case MIN_CMD_PING:
            handle_ping();
            break;
        case MIN_CMD_RESET:
            handle_reset();
            break;
        case MIN_CMD_GET_CONFIG:
            handle_get_config();
            break;
        case MIN_CMD_LOAD_BINARY:
            handle_load_binary_config(min_payload, len_payload);
            break;
        case MIN_CMD_SAVE_CONFIG:
            handle_save_config();
            break;
        case MIN_CMD_CLEAR_CONFIG:
            handle_clear_config();
            break;
        case MIN_CMD_START_STREAM:
            handle_start_stream(min_payload, len_payload);
            break;
        case MIN_CMD_STOP_STREAM:
            handle_stop_stream();
            break;
        case MIN_CMD_SET_OUTPUT:
            handle_set_output(min_payload, len_payload);
            break;
        case MIN_CMD_GET_CAPABILITIES:
            handle_get_capabilities();
            break;
        default:
            {
                uint8_t nack[2] = {min_id, 0x01};
                min_send_frame(&g_min_ctx, MIN_CMD_NACK, nack, 2);  /* Unreliable NACK */
            }
            break;
    }
}

/* ============================================================================
 * Telemetry
 * ============================================================================ */

static void build_telemetry_packet(uint8_t* buf, uint16_t* len)
{
    uint16_t idx = 0;

    /* Stream counter (4 bytes) */
    buf[idx++] = min_stream_counter & 0xFF;
    buf[idx++] = (min_stream_counter >> 8) & 0xFF;
    buf[idx++] = (min_stream_counter >> 16) & 0xFF;
    buf[idx++] = (min_stream_counter >> 24) & 0xFF;
    min_stream_counter++;

    /* Timestamp (4 bytes) */
    uint32_t ts = min_time_ms();
    buf[idx++] = ts & 0xFF;
    buf[idx++] = (ts >> 8) & 0xFF;
    buf[idx++] = (ts >> 16) & 0xFF;
    buf[idx++] = (ts >> 24) & 0xFF;

    /* Output states (30 bytes) */
    for (int i = 0; i < 30; i++) {
        buf[idx++] = PMU_PROFET_GetState(i);
    }

    /* ADC values (40 bytes) */
    for (int i = 0; i < 20; i++) {
        uint16_t adc = PMU_ADC_GetValue(i);
        buf[idx++] = adc & 0xFF;
        buf[idx++] = (adc >> 8) & 0xFF;
    }

    /* Digital inputs bitmask (1 byte) */
    uint8_t din_mask = 0;
    for (int i = 0; i < 8; i++) {
        if (g_digital_inputs[i]) din_mask |= (1 << i);
    }
    buf[idx++] = din_mask;

    /* System info (15 bytes) */
    uint32_t uptime = min_time_ms() / 1000;
    buf[idx++] = uptime & 0xFF;
    buf[idx++] = (uptime >> 8) & 0xFF;
    buf[idx++] = (uptime >> 16) & 0xFF;
    buf[idx++] = (uptime >> 24) & 0xFF;
    for (int i = 0; i < 8; i++) buf[idx++] = 0;  /* RAM/Flash */
    uint16_t ch_count = PMU_ChannelExec_GetChannelCount();
    buf[idx++] = ch_count & 0xFF;
    buf[idx++] = (ch_count >> 8) & 0xFF;
    buf[idx++] = 0;  /* Reserved */

    /* Status (10 bytes) */
    for (int i = 0; i < 10; i++) buf[idx++] = 0;

    /* Virtual channels */
    buf[idx++] = ch_count & 0xFF;
    buf[idx++] = (ch_count >> 8) & 0xFF;

    for (uint16_t i = 0; i < ch_count && idx + 6 <= 200; i++) {
        uint16_t ch_id;
        int32_t value;
        if (PMU_ChannelExec_GetChannelInfo(i, &ch_id, &value)) {
            buf[idx++] = ch_id & 0xFF;
            buf[idx++] = (ch_id >> 8) & 0xFF;
            buf[idx++] = value & 0xFF;
            buf[idx++] = (value >> 8) & 0xFF;
            buf[idx++] = (value >> 16) & 0xFF;
            buf[idx++] = (value >> 24) & 0xFF;
        }
    }

    *len = idx;
}

/* ============================================================================
 * Public API
 * ============================================================================ */

void PMU_MIN_Init(void)
{
    min_init_context(&g_min_ctx, 0);
    min_stream_active = false;
    min_config_len = 0;
    min_stream_counter = 0;
}

void PMU_MIN_ProcessByte(uint8_t byte)
{
    min_poll(&g_min_ctx, &byte, 1);
}

void PMU_MIN_Update(void)
{
    /* Handle retransmits */
    min_poll(&g_min_ctx, NULL, 0);

    /* Telemetry streaming */
    if (min_stream_active) {
        uint32_t now = min_time_ms();
        if (now - min_last_stream_time >= min_stream_period_ms) {
            min_last_stream_time = now;

            uint8_t telem_buf[200];
            uint16_t telem_len = 0;
            build_telemetry_packet(telem_buf, &telem_len);

            if (telem_len > 0 && telem_len <= MAX_PAYLOAD) {
                min_send_frame(&g_min_ctx, MIN_CMD_DATA, telem_buf, telem_len);
            }
        }
    }
}

bool PMU_MIN_IsStreamActive(void)
{
    return min_stream_active;
}

bool PMU_MIN_IsTxInProgress(void)
{
    return min_tx_in_progress;
}

struct min_context* PMU_MIN_GetContext(void)
{
    return &g_min_ctx;
}

bool PMU_MIN_LoadSavedConfig(void)
{
    /* Load config from flash */
    if (!Config_LoadFromFlash()) {
        return false;
    }

    /* Apply to channel executor */
    if (min_config_len > 0) {
        int result = PMU_ChannelExec_LoadConfig(min_config_buffer, min_config_len);
        return (result >= 0);
    }

    return false;
}

#endif /* NUCLEO_F446RE */
