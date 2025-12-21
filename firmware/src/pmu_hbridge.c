/**
 ******************************************************************************
 * @file           : pmu_hbridge.c
 * @brief          : Dual H-Bridge Motor Driver Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * 4x Dual H-Bridge Motor Control Implementation:
 * - Forward/Reverse/Brake/Coast control
 * - PWM speed control at 1kHz
 * - Current sensing and overcurrent protection
 * - Stall detection
 * - Wiper park mode with position sensing
 * - PID position control for precise actuation
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_hbridge.h"
#include "stm32h7xx_hal.h"
#include <string.h>
#include <math.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/
#define HBRIDGE_FAULT_THRESHOLD     3       /* Faults before lockout */
#define HBRIDGE_RETRY_DELAY_MS      200     /* Retry delay after fault */
#define HBRIDGE_WIPER_PARK_POS      50      /* Park position (0-1000) */
#define HBRIDGE_WIPER_TIMEOUT_MS    5000    /* Max parking time */
#define HBRIDGE_PID_UPDATE_MS       10      /* PID update rate (100Hz) */

/* Private macro -------------------------------------------------------------*/
#define IS_VALID_BRIDGE(b)      ((b) < PMU_NUM_HBRIDGES)
#define CLAMP(x, min, max)      (((x) < (min)) ? (min) : (((x) > (max)) ? (max) : (x)))

/* Private variables ---------------------------------------------------------*/
static PMU_HBridge_Channel_t bridges[PMU_NUM_HBRIDGES];
static PMU_HBridgeConfig_t* bridge_configs[PMU_NUM_HBRIDGES];
static PMU_PID_Controller_t pid_controllers[PMU_NUM_HBRIDGES];
static TIM_HandleTypeDef* htim_pwm_hbridge;
static ADC_HandleTypeDef* hadc_hbridge;

/* GPIO and timer mapping for H-Bridge control */
typedef struct {
    GPIO_TypeDef* in1_port;
    uint16_t in1_pin;
    GPIO_TypeDef* in2_port;
    uint16_t in2_pin;
    uint32_t tim_channel_1;
    uint32_t tim_channel_2;
} HBridge_GPIO_Map_t;

static const HBridge_GPIO_Map_t hbridge_gpio[PMU_NUM_HBRIDGES] = {
    /* Bridge 0 */
    {GPIOG, GPIO_PIN_0, GPIOG, GPIO_PIN_1, TIM_CHANNEL_1, TIM_CHANNEL_2},
    /* Bridge 1 */
    {GPIOG, GPIO_PIN_2, GPIOG, GPIO_PIN_3, TIM_CHANNEL_3, TIM_CHANNEL_4},
    /* Bridge 2 */
    {GPIOG, GPIO_PIN_4, GPIOG, GPIO_PIN_5, TIM_CHANNEL_1, TIM_CHANNEL_2},
    /* Bridge 3 */
    {GPIOG, GPIO_PIN_6, GPIOG, GPIO_PIN_7, TIM_CHANNEL_3, TIM_CHANNEL_4},
};

/* Private function prototypes -----------------------------------------------*/
static void HBridge_UpdateCurrentSensing(uint8_t bridge);
static void HBridge_UpdatePID(uint8_t bridge);
static void HBridge_UpdateWiperPark(uint8_t bridge);
static void HBridge_HandleFault(uint8_t bridge, PMU_HBridge_Fault_t fault);
static void HBridge_SetOutputs(uint8_t bridge, uint8_t in1, uint8_t in2, uint16_t pwm1, uint16_t pwm2);
static float PID_Compute(PMU_PID_Controller_t* pid, float setpoint, float measured, float dt);
static uint16_t HBridge_ReadCurrentADC(uint8_t bridge);
static uint16_t HBridge_ReadPositionADC(uint8_t bridge);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize H-Bridge driver
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_HBridge_Init(void)
{
    HAL_StatusTypeDef status = HAL_OK;

    /* Clear all data */
    memset(bridges, 0, sizeof(bridges));
    memset(bridge_configs, 0, sizeof(bridge_configs));
    memset(pid_controllers, 0, sizeof(pid_controllers));

    /* Initialize all bridges to COAST */
    for (uint8_t i = 0; i < PMU_NUM_HBRIDGES; i++) {
        bridges[i].state = PMU_HBRIDGE_STATE_IDLE;
        bridges[i].mode = PMU_HBRIDGE_MODE_COAST;
        bridges[i].fault_flags = PMU_HBRIDGE_FAULT_NONE;

        /* Set outputs to coast (both LOW) */
        HAL_GPIO_WritePin(hbridge_gpio[i].in1_port, hbridge_gpio[i].in1_pin, GPIO_PIN_RESET);
        HAL_GPIO_WritePin(hbridge_gpio[i].in2_port, hbridge_gpio[i].in2_pin, GPIO_PIN_RESET);

        /* Initialize PID with default values */
        pid_controllers[i].kp = 1.0f;
        pid_controllers[i].ki = 0.1f;
        pid_controllers[i].kd = 0.05f;
        pid_controllers[i].output_min = -1000.0f;
        pid_controllers[i].output_max = 1000.0f;
    }

    /* TODO: Initialize timers for PWM (TIM5-6 @ 1kHz) */
    /* TODO: Initialize ADC for current sensing */

    return status;
}

