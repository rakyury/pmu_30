/**
 ******************************************************************************
 * @file           : pmu_can.c
 * @brief          : CAN Bus Driver (2x CAN FD + 2x CAN 2.0) Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module implements:
 * - 2x CAN FD interfaces (up to 5Mbps data phase)
 * - 2x CAN 2.0 A/B interfaces (up to 1Mbps)
 * - DBC signal mapping and parsing
 * - Virtual channel updates from CAN data
 * - Signal timeout detection
 * - Bus statistics and monitoring
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_can.h"
#include "pmu_logic.h"
#include "stm32h7xx_hal.h"
#include <string.h>
#include <math.h>

/* Private typedef -----------------------------------------------------------*/

/**
 * @brief CAN bus state
 */
typedef struct {
    FDCAN_HandleTypeDef* hfdcan;        /* FDCAN handle (or NULL for classic CAN) */
    PMU_CAN_BusConfig_t config;         /* Bus configuration */
    PMU_CAN_Statistics_t stats;         /* Bus statistics */
    PMU_CAN_SignalMap_t signal_maps[PMU_CAN_MAX_SIGNAL_MAPS];  /* Signal mappings */
    uint16_t signal_count;              /* Number of active signal mappings */
    uint8_t is_initialized;             /* Initialization flag */
} PMU_CAN_BusState_t;

/* Private define ------------------------------------------------------------*/

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_CAN_BusState_t can_buses[PMU_CAN_BUS_COUNT];
static FDCAN_HandleTypeDef hfdcan1;     /* CAN FD 1 */
static FDCAN_HandleTypeDef hfdcan2;     /* CAN FD 2 */
static FDCAN_HandleTypeDef hfdcan3;     /* CAN 2.0 (FDCAN in classic mode) */
static uint32_t system_tick_ms = 0;     /* System tick counter in ms */

/* Private function prototypes -----------------------------------------------*/
static HAL_StatusTypeDef CAN_InitBus(PMU_CAN_Bus_t bus);
static void CAN_ProcessRxMessage(PMU_CAN_Bus_t bus, PMU_CAN_Message_t* msg);
static void CAN_ParseSignals(PMU_CAN_Bus_t bus, PMU_CAN_Message_t* msg);
static float CAN_ExtractSignal(uint8_t* data, PMU_CAN_SignalMap_t* signal);
static void CAN_CheckTimeouts(PMU_CAN_Bus_t bus);
static uint8_t CAN_BytesToDLC(uint8_t bytes);

/* Private user code ---------------------------------------------------------*/

/**
 * @brief Initialize CAN bus driver
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_Init(void)
{
    /* Clear bus states */
    memset(can_buses, 0, sizeof(can_buses));

    /* Assign FDCAN handles */
    can_buses[PMU_CAN_BUS_1].hfdcan = &hfdcan1;
    can_buses[PMU_CAN_BUS_2].hfdcan = &hfdcan2;
    can_buses[PMU_CAN_BUS_3].hfdcan = &hfdcan3;
    can_buses[PMU_CAN_BUS_4].hfdcan = NULL;  /* TODO: Assign if available */

    /* Set default configurations */
    for (uint8_t i = 0; i < PMU_CAN_BUS_COUNT; i++) {
        can_buses[i].config.bitrate = PMU_CAN_BITRATE_500K;
        can_buses[i].config.fd_bitrate = PMU_CAN_FD_BITRATE_2M;
        can_buses[i].config.enable_fd = (i < 2) ? 1 : 0;  /* FD for first 2 buses */
        can_buses[i].config.enable_termination = 1;
    }

    /* Initialize each bus */
    for (uint8_t i = 0; i < PMU_CAN_BUS_COUNT; i++) {
        if (can_buses[i].hfdcan != NULL) {
            if (CAN_InitBus(i) == HAL_OK) {
                can_buses[i].is_initialized = 1;
            }
        }
    }

    return HAL_OK;
}

/**
 * @brief Initialize a single CAN bus
 * @param bus Bus identifier
 * @retval HAL status
 */
