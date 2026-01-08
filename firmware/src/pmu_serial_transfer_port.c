/**
 ******************************************************************************
 * @file           : pmu_serial_transfer_port.c
 * @brief          : SerialTransfer Protocol Port for STM32 (Nucleo-F446RE)
 ******************************************************************************
 *
 * Implements SerialTransfer protocol for USART2.
 * Replaces MIN protocol with simpler COBS + CRC8 framing.
 *
 ******************************************************************************
 */

#include "pmu_serial_transfer.h"
#include "pmu_serial_transfer_port.h"
#include <string.h>
#include <stdbool.h>

#ifdef NUCLEO_F446RE
#include "stm32f4xx_hal.h"

/* External references */
extern UART_HandleTypeDef huart2;
extern UART_HandleTypeDef huart1;  /* ESP32 WiFi bridge - Arduino D8(TX)/D2(RX) */
extern uint32_t HAL_GetTick(void);
extern IWDG_HandleTypeDef hiwdg;

/* ============================================================================
 * Flash Storage (same as MIN version)
 * ============================================================================ */
#define CONFIG_FLASH_ADDR    0x0800C000UL
#define CONFIG_FLASH_SECTOR  FLASH_SECTOR_3
#define CONFIG_FLASH_MAGIC   0x434F4E46UL

typedef struct __attribute__((packed)) {
    uint32_t magic;
    uint16_t size;
    uint16_t crc16;
} ConfigFlashHeader_t;

/* ============================================================================
 * Global State
 * ============================================================================ */

/* SerialTransfer context */
static ST_Context g_st_ctx;

/* TX buffer for complete frames */
#define ST_TX_BUFFER_SIZE 300
static uint8_t st_tx_buffer[ST_TX_BUFFER_SIZE];

/* RX ring buffer for ISR */
#define ST_RX_RING_SIZE 512
static volatile uint8_t st_rx_ring[ST_RX_RING_SIZE];
static volatile uint16_t st_rx_head = 0;
static volatile uint16_t st_rx_tail = 0;

/* Config buffer */
#define CONFIG_BUFFER_SIZE 2048
static uint8_t config_buffer[CONFIG_BUFFER_SIZE];
static uint16_t config_len = 0;

/* Stream state */
static bool stream_active = false;
static uint32_t stream_period_ms = 100;
static uint32_t last_stream_time = 0;
static uint32_t stream_counter = 0;

/* Debug counters */
static volatile uint32_t rx_packet_count = 0;
static volatile uint8_t last_cmd = 0;
static volatile uint32_t usart1_tx_bytes = 0;  /* Debug: count bytes sent to ESP32 */
static volatile uint32_t usart2_tx_bytes = 0;  /* Debug: count bytes sent to USB */

/* ============================================================================
 * External Functions
 * ============================================================================ */

extern int PMU_ChannelExec_LoadConfig(const uint8_t* data, uint16_t size);
extern void PMU_ChannelExec_Clear(void);
extern uint16_t PMU_ChannelExec_GetChannelCount(void);
extern bool PMU_ChannelExec_GetChannelInfo(uint16_t index, uint16_t* channel_id, int32_t* value);
extern bool PMU_ChannelExec_GetTimerSubChannel(uint16_t index, uint8_t sub_index,
                                                uint16_t* sub_channel_id, int32_t* sub_value);
extern uint8_t PMU_ChannelExec_GetSubChannelCount(uint16_t index);
extern void PMU_PROFET_SetState(uint8_t channel, bool state);
extern uint8_t PMU_PROFET_GetState(uint8_t channel);
extern uint16_t PMU_ADC_GetValue(uint8_t channel);
extern uint8_t g_digital_inputs[8];

/* ============================================================================
 * Low-level TX/RX
 * ============================================================================ */

/* Helper to poll RX bytes from USART2 and USART1 into ring buffer */
static inline void poll_rx_byte(void)
{
    /* Poll USART2 (USB / ST-Link VCP) */
    if (USART2->SR & USART_SR_RXNE) {
        uint8_t rx_byte = (uint8_t)(USART2->DR & 0xFF);
        uint16_t next = (st_rx_head + 1) % ST_RX_RING_SIZE;
        if (next != st_rx_tail) {
            st_rx_ring[st_rx_head] = rx_byte;
            st_rx_head = next;
        }
    }
    if (USART2->SR & USART_SR_ORE) {
        (void)USART2->DR; /* Clear ORE by reading DR */
    }

    /* Poll USART1 (ESP32 WiFi bridge) */
    if (USART1->SR & USART_SR_RXNE) {
        uint8_t rx_byte = (uint8_t)(USART1->DR & 0xFF);
        uint16_t next = (st_rx_head + 1) % ST_RX_RING_SIZE;
        if (next != st_rx_tail) {
            st_rx_ring[st_rx_head] = rx_byte;
            st_rx_head = next;
        }
    }
    if (USART1->SR & USART_SR_ORE) {
        (void)USART1->DR; /* Clear ORE by reading DR */
    }
}

