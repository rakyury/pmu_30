/**
 * FreeRTOS queue.h stub header
 * TODO: Replace with actual FreeRTOS kernel
 */

#ifndef FREERTOS_QUEUE_H
#define FREERTOS_QUEUE_H

#include "FreeRTOS.h"

/* Queue handle type */
typedef void* QueueHandle_t;

/* Queue functions */
QueueHandle_t xQueueCreate(UBaseType_t uxQueueLength, UBaseType_t uxItemSize);
BaseType_t xQueueSend(QueueHandle_t xQueue, const void * pvItemToQueue, TickType_t xTicksToWait);
BaseType_t xQueueReceive(QueueHandle_t xQueue, void * pvBuffer, TickType_t xTicksToWait);
UBaseType_t uxQueueMessagesWaiting(const QueueHandle_t xQueue);
BaseType_t xQueueSendFromISR(QueueHandle_t xQueue, const void * pvItemToQueue, BaseType_t * pxHigherPriorityTaskWoken);
BaseType_t xQueueReceiveFromISR(QueueHandle_t xQueue, void * pvBuffer, BaseType_t * pxHigherPriorityTaskWoken);

#endif /* FREERTOS_QUEUE_H */
