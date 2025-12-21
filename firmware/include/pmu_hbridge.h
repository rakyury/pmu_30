/**
 ******************************************************************************
 * @file           : pmu_hbridge.h
 * @brief          : Dual H-Bridge Motor Driver Header
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * 4x Dual H-Bridge outputs for motor control:
 * - Forward/Reverse/Brake/Coast modes
 * - 30A continuous per bridge
 * - PWM speed control (1kHz)
 * - Current sensing and overcurrent protection
 * - Wiper park/brake support
 * - PID position control
 *
 ******************************************************************************
 */

#ifndef __PMU_HBRIDGE_H
#define __PMU_HBRIDGE_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "pmu_config.h"

/* Exported types ------------------------------------------------------------*/

/**
 * @brief H-Bridge operating mode
 */
typedef enum {
    PMU_HBRIDGE_MODE_COAST = 0,     /* Both outputs OFF (coast) */
    PMU_HBRIDGE_MODE_FORWARD,       /* Forward direction */
    PMU_HBRIDGE_MODE_REVERSE,       /* Reverse direction */
    PMU_HBRIDGE_MODE_BRAKE,         /* Active brake (both outputs ON) */
    PMU_HBRIDGE_MODE_WIPER_PARK,    /* Wiper park mode with position control */
    PMU_HBRIDGE_MODE_PID            /* PID position control */
} PMU_HBridge_Mode_t;

/**
 * @brief H-Bridge fault flags
 */
typedef enum {
    PMU_HBRIDGE_FAULT_NONE = 0x00,
    PMU_HBRIDGE_FAULT_OVERCURRENT_FWD = 0x01,
    PMU_HBRIDGE_FAULT_OVERCURRENT_REV = 0x02,
    PMU_HBRIDGE_FAULT_OVERTEMP = 0x04,
    PMU_HBRIDGE_FAULT_STALL = 0x08,
    PMU_HBRIDGE_FAULT_POSITION_LOST = 0x10
} PMU_HBridge_Fault_t;

/**
 * @brief H-Bridge state
 */
typedef enum {
    PMU_HBRIDGE_STATE_IDLE = 0,
    PMU_HBRIDGE_STATE_RUNNING,
    PMU_HBRIDGE_STATE_PARKING,      /* Wiper parking in progress */
    PMU_HBRIDGE_STATE_PARKED,
    PMU_HBRIDGE_STATE_FAULT
} PMU_HBridge_State_t;

/**
 * @brief H-Bridge runtime data
 */
typedef struct {
    PMU_HBridge_State_t state;      /* Current state */
    PMU_HBridge_Mode_t mode;        /* Operating mode */
    uint16_t duty_cycle;            /* PWM duty (0-1000 = 0-100%) */
    uint16_t current_mA;            /* Measured current */
    int16_t temperature_C;          /* Estimated temperature */
    uint16_t position;              /* Position feedback (0-1000) */
    uint16_t target_position;       /* Target position for PID */
    int16_t pid_output;             /* PID controller output */
    uint32_t run_time_ms;           /* Total run time */
    uint8_t fault_flags;            /* Fault status */
    uint8_t fault_count;            /* Fault counter */
} PMU_HBridge_Channel_t;

/**
 * @brief PID Controller structure
 */
typedef struct {
    float kp;                       /* Proportional gain */
    float ki;                       /* Integral gain */
    float kd;                       /* Derivative gain */
    float integral;                 /* Integral accumulator */
    float prev_error;               /* Previous error for derivative */
    float output_min;               /* Minimum output limit */
    float output_max;               /* Maximum output limit */
} PMU_PID_Controller_t;

/* Exported constants --------------------------------------------------------*/

/* Hardware limits */
#define PMU_HBRIDGE_MAX_CURRENT_MA      30000   /* 30A per bridge */
#define PMU_HBRIDGE_MAX_TEMP_C          125     /* 125°C */
#define PMU_HBRIDGE_PWM_RESOLUTION      1000    /* 0.1% resolution */
#define PMU_HBRIDGE_STALL_CURRENT_MA    25000   /* Stall detection threshold */
#define PMU_HBRIDGE_STALL_TIME_MS       500     /* Stall time before fault */

/* Exported macro ------------------------------------------------------------*/

/* Exported functions prototypes ---------------------------------------------*/

/**
 * @brief Initialize H-Bridge driver
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_HBridge_Init(void);

/**
 * @brief Update all H-Bridge channels (call at 1kHz)
 * @retval None
 */
void PMU_HBridge_Update(void);

/**
 * @brief Set H-Bridge mode and duty cycle
 * @param bridge Bridge number (0-3)
 * @param mode Operating mode
 * @param duty Duty cycle (0-1000 = 0-100%)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_HBridge_SetMode(uint8_t bridge, PMU_HBridge_Mode_t mode, uint16_t duty);

/**
 * @brief Set target position for PID control
 * @param bridge Bridge number (0-3)
 * @param position Target position (0-1000)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_HBridge_SetPosition(uint8_t bridge, uint16_t position);

/**
 * @brief Configure PID controller parameters
 * @param bridge Bridge number (0-3)
 * @param kp Proportional gain
 * @param ki Integral gain
 * @param kd Derivative gain
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_HBridge_SetPID(uint8_t bridge, float kp, float ki, float kd);

/**
 * @brief Trigger wiper park sequence
 * @param bridge Bridge number (0-3)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_HBridge_WiperPark(uint8_t bridge);

/**
 * @brief Get bridge current
 * @param bridge Bridge number (0-3)
 * @retval Current in mA
 */
uint16_t PMU_HBridge_GetCurrent(uint8_t bridge);

/**
 * @brief Get bridge position feedback
 * @param bridge Bridge number (0-3)
 * @retval Position (0-1000)
 */
uint16_t PMU_HBridge_GetPosition(uint8_t bridge);

/**
 * @brief Get bridge fault status
 * @param bridge Bridge number (0-3)
 * @retval Fault flags
 */
uint8_t PMU_HBridge_GetFaults(uint8_t bridge);

/**
 * @brief Clear bridge faults
 * @param bridge Bridge number (0-3)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_HBridge_ClearFaults(uint8_t bridge);

/**
 * @brief Get bridge runtime data
 * @param bridge Bridge number (0-3)
 * @retval Pointer to channel data
 */
PMU_HBridge_Channel_t* PMU_HBridge_GetChannelData(uint8_t bridge);

#ifdef __cplusplus
}
#endif

#endif /* __PMU_HBRIDGE_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
