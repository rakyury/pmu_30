/**
 * MIN Protocol Configuration for PMU-30
 *
 * Compile-time options for MIN protocol.
 */

#ifndef MIN_CONFIG_H
#define MIN_CONFIG_H

/* Maximum payload size (0-255 bytes) */
#define MAX_PAYLOAD 255

/* Disable transport protocol - we use min_send_frame() only (no ACK/retransmit) */
#define NO_TRANSPORT_PROTOCOL

/* Note: These are kept for reference but not used with NO_TRANSPORT_PROTOCOL:
 * TRANSPORT_FIFO_SIZE_FRAMES_BITS 4
 * TRANSPORT_FIFO_SIZE_FRAME_DATA_BITS 10
 * TRANSPORT_ACK_RETRANSMIT_TIMEOUT_MS 25
 * TRANSPORT_FRAME_RETRANSMIT_TIMEOUT_MS 50
 * TRANSPORT_MAX_WINDOW_SIZE 8
 * TRANSPORT_IDLE_TIMEOUT_MS 3000
 */

#endif /* MIN_CONFIG_H */
