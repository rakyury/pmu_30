/**
 ******************************************************************************
 * @file           : pmu_serial_transfer_port.h
 * @brief          : SerialTransfer Protocol Port Adapter Header
 ******************************************************************************
 */

#ifndef PMU_SERIAL_TRANSFER_PORT_H
#define PMU_SERIAL_TRANSFER_PORT_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

/* SerialTransfer Command IDs (Packet ID) */
#define ST_CMD_PING              0x01
#define ST_CMD_PONG              0x02
#define ST_CMD_RESET             0x05  /* Software reset (NVIC_SystemReset) */
#define ST_CMD_GET_CONFIG        0x10
#define ST_CMD_CONFIG_DATA       0x11
#define ST_CMD_LOAD_CONFIG       0x12
#define ST_CMD_CONFIG_ACK        0x13
#define ST_CMD_SAVE_CONFIG       0x14
#define ST_CMD_FLASH_ACK         0x15
#define ST_CMD_CLEAR_CONFIG      0x16
#define ST_CMD_CLEAR_CONFIG_ACK  0x17
#define ST_CMD_LOAD_BINARY       0x18
#define ST_CMD_BINARY_ACK        0x19
#define ST_CMD_START_STREAM      0x20
#define ST_CMD_STOP_STREAM       0x21
#define ST_CMD_DATA              0x22
#define ST_CMD_SET_OUTPUT        0x28
#define ST_CMD_OUTPUT_ACK        0x29
#define ST_CMD_GET_CAPABILITIES  0x30
#define ST_CMD_CAPABILITIES      0x31
#define ST_CMD_CAN_INJECT        0x40  /* Inject CAN message for testing */
#define ST_CMD_CAN_INJECT_ACK    0x41
#define ST_CMD_ACK               0x3E
#define ST_CMD_NACK              0x3F

/* Device Types */
#define PMU_DEVICE_TYPE_PMU30           0x00
#define PMU_DEVICE_TYPE_PMU30_PRO       0x01
#define PMU_DEVICE_TYPE_PMU16_MINI      0x02
#define PMU_DEVICE_TYPE_NUCLEO_F446RE   0x10  /* Development board */

/* Firmware Version */
#define PMU_FW_VERSION_MAJOR        1
#define PMU_FW_VERSION_MINOR        0
#define PMU_FW_VERSION_PATCH        0

/* Device-specific capabilities */
#ifdef NUCLEO_F446RE
/* Nucleo-F446RE Development Board:
 * - Outputs: 6 (PA5-LED, PB0, PB1, PC8, PC9, PA8-PWM)
 * - Analog inputs: 3 (PA0, PA1, PA4 via ADC1)
 * - Digital inputs: 1 (PC13 User button B1)
 * - H-Bridges: 0 (no H-Bridge drivers)
 * - CAN buses: 1 (CAN1 on PB8/PB9)
 */
#define PMU_DEVICE_TYPE             PMU_DEVICE_TYPE_NUCLEO_F446RE
#define PMU_OUTPUT_COUNT            6
#define PMU_ANALOG_INPUT_COUNT      3
#define PMU_DIGITAL_INPUT_COUNT     1
#define PMU_HBRIDGE_COUNT           0
#define PMU_CAN_BUS_COUNT           1
#else
/* Production PMU-30 */
#define PMU_DEVICE_TYPE             PMU_DEVICE_TYPE_PMU30
#define PMU_OUTPUT_COUNT            30
#define PMU_ANALOG_INPUT_COUNT      10
#define PMU_DIGITAL_INPUT_COUNT     8
#define PMU_HBRIDGE_COUNT           2
#define PMU_CAN_BUS_COUNT           2
#endif

/**
 * @brief Initialize SerialTransfer protocol
 */
void PMU_ST_Init(void);

/**
 * @brief Add received byte to ring buffer (used by main loop and TX polling)
 * @param byte Received byte
 * @note All RX bytes must go through ring buffer for consistent FIFO ordering
 */
void PMU_ST_RxByte(uint8_t byte);

/**
 * @brief Process received byte through SerialTransfer (deprecated - use PMU_ST_RxByte)
 * @param byte Received byte
 */
void PMU_ST_ProcessByte(uint8_t byte);

/**
 * @brief Periodic SerialTransfer update - call every 1ms
 */
void PMU_ST_Update(void);

/**
 * @brief Send telemetry data packet
 */
void PMU_ST_SendTelemetry(void);

/**
 * @brief Check if stream is active
 * @return true if streaming
 */
bool PMU_ST_IsStreamActive(void);

/**
 * @brief Load saved config from flash and apply to channel executor
 * @return true if valid config was loaded
 */
bool PMU_ST_LoadSavedConfig(void);

#ifdef __cplusplus
}
#endif

#endif /* PMU_SERIAL_TRANSFER_PORT_H */
