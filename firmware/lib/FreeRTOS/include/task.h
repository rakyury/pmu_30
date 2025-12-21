/**
 * FreeRTOS task.h stub header
 * TODO: Replace with actual FreeRTOS kernel
 */

#ifndef FREERTOS_TASK_H
#define FREERTOS_TASK_H

#include "FreeRTOS.h"

/* Task states */
#define eRunning        0
#define eReady          1
#define eBlocked        2
#define eSuspended      3
#define eDeleted        4

/* Task functions */
BaseType_t xTaskCreate(TaskFunction_t pxTaskCode,
                       const char * const pcName,
                       const uint16_t usStackDepth,
                       void * const pvParameters,
                       UBaseType_t uxPriority,
                       TaskHandle_t * const pxCreatedTask);

void vTaskDelay(const TickType_t xTicksToDelay);
void vTaskDelayUntil(TickType_t * const pxPreviousWakeTime, const TickType_t xTimeIncrement);
TickType_t xTaskGetTickCount(void);
void vTaskStartScheduler(void);
void vTaskSuspend(TaskHandle_t xTaskToSuspend);
void vTaskResume(TaskHandle_t xTaskToResume);
void taskYIELD(void);

#endif /* FREERTOS_TASK_H */
