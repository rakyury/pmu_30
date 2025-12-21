/**
 * FreeRTOS semphr.h stub header
 * TODO: Replace with actual FreeRTOS kernel
 */

#ifndef FREERTOS_SEMPHR_H
#define FREERTOS_SEMPHR_H

#include "FreeRTOS.h"
#include "queue.h"

/* Semaphore handle types */
typedef QueueHandle_t SemaphoreHandle_t;

/* Semaphore functions */
SemaphoreHandle_t xSemaphoreCreateBinary(void);
SemaphoreHandle_t xSemaphoreCreateCounting(UBaseType_t uxMaxCount, UBaseType_t uxInitialCount);
SemaphoreHandle_t xSemaphoreCreateMutex(void);

BaseType_t xSemaphoreGive(SemaphoreHandle_t xSemaphore);
BaseType_t xSemaphoreTake(SemaphoreHandle_t xSemaphore, TickType_t xTicksToWait);
BaseType_t xSemaphoreGiveFromISR(SemaphoreHandle_t xSemaphore, BaseType_t * pxHigherPriorityTaskWoken);
BaseType_t xSemaphoreTakeFromISR(SemaphoreHandle_t xSemaphore, BaseType_t * pxHigherPriorityTaskWoken);

#endif /* FREERTOS_SEMPHR_H */