/**
 * @brief Update all H-Bridge channels - call at 1kHz
 * @retval None
 */
void PMU_HBridge_Update(void)
{
    static uint32_t tick_1khz = 0;
    tick_1khz++;

    for (uint8_t i = 0; i < PMU_NUM_HBRIDGES; i++) {
        /* Update runtime counter */
        if (bridges[i].state == PMU_HBRIDGE_STATE_RUNNING) {
            bridges[i].run_time_ms++;
        }

        /* Update current sensing every cycle (1kHz) */
        HBridge_UpdateCurrentSensing(i);

        /* Update PID control every 10ms (100Hz) */
        if ((tick_1khz % 10) == 0) {
            if (bridges[i].mode == PMU_HBRIDGE_MODE_PID) {
                HBridge_UpdatePID(i);
            }
        }

        /* Update wiper park state machine */
        if (bridges[i].mode == PMU_HBRIDGE_MODE_WIPER_PARK) {
            HBridge_UpdateWiperPark(i);
        }

        /* Check stall detection */
        if (bridges[i].duty_cycle > 500 &&
            bridges[i].current_mA > HBRIDGE_STALL_CURRENT_MA &&
            bridges[i].run_time_ms > HBRIDGE_STALL_TIME_MS) {
            HBridge_HandleFault(i, PMU_HBRIDGE_FAULT_STALL);
        }

        /* Check overcurrent */
        if (bridges[i].current_mA > PMU_HBRIDGE_MAX_CURRENT_MA) {
            PMU_HBridge_Fault_t fault = (bridges[i].mode == PMU_HBRIDGE_MODE_FORWARD) ?
                PMU_HBRIDGE_FAULT_OVERCURRENT_FWD : PMU_HBRIDGE_FAULT_OVERCURRENT_REV;
            HBridge_HandleFault(i, fault);
        }
    }
}

/**
 * @brief Set H-Bridge mode and duty cycle
 * @param bridge Bridge number (0-3)
 * @param mode Operating mode
 * @param duty Duty cycle (0-1000 = 0-100%)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_HBridge_SetMode(uint8_t bridge, PMU_HBridge_Mode_t mode, uint16_t duty)
{
    if (!IS_VALID_BRIDGE(bridge)) {
        return HAL_ERROR;
    }

    /* Don't allow mode change if in fault */
    if (bridges[bridge].state == PMU_HBRIDGE_STATE_FAULT &&
        bridges[bridge].fault_count >= HBRIDGE_FAULT_THRESHOLD) {
        return HAL_ERROR;
    }

    /* Clamp duty cycle */
    duty = CLAMP(duty, 0, PMU_HBRIDGE_PWM_RESOLUTION);

    bridges[bridge].mode = mode;
    bridges[bridge].duty_cycle = duty;

    switch (mode) {
        case PMU_HBRIDGE_MODE_COAST:
            /* Both outputs LOW (high impedance) */
            HBridge_SetOutputs(bridge, 0, 0, 0, 0);
            bridges[bridge].state = PMU_HBRIDGE_STATE_IDLE;
            bridges[bridge].run_time_ms = 0;
            break;

        case PMU_HBRIDGE_MODE_FORWARD:
            /* IN1=PWM, IN2=LOW */
            HBridge_SetOutputs(bridge, 1, 0, duty, 0);
            bridges[bridge].state = PMU_HBRIDGE_STATE_RUNNING;
            break;

        case PMU_HBRIDGE_MODE_REVERSE:
            /* IN1=LOW, IN2=PWM */
            HBridge_SetOutputs(bridge, 0, 1, 0, duty);
            bridges[bridge].state = PMU_HBRIDGE_STATE_RUNNING;
            break;

        case PMU_HBRIDGE_MODE_BRAKE:
            /* Both outputs HIGH */
            HBridge_SetOutputs(bridge, 1, 1, 1000, 1000);
            bridges[bridge].state = PMU_HBRIDGE_STATE_IDLE;
            bridges[bridge].run_time_ms = 0;
            break;

        case PMU_HBRIDGE_MODE_WIPER_PARK:
            /* Initiate wiper park sequence */
            bridges[bridge].target_position = HBRIDGE_WIPER_PARK_POS;
            bridges[bridge].state = PMU_HBRIDGE_STATE_PARKING;
            break;

        case PMU_HBRIDGE_MODE_PID:
            /* PID mode - set target, PID will control outputs */
            bridges[bridge].state = PMU_HBRIDGE_STATE_RUNNING;
            break;

        default:
            return HAL_ERROR;
    }

    return HAL_OK;
}

