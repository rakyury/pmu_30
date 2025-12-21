/**
 * pmu_ui.h - UI and LED Control
 * Owner: R2 m-sport © 2025
 */
#ifndef __PMU_UI_H
#define __PMU_UI_H
#include "main.h"
HAL_StatusTypeDef PMU_UI_Init(void);
void PMU_UI_Update(void);
void PMU_UI_SetLED(uint8_t channel, uint8_t color);
#endif
