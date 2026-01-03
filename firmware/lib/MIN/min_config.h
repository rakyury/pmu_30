/**
 * MIN Protocol Configuration for PMU-30
 *
 * T-MIN (Transport MIN) with automatic retransmission.
 */

#ifndef MIN_CONFIG_H
#define MIN_CONFIG_H

/* Maximum payload size (0-255 bytes) */
#define MAX_PAYLOAD 255

/* T-MIN Transport Protocol Configuration */
#define TRANSPORT_FIFO_SIZE_FRAMES_BITS 4       /* 16 frames queue */
#define TRANSPORT_FIFO_SIZE_FRAME_DATA_BITS 10  /* 1KB buffer */
#define TRANSPORT_ACK_RETRANSMIT_TIMEOUT_MS 25
#define TRANSPORT_FRAME_RETRANSMIT_TIMEOUT_MS 50
#define TRANSPORT_MAX_WINDOW_SIZE 8
#define TRANSPORT_IDLE_TIMEOUT_MS 3000

#endif /* MIN_CONFIG_H */
