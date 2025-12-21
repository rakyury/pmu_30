/**
 * pmu_logging.h - Data Logging
 * Owner: R2 m-sport © 2025
 */
#ifndef __PMU_LOGGING_H
#define __PMU_LOGGING_H
#include "main.h"
HAL_StatusTypeDef PMU_Logging_Init(void);
void PMU_Logging_LogData(void);
#endif
