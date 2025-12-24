/**
 ******************************************************************************
 * @file           : pmu_lin.h
 * @brief          : LIN Bus Protocol Handler - Two-Level Architecture v3.0
 * @author         : R2 m-sport
 * @date           : 2025-12-24
 ******************************************************************************
 * LIN (Local Interconnect Network) protocol implementation for PMU-30.
 * Follows the same two-level architecture as CAN:
 *   Level 1: LIN Frame Objects (message definitions)
 *   Level 2: LIN Inputs/Outputs (signal extraction/packing)
 *
 * Features:
 *   - LIN 2.x protocol support
 *   - Master and Slave node operation
 *   - Schedule table support
 *   - Signal extraction with scaling
 *   - Diagnostic frames support
 *   - Sleep/Wakeup handling
 ******************************************************************************
 */

#ifndef PMU_LIN_H
#define PMU_LIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include <stdint.h>
#include <stdbool.h>
#include "pmu_types.h"

/* Exported defines ----------------------------------------------------------*/

#define PMU_LIN_MAX_FRAME_OBJECTS   32      /**< Maximum LIN frame objects */
#define PMU_LIN_MAX_INPUTS          128     /**< Maximum LIN input signals */
#define PMU_LIN_MAX_OUTPUTS         64      /**< Maximum LIN output signals */
#define PMU_LIN_MAX_SCHEDULE_SLOTS  32      /**< Maximum schedule table slots */
#define PMU_LIN_FRAME_DATA_LEN      8       /**< LIN frame data length */
#define PMU_LIN_ID_LEN              32      /**< ID string length */

/* LIN Protocol Constants */
#define PMU_LIN_SYNC_BYTE           0x55    /**< LIN sync field */
#define PMU_LIN_DIAG_MASTER_REQ     0x3C    /**< Diagnostic master request ID */
#define PMU_LIN_DIAG_SLAVE_RESP     0x3D    /**< Diagnostic slave response ID */
#define PMU_LIN_MAX_FRAME_ID        0x3F    /**< Maximum frame ID (6 bits) */

/* Exported types ------------------------------------------------------------*/

/**
 * @brief LIN bus identifier
 */
typedef enum {
    PMU_LIN_BUS_1 = 0,              /**< LIN Bus 1 */
    PMU_LIN_BUS_2,                  /**< LIN Bus 2 */
    PMU_LIN_BUS_COUNT
} PMU_LIN_Bus_t;

/**
 * @brief LIN node mode
 */
typedef enum {
    PMU_LIN_MODE_SLAVE = 0,         /**< Slave node (responds to master) */
    PMU_LIN_MODE_MASTER             /**< Master node (controls schedule) */
} PMU_LIN_Mode_t;

/**
 * @brief LIN frame type
 */
typedef enum {
    PMU_LIN_FRAME_TYPE_UNCONDITIONAL = 0,  /**< Unconditional frame */
    PMU_LIN_FRAME_TYPE_EVENT_TRIGGERED,    /**< Event-triggered frame */
    PMU_LIN_FRAME_TYPE_SPORADIC,           /**< Sporadic frame */
    PMU_LIN_FRAME_TYPE_DIAGNOSTIC          /**< Diagnostic frame */
} PMU_LIN_FrameType_t;

/**
 * @brief LIN frame direction
 */
typedef enum {
    PMU_LIN_DIR_SUBSCRIBE = 0,      /**< Subscribe (receive) */
    PMU_LIN_DIR_PUBLISH             /**< Publish (transmit) */
} PMU_LIN_Direction_t;

/**
 * @brief LIN checksum type
 */
typedef enum {
    PMU_LIN_CHECKSUM_CLASSIC = 0,   /**< LIN 1.x classic checksum */
    PMU_LIN_CHECKSUM_ENHANCED       /**< LIN 2.x enhanced checksum */
} PMU_LIN_ChecksumType_t;

/**
 * @brief LIN data type for signal extraction
 */
typedef enum {
    PMU_LIN_DATA_TYPE_UNSIGNED = 0, /**< Unsigned integer */
    PMU_LIN_DATA_TYPE_SIGNED,       /**< Signed integer (two's complement) */
    PMU_LIN_DATA_TYPE_BOOL          /**< Boolean (1-bit) */
} PMU_LIN_DataType_t;

/**
 * @brief LIN timeout behavior
 */
typedef enum {
    PMU_LIN_TIMEOUT_USE_DEFAULT = 0,/**< Use configured default value */
    PMU_LIN_TIMEOUT_HOLD_LAST,      /**< Hold last valid value */
    PMU_LIN_TIMEOUT_SET_ZERO        /**< Set to zero */
} PMU_LIN_TimeoutBehavior_t;

