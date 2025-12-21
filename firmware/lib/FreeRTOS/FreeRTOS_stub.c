/**
 * FreeRTOS stub implementation
 * This is a minimal stub to allow compilation without FreeRTOS
 * TODO: Replace with actual FreeRTOS kernel
 */

#include <stddef.h>
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "semphr.h"

/* Task API stub implementations */
BaseType_t xTaskCreate(TaskFunction_t pxTaskCode,
                       const char * const pcName,
                       const uint16_t usStackDepth,
                       void * const pvParameters,
                       UBaseType_t uxPriority,
                       TaskHandle_t * const pxCreatedTask)
{
    (void)pxTaskCode;
    (void)pcName;
    (void)usStackDepth;
    (void)pvParameters;
    (void)uxPriority;
    if (pxCreatedTask != NULL) {
        *pxCreatedTask = (TaskHandle_t)1;
    }
    return pdPASS;
}

void vTaskDelay(const TickType_t xTicksToDelay)
{
    (void)xTicksToDelay;
    /* TODO: Implement actual delay */
}

void vTaskDelayUntil(TickType_t * const pxPreviousWakeTime, const TickType_t xTimeIncrement)
{
    (void)pxPreviousWakeTime;
    (void)xTimeIncrement;
    /* TODO: Implement actual delay */
}

TickType_t xTaskGetTickCount(void)
{
    /* TODO: Return actual tick count */
    return 0;
}

void vTaskStartScheduler(void)
{
    /* TODO: Start actual scheduler */
    while(1) {
        /* Infinite loop for now */
    }
}

void vTaskSuspend(TaskHandle_t xTaskToSuspend)
{
    (void)xTaskToSuspend;
}

void vTaskResume(TaskHandle_t xTaskToResume)
{
    (void)xTaskToResume;
}

void taskYIELD(void)
{
    /* TODO: Implement task yield */
}

/* Queue API stub implementations */
QueueHandle_t xQueueCreate(UBaseType_t uxQueueLength, UBaseType_t uxItemSize)
{
    (void)uxQueueLength;
    (void)uxItemSize;
    return (QueueHandle_t)1;
}

BaseType_t xQueueSend(QueueHandle_t xQueue, const void * pvItemToQueue, TickType_t xTicksToWait)
{
    (void)xQueue;
    (void)pvItemToQueue;
    (void)xTicksToWait;
    return pdPASS;
}

BaseType_t xQueueReceive(QueueHandle_t xQueue, void * pvBuffer, TickType_t xTicksToWait)
{
    (void)xQueue;
    (void)pvBuffer;
    (void)xTicksToWait;
    return pdFAIL;
}

UBaseType_t uxQueueMessagesWaiting(const QueueHandle_t xQueue)
{
    (void)xQueue;
    return 0;
}

BaseType_t xQueueSendFromISR(QueueHandle_t xQueue, const void * pvItemToQueue, BaseType_t * pxHigherPriorityTaskWoken)
{
    (void)xQueue;
    (void)pvItemToQueue;
    (void)pxHigherPriorityTaskWoken;
    return pdPASS;
}

BaseType_t xQueueReceiveFromISR(QueueHandle_t xQueue, void * pvBuffer, BaseType_t * pxHigherPriorityTaskWoken)
{
    (void)xQueue;
    (void)pvBuffer;
    (void)pxHigherPriorityTaskWoken;
    return pdFAIL;
}

/* Semaphore API stub implementations */
SemaphoreHandle_t xSemaphoreCreateBinary(void)
{
    return (SemaphoreHandle_t)1;
}

SemaphoreHandle_t xSemaphoreCreateCounting(UBaseType_t uxMaxCount, UBaseType_t uxInitialCount)
{
    (void)uxMaxCount;
    (void)uxInitialCount;
    return (SemaphoreHandle_t)1;
}

SemaphoreHandle_t xSemaphoreCreateMutex(void)
{
    return (SemaphoreHandle_t)1;
}

BaseType_t xSemaphoreGive(SemaphoreHandle_t xSemaphore)
{
    (void)xSemaphore;
    return pdPASS;
}

BaseType_t xSemaphoreTake(SemaphoreHandle_t xSemaphore, TickType_t xTicksToWait)
{
    (void)xSemaphore;
    (void)xTicksToWait;
    return pdPASS;
}

BaseType_t xSemaphoreGiveFromISR(SemaphoreHandle_t xSemaphore, BaseType_t * pxHigherPriorityTaskWoken)
{
    (void)xSemaphore;
    (void)pxHigherPriorityTaskWoken;
    return pdPASS;
}

BaseType_t xSemaphoreTakeFromISR(SemaphoreHandle_t xSemaphore, BaseType_t * pxHigherPriorityTaskWoken)
{
    (void)xSemaphore;
    (void)pxHigherPriorityTaskWoken;
    return pdPASS;
}
