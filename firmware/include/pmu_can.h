/**
 * pmu_can.h - CAN Bus Driver
 * Owner: R2 m-sport © 2025
 */
#ifndef __PMU_CAN_H
#define __PMU_CAN_H
#include "main.h"
HAL_StatusTypeDef PMU_CAN_Init(void);
void PMU_CAN_ProcessMessages(uint32_t timeout_ms);
void PMU_CAN_TransmitPeriodic(void);
HAL_StatusTypeDef PMU_CAN_SendMessage(uint8_t bus, uint32_t id, uint8_t *data, uint8_t len);
float PMU_CAN_GetSignalValue(const char *signal_name);
#endif