/**
 * @brief LIN bus state
 */
typedef enum {
    PMU_LIN_STATE_UNINIT = 0,       /**< Not initialized */
    PMU_LIN_STATE_IDLE,             /**< Idle, ready for communication */
    PMU_LIN_STATE_ACTIVE,           /**< Active communication */
    PMU_LIN_STATE_SLEEP,            /**< Sleep mode */
    PMU_LIN_STATE_ERROR             /**< Bus error state */
} PMU_LIN_State_t;

/**
 * @brief LIN error flags
 */
typedef enum {
    PMU_LIN_ERROR_NONE = 0,
    PMU_LIN_ERROR_SYNC = (1 << 0),          /**< Sync field error */
    PMU_LIN_ERROR_PARITY = (1 << 1),        /**< ID parity error */
    PMU_LIN_ERROR_CHECKSUM = (1 << 2),      /**< Checksum error */
    PMU_LIN_ERROR_TIMEOUT = (1 << 3),       /**< Frame timeout */
    PMU_LIN_ERROR_NO_RESPONSE = (1 << 4),   /**< No slave response */
    PMU_LIN_ERROR_FRAMING = (1 << 5),       /**< Framing error */
    PMU_LIN_ERROR_BIT = (1 << 6)            /**< Bit error */
} PMU_LIN_Error_t;

/* ============================================================================
 * Level 1: LIN Frame Objects
 * ============================================================================ */

/**
 * @brief LIN Frame Object structure (Level 1)
 *
 * Defines a LIN frame with ID, direction, and data buffer.
 * Multiple input signals can reference this frame.
 */
typedef struct {
    /* Configuration (set once) */
    char id[PMU_LIN_ID_LEN];            /**< Unique frame identifier */
    char name[PMU_LIN_ID_LEN];          /**< Human-readable name */
    PMU_LIN_Bus_t bus;                  /**< LIN bus (0 or 1) */
    uint8_t frame_id;                   /**< LIN frame ID (0-63) */
    PMU_LIN_FrameType_t frame_type;     /**< Frame type */
    PMU_LIN_Direction_t direction;      /**< Subscribe or publish */
    PMU_LIN_ChecksumType_t checksum;    /**< Checksum type */
    uint8_t length;                     /**< Data length (1-8 bytes) */
    uint16_t timeout_ms;                /**< Reception timeout (ms) */
    uint8_t enabled;                    /**< Frame enabled flag */

    /* Runtime state */
    uint8_t data[PMU_LIN_FRAME_DATA_LEN];   /**< Frame data buffer */
    uint32_t last_rx_tick;              /**< Last receive timestamp (ms) */
    uint32_t last_tx_tick;              /**< Last transmit timestamp (ms) */
    uint8_t timeout_flag;               /**< Timeout occurred */
    uint8_t error_flags;                /**< Error flags */
    uint32_t rx_count;                  /**< Receive counter */
    uint32_t tx_count;                  /**< Transmit counter */
    uint32_t error_count;               /**< Error counter */
} PMU_LIN_FrameObject_t;

/* ============================================================================
 * Level 2: LIN Input/Output Signals
 * ============================================================================ */

/**
 * @brief LIN Input Signal structure (Level 2)
 *
 * Extracts a signal value from a LIN frame with scaling support.
 */
typedef struct {
    /* Configuration */
    char id[PMU_LIN_ID_LEN];            /**< Unique signal identifier */
    char frame_ref[PMU_LIN_ID_LEN];     /**< Reference to frame object ID */

    /* Signal position and format */
    PMU_LIN_DataType_t data_type;       /**< Data type */
    uint8_t start_bit;                  /**< Start bit position (0-63) */
    uint8_t bit_length;                 /**< Bit length (1-32) */
    uint8_t byte_order;                 /**< 0=Little endian, 1=Big endian */

    /* Scaling: value = (raw * multiplier / divider) + offset */
    float multiplier;                   /**< Scale multiplier */
    float divider;                      /**< Scale divider */
    float offset;                       /**< Offset after scaling */
    uint8_t decimal_places;             /**< Decimal places for display */

    /* Timeout handling */
    float default_value;                /**< Default value on timeout */
    PMU_LIN_TimeoutBehavior_t timeout_behavior;  /**< Timeout behavior */

    /* Runtime state */
    uint16_t virtual_channel;           /**< Target virtual channel index */
    float current_value;                /**< Current scaled value */
    uint8_t timeout_flag;               /**< Signal in timeout state */

    /* Linked frame pointer (resolved at runtime) */
    PMU_LIN_FrameObject_t* frame_ptr;   /**< Pointer to parent frame */
} PMU_LIN_Input_t;

