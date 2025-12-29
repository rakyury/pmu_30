/**
 ******************************************************************************
 * @file           : pmu_esp32.c
 * @brief          : ESP32-C3 Communication Bridge Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-30
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module implements UART communication with the ESP32-C3 module using
 * AT commands. It provides a ring buffer for async RX and blocking command
 * execution with timeout handling.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_esp32.h"
#include <string.h>
#include <stdio.h>
#include <stdarg.h>

/* ============================================================================
 * EMULATOR STUB IMPLEMENTATION
 * ============================================================================
 * In the emulator, we don't have actual ESP32 hardware. These stubs provide
 * a simulated "always ready" ESP32 module for testing.
 * ============================================================================ */
#ifdef PMU_EMULATOR

/* Module state */
static PMU_ESP32_State_t s_state = PMU_ESP32_STATE_OFF;
static uint8_t s_initialized = 0;
static PMU_ESP32_Stats_t s_stats;
static PMU_ESP32_Callback_t s_callback = NULL;
static void* s_callback_user_data = NULL;

HAL_StatusTypeDef PMU_ESP32_Init(void)
{
    if (s_initialized) return HAL_OK;
    memset(&s_stats, 0, sizeof(s_stats));
    s_state = PMU_ESP32_STATE_READY;
    s_initialized = 1;
    return HAL_OK;
}

HAL_StatusTypeDef PMU_ESP32_DeInit(void)
{
    s_state = PMU_ESP32_STATE_OFF;
    s_initialized = 0;
    return HAL_OK;
}

HAL_StatusTypeDef PMU_ESP32_Reset(void)
{
    s_state = PMU_ESP32_STATE_READY;
    return HAL_OK;
}

bool PMU_ESP32_IsReady(void) { return (s_state == PMU_ESP32_STATE_READY); }
PMU_ESP32_State_t PMU_ESP32_GetState(void) { return s_state; }

PMU_ESP32_Response_t PMU_ESP32_SendCommand(const char* cmd, char* response,
                                            uint16_t response_size, uint32_t timeout_ms)
{
    (void)timeout_ms;
    if (!s_initialized || !cmd) return PMU_ESP32_RESP_ERROR;
    s_stats.commands_sent++;
    s_stats.responses_ok++;
    if (response && response_size > 0) response[0] = '\0';
    return PMU_ESP32_RESP_OK;
}

PMU_ESP32_Response_t PMU_ESP32_SendCommandF(const char* fmt, ...)
{
    (void)fmt;
    if (!s_initialized) return PMU_ESP32_RESP_ERROR;
    s_stats.commands_sent++;
    s_stats.responses_ok++;
    return PMU_ESP32_RESP_OK;
}

HAL_StatusTypeDef PMU_ESP32_SendData(const uint8_t* data, uint16_t length, uint32_t timeout_ms)
{
    (void)data; (void)timeout_ms;
    if (!s_initialized || length == 0) return HAL_ERROR;
    s_stats.tx_bytes += length;
    return HAL_OK;
}

void PMU_ESP32_ProcessRx(void) { }
void PMU_ESP32_Update(void) { }

HAL_StatusTypeDef PMU_ESP32_GetInfo(PMU_ESP32_Info_t* info)
{
    if (!info) return HAL_ERROR;
    memset(info, 0, sizeof(*info));
    strncpy(info->at_version, "EMU-1.0.0", sizeof(info->at_version) - 1);
    strncpy(info->sdk_version, "Emulator", sizeof(info->sdk_version) - 1);
    strncpy(info->mac_sta, "00:00:00:00:00:00", sizeof(info->mac_sta) - 1);
    strncpy(info->mac_ap, "00:00:00:00:00:01", sizeof(info->mac_ap) - 1);
    return HAL_OK;
}

const PMU_ESP32_Stats_t* PMU_ESP32_GetStats(void) { return &s_stats; }

void PMU_ESP32_SetCallback(PMU_ESP32_Callback_t callback, void* user_data)
{
    s_callback = callback;
    s_callback_user_data = user_data;
}

