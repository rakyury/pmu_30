/**
 ******************************************************************************
 * @file           : pmu_flash.h
 * @brief          : W25Q512JV SPI Flash Driver Header
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * W25Q512JV Specifications:
 * - Capacity: 512 Mbit (64 MB)
 * - Interface: SPI (up to 104 MHz)
 * - Voltage: 2.7V - 3.6V
 * - Page Size: 256 bytes
 * - Sector Size: 4 KB
 * - Block Size: 64 KB
 * - Erase: Sector (4KB), Block (32/64KB), Chip
 * - Programming: Page (256B)
 *
 ******************************************************************************
 */

#ifndef PMU_FLASH_H
#define PMU_FLASH_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32h7xx_hal.h"
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Flash operation status
 */
typedef enum {
    PMU_FLASH_OK = 0,         /**< Operation successful */
    PMU_FLASH_ERROR,          /**< Generic error */
    PMU_FLASH_TIMEOUT,        /**< Operation timeout */
    PMU_FLASH_BUSY,           /**< Flash busy */
    PMU_FLASH_ERROR_WP,       /**< Write protected */
    PMU_FLASH_ERROR_ID        /**< Invalid chip ID */
} PMU_Flash_Status_t;

/**
 * @brief Flash information structure
 */
typedef struct {
    uint8_t manufacturer_id;  /**< Manufacturer ID (0xEF for Winbond) */
    uint8_t memory_type;      /**< Memory type (0x40 for W25Q) */
    uint8_t capacity;         /**< Capacity (0x20 for 512Mbit) */
    uint32_t jedec_id;        /**< Full JEDEC ID */
    uint64_t unique_id;       /**< 64-bit unique ID */
    uint32_t total_size;      /**< Total size in bytes */
} PMU_Flash_Info_t;

/**
 * @brief Flash statistics
 */
typedef struct {
    uint32_t read_count;      /**< Number of read operations */
    uint32_t write_count;     /**< Number of write operations */
    uint32_t erase_count;     /**< Number of erase operations */
    uint32_t error_count;     /**< Number of errors */
    uint32_t bytes_read;      /**< Total bytes read */
    uint32_t bytes_written;   /**< Total bytes written */
} PMU_Flash_Stats_t;

/* Exported constants --------------------------------------------------------*/

/* Flash memory organization */
#define W25Q_FLASH_SIZE           (64 * 1024 * 1024)  /**< 64 MB total */
#define W25Q_PAGE_SIZE            256                 /**< 256 bytes per page */
#define W25Q_SECTOR_SIZE          (4 * 1024)          /**< 4 KB per sector */
#define W25Q_BLOCK_SIZE_32K       (32 * 1024)         /**< 32 KB block */
#define W25Q_BLOCK_SIZE_64K       (64 * 1024)         /**< 64 KB block */

/* W25Q512JV Command set */
#define W25Q_CMD_WRITE_ENABLE     0x06  /**< Write Enable */
#define W25Q_CMD_WRITE_DISABLE    0x04  /**< Write Disable */
#define W25Q_CMD_READ_STATUS_REG1 0x05  /**< Read Status Register 1 */
#define W25Q_CMD_READ_STATUS_REG2 0x35  /**< Read Status Register 2 */
#define W25Q_CMD_READ_STATUS_REG3 0x15  /**< Read Status Register 3 */
#define W25Q_CMD_WRITE_STATUS_REG1 0x01 /**< Write Status Register 1 */
#define W25Q_CMD_PAGE_PROGRAM     0x02  /**< Page Program */
#define W25Q_CMD_QUAD_PAGE_PROGRAM 0x32 /**< Quad Page Program */
#define W25Q_CMD_BLOCK_ERASE_64K  0xD8  /**< 64KB Block Erase */
#define W25Q_CMD_BLOCK_ERASE_32K  0x52  /**< 32KB Block Erase */
#define W25Q_CMD_SECTOR_ERASE     0x20  /**< 4KB Sector Erase */
#define W25Q_CMD_CHIP_ERASE       0xC7  /**< Chip Erase */
#define W25Q_CMD_READ_DATA        0x03  /**< Read Data */
#define W25Q_CMD_FAST_READ        0x0B  /**< Fast Read */
#define W25Q_CMD_READ_UNIQUE_ID   0x4B  /**< Read Unique ID */
#define W25Q_CMD_JEDEC_ID         0x9F  /**< Read JEDEC ID */
#define W25Q_CMD_POWER_DOWN       0xB9  /**< Power Down */
#define W25Q_CMD_RELEASE_POWER_DOWN 0xAB /**< Release Power Down */
#define W25Q_CMD_ENABLE_RESET     0x66  /**< Enable Reset */
#define W25Q_CMD_RESET            0x99  /**< Reset Device */