static void uart_send_packet(uint8_t cmd, const uint8_t* payload, uint8_t len)
{
    /* Build packet */
    if (len > 0 && payload != NULL) {
        memcpy(g_st_ctx.tx_buff, payload, len);
    }

    uint16_t frame_len = ST_BuildPacket(&g_st_ctx, len, cmd, st_tx_buffer, ST_TX_BUFFER_SIZE);
    if (frame_len == 0) return;

    /* Send bytes to BOTH USART2 (USB) and USART1 (ESP32 WiFi bridge)
     * This enables transparent WiFi bridging - configurator can connect via either */
    for (uint16_t i = 0; i < frame_len; i++) {
        /* Wait for USART2 ready */
        while (!(USART2->SR & USART_SR_TXE)) {
            poll_rx_byte();
        }
        USART2->DR = st_tx_buffer[i];
        usart2_tx_bytes++;

        /* Wait for USART1 ready */
        while (!(USART1->SR & USART_SR_TXE)) {
            poll_rx_byte();
        }
        USART1->DR = st_tx_buffer[i];
        usart1_tx_bytes++;
    }

    /* Wait for both TX complete - also poll RX */
    while (!(USART2->SR & USART_SR_TC) || !(USART1->SR & USART_SR_TC)) {
        poll_rx_byte();
    }
}

/* Call from USART2 IRQ or polling */
void PMU_ST_RxByte(uint8_t byte)
{
    uint16_t next = (st_rx_head + 1) % ST_RX_RING_SIZE;
    if (next != st_rx_tail) {
        st_rx_ring[st_rx_head] = byte;
        st_rx_head = next;
    }
}

/* ============================================================================
 * Flash Storage
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
    if (config_len == 0 || config_len > CONFIG_BUFFER_SIZE) return false;

    ConfigFlashHeader_t header = {
        .magic = CONFIG_FLASH_MAGIC,
        .size = config_len,
        .crc16 = Config_CRC16(config_buffer, config_len)
    };

    HAL_IWDG_Refresh(&hiwdg);
    HAL_FLASH_Unlock();

    FLASH_EraseInitTypeDef erase = {
        .TypeErase = FLASH_TYPEERASE_SECTORS,
        .Sector = CONFIG_FLASH_SECTOR,
        .NbSectors = 1,
        .VoltageRange = FLASH_VOLTAGE_RANGE_3
    };
    uint32_t error = 0;
    if (HAL_FLASHEx_Erase(&erase, &error) != HAL_OK) {
        HAL_FLASH_Lock();
        return false;
    }

    HAL_IWDG_Refresh(&hiwdg);

    /* Write header */
    uint32_t addr = CONFIG_FLASH_ADDR;
    uint32_t* hp = (uint32_t*)&header;
    for (int i = 0; i < 2; i++) {
        HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, addr, hp[i]);
        addr += 4;
    }

    /* Write data */
    uint32_t words = (config_len + 3) / 4;
    uint32_t* dp = (uint32_t*)config_buffer;
    for (uint32_t i = 0; i < words; i++) {
        HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, addr, dp[i]);
        addr += 4;
        if ((i & 0x0F) == 0x0F) HAL_IWDG_Refresh(&hiwdg);
    }

    HAL_IWDG_Refresh(&hiwdg);
    HAL_FLASH_Lock();
    return true;
}

static bool Config_LoadFromFlash(void)
{
    ConfigFlashHeader_t* h = (ConfigFlashHeader_t*)CONFIG_FLASH_ADDR;
    if (h->magic != CONFIG_FLASH_MAGIC) return false;
    if (h->size == 0 || h->size > CONFIG_BUFFER_SIZE) return false;

    uint8_t* data = (uint8_t*)(CONFIG_FLASH_ADDR + sizeof(ConfigFlashHeader_t));
    memcpy(config_buffer, data, h->size);
    config_len = h->size;

    if (Config_CRC16(config_buffer, config_len) != h->crc16) {
        config_len = 0;
        return false;
    }
    return true;
}

/* ============================================================================
 * Command Handlers
 * ============================================================================ */

static void handle_ping(void)
{
    uart_send_packet(ST_CMD_PONG, NULL, 0);
}