static HAL_StatusTypeDef CAN_InitBus(PMU_CAN_Bus_t bus)
{
    if (bus >= PMU_CAN_BUS_COUNT || can_buses[bus].hfdcan == NULL) {
        return HAL_ERROR;
    }

#ifdef UNIT_TEST
    /* Skip hardware initialization for unit tests */
    return HAL_OK;
#else
    /* Configure FDCAN peripheral for STM32H7
     * STM32H7 has FDCAN1, FDCAN2, FDCAN3
     * Clock: typically 80MHz from PLL1Q
     */

    FDCAN_HandleTypeDef* hfdcan = can_buses[bus].hfdcan;

    /* Assign FDCAN instance */
    hfdcan->Instance = (bus == PMU_CAN_BUS_1) ? FDCAN1 :
                       (bus == PMU_CAN_BUS_2) ? FDCAN2 : FDCAN3;

    /* Basic FDCAN configuration */
    hfdcan->Init.FrameFormat = can_buses[bus].config.enable_fd ?
                               FDCAN_FRAME_FD_BRS : FDCAN_FRAME_CLASSIC;
    hfdcan->Init.Mode = FDCAN_MODE_NORMAL;
    hfdcan->Init.AutoRetransmission = ENABLE;
    hfdcan->Init.TransmitPause = DISABLE;
    hfdcan->Init.ProtocolException = DISABLE;

    /* Nominal bit timing (500kbps @ 80MHz FDCAN clock)
     * Bit time = NominalPrescaler × (NominalSyncJumpWidth + NominalTimeSeg1 + NominalTimeSeg2)
     * Target: 500 kbps = 2µs bit time
     * Formula: Bit rate = Clock / (Prescaler × (1 + TimeSeg1 + TimeSeg2))
     *          500k = 80MHz / (Prescaler × Total)
     *          Prescaler × Total = 160
     * Using Prescaler=10, Total=16: 1 + 13 + 2 = 16
     */
    hfdcan->Init.NominalPrescaler = 10;           /* 80MHz / 10 = 8MHz */
    hfdcan->Init.NominalSyncJumpWidth = 2;        /* Max 1-4 */
    hfdcan->Init.NominalTimeSeg1 = 13;            /* Prop + Phase1: 1-256 */
    hfdcan->Init.NominalTimeSeg2 = 2;             /* Phase2: 1-128 */

    /* Data bit timing for CAN FD (2Mbps @ 80MHz)
     * Only used if enable_fd = 1
     * Faster data phase: 2 Mbps = 0.5µs bit time
     * Using Prescaler=2, Total=20: 1 + 15 + 4 = 20
     */
    hfdcan->Init.DataPrescaler = 2;               /* 80MHz / 2 = 40MHz */
    hfdcan->Init.DataSyncJumpWidth = 4;
    hfdcan->Init.DataTimeSeg1 = 15;
    hfdcan->Init.DataTimeSeg2 = 4;

    /* Message RAM configuration
     * STM32H7 FDCAN uses shared message RAM (10KB total)
     * Configure Tx/Rx buffer sizes
     */
    hfdcan->Init.MessageRAMOffset = bus * 0x400;  /* 1KB per bus offset */
    hfdcan->Init.StdFiltersNbr = 8;               /* 8 standard ID filters */
    hfdcan->Init.ExtFiltersNbr = 0;               /* No extended ID filters */
    hfdcan->Init.RxFifo0ElmtsNbr = 16;            /* 16 RX FIFO0 elements */
    hfdcan->Init.RxFifo0ElmtSize = FDCAN_DATA_BYTES_8;
    hfdcan->Init.RxFifo1ElmtsNbr = 0;             /* No FIFO1 */
    hfdcan->Init.RxBuffersNbr = 0;                /* No dedicated RX buffers */
    hfdcan->Init.TxEventsNbr = 0;                 /* No TX event FIFO */
    hfdcan->Init.TxBuffersNbr = 0;                /* No dedicated TX buffers */
    hfdcan->Init.TxFifoQueueElmtsNbr = 8;         /* 8 TX FIFO elements */
    hfdcan->Init.TxFifoQueueMode = FDCAN_TX_FIFO_OPERATION;
    hfdcan->Init.TxElmtSize = FDCAN_DATA_BYTES_8;

    /* Initialize FDCAN peripheral */
    if (HAL_FDCAN_Init(hfdcan) != HAL_OK) {
        return HAL_ERROR;
    }

    /* Configure filter to accept all standard IDs (0x000-0x7FF) */
    FDCAN_FilterTypeDef sFilterConfig;
    sFilterConfig.IdType = FDCAN_STANDARD_ID;
    sFilterConfig.FilterIndex = 0;
    sFilterConfig.FilterType = FDCAN_FILTER_RANGE;
    sFilterConfig.FilterConfig = FDCAN_FILTER_TO_RXFIFO0;
    sFilterConfig.FilterID1 = 0x000;              /* Start of range */
    sFilterConfig.FilterID2 = 0x7FF;              /* End of range */

    if (HAL_FDCAN_ConfigFilter(hfdcan, &sFilterConfig) != HAL_OK) {
        return HAL_ERROR;
    }

    /* Configure global filter to reject remote frames, non-matching frames go to FIFO0 */
    if (HAL_FDCAN_ConfigGlobalFilter(hfdcan,
                                       FDCAN_REJECT,     /* Reject remote standard frames */
                                       FDCAN_REJECT,     /* Reject remote extended frames */
                                       FDCAN_FILTER_REMOTE,  /* Filter remote frames */
                                       FDCAN_FILTER_REMOTE) != HAL_OK) {
        return HAL_ERROR;
    }

    /* Enable FDCAN RX FIFO0 New Message notification */
    if (HAL_FDCAN_ActivateNotification(hfdcan, FDCAN_IT_RX_FIFO0_NEW_MESSAGE, 0) != HAL_OK) {
        return HAL_ERROR;
    }

    /* Start FDCAN module */
    if (HAL_FDCAN_Start(hfdcan) != HAL_OK) {
        return HAL_ERROR;
    }

    can_buses[bus].stats.tx_count = 0;
    can_buses[bus].stats.rx_count = 0;
    can_buses[bus].stats.error_count = 0;

    return HAL_OK;
#endif
}