/**
 * @brief LIN Output Signal structure
 *
 * Packs a value into a LIN frame for transmission.
 */
typedef struct {
    /* Configuration */
    char id[PMU_LIN_ID_LEN];            /**< Unique signal identifier */
    char frame_ref[PMU_LIN_ID_LEN];     /**< Reference to frame object ID */
    char source_channel[PMU_LIN_ID_LEN];/**< Source channel for value */

    /* Signal position and format */
    PMU_LIN_DataType_t data_type;       /**< Data type */
    uint8_t start_bit;                  /**< Start bit position (0-63) */
    uint8_t bit_length;                 /**< Bit length (1-32) */
    uint8_t byte_order;                 /**< 0=Little endian, 1=Big endian */

    /* Scaling (reverse): raw = (value - offset) * divider / multiplier */
    float multiplier;                   /**< Scale multiplier */
    float divider;                      /**< Scale divider */
    float offset;                       /**< Offset before inverse scaling */

    /* Runtime state */
    uint16_t source_channel_idx;        /**< Resolved source channel index */
    float current_value;                /**< Current value before packing */

    /* Linked frame pointer (resolved at runtime) */
    PMU_LIN_FrameObject_t* frame_ptr;   /**< Pointer to parent frame */
} PMU_LIN_Output_t;

/* ============================================================================
 * Schedule Table
 * ============================================================================ */

/**
 * @brief Schedule table slot
 */
typedef struct {
    uint8_t frame_id;                   /**< Frame ID to transmit */
    uint16_t delay_ms;                  /**< Delay after this frame (ms) */
    uint8_t enabled;                    /**< Slot enabled */
} PMU_LIN_ScheduleSlot_t;

/**
 * @brief Schedule table
 */
typedef struct {
    char name[PMU_LIN_ID_LEN];          /**< Schedule table name */
    PMU_LIN_ScheduleSlot_t slots[PMU_LIN_MAX_SCHEDULE_SLOTS];
    uint8_t slot_count;                 /**< Number of slots */
    uint8_t current_slot;               /**< Current slot index */
    uint8_t enabled;                    /**< Schedule enabled */
    uint32_t next_slot_tick;            /**< Next slot execution time */
} PMU_LIN_Schedule_t;

/* ============================================================================
 * Bus Statistics
 * ============================================================================ */

/**
 * @brief LIN bus statistics
 */
typedef struct {
    uint32_t frames_rx;                 /**< Total frames received */
    uint32_t frames_tx;                 /**< Total frames transmitted */
    uint32_t errors_sync;               /**< Sync errors */
    uint32_t errors_parity;             /**< Parity errors */
    uint32_t errors_checksum;           /**< Checksum errors */
    uint32_t errors_timeout;            /**< Timeout errors */
    uint32_t errors_no_response;        /**< No response errors */
    uint32_t bus_off_count;             /**< Bus-off occurrences */
    uint32_t wakeup_count;              /**< Wakeup events */
    uint32_t sleep_count;               /**< Sleep events */
} PMU_LIN_Stats_t;

/* ============================================================================
 * Callback Types
 * ============================================================================ */

/**
 * @brief Frame received callback
 * @param bus LIN bus
 * @param frame_id Frame ID
 * @param data Frame data
 * @param length Data length
 */
typedef void (*PMU_LIN_RxCallback_t)(PMU_LIN_Bus_t bus, uint8_t frame_id,
                                     const uint8_t* data, uint8_t length);

/**
 * @brief Error callback
 * @param bus LIN bus
 * @param error Error code
 */
typedef void (*PMU_LIN_ErrorCallback_t)(PMU_LIN_Bus_t bus, PMU_LIN_Error_t error);

/* Exported functions --------------------------------------------------------*/

/* ============================================================================
 * Initialization
 * ============================================================================ */

/**
 * @brief Initialize LIN subsystem
 * @param mode Operating mode (master or slave)
 * @retval 0 on success, -1 on error
 */
int PMU_LIN_Init(PMU_LIN_Mode_t mode);

/**
 * @brief Deinitialize LIN subsystem
 */
void PMU_LIN_DeInit(void);

/**
 * @brief Reset LIN subsystem (clear frames, inputs, outputs)
 */
void PMU_LIN_Reset(void);

/**
 * @brief Configure LIN bus baudrate
 * @param bus LIN bus
 * @param baudrate Baudrate (typically 9600, 19200, or 20000)
 * @retval 0 on success, -1 on error
 */
