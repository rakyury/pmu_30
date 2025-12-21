/**
 ******************************************************************************
 * @file           : FreeRTOS.h
 * @brief          : FreeRTOS stub header for unit testing
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 */

#ifndef FREERTOS_H
#define FREERTOS_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

/* FreeRTOS type stubs */
typedef uint32_t TickType_t;
typedef void* TaskHandle_t;
typedef void* QueueHandle_t;
typedef void* SemaphoreHandle_t;

/* FreeRTOS constants */
#define configMAX_PRIORITIES    5
#define tskIDLE_PRIORITY        0
#define pdMS_TO_TICKS(ms)       (ms)

/* FreeRTOS function stubs */
static inline void vTaskStartScheduler(void) {}
static inline TickType_t xTaskGetTickCount(void) { return 0; }
static inline void vTaskDelay(TickType_t ticks) { (void)ticks; }
static inline void vTaskDelayUntil(TickType_t* pxPreviousWakeTime, TickType_t xTimeIncrement) {
    (void)pxPreviousWakeTime;
    (void)xTimeIncrement;
}

/* Task creation stub */
typedef void (*TaskFunction_t)(void*);
static inline int xTaskCreate(
    TaskFunction_t pvTaskCode,
    const char* pcName,
    uint32_t usStackDepth,
    void* pvParameters,
    uint32_t uxPriority,
    TaskHandle_t* pxCreatedTask)
{
    (void)pvTaskCode;
    (void)pcName;
    (void)usStackDepth;
    (void)pvParameters;
    (void)uxPriority;
    (void)pxCreatedTask;
    return 1;
}

#ifdef __cplusplus
}
#endif

#endif /* FREERTOS_H */