/**
 * @brief Update CAN communication (call periodically)
 * @retval None
 */
void PMU_CAN_Update(void)
{
    /* Increment system tick (called at ~10ms rate) */
    system_tick_ms += 10;

    /* Process each bus */
    for (uint8_t bus = 0; bus < PMU_CAN_BUS_COUNT; bus++) {
        if (!can_buses[bus].is_initialized) {
            continue;
        }

#ifndef UNIT_TEST
        /* Check for received messages in RX FIFO0
         * In real implementation, this is typically done in IRQ handler
         * Here we poll for demonstration
         */
        FDCAN_HandleTypeDef* hfdcan = can_buses[bus].hfdcan;

        if (HAL_FDCAN_GetRxFifoFillLevel(hfdcan, FDCAN_RX_FIFO0) > 0) {
            FDCAN_RxHeaderTypeDef rx_header;
            uint8_t rx_data[64];

            if (HAL_FDCAN_GetRxMessage(hfdcan, FDCAN_RX_FIFO0, &rx_header, rx_data) == HAL_OK) {
                /* Process received message */
                PMU_CAN_Message_t msg;
                msg.id = rx_header.Identifier;
                msg.length = CAN_DLCToBytes(rx_header.DataLength);
                msg.is_extended = (rx_header.IdType == FDCAN_EXTENDED_ID);
                msg.is_fd = (rx_header.FDFormat == FDCAN_FD_CAN);
                memcpy(msg.data, rx_data, msg.length);

                can_buses[bus].stats.rx_count++;

                /* Process signal mapping for this message */
                CAN_ProcessReceivedMessage(bus, &msg);
            }
        }
#endif

        /* Check for signal timeouts */
        CAN_CheckTimeouts(bus);
    }
}

