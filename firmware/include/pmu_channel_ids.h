/**
 ******************************************************************************
 * @file           : pmu_channel_ids.h
 * @brief          : Fixed Channel ID Constants
 * @author         : R2 m-sport
 * @date           : 2025-12-28
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This file defines FIXED channel IDs that are IDENTICAL in firmware and
 * configurator. IDs are assigned based on channel type and hardware index,
 * ensuring predictable mapping without runtime translation.
 *
 * IMPORTANT: These constants must be mirrored in configurator/src/constants.py
 *
 ******************************************************************************
 */

#ifndef __PMU_CHANNEL_IDS_H
#define __PMU_CHANNEL_IDS_H

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Channel ID Ranges
 * ============================================================================
 * Each channel type has a dedicated range for its IDs.
 * Hardware-based channels use: BASE + hardware_index
 * Software-based channels use: BASE + allocation_index
 * ============================================================================ */

/* Analog Inputs: 0-19 (direct ADC channel number) */
#define PMU_CHID_ANALOG_BASE            0
#define PMU_CHID_ANALOG_MAX             19
#define PMU_CHID_ANALOG(pin)            (PMU_CHID_ANALOG_BASE + (pin))

/* Digital Inputs: 50-69 (50 + pin number) */
#define PMU_CHID_DIGITAL_BASE           50
#define PMU_CHID_DIGITAL_MAX            69
#define PMU_CHID_DIGITAL(pin)           (PMU_CHID_DIGITAL_BASE + (pin))

/* Power Outputs (PROFET): 100-129 (100 + output number) */
#define PMU_CHID_OUTPUT_BASE            100
#define PMU_CHID_OUTPUT_MAX             129
#define PMU_CHID_OUTPUT(pin)            (PMU_CHID_OUTPUT_BASE + (pin))

/* H-Bridge Outputs: 130-133 (130 + bridge index) */
#define PMU_CHID_HBRIDGE_BASE           130
#define PMU_CHID_HBRIDGE_MAX            133
#define PMU_CHID_HBRIDGE(idx)           (PMU_CHID_HBRIDGE_BASE + (idx))

/* CAN RX Channels: 200-299 (200 + allocation index) */
#define PMU_CHID_CAN_RX_BASE            200
#define PMU_CHID_CAN_RX_MAX             299
#define PMU_CHID_CAN_RX(idx)            (PMU_CHID_CAN_RX_BASE + (idx))

/* CAN TX Channels: 300-399 (300 + allocation index) */
#define PMU_CHID_CAN_TX_BASE            300
#define PMU_CHID_CAN_TX_MAX             399
#define PMU_CHID_CAN_TX(idx)            (PMU_CHID_CAN_TX_BASE + (idx))

/* Logic Channels: 400-499 (400 + allocation index) */
#define PMU_CHID_LOGIC_BASE             400
#define PMU_CHID_LOGIC_MAX              499
#define PMU_CHID_LOGIC(idx)             (PMU_CHID_LOGIC_BASE + (idx))

/* Number (Math) Channels: 500-599 (500 + allocation index) */
#define PMU_CHID_NUMBER_BASE            500
#define PMU_CHID_NUMBER_MAX             599
#define PMU_CHID_NUMBER(idx)            (PMU_CHID_NUMBER_BASE + (idx))

/* Timer Channels: 600-699 (600 + allocation index) */
#define PMU_CHID_TIMER_BASE             600
#define PMU_CHID_TIMER_MAX              699
#define PMU_CHID_TIMER(idx)             (PMU_CHID_TIMER_BASE + (idx))

/* Filter Channels: 700-799 (700 + allocation index) */
#define PMU_CHID_FILTER_BASE            700
#define PMU_CHID_FILTER_MAX             799
#define PMU_CHID_FILTER(idx)            (PMU_CHID_FILTER_BASE + (idx))

/* Switch Channels: 800-899 (800 + allocation index) */
#define PMU_CHID_SWITCH_BASE            800
#define PMU_CHID_SWITCH_MAX             899
#define PMU_CHID_SWITCH(idx)            (PMU_CHID_SWITCH_BASE + (idx))

/* PID Controllers: 900-915 (900 + controller index) */
#define PMU_CHID_PID_BASE               900
#define PMU_CHID_PID_MAX                915
#define PMU_CHID_PID(idx)               (PMU_CHID_PID_BASE + (idx))

/* User-defined Channels: 1000+ (dynamically allocated) */
#define PMU_CHID_USER_BASE              1000

/* ============================================================================
 * Helper Macros for Type Detection
 * ============================================================================ */

#define PMU_CHID_IS_ANALOG(id)    ((id) >= PMU_CHID_ANALOG_BASE && (id) <= PMU_CHID_ANALOG_MAX)
#define PMU_CHID_IS_DIGITAL(id)   ((id) >= PMU_CHID_DIGITAL_BASE && (id) <= PMU_CHID_DIGITAL_MAX)
#define PMU_CHID_IS_OUTPUT(id)    ((id) >= PMU_CHID_OUTPUT_BASE && (id) <= PMU_CHID_OUTPUT_MAX)
#define PMU_CHID_IS_HBRIDGE(id)   ((id) >= PMU_CHID_HBRIDGE_BASE && (id) <= PMU_CHID_HBRIDGE_MAX)
#define PMU_CHID_IS_CAN_RX(id)    ((id) >= PMU_CHID_CAN_RX_BASE && (id) <= PMU_CHID_CAN_RX_MAX)
#define PMU_CHID_IS_CAN_TX(id)    ((id) >= PMU_CHID_CAN_TX_BASE && (id) <= PMU_CHID_CAN_TX_MAX)
#define PMU_CHID_IS_LOGIC(id)     ((id) >= PMU_CHID_LOGIC_BASE && (id) <= PMU_CHID_LOGIC_MAX)
#define PMU_CHID_IS_NUMBER(id)    ((id) >= PMU_CHID_NUMBER_BASE && (id) <= PMU_CHID_NUMBER_MAX)
#define PMU_CHID_IS_TIMER(id)     ((id) >= PMU_CHID_TIMER_BASE && (id) <= PMU_CHID_TIMER_MAX)
#define PMU_CHID_IS_FILTER(id)    ((id) >= PMU_CHID_FILTER_BASE && (id) <= PMU_CHID_FILTER_MAX)
#define PMU_CHID_IS_SWITCH(id)    ((id) >= PMU_CHID_SWITCH_BASE && (id) <= PMU_CHID_SWITCH_MAX)
#define PMU_CHID_IS_PID(id)       ((id) >= PMU_CHID_PID_BASE && (id) <= PMU_CHID_PID_MAX)
#define PMU_CHID_IS_USER(id)      ((id) >= PMU_CHID_USER_BASE)

/* Get hardware index from channel ID */
#define PMU_CHID_TO_ANALOG_PIN(id)    ((id) - PMU_CHID_ANALOG_BASE)
#define PMU_CHID_TO_DIGITAL_PIN(id)   ((id) - PMU_CHID_DIGITAL_BASE)
#define PMU_CHID_TO_OUTPUT_PIN(id)    ((id) - PMU_CHID_OUTPUT_BASE)
#define PMU_CHID_TO_HBRIDGE_IDX(id)   ((id) - PMU_CHID_HBRIDGE_BASE)

#ifdef __cplusplus
}
#endif

#endif /* __PMU_CHANNEL_IDS_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
