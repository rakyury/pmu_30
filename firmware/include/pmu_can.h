/**
 * pmu_can.h - CAN Bus Driver
 * Owner: R2 m-sport © 2025
 */
#ifndef __PMU_CAN_H
#define __PMU_CAN_H
#include "main.h"
HAL_StatusTypeDef PMU_CAN_Init(void);
void PMU_CAN_Update(void);
HAL_StatusTypeDef PMU_CAN_Send(uint8_t bus, uint32_t id, uint8_t* data, uint8_t len);
#endif