/**
 * @brief Convert DLC code to number of bytes
 * @param dlc DLC code
 * @retval Number of bytes
 */
static uint8_t CAN_DLCToBytes(uint8_t dlc)
{
    /* CAN FD DLC to bytes mapping */
    const uint8_t dlc_to_bytes[] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64};

    if (dlc < 16) {
        return dlc_to_bytes[dlc];
    }
    return 8;  /* Default to 8 for classic CAN */
}

/**
 * @brief Configure CAN bus
 * @param bus Bus identifier
 * @param config Bus configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_ConfigureBus(PMU_CAN_Bus_t bus, PMU_CAN_BusConfig_t* config)
{
    if (bus >= PMU_CAN_BUS_COUNT || config == NULL) {
        return HAL_ERROR;
    }

    /* Copy configuration */
    memcpy(&can_buses[bus].config, config, sizeof(PMU_CAN_BusConfig_t));

    /* Re-initialize bus with new config */
    return CAN_InitBus(bus);
}

/**
 * @brief Send CAN message
 * @param bus Bus identifier
 * @param msg Message to send
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_SendMessage(PMU_CAN_Bus_t bus, PMU_CAN_Message_t* msg)
{
    if (bus >= PMU_CAN_BUS_COUNT || msg == NULL || !can_buses[bus].is_initialized) {
        return HAL_ERROR;
    }

#ifdef UNIT_TEST
    /* For unit tests, just increment counter */
    can_buses[bus].stats.tx_count++;
    return HAL_OK;
#else
    /* Transmit message via FDCAN */
    FDCAN_TxHeaderTypeDef tx_header;

    /* Configure TX header */
    tx_header.Identifier = msg->id;
    tx_header.IdType = msg->is_extended ? FDCAN_EXTENDED_ID : FDCAN_STANDARD_ID;
    tx_header.TxFrameType = FDCAN_DATA_FRAME;  /* Always data frame for now */
    tx_header.DataLength = CAN_BytesToDLC(msg->length) << 16;
    tx_header.ErrorStateIndicator = FDCAN_ESI_ACTIVE;
    tx_header.BitRateSwitch = msg->is_fd ? FDCAN_BRS_ON : FDCAN_BRS_OFF;
    tx_header.FDFormat = msg->is_fd ? FDCAN_FD_CAN : FDCAN_CLASSIC_CAN;
    tx_header.TxEventFifoControl = FDCAN_NO_TX_EVENTS;
    tx_header.MessageMarker = 0;

    /* Add message to TX FIFO */
    if (HAL_FDCAN_AddMessageToTxFifoQ(can_buses[bus].hfdcan, &tx_header, msg->data) != HAL_OK) {
        can_buses[bus].stats.error_count++;
        return HAL_ERROR;
    }

    can_buses[bus].stats.tx_count++;
    return HAL_OK;
#endif
}

/**
 * @brief Send simple CAN message
 * @param bus Bus identifier
 * @param id CAN ID
 * @param data Data bytes
 * @param len Data length
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_Send(uint8_t bus, uint32_t id, uint8_t* data, uint8_t len)
{
    PMU_CAN_Message_t msg;

    msg.id = id;
    msg.dlc = (len > 8) ? CAN_BytesToDLC(len) : len;
    msg.id_type = (id > 0x7FF) ? PMU_CAN_ID_EXTENDED : PMU_CAN_ID_STANDARD;
    msg.frame_type = (len > 8) ? PMU_CAN_FRAME_FD : PMU_CAN_FRAME_CLASSIC;
    msg.rtr = 0;

    if (data != NULL && len > 0) {
        memcpy(msg.data, data, (len > 64) ? 64 : len);
    }

    return PMU_CAN_SendMessage(bus, &msg);
}

/**
 * @brief Process received CAN message
 * @param bus Bus identifier
 * @param msg Received message
 */
