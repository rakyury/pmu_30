/**
 ******************************************************************************
 * @file           : pmu_can.h
 * @brief          : CAN Bus Driver Header (2x CAN FD + 2x CAN 2.0)
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 ******************************************************************************
 */

#ifndef __PMU_CAN_H
#define __PMU_CAN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Exported types ------------------------------------------------------------*/

/**
 * @brief CAN bus identifier
 */
typedef enum {
    PMU_CAN_BUS_1 = 0,      /* CAN FD 1 */
    PMU_CAN_BUS_2,          /* CAN FD 2 */
    PMU_CAN_BUS_3,          /* CAN 2.0 A/B */
    PMU_CAN_BUS_4,          /* CAN 2.0 A/B */
    PMU_CAN_BUS_COUNT
} PMU_CAN_Bus_t;

/**
 * @brief CAN frame type
 */
typedef enum {
    PMU_CAN_FRAME_CLASSIC = 0,  /* CAN 2.0 frame */
    PMU_CAN_FRAME_FD            /* CAN FD frame */
} PMU_CAN_FrameType_t;

/**
 * @brief CAN ID type
 */
typedef enum {
    PMU_CAN_ID_STANDARD = 0,    /* 11-bit ID */
    PMU_CAN_ID_EXTENDED         /* 29-bit ID */
} PMU_CAN_IDType_t;

/**
 * @brief CAN message structure
 */
typedef struct {
    uint32_t id;                /* CAN ID (11 or 29 bit) */
    uint8_t data[64];           /* Data bytes (8 for CAN 2.0, up to 64 for CAN FD) */
    uint8_t dlc;                /* Data Length Code (0-8 for CAN 2.0, 0-15 for CAN FD) */
    PMU_CAN_FrameType_t frame_type;  /* Classic or FD */
    PMU_CAN_IDType_t id_type;   /* Standard or Extended */
    uint8_t rtr;                /* Remote Transmission Request */
} PMU_CAN_Message_t;

/**
 * @brief CAN bus configuration
 */
typedef struct {
    uint32_t bitrate;           /* Nominal bitrate (e.g., 500000, 1000000) */
    uint32_t fd_bitrate;        /* FD data phase bitrate (e.g., 5000000) */
    uint8_t enable_fd;          /* Enable CAN FD mode */
    uint8_t enable_termination; /* Enable built-in 120Ω termination */
} PMU_CAN_BusConfig_t;

/**
 * @brief CAN signal mapping (for DBC support)
 */
typedef struct {
    uint32_t can_id;            /* CAN message ID */
    uint8_t start_bit;          /* Start bit in message */
    uint8_t length_bits;        /* Length in bits */
    uint8_t byte_order;         /* 0=Intel (LSB), 1=Motorola (MSB) */
    uint8_t value_type;         /* 0=unsigned, 1=signed, 2=float */
    float scale;                /* Scale factor */
    float offset;               /* Offset value */
    uint16_t virtual_channel;   /* Target virtual channel */
    uint32_t timeout_ms;        /* Signal timeout in ms */
    uint32_t last_update_ms;    /* Last update timestamp */
} PMU_CAN_SignalMap_t;

/**
 * @brief CAN bus statistics
 */
typedef struct {
    uint32_t rx_count;          /* Received messages */
    uint32_t tx_count;          /* Transmitted messages */
    uint32_t rx_errors;         /* Receive errors */
    uint32_t tx_errors;         /* Transmit errors */
    uint32_t bus_off_count;     /* Bus-off events */
    uint32_t overflow_count;    /* RX FIFO overflow */
    uint8_t  bus_status;        /* 0=OK, 1=Warning, 2=Passive, 3=Bus-off */
} PMU_CAN_Statistics_t;

/* Exported constants --------------------------------------------------------*/

/* CAN bitrates */
#define PMU_CAN_BITRATE_125K        125000
#define PMU_CAN_BITRATE_250K        250000
#define PMU_CAN_BITRATE_500K        500000
#define PMU_CAN_BITRATE_1M          1000000