int PMU_LIN_ConfigureBus(PMU_LIN_Bus_t bus, uint32_t baudrate);

/* ============================================================================
 * Frame Object Management (Level 1)
 * ============================================================================ */

/**
 * @brief Add a LIN frame object
 * @param frame Frame configuration
 * @retval Index of added frame, or -1 on error
 */
int PMU_LIN_AddFrameObject(const PMU_LIN_FrameObject_t* frame);

/**
 * @brief Get frame object by ID
 * @param id Frame ID string
 * @retval Pointer to frame object, or NULL if not found
 */
PMU_LIN_FrameObject_t* PMU_LIN_GetFrameObject(const char* id);

/**
 * @brief Get frame object by frame ID number
 * @param bus LIN bus
 * @param frame_id Frame ID (0-63)
 * @retval Pointer to frame object, or NULL if not found
 */
PMU_LIN_FrameObject_t* PMU_LIN_GetFrameByID(PMU_LIN_Bus_t bus, uint8_t frame_id);

/**
 * @brief Get frame object count
 * @retval Number of registered frame objects
 */
uint16_t PMU_LIN_GetFrameCount(void);

/* ============================================================================
 * Input Signal Management (Level 2)
 * ============================================================================ */

/**
 * @brief Add a LIN input signal
 * @param input Input configuration
 * @retval Index of added input, or -1 on error
 */
int PMU_LIN_AddInput(const PMU_LIN_Input_t* input);

/**
 * @brief Get input signal by ID
 * @param id Input ID string
 * @retval Pointer to input, or NULL if not found
 */
PMU_LIN_Input_t* PMU_LIN_GetInput(const char* id);

/**
 * @brief Link inputs to frame objects (call after adding all)
 * @retval Number of successfully linked inputs
 */
int PMU_LIN_LinkInputsToFrames(void);

/**
 * @brief Get input count
 * @retval Number of registered inputs
 */
uint16_t PMU_LIN_GetInputCount(void);

/* ============================================================================
 * Output Signal Management
 * ============================================================================ */

/**
 * @brief Add a LIN output signal
 * @param output Output configuration
 * @retval Index of added output, or -1 on error
 */
int PMU_LIN_AddOutput(const PMU_LIN_Output_t* output);

/**
 * @brief Get output signal by ID
 * @param id Output ID string
 * @retval Pointer to output, or NULL if not found
 */
PMU_LIN_Output_t* PMU_LIN_GetOutput(const char* id);

/**
 * @brief Link outputs to frame objects (call after adding all)
 * @retval Number of successfully linked outputs
 */
int PMU_LIN_LinkOutputsToFrames(void);

/**
 * @brief Get output count
 * @retval Number of registered outputs
 */
uint16_t PMU_LIN_GetOutputCount(void);

/* ============================================================================
 * Frame Processing
 * ============================================================================ */

/**
 * @brief Handle received LIN frame (called from ISR/driver)
 * @param bus LIN bus
 * @param frame_id Frame ID (0-63)
 * @param data Frame data
 * @param length Data length
 */
void PMU_LIN_HandleRxFrame(PMU_LIN_Bus_t bus, uint8_t frame_id,
                           const uint8_t* data, uint8_t length);

/**
 * @brief Process input signals (extract values from frames)
 * Call periodically from main loop.
 */
void PMU_LIN_ProcessInputs(void);

/**
 * @brief Process output signals (pack values into frames)
 * Call periodically from main loop.
 */
void PMU_LIN_ProcessOutputs(void);

/**
 * @brief Process frame timeouts
 * Call periodically (e.g., every 10ms)
 */
void PMU_LIN_ProcessTimeouts(void);

/**
 * @brief Transmit a LIN frame (master mode)
 * @param bus LIN bus
 * @param frame_id Frame ID
 * @param data Frame data
 * @param length Data length
 * @retval 0 on success, -1 on error
 */
int PMU_LIN_TransmitFrame(PMU_LIN_Bus_t bus, uint8_t frame_id,
                          const uint8_t* data, uint8_t length);

/**
 * @brief Request slave response (master mode)
 * @param bus LIN bus
 * @param frame_id Frame ID to request
 * @retval 0 on success, -1 on error
 */
int PMU_LIN_RequestFrame(PMU_LIN_Bus_t bus, uint8_t frame_id);

/* ============================================================================
 * Schedule Table (Master Mode)
 * ============================================================================ */

/**
 * @brief Add schedule slot
 * @param frame_id Frame ID
 * @param delay_ms Delay after frame (ms)
 * @retval Slot index, or -1 on error
 */
