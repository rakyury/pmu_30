/**
 * FreeRTOS stub header
 * TODO: Replace with actual FreeRTOS kernel
 */

#ifndef FREERTOS_H
#define FREERTOS_H

#include <stdint.h>

/* FreeRTOS basic types */
typedef void (*TaskFunction_t)(void *);
typedef void* TaskHandle_t;
typedef uint32_t TickType_t;
typedef uint32_t UBaseType_t;
typedef int32_t BaseType_t;

/* Task priorities */
#define tskIDLE_PRIORITY            0
#define configMAX_PRIORITIES        5

/* Time conversion */
#define pdMS_TO_TICKS(ms)           ((TickType_t)(ms))
#define portMAX_DELAY               ((TickType_t)0xFFFFFFFF)

/* Return codes */
#define pdPASS                      1
#define pdFAIL                      0
#define pdTRUE                      1
#define pdFALSE                     0

#endif /* FREERTOS_H */