bool PMU_ESP32_Test(void) { return s_initialized; }

#else /* !PMU_EMULATOR - Real hardware implementation */

/* Private typedef -----------------------------------------------------------*/

/**
 * @brief Ring buffer structure
 */
typedef struct {
    uint8_t buffer[PMU_ESP32_RX_BUFFER_SIZE];
    volatile uint16_t head;
    volatile uint16_t tail;
} RingBuffer_t;

/* Private define ------------------------------------------------------------*/

/* GPIO pins for ESP32 control (adjust based on hardware) */
#ifndef ESP32_RST_GPIO_Port
#define ESP32_RST_GPIO_Port     GPIOD
#endif
#ifndef ESP32_RST_Pin
#define ESP32_RST_Pin           GPIO_PIN_0
#endif
#ifndef ESP32_BOOT_GPIO_Port
#define ESP32_BOOT_GPIO_Port    GPIOD
#endif
#ifndef ESP32_BOOT_Pin
#define ESP32_BOOT_Pin          GPIO_PIN_1
#endif

/* Private macro -------------------------------------------------------------*/

/* Ring buffer macros */
#define RING_BUFFER_SIZE(rb)    (((rb).head - (rb).tail) & (PMU_ESP32_RX_BUFFER_SIZE - 1))
#define RING_BUFFER_EMPTY(rb)   ((rb).head == (rb).tail)
#define RING_BUFFER_FULL(rb)    (RING_BUFFER_SIZE(rb) == (PMU_ESP32_RX_BUFFER_SIZE - 1))

/* Private variables ---------------------------------------------------------*/

/* UART handle for ESP32 communication */
extern UART_HandleTypeDef huart3;

/* Module state */
static PMU_ESP32_State_t s_state = PMU_ESP32_STATE_OFF;
static uint8_t s_initialized = 0;

/* Ring buffer for UART RX */
static RingBuffer_t s_rx_buffer;

/* Response parsing */
static char s_line_buffer[PMU_ESP32_RESP_BUFFER_SIZE];
static uint16_t s_line_pos = 0;

/* Async callback */
static PMU_ESP32_Callback_t s_callback = NULL;
static void* s_callback_user_data = NULL;

/* Statistics */
static PMU_ESP32_Stats_t s_stats;

/* Single byte receive buffer for interrupt */
static uint8_t s_rx_byte;

/* Private function prototypes -----------------------------------------------*/
static void RingBuffer_Init(RingBuffer_t* rb);
static uint8_t RingBuffer_Put(RingBuffer_t* rb, uint8_t byte);
static uint8_t RingBuffer_Get(RingBuffer_t* rb, uint8_t* byte);
static uint16_t RingBuffer_Read(RingBuffer_t* rb, uint8_t* data, uint16_t max_len);
static void ESP32_GPIO_Init(void);
static HAL_StatusTypeDef ESP32_UART_Init(void);
static PMU_ESP32_Response_t ESP32_ParseResponse(const char* response);
static uint8_t ESP32_ReadLine(char* line, uint16_t max_len, uint32_t timeout_ms);
static uint32_t ESP32_GetTick(void);

/* Exported functions --------------------------------------------------------*/

HAL_StatusTypeDef PMU_ESP32_Init(void)
{
    if (s_initialized) {
        return HAL_OK;
    }

    /* Initialize state */
    s_state = PMU_ESP32_STATE_OFF;
    memset(&s_stats, 0, sizeof(s_stats));

    /* Initialize ring buffer */
    RingBuffer_Init(&s_rx_buffer);
    s_line_pos = 0;

    /* Initialize GPIO for reset/boot control */
    ESP32_GPIO_Init();

    /* Initialize UART */
    HAL_StatusTypeDef status = ESP32_UART_Init();
    if (status != HAL_OK) {
        return status;
    }

    /* Start UART receive interrupt */
    HAL_UART_Receive_IT(&huart3, &s_rx_byte, 1);

    s_initialized = 1;

    /* Reset and wait for ready */
    status = PMU_ESP32_Reset();
    if (status == HAL_OK) {
        s_state = PMU_ESP32_STATE_READY;
    }

    return status;
}

