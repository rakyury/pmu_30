/**
 * @file crc32.h
 * @brief CRC-32 calculation for PMU-30 shared library
 *
 * Used for binary configuration and telemetry validation.
 * Uses standard CRC-32 (IEEE 802.3 / zlib / PNG polynomial).
 *
 * @version 1.0
 * @date January 2026
 */

#ifndef PMU_CRC32_H
#define PMU_CRC32_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Calculate CRC-32 checksum
 *
 * @param data Pointer to data buffer
 * @param size Size of data in bytes
 * @return CRC-32 checksum
 */
uint32_t pmu_crc32(const uint8_t* data, size_t size);

/**
 * @brief Update CRC-32 with additional data (for streaming)
 *
 * @param crc Current CRC value (use 0xFFFFFFFF for initial)
 * @param data Pointer to data buffer
 * @param size Size of data in bytes
 * @return Updated CRC-32 value
 */
uint32_t pmu_crc32_update(uint32_t crc, const uint8_t* data, size_t size);

/**
 * @brief Finalize CRC-32 calculation
 *
 * @param crc CRC value from pmu_crc32_update
 * @return Final CRC-32 checksum
 */
uint32_t pmu_crc32_finalize(uint32_t crc);

/**
 * @brief CRC-16-CCITT calculation (for protocol compatibility)
 *
 * Uses polynomial 0x1021, initial 0xFFFF (same as current firmware)
 *
 * @param data Pointer to data buffer
 * @param size Size of data in bytes
 * @return CRC-16-CCITT checksum
 */
uint16_t pmu_crc16_ccitt(const uint8_t* data, size_t size);

#ifdef __cplusplus
}
#endif

#endif /* PMU_CRC32_H */