static void handle_reset(void)
{
    uint8_t ack[1] = {ST_CMD_RESET};
    uart_send_packet(ST_CMD_ACK, ack, 1);
    while (!(USART2->SR & USART_SR_TC)) {}
    NVIC_SystemReset();
}

static void handle_get_config(void)
{
    if (config_len == 0) {
        uint8_t resp[6] = {0, 0, 1, 0, 0, 0};
        uart_send_packet(ST_CMD_CONFIG_DATA, resp, 6);
        return;
    }

    uint8_t resp[260];
    resp[0] = 0; resp[1] = 0;  /* chunk_idx */
    resp[2] = 1; resp[3] = 0;  /* total_chunks */

    uint16_t copy_len = (config_len > 250) ? 250 : config_len;
    memcpy(resp + 4, config_buffer, copy_len);
    uart_send_packet(ST_CMD_CONFIG_DATA, resp, 4 + copy_len);
}

static void handle_load_binary(const uint8_t* payload, uint8_t len)
{
    /* DEBUG: Toggle LED to show command received */
    GPIOA->ODR ^= (1 << 5);  /* Toggle PA5 */

    if (len < 4) {
        uint8_t nack[2] = {ST_CMD_LOAD_BINARY, 0x02};
        uart_send_packet(ST_CMD_NACK, nack, 2);
        return;
    }

    stream_active = false;

    uint16_t data_len = len - 4;
    const uint8_t* data = payload + 4;

    if (data_len <= CONFIG_BUFFER_SIZE) {
        memcpy(config_buffer, data, data_len);
        config_len = data_len;
    }

    HAL_IWDG_Refresh(&hiwdg);
    int result = PMU_ChannelExec_LoadConfig(data, data_len);
    HAL_IWDG_Refresh(&hiwdg);

    uint16_t channels = (result >= 0) ? (uint16_t)result : 0;
    uint8_t ack[4] = {
        (result >= 0) ? 1 : 0,
        0,
        channels & 0xFF,
        (channels >> 8) & 0xFF
    };
    uart_send_packet(ST_CMD_BINARY_ACK, ack, 4);
}

static void handle_save_config(void)
{
    HAL_IWDG_Refresh(&hiwdg);
    bool ok = Config_SaveToFlash();
    HAL_IWDG_Refresh(&hiwdg);
    uint8_t ack[1] = {ok ? 1 : 0};
    uart_send_packet(ST_CMD_FLASH_ACK, ack, 1);
}

static void handle_clear_config(void)
{
    PMU_ChannelExec_Clear();
    config_len = 0;

    HAL_IWDG_Refresh(&hiwdg);
    HAL_FLASH_Unlock();
    FLASH_EraseInitTypeDef erase = {
        .TypeErase = FLASH_TYPEERASE_SECTORS,
        .Sector = CONFIG_FLASH_SECTOR,
        .NbSectors = 1,
        .VoltageRange = FLASH_VOLTAGE_RANGE_3
    };
    uint32_t error = 0;
    HAL_FLASHEx_Erase(&erase, &error);
    HAL_FLASH_Lock();
    HAL_IWDG_Refresh(&hiwdg);

    uint8_t ack[1] = {1};
    uart_send_packet(ST_CMD_CLEAR_CONFIG_ACK, ack, 1);
}

static void handle_start_stream(const uint8_t* payload, uint8_t len)
{
    uint16_t rate = 10;
    if (len >= 2) {
        rate = payload[0] | (payload[1] << 8);
        if (rate == 0) rate = 10;
        if (rate > 100) rate = 100;
    }
    stream_period_ms = 1000 / rate;
    stream_active = true;
    last_stream_time = HAL_GetTick();

    uint8_t ack[1] = {ST_CMD_START_STREAM};
    uart_send_packet(ST_CMD_ACK, ack, 1);
}

static void handle_stop_stream(void)
{
    HAL_IWDG_Refresh(&hiwdg);
    stream_active = false;

    uint8_t ack[1] = {ST_CMD_STOP_STREAM};
    uart_send_packet(ST_CMD_ACK, ack, 1);
    while (!(USART2->SR & USART_SR_TC)) {}
    HAL_IWDG_Refresh(&hiwdg);
}

static void handle_set_output(const uint8_t* payload, uint8_t len)
{
    if (len < 2) {
        uint8_t nack[2] = {ST_CMD_SET_OUTPUT, 0x02};
        uart_send_packet(ST_CMD_NACK, nack, 2);
        return;
    }
    PMU_PROFET_SetState(payload[0], payload[1] != 0);
    uint8_t ack[2] = {payload[0], payload[1]};
    uart_send_packet(ST_CMD_OUTPUT_ACK, ack, 2);
}