HAL_StatusTypeDef PMU_ESP32_DeInit(void)
{
    if (!s_initialized) {
        return HAL_OK;
    }

    /* Stop UART */
    HAL_UART_AbortReceive(&huart3);
    HAL_UART_DeInit(&huart3);

    /* Put ESP32 in reset */
    HAL_GPIO_WritePin(ESP32_RST_GPIO_Port, ESP32_RST_Pin, GPIO_PIN_RESET);

    s_state = PMU_ESP32_STATE_OFF;
    s_initialized = 0;

    return HAL_OK;
}

HAL_StatusTypeDef PMU_ESP32_Reset(void)
{
    if (!s_initialized) {
        return HAL_ERROR;
    }

    s_state = PMU_ESP32_STATE_BOOTING;

    /* Clear RX buffer */
    RingBuffer_Init(&s_rx_buffer);
    s_line_pos = 0;

    /* Hardware reset sequence */
    /* Pull EN low */
    HAL_GPIO_WritePin(ESP32_RST_GPIO_Port, ESP32_RST_Pin, GPIO_PIN_RESET);
    HAL_Delay(100);

    /* Release EN - ESP32 starts booting */
    HAL_GPIO_WritePin(ESP32_RST_GPIO_Port, ESP32_RST_Pin, GPIO_PIN_SET);

    /* Wait for "ready" response */
    char line[128];
    uint32_t start = ESP32_GetTick();

    while ((ESP32_GetTick() - start) < PMU_ESP32_RESET_TIMEOUT_MS) {
        if (ESP32_ReadLine(line, sizeof(line), 100)) {
            if (strstr(line, PMU_ESP32_RESP_READY_STR) != NULL) {
                s_state = PMU_ESP32_STATE_READY;
                return HAL_OK;
            }
        }
    }

    s_state = PMU_ESP32_STATE_ERROR;
    s_stats.timeouts++;
    return HAL_TIMEOUT;
}

bool PMU_ESP32_IsReady(void)
{
    return (s_state == PMU_ESP32_STATE_READY);
}

PMU_ESP32_State_t PMU_ESP32_GetState(void)
{
    return s_state;
}