static void CAN_ProcessRxMessage(PMU_CAN_Bus_t bus, PMU_CAN_Message_t* msg)
{
    /* Update statistics */
    can_buses[bus].stats.rx_count++;

    /* Parse signals if any mappings exist */
    if (can_buses[bus].signal_count > 0) {
        CAN_ParseSignals(bus, msg);
    }
}

/**
 * @brief Parse CAN signals and update virtual channels
 * @param bus Bus identifier
 * @param msg CAN message
 */
static void CAN_ParseSignals(PMU_CAN_Bus_t bus, PMU_CAN_Message_t* msg)
{
    /* Iterate through signal mappings */
    for (uint16_t i = 0; i < can_buses[bus].signal_count; i++) {
        PMU_CAN_SignalMap_t* signal = &can_buses[bus].signal_maps[i];

        /* Check if this signal is in this message */
        if (signal->can_id == msg->id) {
            /* Extract signal value */
            float value = CAN_ExtractSignal(msg->data, signal);

            /* Update virtual channel */
            PMU_Logic_SetVirtualChannel(signal->virtual_channel, (int32_t)value);

            /* Update timestamp */
            signal->last_update_ms = system_tick_ms;
        }
    }
}

/**
 * @brief Extract signal value from CAN data
 * @param data CAN data bytes
 * @param signal Signal mapping
 * @retval Extracted and scaled value
 */
static float CAN_ExtractSignal(uint8_t* data, PMU_CAN_SignalMap_t* signal)
{
    uint64_t raw_value = 0;
    uint8_t start_byte = signal->start_bit / 8;
    uint8_t start_bit_in_byte = signal->start_bit % 8;

    /* Extract bits based on byte order */
    if (signal->byte_order == 0) {  /* Intel (LSB first) */
        for (uint8_t i = 0; i < ((signal->length_bits + 7) / 8); i++) {
            raw_value |= ((uint64_t)data[start_byte + i] << (i * 8));
        }
        raw_value >>= start_bit_in_byte;
    } else {  /* Motorola (MSB first) */
        /* TODO: Implement Motorola byte order extraction */
        raw_value = 0;
    }

    /* Mask to length */
    uint64_t mask = (1ULL << signal->length_bits) - 1;
    raw_value &= mask;

    /* Convert to signed if needed */
    float value;
    if (signal->value_type == 1) {  /* Signed */
        /* Sign extend if MSB is set */
        if (raw_value & (1ULL << (signal->length_bits - 1))) {
            raw_value |= ~mask;
        }
        value = (float)((int64_t)raw_value);
    } else {  /* Unsigned or float */
        value = (float)raw_value;
    }

    /* Apply scale and offset */
    value = value * signal->scale + signal->offset;

    return value;
}

/**
 * @brief Check for signal timeouts
 * @param bus Bus identifier
 */
static void CAN_CheckTimeouts(PMU_CAN_Bus_t bus)
{
    for (uint16_t i = 0; i < can_buses[bus].signal_count; i++) {
        PMU_CAN_SignalMap_t* signal = &can_buses[bus].signal_maps[i];

        /* Check if timeout enabled and exceeded */
        if (signal->timeout_ms > 0) {
            uint32_t elapsed = system_tick_ms - signal->last_update_ms;
            if (elapsed > signal->timeout_ms) {
                /* TODO: Set virtual channel to fault/default value */
                /* Or trigger fault handler */
            }
        }
    }
}

/**
 * @brief Add signal mapping
 * @param bus Bus identifier
 * @param signal Signal mapping
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_AddSignalMap(PMU_CAN_Bus_t bus, PMU_CAN_SignalMap_t* signal)
{
    if (bus >= PMU_CAN_BUS_COUNT || signal == NULL) {
        return HAL_ERROR;
    }

    if (can_buses[bus].signal_count >= PMU_CAN_MAX_SIGNAL_MAPS) {
        return HAL_ERROR;  /* No space */
    }

    /* Copy signal mapping */
    memcpy(&can_buses[bus].signal_maps[can_buses[bus].signal_count],
           signal, sizeof(PMU_CAN_SignalMap_t));

    /* Set default timeout if not specified */
    if (signal->timeout_ms == 0) {
        can_buses[bus].signal_maps[can_buses[bus].signal_count].timeout_ms =
            PMU_CAN_SIGNAL_TIMEOUT_MS;
    }

    can_buses[bus].signal_count++;
    return HAL_OK;
}