static void handle_get_capabilities(void)
{
    uint8_t caps[10] = {
        0x10,  /* Device type: Nucleo-F446RE */
        1, 0, 0,  /* Version 1.0.0 */
        30,   /* outputs */
        10,   /* analog inputs */
        8,    /* digital inputs */
        2,    /* h-bridges */
        0,    /* can buses (none on Nucleo) */
        0     /* reserved */
    };
    uart_send_packet(ST_CMD_CAPABILITIES, caps, 10);
}

/* ============================================================================
 * Packet Handler (callback)
 * ============================================================================ */

static void on_packet(uint8_t cmd, const uint8_t* payload, uint8_t len)
{
    rx_packet_count++;
    last_cmd = cmd;

    switch (cmd) {
        case ST_CMD_PING:          handle_ping(); break;
        case ST_CMD_RESET:         handle_reset(); break;
        case ST_CMD_GET_CONFIG:    handle_get_config(); break;
        case ST_CMD_LOAD_BINARY:   handle_load_binary(payload, len); break;
        case ST_CMD_SAVE_CONFIG:   handle_save_config(); break;
        case ST_CMD_CLEAR_CONFIG:  handle_clear_config(); break;
        case ST_CMD_START_STREAM:  handle_start_stream(payload, len); break;
        case ST_CMD_STOP_STREAM:   handle_stop_stream(); break;
        case ST_CMD_SET_OUTPUT:    handle_set_output(payload, len); break;
        case ST_CMD_GET_CAPABILITIES: handle_get_capabilities(); break;
        default: {
            uint8_t nack[2] = {cmd, 0x01};
            uart_send_packet(ST_CMD_NACK, nack, 2);
            break;
        }
    }
}

/* ============================================================================
 * Telemetry
 * ============================================================================ */

static void build_telemetry(uint8_t* buf, uint16_t* len)
{
    uint16_t idx = 0;

    /* Stream counter (4) */
    buf[idx++] = stream_counter & 0xFF;
    buf[idx++] = (stream_counter >> 8) & 0xFF;
    buf[idx++] = (stream_counter >> 16) & 0xFF;
    buf[idx++] = (stream_counter >> 24) & 0xFF;
    stream_counter++;

    /* Timestamp (4) */
    uint32_t ts = HAL_GetTick();
    buf[idx++] = ts & 0xFF;
    buf[idx++] = (ts >> 8) & 0xFF;
    buf[idx++] = (ts >> 16) & 0xFF;
    buf[idx++] = (ts >> 24) & 0xFF;

    /* Output states (30) */
    for (int i = 0; i < 30; i++) {
        buf[idx++] = PMU_PROFET_GetState(i);
    }

    /* ADC values (40) */
    for (int i = 0; i < 20; i++) {
        uint16_t adc = PMU_ADC_GetValue(i);
        buf[idx++] = adc & 0xFF;
        buf[idx++] = (adc >> 8) & 0xFF;
    }

    /* Digital inputs (1) */
    uint8_t din = 0;
    for (int i = 0; i < 8; i++) {
        if (g_digital_inputs[i]) din |= (1 << i);
    }
    buf[idx++] = din;

    /* System info (15) */
    uint32_t uptime = HAL_GetTick() / 1000;
    buf[idx++] = uptime & 0xFF;
    buf[idx++] = (uptime >> 8) & 0xFF;
    buf[idx++] = (uptime >> 16) & 0xFF;
    buf[idx++] = (uptime >> 24) & 0xFF;
    /* Debug fields */
    buf[idx++] = rx_packet_count & 0xFF;
    buf[idx++] = last_cmd;
    /* Debug: TX byte counts (lower 16 bits each) */
    buf[idx++] = (usart2_tx_bytes >> 0) & 0xFF;
    buf[idx++] = (usart2_tx_bytes >> 8) & 0xFF;
    buf[idx++] = (usart1_tx_bytes >> 0) & 0xFF;
    buf[idx++] = (usart1_tx_bytes >> 8) & 0xFF;
    buf[idx++] = 0;
    buf[idx++] = 0;
    uint16_t ch_count = PMU_ChannelExec_GetChannelCount();
    buf[idx++] = ch_count & 0xFF;
    buf[idx++] = (ch_count >> 8) & 0xFF;
    buf[idx++] = 0;

    /* Status (10) - Debug USART/GPIO info */
    /* Byte 0: USART1->CR1 UE bit (1=enabled, 0=disabled) */
    buf[idx++] = (USART1->CR1 & USART_CR1_UE) ? 1 : 0;
    /* Byte 1: USART1->SR status register low byte (TXE=0x80, TC=0x40, RXNE=0x20) */
    buf[idx++] = USART1->SR & 0xFF;
    /* Byte 2: USART1->CR1 TE bit (TX enable) */
    buf[idx++] = (USART1->CR1 & USART_CR1_TE) ? 1 : 0;
    /* Byte 3: USART1->CR1 RE bit (RX enable) */
    buf[idx++] = (USART1->CR1 & USART_CR1_RE) ? 1 : 0;
    /* Byte 4: PA9 pin state (USART1 TX) - should be HIGH when idle */
    buf[idx++] = (GPIOA->IDR & GPIO_IDR_ID9) ? 1 : 0;
    /* Byte 5: PA10 pin state (USART1 RX) */
    buf[idx++] = (GPIOA->IDR & GPIO_IDR_ID10) ? 1 : 0;
    /* Byte 6: GPIOA MODER for PA9 (should be 0x2 = AF mode) */
    buf[idx++] = (GPIOA->MODER >> 18) & 0x3;
    /* Byte 7: GPIOA AFR[1] for PA9 (should be 0x7 = AF7 USART1) */
    buf[idx++] = (GPIOA->AFR[1] >> 4) & 0xF;
    /* Byte 8-9: zeros */
    buf[idx++] = 0;
    buf[idx++] = 0;

    /* Virtual channels + sub-channels */
    /* Count total: main channels + sub-channels (Timer has 3 sub-channels each) */
    uint16_t total_count = ch_count;
    for (uint16_t i = 0; i < ch_count; i++) {
        total_count += PMU_ChannelExec_GetSubChannelCount(i);
    }

    buf[idx++] = total_count & 0xFF;
    buf[idx++] = (total_count >> 8) & 0xFF;

    /* Main channel values */
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

    /* Sub-channels (Timer: elapsed, remaining, state) */
    for (uint16_t i = 0; i < ch_count && idx + 6 <= 200; i++) {
        uint8_t sub_count = PMU_ChannelExec_GetSubChannelCount(i);
        for (uint8_t s = 0; s < sub_count && idx + 6 <= 200; s++) {
            uint16_t sub_id;
            int32_t sub_value;
            if (PMU_ChannelExec_GetTimerSubChannel(i, s, &sub_id, &sub_value)) {
                buf[idx++] = sub_id & 0xFF;
                buf[idx++] = (sub_id >> 8) & 0xFF;
                buf[idx++] = sub_value & 0xFF;
                buf[idx++] = (sub_value >> 8) & 0xFF;
                buf[idx++] = (sub_value >> 16) & 0xFF;
                buf[idx++] = (sub_value >> 24) & 0xFF;
            }
        }
    }

    *len = idx;
}