PMU_ESP32_Response_t PMU_ESP32_SendCommand(const char* cmd,
                                            char* response,
                                            uint16_t response_size,
                                            uint32_t timeout_ms)
{
    if (!s_initialized || !cmd) {
        return PMU_ESP32_RESP_ERROR;
    }

    if (s_state != PMU_ESP32_STATE_READY) {
        return PMU_ESP32_RESP_BUSY;
    }

    s_state = PMU_ESP32_STATE_BUSY;

    /* Clear any pending data */
    RingBuffer_Init(&s_rx_buffer);
    s_line_pos = 0;

    /* Send command with CRLF */
    char cmd_buf[PMU_ESP32_TX_BUFFER_SIZE];
    int len = snprintf(cmd_buf, sizeof(cmd_buf), "%s\r\n", cmd);

    HAL_StatusTypeDef status = HAL_UART_Transmit(&huart3, (uint8_t*)cmd_buf, len, PMU_ESP32_UART_TIMEOUT_MS);
    if (status != HAL_OK) {
        s_state = PMU_ESP32_STATE_READY;
        return PMU_ESP32_RESP_ERROR;
    }

    s_stats.commands_sent++;
    s_stats.tx_bytes += len;

    /* Initialize response buffer */
    if (response && response_size > 0) {
        response[0] = '\0';
    }
    uint16_t resp_pos = 0;

    /* Wait for response */
    char line[PMU_ESP32_RESP_BUFFER_SIZE];
    uint32_t start = ESP32_GetTick();
    PMU_ESP32_Response_t result = PMU_ESP32_RESP_PENDING;

    while ((ESP32_GetTick() - start) < timeout_ms && result == PMU_ESP32_RESP_PENDING) {
        if (ESP32_ReadLine(line, sizeof(line), 50)) {
            /* Skip echo of command */
            if (strncmp(line, cmd, strlen(cmd)) == 0) {
                continue;
            }

            /* Check for final response */
            if (strstr(line, PMU_ESP32_RESP_OK_STR) != NULL) {
                result = PMU_ESP32_RESP_OK;
                s_stats.responses_ok++;
            } else if (strstr(line, PMU_ESP32_RESP_ERROR_STR) != NULL) {
                result = PMU_ESP32_RESP_ERROR;
                s_stats.responses_error++;
            } else if (strstr(line, PMU_ESP32_RESP_FAIL_STR) != NULL) {
                result = PMU_ESP32_RESP_FAIL;
                s_stats.responses_error++;
            } else if (strstr(line, PMU_ESP32_RESP_BUSY_P_STR) != NULL ||
                       strstr(line, PMU_ESP32_RESP_BUSY_S_STR) != NULL) {
                result = PMU_ESP32_RESP_BUSY;
            } else {
                /* Append to response buffer */
                if (response && resp_pos < response_size - 1) {
                    int line_len = strlen(line);
                    int copy_len = (resp_pos + line_len < response_size - 1) ?
                                   line_len : (response_size - 1 - resp_pos);
                    memcpy(response + resp_pos, line, copy_len);
                    resp_pos += copy_len;
                    response[resp_pos] = '\0';

                    /* Add newline if there's room */
                    if (resp_pos < response_size - 2) {
                        response[resp_pos++] = '\n';
                        response[resp_pos] = '\0';
                    }
                }

                /* Check for async notification */
                if (s_callback && (line[0] == '+' || strncmp(line, "WIFI", 4) == 0)) {
                    s_callback(line, s_callback_user_data);
                }
            }
        }
    }

    if (result == PMU_ESP32_RESP_PENDING) {
        result = PMU_ESP32_RESP_TIMEOUT;
        s_stats.timeouts++;
    } else {
        s_stats.last_response_time_ms = ESP32_GetTick();
    }

    s_state = PMU_ESP32_STATE_READY;
    return result;
}

PMU_ESP32_Response_t PMU_ESP32_SendCommandF(const char* fmt, ...)
{
    char cmd[PMU_ESP32_TX_BUFFER_SIZE];
    va_list args;
    va_start(args, fmt);
    vsnprintf(cmd, sizeof(cmd), fmt, args);
    va_end(args);

    return PMU_ESP32_SendCommand(cmd, NULL, 0, PMU_ESP32_CMD_TIMEOUT_MS);
}

HAL_StatusTypeDef PMU_ESP32_SendData(const uint8_t* data,
                                      uint16_t length,
                                      uint32_t timeout_ms)
{
    if (!s_initialized || !data || length == 0) {
        return HAL_ERROR;
    }

    HAL_StatusTypeDef status = HAL_UART_Transmit(&huart3, (uint8_t*)data, length, timeout_ms);
    if (status == HAL_OK) {
        s_stats.tx_bytes += length;
    }
    return status;
}

void PMU_ESP32_ProcessRx(void)
{
    /* Called from UART RX complete callback */
    if (!s_initialized) {
        return;
    }

    RingBuffer_Put(&s_rx_buffer, s_rx_byte);
    s_stats.rx_bytes++;

    /* Re-arm receive interrupt */
    HAL_UART_Receive_IT(&huart3, &s_rx_byte, 1);
}

void PMU_ESP32_Update(void)
{
    if (!s_initialized) {
        return;
    }

    /* Check for unsolicited messages when idle */
    if (s_state == PMU_ESP32_STATE_READY) {
        char line[128];
        while (ESP32_ReadLine(line, sizeof(line), 0)) {
            /* Handle async notifications */
            if (s_callback && (line[0] == '+' || strncmp(line, "WIFI", 4) == 0)) {
                s_callback(line, s_callback_user_data);
            }
        }
    }
}