/* Status Register bits */
#define W25Q_SR_BUSY              0x01  /**< Busy bit */
#define W25Q_SR_WEL               0x02  /**< Write Enable Latch */
#define W25Q_SR_BP0               0x04  /**< Block Protect bit 0 */
#define W25Q_SR_BP1               0x08  /**< Block Protect bit 1 */
#define W25Q_SR_BP2               0x10  /**< Block Protect bit 2 */
#define W25Q_SR_TB                0x20  /**< Top/Bottom Protect */
#define W25Q_SR_SEC               0x40  /**< Sector Protect */
#define W25Q_SR_SRP0              0x80  /**< Status Register Protect 0 */

/* Expected JEDEC ID for W25Q512JV */
#define W25Q512_MANUFACTURER_ID   0xEF  /**< Winbond */
#define W25Q512_MEMORY_TYPE       0x40  /**< W25Q series */
#define W25Q512_CAPACITY          0x20  /**< 512 Mbit */
#define W25Q512_JEDEC_ID          0xEF4020 /**< Full JEDEC ID */

/* Timeouts */
#define FLASH_TIMEOUT_MS          5000  /**< Generic operation timeout */
#define FLASH_ERASE_SECTOR_MS     400   /**< Sector erase timeout */
#define FLASH_ERASE_BLOCK_MS      2000  /**< Block erase timeout */
#define FLASH_ERASE_CHIP_MS       200000 /**< Chip erase timeout */
#define FLASH_PROGRAM_PAGE_MS     3     /**< Page program timeout */

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize flash driver
 * @retval Flash status
 */
PMU_Flash_Status_t PMU_Flash_Init(void);

/**
 * @brief Read flash information (JEDEC ID, Unique ID)
 * @param info Pointer to information structure
 * @retval Flash status
 */
PMU_Flash_Status_t PMU_Flash_GetInfo(PMU_Flash_Info_t* info);

/**
 * @brief Read data from flash
 * @param address Flash address (0 to FLASH_SIZE-1)
 * @param data Pointer to data buffer
 * @param length Number of bytes to read
 * @retval Flash status
 */
PMU_Flash_Status_t PMU_Flash_Read(uint32_t address, uint8_t* data, uint32_t length);

/**
 * @brief Write data to flash (page program)
 * @param address Flash address (must be page-aligned for optimal performance)
 * @param data Pointer to data buffer
 * @param length Number of bytes to write (max 256 per page)
 * @retval Flash status
 */
PMU_Flash_Status_t PMU_Flash_Write(uint32_t address, const uint8_t* data, uint32_t length);

/**
 * @brief Erase sector (4KB)
 * @param address Sector address (must be sector-aligned)
 * @retval Flash status
 */
PMU_Flash_Status_t PMU_Flash_EraseSector(uint32_t address);

/**
 * @brief Erase 64KB block
 * @param address Block address (must be block-aligned)
 * @retval Flash status
 */
PMU_Flash_Status_t PMU_Flash_EraseBlock64K(uint32_t address);

/**
 * @brief Erase entire chip
 * @retval Flash status
 */
PMU_Flash_Status_t PMU_Flash_EraseChip(void);

/**
 * @brief Check if flash is busy
 * @retval true if busy, false if ready
 */
bool PMU_Flash_IsBusy(void);

/**
 * @brief Wait until flash is ready
 * @param timeout_ms Timeout in milliseconds
 * @retval Flash status
 */
PMU_Flash_Status_t PMU_Flash_WaitReady(uint32_t timeout_ms);

/**
 * @brief Enable write operations
 * @retval Flash status
 */
PMU_Flash_Status_t PMU_Flash_WriteEnable(void);

/**
 * @brief Disable write operations
 * @retval Flash status
 */
PMU_Flash_Status_t PMU_Flash_WriteDisable(void);

/**
 * @brief Read status register
 * @param reg_num Register number (1, 2, or 3)
 * @param status Pointer to store status byte
 * @retval Flash status
 */
PMU_Flash_Status_t PMU_Flash_ReadStatus(uint8_t reg_num, uint8_t* status);

/**
 * @brief Power down flash (low power mode)
 * @retval Flash status
 */
PMU_Flash_Status_t PMU_Flash_PowerDown(void);

/**
 * @brief Wake up flash from power down
 * @retval Flash status
 */
PMU_Flash_Status_t PMU_Flash_WakeUp(void);

/**
 * @brief Reset flash device
 * @retval Flash status
 */
PMU_Flash_Status_t PMU_Flash_Reset(void);

/**
 * @brief Get flash statistics
 * @retval Pointer to statistics structure
 */
PMU_Flash_Stats_t* PMU_Flash_GetStats(void);

/**
 * @brief Clear flash statistics
 * @retval None
 */
void PMU_Flash_ClearStats(void);

#ifdef __cplusplus
}
#endif

#endif /* PMU_FLASH_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