/* CAN FD data phase bitrates */
#define PMU_CAN_FD_BITRATE_2M       2000000
#define PMU_CAN_FD_BITRATE_4M       4000000
#define PMU_CAN_FD_BITRATE_5M       5000000

/* CAN DLC to byte count mapping for CAN FD */
#define PMU_CAN_FD_DLC_12           9
#define PMU_CAN_FD_DLC_16           10
#define PMU_CAN_FD_DLC_20           11
#define PMU_CAN_FD_DLC_24           12
#define PMU_CAN_FD_DLC_32           13
#define PMU_CAN_FD_DLC_48           14
#define PMU_CAN_FD_DLC_64           15

/* Maximum signal mappings per bus */
#define PMU_CAN_MAX_SIGNAL_MAPS     256

/* Signal timeout default */
#define PMU_CAN_SIGNAL_TIMEOUT_MS   500

/* Exported macro ------------------------------------------------------------*/

/* Convert DLC to bytes */
#define PMU_CAN_DLC_TO_BYTES(dlc) \
    ((dlc) <= 8 ? (dlc) : \
     (dlc) == 9 ? 12 : \
     (dlc) == 10 ? 16 : \
     (dlc) == 11 ? 20 : \
     (dlc) == 12 ? 24 : \
     (dlc) == 13 ? 32 : \
     (dlc) == 14 ? 48 : 64)

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize CAN bus driver
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_Init(void);

/**
 * @brief Update CAN communication (call periodically)
 * @retval None
 */
void PMU_CAN_Update(void);

/**
 * @brief Configure CAN bus
 * @param bus Bus identifier
 * @param config Bus configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_ConfigureBus(PMU_CAN_Bus_t bus, PMU_CAN_BusConfig_t* config);

/**
 * @brief Send CAN message
 * @param bus Bus identifier
 * @param msg Message to send
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_SendMessage(PMU_CAN_Bus_t bus, PMU_CAN_Message_t* msg);

/**
 * @brief Send simple CAN message
 * @param bus Bus identifier
 * @param id CAN ID
 * @param data Data bytes
 * @param len Data length
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_Send(uint8_t bus, uint32_t id, uint8_t* data, uint8_t len);

/**
 * @brief Add signal mapping for DBC support
 * @param bus Bus identifier
 * @param signal Signal mapping configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_AddSignalMap(PMU_CAN_Bus_t bus, PMU_CAN_SignalMap_t* signal);

/**
 * @brief Remove signal mapping
 * @param bus Bus identifier
 * @param can_id CAN message ID
 * @param virtual_channel Target virtual channel
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_RemoveSignalMap(PMU_CAN_Bus_t bus, uint32_t can_id, uint16_t virtual_channel);

/**
 * @brief Clear all signal mappings on a bus
 * @param bus Bus identifier
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_ClearSignalMaps(PMU_CAN_Bus_t bus);

/**
 * @brief Get bus statistics
 * @param bus Bus identifier
 * @retval Pointer to statistics
 */
PMU_CAN_Statistics_t* PMU_CAN_GetStatistics(PMU_CAN_Bus_t bus);

/**
 * @brief Reset bus statistics
 * @param bus Bus identifier
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_ResetStatistics(PMU_CAN_Bus_t bus);

/**
 * @brief Check if bus is online
 * @param bus Bus identifier
 * @retval 1 if online, 0 if offline
 */
uint8_t PMU_CAN_IsBusOnline(PMU_CAN_Bus_t bus);

/**
 * @brief Set acceptance filter
 * @param bus Bus identifier
 * @param filter_id Filter ID
 * @param filter_mask Filter mask
 * @param id_type Standard or Extended
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_SetFilter(PMU_CAN_Bus_t bus, uint32_t filter_id,
                                     uint32_t filter_mask, PMU_CAN_IDType_t id_type);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_CAN_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