HAL_StatusTypeDef PMU_ESP32_GetInfo(PMU_ESP32_Info_t* info)
{
    if (!s_initialized || !info) {
        return HAL_ERROR;
    }

    memset(info, 0, sizeof(PMU_ESP32_Info_t));

    /* Get version info */
    char response[256];
    if (PMU_ESP32_SendCommand(PMU_ESP32_CMD_GMR, response, sizeof(response),
                               PMU_ESP32_CMD_TIMEOUT_MS) != PMU_ESP32_RESP_OK) {
        return HAL_ERROR;
    }

    /* Parse AT version */
    char* at_ver = strstr(response, "AT version:");
    if (at_ver) {
        sscanf(at_ver, "AT version:%31s", info->at_version);
    }

    /* Parse SDK version */
    char* sdk_ver = strstr(response, "SDK version:");
    if (sdk_ver) {
        sscanf(sdk_ver, "SDK version:%31s", info->sdk_version);
    }

    /* Get MAC addresses */
    if (PMU_ESP32_SendCommand(PMU_ESP32_CMD_CIFSR, response, sizeof(response),
                               PMU_ESP32_CMD_TIMEOUT_MS) == PMU_ESP32_RESP_OK) {
        /* Parse STA MAC */
        char* sta_mac = strstr(response, "STAMAC,");
        if (sta_mac) {
            sscanf(sta_mac, "STAMAC,\"%17[^\"]\"", info->mac_sta);
        }

        /* Parse AP MAC */
        char* ap_mac = strstr(response, "APMAC,");
        if (ap_mac) {
            sscanf(ap_mac, "APMAC,\"%17[^\"]\"", info->mac_ap);
        }
    }

    return HAL_OK;
}

const PMU_ESP32_Stats_t* PMU_ESP32_GetStats(void)
{
    return &s_stats;
}

void PMU_ESP32_SetCallback(PMU_ESP32_Callback_t callback, void* user_data)
{
    s_callback = callback;
    s_callback_user_data = user_data;
}

bool PMU_ESP32_Test(void)
{
    return (PMU_ESP32_SendCommand(PMU_ESP32_CMD_AT, NULL, 0,
                                   PMU_ESP32_CMD_TIMEOUT_MS) == PMU_ESP32_RESP_OK);
}

/* Private functions ---------------------------------------------------------*/

static void RingBuffer_Init(RingBuffer_t* rb)
{
    rb->head = 0;
    rb->tail = 0;
}

static uint8_t RingBuffer_Put(RingBuffer_t* rb, uint8_t byte)
{
    uint16_t next = (rb->head + 1) & (PMU_ESP32_RX_BUFFER_SIZE - 1);
    if (next == rb->tail) {
        /* Buffer full */
        return 0;
    }
    rb->buffer[rb->head] = byte;
    rb->head = next;
    return 1;
}

static uint8_t RingBuffer_Get(RingBuffer_t* rb, uint8_t* byte)
{
    if (rb->head == rb->tail) {
        /* Buffer empty */
        return 0;
    }
    *byte = rb->buffer[rb->tail];
    rb->tail = (rb->tail + 1) & (PMU_ESP32_RX_BUFFER_SIZE - 1);
    return 1;
}

static uint16_t RingBuffer_Read(RingBuffer_t* rb, uint8_t* data, uint16_t max_len)
{
    uint16_t count = 0;
    while (count < max_len && RingBuffer_Get(rb, &data[count])) {
        count++;
    }
    return count;
}