/* ============================================================================
 * Public API
 * ============================================================================ */

void PMU_ST_Init(void)
{
    ST_Init(&g_st_ctx, 100);  /* 100ms timeout */
    g_st_ctx.on_packet = on_packet;

    stream_active = false;
    config_len = 0;
    stream_counter = 0;
}

bool PMU_ST_LoadSavedConfig(void)
{
    if (Config_LoadFromFlash() && config_len > 0) {
        PMU_ChannelExec_LoadConfig(config_buffer, config_len);
        return true;
    }
    return false;
}

void PMU_ST_ProcessByte(uint8_t byte)
{
    /* Direct processing (used by main loop polling) */
    ST_ProcessByte(&g_st_ctx, byte, HAL_GetTick());
}

void PMU_ST_Update(void)
{
    uint32_t now = HAL_GetTick();

    /* Process RX bytes - refresh timestamp periodically to avoid stale timeout detection */
    while (st_rx_tail != st_rx_head) {
        uint8_t byte = st_rx_ring[st_rx_tail];
        st_rx_tail = (st_rx_tail + 1) % ST_RX_RING_SIZE;

        /* Refresh timestamp before processing each byte to prevent false stale packet detection */
        now = HAL_GetTick();
        ST_ProcessByte(&g_st_ctx, byte, now);
    }

    /* Note: Direct UART polling removed - all bytes go through ring buffer
     * from main loop (PMU_ST_RxByte) and TX polling (poll_rx_byte) */

    /* Send telemetry if streaming */
    if (stream_active && (now - last_stream_time) >= stream_period_ms) {
        last_stream_time = now;

        static uint8_t telemetry_buf[250];
        uint16_t len = 0;
        build_telemetry(telemetry_buf, &len);
        uart_send_packet(ST_CMD_DATA, telemetry_buf, len);
    }
}

#endif /* NUCLEO_F446RE */