/**
 * @brief Set target position for PID control
 * @param bridge Bridge number (0-3)
 * @param position Target position (0-1000)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_HBridge_SetPosition(uint8_t bridge, uint16_t position)
{
    if (!IS_VALID_BRIDGE(bridge)) {
        return HAL_ERROR;
    }

    position = CLAMP(position, 0, 1000);
    bridges[bridge].target_position = position;

    return HAL_OK;
}

/**
 * @brief Configure PID controller parameters
 * @param bridge Bridge number (0-3)
 * @param kp Proportional gain
 * @param ki Integral gain
 * @param kd Derivative gain
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_HBridge_SetPID(uint8_t bridge, float kp, float ki, float kd)
{
    if (!IS_VALID_BRIDGE(bridge)) {
        return HAL_ERROR;
    }

    pid_controllers[bridge].kp = kp;
    pid_controllers[bridge].ki = ki;
    pid_controllers[bridge].kd = kd;

    /* Reset integrator */
    pid_controllers[bridge].integral = 0;
    pid_controllers[bridge].prev_error = 0;

    return HAL_OK;
}

/**
 * @brief Trigger wiper park sequence
 * @param bridge Bridge number (0-3)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_HBridge_WiperPark(uint8_t bridge)
{
    if (!IS_VALID_BRIDGE(bridge)) {
        return HAL_ERROR;
    }

    return PMU_HBridge_SetMode(bridge, PMU_HBRIDGE_MODE_WIPER_PARK, 700);
}

/**
 * @brief Get bridge current
 * @param bridge Bridge number (0-3)
 * @retval Current in mA
 */
uint16_t PMU_HBridge_GetCurrent(uint8_t bridge)
{
    if (!IS_VALID_BRIDGE(bridge)) {
        return 0;
    }
    return bridges[bridge].current_mA;
}

/**
 * @brief Get bridge position feedback
 * @param bridge Bridge number (0-3)
 * @retval Position (0-1000)
 */
uint16_t PMU_HBridge_GetPosition(uint8_t bridge)
{
    if (!IS_VALID_BRIDGE(bridge)) {
        return 0;
    }
    return bridges[bridge].position;
}

/**
 * @brief Get bridge fault status
 * @param bridge Bridge number (0-3)
 * @retval Fault flags
 */
uint8_t PMU_HBridge_GetFaults(uint8_t bridge)
{
    if (!IS_VALID_BRIDGE(bridge)) {
        return 0;
    }
    return bridges[bridge].fault_flags;
}

/**
 * @brief Clear bridge faults
 * @param bridge Bridge number (0-3)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_HBridge_ClearFaults(uint8_t bridge)
{
    if (!IS_VALID_BRIDGE(bridge)) {
        return HAL_ERROR;
    }

    bridges[bridge].fault_flags = PMU_HBRIDGE_FAULT_NONE;
    bridges[bridge].fault_count = 0;

    if (bridges[bridge].state == PMU_HBRIDGE_STATE_FAULT) {
        bridges[bridge].state = PMU_HBRIDGE_STATE_IDLE;
        bridges[bridge].mode = PMU_HBRIDGE_MODE_COAST;
    }

    return HAL_OK;
}

/**
 * @brief Get bridge runtime data
 * @param bridge Bridge number (0-3)
 * @retval Pointer to channel data
 */