static void ESP32_GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* Enable GPIO clocks */
    __HAL_RCC_GPIOD_CLK_ENABLE();

    /* Configure reset pin as output (active low) */
    GPIO_InitStruct.Pin = ESP32_RST_Pin;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(ESP32_RST_GPIO_Port, &GPIO_InitStruct);

    /* Configure boot pin as output (for programming mode) */
    GPIO_InitStruct.Pin = ESP32_BOOT_Pin;
    HAL_GPIO_Init(ESP32_BOOT_GPIO_Port, &GPIO_InitStruct);

    /* Set initial states */
    HAL_GPIO_WritePin(ESP32_RST_GPIO_Port, ESP32_RST_Pin, GPIO_PIN_SET);   /* Not reset */
    HAL_GPIO_WritePin(ESP32_BOOT_GPIO_Port, ESP32_BOOT_Pin, GPIO_PIN_SET); /* Normal boot */
}

static HAL_StatusTypeDef ESP32_UART_Init(void)
{
    /* Enable UART3 clock */
    __HAL_RCC_USART3_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();

    /* Configure UART pins PC10 (TX), PC11 (RX) */
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin = GPIO_PIN_10 | GPIO_PIN_11;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF7_USART3;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

    /* Configure UART3 */
    huart3.Instance = USART3;
    huart3.Init.BaudRate = PMU_ESP32_UART_BAUD;
    huart3.Init.WordLength = UART_WORDLENGTH_8B;
    huart3.Init.StopBits = UART_STOPBITS_1;
    huart3.Init.Parity = UART_PARITY_NONE;
    huart3.Init.Mode = UART_MODE_TX_RX;
    huart3.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart3.Init.OverSampling = UART_OVERSAMPLING_16;
    huart3.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
    huart3.Init.ClockPrescaler = UART_PRESCALER_DIV1;

    HAL_StatusTypeDef status = HAL_UART_Init(&huart3);
    if (status != HAL_OK) {
        return status;
    }

    /* Enable UART interrupt */
    HAL_NVIC_SetPriority(USART3_IRQn, 5, 0);
    HAL_NVIC_EnableIRQ(USART3_IRQn);

    return HAL_OK;
}

static PMU_ESP32_Response_t ESP32_ParseResponse(const char* response)
{
    if (strstr(response, PMU_ESP32_RESP_OK_STR)) {
        return PMU_ESP32_RESP_OK;
    }
    if (strstr(response, PMU_ESP32_RESP_ERROR_STR)) {
        return PMU_ESP32_RESP_ERROR;
    }
    if (strstr(response, PMU_ESP32_RESP_FAIL_STR)) {
        return PMU_ESP32_RESP_FAIL;
    }
    return PMU_ESP32_RESP_PENDING;
}

static uint8_t ESP32_ReadLine(char* line, uint16_t max_len, uint32_t timeout_ms)
{
    uint32_t start = ESP32_GetTick();
    uint8_t byte;

    while ((ESP32_GetTick() - start) <= timeout_ms || timeout_ms == 0) {
        while (RingBuffer_Get(&s_rx_buffer, &byte)) {
            if (byte == '\n') {
                /* End of line */
                if (s_line_pos > 0 && s_line_buffer[s_line_pos - 1] == '\r') {
                    s_line_pos--;
                }
                s_line_buffer[s_line_pos] = '\0';

                if (s_line_pos > 0) {
                    /* Copy to output */
                    strncpy(line, s_line_buffer, max_len - 1);
                    line[max_len - 1] = '\0';
                    s_line_pos = 0;
                    return 1;
                }
                s_line_pos = 0;
            } else if (byte != '\r' && s_line_pos < sizeof(s_line_buffer) - 1) {
                s_line_buffer[s_line_pos++] = byte;
            }
        }

        if (timeout_ms == 0) {
            break;
        }
    }

    return 0;
}

static uint32_t ESP32_GetTick(void)
{
    return HAL_GetTick();
}

/* UART callbacks ------------------------------------------------------------*/

/**
 * @brief UART RX complete callback - called when byte received
 */
void HAL_UART_RxCpltCallback_ESP32(UART_HandleTypeDef* huart)
{
    if (huart->Instance == USART3) {
        PMU_ESP32_ProcessRx();
    }
}

#endif /* PMU_EMULATOR */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