int PMU_LIN_AddScheduleSlot(uint8_t frame_id, uint16_t delay_ms);

/**
 * @brief Start schedule execution
 */
void PMU_LIN_StartSchedule(void);

/**
 * @brief Stop schedule execution
 */
void PMU_LIN_StopSchedule(void);

/**
 * @brief Process schedule table (call from main loop)
 */
void PMU_LIN_ProcessSchedule(void);

/* ============================================================================
 * Sleep/Wakeup
 * ============================================================================ */

/**
 * @brief Send sleep command (master mode)
 * @param bus LIN bus
 */
void PMU_LIN_SendSleep(PMU_LIN_Bus_t bus);

/**
 * @brief Send wakeup signal
 * @param bus LIN bus
 */
void PMU_LIN_SendWakeup(PMU_LIN_Bus_t bus);

/**
 * @brief Check if bus is in sleep mode
 * @param bus LIN bus
 * @retval true if sleeping
 */
bool PMU_LIN_IsSleeping(PMU_LIN_Bus_t bus);

/* ============================================================================
 * Diagnostics
 * ============================================================================ */

/**
 * @brief Send diagnostic request (master mode)
 * @param bus LIN bus
 * @param nad Node address
 * @param data Request data (6 bytes)
 * @retval 0 on success, -1 on error
 */
int PMU_LIN_SendDiagRequest(PMU_LIN_Bus_t bus, uint8_t nad, const uint8_t* data);

/**
 * @brief Read diagnostic response
 * @param bus LIN bus
 * @param nad Expected NAD
 * @param data Response data buffer (6 bytes)
 * @param timeout_ms Timeout in milliseconds
 * @retval 0 on success, -1 on error/timeout
 */
int PMU_LIN_ReadDiagResponse(PMU_LIN_Bus_t bus, uint8_t nad,
                             uint8_t* data, uint32_t timeout_ms);

/* ============================================================================
 * Callbacks
 * ============================================================================ */

/**
 * @brief Set frame received callback
 * @param callback Callback function
 */
void PMU_LIN_SetRxCallback(PMU_LIN_RxCallback_t callback);

/**
 * @brief Set error callback
 * @param callback Callback function
 */
void PMU_LIN_SetErrorCallback(PMU_LIN_ErrorCallback_t callback);

/* ============================================================================
 * Statistics
 * ============================================================================ */

/**
 * @brief Get bus statistics
 * @param bus LIN bus
 * @retval Pointer to statistics structure
 */
const PMU_LIN_Stats_t* PMU_LIN_GetStats(PMU_LIN_Bus_t bus);

/**
 * @brief Reset bus statistics
 * @param bus LIN bus
 */
void PMU_LIN_ResetStats(PMU_LIN_Bus_t bus);

/**
 * @brief Get bus state
 * @param bus LIN bus
 * @retval Current bus state
 */
PMU_LIN_State_t PMU_LIN_GetState(PMU_LIN_Bus_t bus);

/* ============================================================================
 * Utility Functions
 * ============================================================================ */

/**
 * @brief Calculate LIN checksum
 * @param type Checksum type (classic or enhanced)
 * @param pid Protected ID (for enhanced checksum)
 * @param data Frame data
 * @param length Data length
 * @retval Calculated checksum
 */
uint8_t PMU_LIN_CalculateChecksum(PMU_LIN_ChecksumType_t type, uint8_t pid,
                                  const uint8_t* data, uint8_t length);

/**
 * @brief Calculate protected ID (add parity bits)
 * @param id Raw frame ID (0-63)
 * @retval Protected ID with parity bits
 */
uint8_t PMU_LIN_CalculatePID(uint8_t id);

/**
 * @brief Extract signal from frame data
 * @param data Frame data buffer
 * @param start_bit Start bit position
 * @param bit_length Bit length
 * @param byte_order 0=little endian, 1=big endian
 * @param is_signed true for signed value
 * @retval Extracted raw value
 */
int32_t PMU_LIN_ExtractSignal(const uint8_t* data, uint8_t start_bit,
                              uint8_t bit_length, uint8_t byte_order,
                              bool is_signed);

/**
 * @brief Pack signal into frame data
 * @param data Frame data buffer
 * @param start_bit Start bit position
 * @param bit_length Bit length
 * @param byte_order 0=little endian, 1=big endian
 * @param value Value to pack
 */
void PMU_LIN_PackSignal(uint8_t* data, uint8_t start_bit,
                        uint8_t bit_length, uint8_t byte_order,
                        int32_t value);

#ifdef __cplusplus
}
#endif

#endif /* PMU_LIN_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