PMU_HBridge_Channel_t* PMU_HBridge_GetChannelData(uint8_t bridge)
{
    if (!IS_VALID_BRIDGE(bridge)) {
        return NULL;
    }
    return &bridges[bridge];
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Update current sensing for H-Bridge
 * @param bridge Bridge number
 * @retval None
 */
static void HBridge_UpdateCurrentSensing(uint8_t bridge)
{
    /* Read current sense ADC */
    uint16_t adc_value = HBridge_ReadCurrentADC(bridge);

    /* Convert ADC to current
     * Assuming current sense resistor and amplifier
     * Example: 0.01Ω shunt with 20x gain
     * 30A × 0.01Ω × 20 = 6V at full scale
     */
    uint32_t voltage_mv = (adc_value * 3300UL) / 4095;
    uint32_t current_ma = (voltage_mv * 5000UL) / 6000; /* Scale to 30A max */

    /* Apply moving average filter */
    bridges[bridge].current_mA = (uint16_t)((bridges[bridge].current_mA * 3 + current_ma) / 4);

    /* Read position feedback */
    uint16_t pos_adc = HBridge_ReadPositionADC(bridge);
    bridges[bridge].position = (uint16_t)((pos_adc * 1000UL) / 4095);
}

/**
 * @brief Update PID position control
 * @param bridge Bridge number
 * @retval None
 */
static void HBridge_UpdatePID(uint8_t bridge)
{
    float dt = HBRIDGE_PID_UPDATE_MS / 1000.0f; /* Convert to seconds */

    /* Compute PID output */
    float output = PID_Compute(&pid_controllers[bridge],
                               (float)bridges[bridge].target_position,
                               (float)bridges[bridge].position,
                               dt);

    bridges[bridge].pid_output = (int16_t)output;

    /* Apply output to H-Bridge */
    if (output > 0) {
        /* Forward */
        uint16_t duty = (uint16_t)CLAMP(output, 0, 1000);
        HBridge_SetOutputs(bridge, 1, 0, duty, 0);
    } else if (output < 0) {
        /* Reverse */
        uint16_t duty = (uint16_t)CLAMP(-output, 0, 1000);
        HBridge_SetOutputs(bridge, 0, 1, 0, duty);
    } else {
        /* Brake at position */
        HBridge_SetOutputs(bridge, 1, 1, 1000, 1000);
    }
}

/**
 * @brief Update wiper park state machine
 * @param bridge Bridge number
 * @retval None
 */
static void HBridge_UpdateWiperPark(uint8_t bridge)
{
    uint16_t current_pos = bridges[bridge].position;
    uint16_t target_pos = bridges[bridge].target_position;

    /* Position tolerance */
    const uint16_t tolerance = 20;

    if (bridges[bridge].state == PMU_HBRIDGE_STATE_PARKING) {
        /* Check if reached park position */
        if (abs((int16_t)(current_pos - target_pos)) < tolerance) {
            /* Reached park position - apply brake */
            HBridge_SetOutputs(bridge, 1, 1, 1000, 1000);
            bridges[bridge].state = PMU_HBRIDGE_STATE_PARKED;
            bridges[bridge].mode = PMU_HBRIDGE_MODE_BRAKE;
        }
        /* Timeout check */
        else if (bridges[bridge].run_time_ms > HBRIDGE_WIPER_TIMEOUT_MS) {
            /* Parking timeout - stop and fault */
            HBridge_HandleFault(bridge, PMU_HBRIDGE_FAULT_POSITION_LOST);
        }
        /* Continue moving toward park */
        else {
            if (current_pos > target_pos) {
                HBridge_SetOutputs(bridge, 0, 1, 0, bridges[bridge].duty_cycle);
            } else {
                HBridge_SetOutputs(bridge, 1, 0, bridges[bridge].duty_cycle, 0);
            }
        }
    }
}

/**
 * @brief Handle H-Bridge fault
 * @param bridge Bridge number
 * @param fault Fault type
 * @retval None
 */
static void HBridge_HandleFault(uint8_t bridge, PMU_HBridge_Fault_t fault)
{
    /* Set fault flag */
    bridges[bridge].fault_flags |= fault;
    bridges[bridge].fault_count++;

    /* Immediate coast for critical faults */
    if (fault == PMU_HBRIDGE_FAULT_OVERCURRENT_FWD ||
        fault == PMU_HBRIDGE_FAULT_OVERCURRENT_REV ||
        fault == PMU_HBRIDGE_FAULT_STALL) {

        HBridge_SetOutputs(bridge, 0, 0, 0, 0);
        bridges[bridge].state = PMU_HBRIDGE_STATE_FAULT;
        bridges[bridge].mode = PMU_HBRIDGE_MODE_COAST;
    }

    /* Lockout after too many faults */
    if (bridges[bridge].fault_count >= HBRIDGE_FAULT_THRESHOLD) {
        bridges[bridge].state = PMU_HBRIDGE_STATE_FAULT;
        HBridge_SetOutputs(bridge, 0, 0, 0, 0);
    }
}

/**
 * @brief Set H-Bridge output states
 * @param bridge Bridge number
 * @param in1 IN1 state (0=LOW, 1=HIGH/PWM)
 * @param in2 IN2 state (0=LOW, 1=HIGH/PWM)
 * @param pwm1 PWM duty for IN1 (0-1000)
 * @param pwm2 PWM duty for IN2 (0-1000)
 * @retval None
 */
static void HBridge_SetOutputs(uint8_t bridge, uint8_t in1, uint8_t in2, uint16_t pwm1, uint16_t pwm2)
{
    /* Simple GPIO control for now (not PWM) */
    HAL_GPIO_WritePin(hbridge_gpio[bridge].in1_port,
                      hbridge_gpio[bridge].in1_pin,
                      in1 ? GPIO_PIN_SET : GPIO_PIN_RESET);

    HAL_GPIO_WritePin(hbridge_gpio[bridge].in2_port,
                      hbridge_gpio[bridge].in2_pin,
                      in2 ? GPIO_PIN_SET : GPIO_PIN_RESET);

    /* TODO: Implement PWM using timers */
    /* if (pwm1 > 0 && pwm1 < 1000) {
        TIM_OC_InitTypeDef sConfigOC;
        sConfigOC.Pulse = (pwm1 * TIM_ARR) / 1000;
        HAL_TIM_PWM_ConfigChannel(htim_pwm_hbridge, &sConfigOC, hbridge_gpio[bridge].tim_channel_1);
        HAL_TIM_PWM_Start(htim_pwm_hbridge, hbridge_gpio[bridge].tim_channel_1);
    } */
}

/**
 * @brief Compute PID controller output
 * @param pid PID controller structure
 * @param setpoint Target value
 * @param measured Current value
 * @param dt Time step in seconds
 * @retval PID output
 */
static float PID_Compute(PMU_PID_Controller_t* pid, float setpoint, float measured, float dt)
{
    float error = setpoint - measured;

    /* Proportional term */
    float p_term = pid->kp * error;

    /* Integral term with anti-windup */
    pid->integral += error * dt;
    float i_term = pid->ki * pid->integral;

    /* Derivative term */
    float d_term = pid->kd * (error - pid->prev_error) / dt;
    pid->prev_error = error;

    /* Compute output */
    float output = p_term + i_term + d_term;

    /* Clamp output and implement anti-windup */
    if (output > pid->output_max) {
        output = pid->output_max;
        /* Anti-windup: stop integrating if saturated */
        pid->integral -= error * dt;
    } else if (output < pid->output_min) {
        output = pid->output_min;
        pid->integral -= error * dt;
    }

    return output;
}

/**
 * @brief Read current sense ADC
 * @param bridge Bridge number
 * @retval ADC value (12-bit)
 */
static uint16_t HBridge_ReadCurrentADC(uint8_t bridge)
{
    /* TODO: Implement ADC reading */
    return 0;
}

/**
 * @brief Read position feedback ADC
 * @param bridge Bridge number
 * @retval ADC value (12-bit)
 */
static uint16_t HBridge_ReadPositionADC(uint8_t bridge)
{
    /* TODO: Implement position ADC reading */
    return 2047; /* Return mid-position for now */
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