/**
 * @brief Remove signal mapping
 * @param bus Bus identifier
 * @param can_id CAN message ID
 * @param virtual_channel Virtual channel
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_RemoveSignalMap(PMU_CAN_Bus_t bus, uint32_t can_id, uint16_t virtual_channel)
{
    if (bus >= PMU_CAN_BUS_COUNT) {
        return HAL_ERROR;
    }

    /* Find and remove signal */
    for (uint16_t i = 0; i < can_buses[bus].signal_count; i++) {
        if (can_buses[bus].signal_maps[i].can_id == can_id &&
            can_buses[bus].signal_maps[i].virtual_channel == virtual_channel) {

            /* Shift remaining signals down */
            for (uint16_t j = i; j < can_buses[bus].signal_count - 1; j++) {
                memcpy(&can_buses[bus].signal_maps[j],
                       &can_buses[bus].signal_maps[j + 1],
                       sizeof(PMU_CAN_SignalMap_t));
            }

            can_buses[bus].signal_count--;
            return HAL_OK;
        }
    }

    return HAL_ERROR;  /* Not found */
}

/**
 * @brief Clear all signal mappings
 * @param bus Bus identifier
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_ClearSignalMaps(PMU_CAN_Bus_t bus)
{
    if (bus >= PMU_CAN_BUS_COUNT) {
        return HAL_ERROR;
    }

    can_buses[bus].signal_count = 0;
    return HAL_OK;
}

/**
 * @brief Get bus statistics
 * @param bus Bus identifier
 * @retval Pointer to statistics
 */
PMU_CAN_Statistics_t* PMU_CAN_GetStatistics(PMU_CAN_Bus_t bus)
{
    if (bus >= PMU_CAN_BUS_COUNT) {
        return NULL;
    }

    return &can_buses[bus].stats;
}

/**
 * @brief Reset bus statistics
 * @param bus Bus identifier
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_ResetStatistics(PMU_CAN_Bus_t bus)
{
    if (bus >= PMU_CAN_BUS_COUNT) {
        return HAL_ERROR;
    }

    memset(&can_buses[bus].stats, 0, sizeof(PMU_CAN_Statistics_t));
    return HAL_OK;
}

/**
 * @brief Check if bus is online
 * @param bus Bus identifier
 * @retval 1 if online, 0 if offline
 */
uint8_t PMU_CAN_IsBusOnline(PMU_CAN_Bus_t bus)
{
    if (bus >= PMU_CAN_BUS_COUNT || !can_buses[bus].is_initialized) {
        return 0;
    }

    /* Check bus status */
    return (can_buses[bus].stats.bus_status < 3) ? 1 : 0;
}

/**
 * @brief Set acceptance filter
 * @param bus Bus identifier
 * @param filter_id Filter ID
 * @param filter_mask Filter mask
 * @param id_type Standard or Extended
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_SetFilter(PMU_CAN_Bus_t bus, uint32_t filter_id,
                                     uint32_t filter_mask, PMU_CAN_IDType_t id_type)
{
    if (bus >= PMU_CAN_BUS_COUNT || !can_buses[bus].is_initialized) {
        return HAL_ERROR;
    }

    /* TODO: Configure FDCAN filter */
    /* This is a placeholder */

    return HAL_OK;
}

/**
 * @brief Convert bytes to DLC value
 * @param bytes Number of bytes
 * @retval DLC value
 */
static uint8_t CAN_BytesToDLC(uint8_t bytes)
{
    if (bytes <= 8) return bytes;
    if (bytes <= 12) return 9;
    if (bytes <= 16) return 10;
    if (bytes <= 20) return 11;
    if (bytes <= 24) return 12;
    if (bytes <= 32) return 13;
    if (bytes <= 48) return 14;
    return 15;  /* 64 bytes */
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
