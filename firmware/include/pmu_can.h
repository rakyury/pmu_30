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
#include "pmu_types.h"

/* Exported types ------------------------------------------------------------*/

/* CAN types are defined in pmu_types.h:
 * - PMU_CAN_Bus_t
 * - PMU_CAN_MessageType_t
 * - PMU_CAN_TimeoutBehavior_t
 * - PMU_CAN_DataType_t
 * - PMU_CAN_DataFormat_t
 * - PMU_CAN_FrameType_t
 * - PMU_CAN_IdType_t
 */

/* Alias for ID type compatibility */
typedef PMU_CAN_IdType_t PMU_CAN_IDType_t;

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

/**
 * @brief CAN Message Object (Level 1) - Container for CAN frame
 *
 * Defines the CAN frame structure: ID, bus, type, timeout.
 * CAN Inputs (Level 2) reference this object to extract signals.
 */
typedef struct {
    char id[32];                        /* Unique message identifier */
    char name[32];                      /* Human-readable name */
    PMU_CAN_Bus_t can_bus;              /* CAN bus (1-4) */
    uint32_t base_id;                   /* CAN message ID (11 or 29 bit) */
    uint8_t is_extended;                /* 1=Extended (29-bit), 0=Standard (11-bit) */
    PMU_CAN_MessageType_t message_type; /* Message type (normal, compound, etc.) */
    uint8_t frame_count;                /* Number of frames for compound (1-8) */
    uint8_t dlc;                        /* Data Length Code */
    uint16_t timeout_ms;                /* Reception timeout in ms */
    uint8_t enabled;                    /* Message enabled flag */
    /* Runtime state */
    uint32_t last_rx_tick;              /* Last receive timestamp (ms) */
    uint8_t timeout_flag;               /* Timeout occurred flag */
    uint8_t rx_data[64];                /* Received data buffer */
    uint8_t compound_frame_idx;         /* Current compound frame index */
} PMU_CAN_MessageObject_t;

/**
 * @brief CAN Input (Level 2) - Signal extraction from CAN Message
 *
 * References a CAN Message Object and defines how to extract
 * a signal value with scaling and timeout behavior.
 */
typedef struct {
    char id[32];                        /* Unique channel identifier */
    char message_ref[32];               /* Reference to CAN Message Object ID */
    uint8_t frame_offset;               /* Frame offset for compound messages (0-7) */
    /* Data extraction */
    PMU_CAN_DataType_t data_type;       /* Value type (unsigned, signed, float) */
    PMU_CAN_DataFormat_t data_format;   /* Format (8bit, 16bit, 32bit, custom) */
    uint8_t byte_order;                 /* 0=Little endian, 1=Big endian */
    uint8_t byte_offset;                /* Starting byte position (0-7) */
    uint8_t start_bit;                  /* Start bit for custom format (0-63) */
    uint8_t bit_length;                 /* Bit length for custom format (1-64) */
    /* Scaling: value = raw * multiplier / divider + offset */
    float multiplier;                   /* Scale multiplier */
    float divider;                      /* Scale divider */
    float offset;                       /* Offset added after scaling */
    uint8_t decimal_places;             /* Decimal places for display */
    /* Timeout behavior */
    float default_value;                /* Value on timeout */
    PMU_CAN_TimeoutBehavior_t timeout_behavior;  /* What to do on timeout */
    /* Runtime state */
    uint16_t virtual_channel;           /* Target virtual channel index */
    float current_value;                /* Current scaled value */
    uint8_t timeout_flag;               /* Signal timeout flag */
    /* Linked message pointer (resolved at runtime) */
    PMU_CAN_MessageObject_t* message_ptr;  /* Pointer to parent message */
} PMU_CAN_Input_t;

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

/* Maximum signal mappings per bus (legacy) */
#define PMU_CAN_MAX_SIGNAL_MAPS     256

/* Signal timeout default */
#define PMU_CAN_SIGNAL_TIMEOUT_MS   500

/* Maximum CAN Message Objects (Level 1) */
#define PMU_CAN_MAX_MESSAGE_OBJECTS 64

/* Maximum CAN Inputs (Level 2) */
#define PMU_CAN_MAX_INPUTS          256

/* Maximum message ID length */
#define PMU_CAN_MSG_ID_LEN          32

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
 * @brief Send extended CAN message (29-bit ID)
 * @param bus Bus identifier
 * @param id 29-bit extended CAN ID
 * @param data Data bytes
 * @param len Data length
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_SendExtended(uint8_t bus, uint32_t id, uint8_t* data, uint8_t len);

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

/* ============================================================================
 * Two-Level Architecture Functions (v3.0)
 * Level 1: CAN Message Objects
 * Level 2: CAN Inputs (signals)
 * ============================================================================ */

/**
 * @brief Add a CAN Message Object (Level 1)
 * @param msg_obj Message object configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_AddMessageObject(PMU_CAN_MessageObject_t* msg_obj);

/**
 * @brief Remove a CAN Message Object by ID
 * @param msg_id Message object ID
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_RemoveMessageObject(const char* msg_id);

/**
 * @brief Get CAN Message Object by ID
 * @param msg_id Message object ID
 * @retval Pointer to message object or NULL
 */
PMU_CAN_MessageObject_t* PMU_CAN_GetMessageObject(const char* msg_id);

/**
 * @brief Clear all CAN Message Objects
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_ClearMessageObjects(void);

/**
 * @brief Get number of active CAN Message Objects
 * @retval Number of message objects
 */
uint16_t PMU_CAN_GetMessageObjectCount(void);

/**
 * @brief Add a CAN Input (Level 2)
 * @param input Input configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_AddInput(PMU_CAN_Input_t* input);

/**
 * @brief Remove a CAN Input by ID
 * @param input_id Input ID
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_RemoveInput(const char* input_id);

/**
 * @brief Get CAN Input by ID
 * @param input_id Input ID
 * @retval Pointer to input or NULL
 */
PMU_CAN_Input_t* PMU_CAN_GetInput(const char* input_id);

/**
 * @brief Clear all CAN Inputs
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_CAN_ClearInputs(void);

/**
 * @brief Get number of active CAN Inputs
 * @retval Number of inputs
 */
uint16_t PMU_CAN_GetInputCount(void);

/**
 * @brief Link CAN Inputs to their parent Message Objects
 *
 * Call after loading configuration to resolve message_ref strings
 * to actual message object pointers.
 *
 * @retval Number of successfully linked inputs
 */
uint16_t PMU_CAN_LinkInputsToMessages(void);

/**
 * @brief Process CAN Message timeouts
 *
 * Check all message objects for reception timeout.
 * Should be called periodically (e.g., every 10ms).
 */
void PMU_CAN_ProcessMessageTimeouts(void);

/**
 * @brief Process CAN Inputs
 *
 * Extract signal values from received messages and apply scaling.
 * Updates virtual channels with the resulting values.
 * Should be called after message reception.
 */
void PMU_CAN_ProcessInputs(void);

/**
 * @brief Handle received CAN message (two-level architecture)
 * @param bus Bus identifier
 * @param can_id CAN message ID
 * @param data Message data bytes
 * @param dlc Data length
 * @param is_extended True if 29-bit extended CAN ID
 */
void PMU_CAN_HandleRxMessage(PMU_CAN_Bus_t bus, uint32_t can_id, uint8_t* data, uint8_t dlc, uint8_t is_extended);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_CAN_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
