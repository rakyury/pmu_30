/**
 ******************************************************************************
 * @file           : pmu_bootloader.h
 * @brief          : Bootloader Header - OTA Firmware Updates for PMU-30
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * Flash Memory Layout (STM32H743 - 2MB internal flash):
 *
 * ┌─────────────────────────────────────────────────────────────────┐
 * │ 0x08000000 │ Bootloader (64 KB)                                 │
 * │            │ - System initialization                            │
 * │            │ - Firmware verification                            │
 * │            │ - Update mechanism                                 │
 * ├─────────────────────────────────────────────────────────────────┤
 * │ 0x08010000 │ Application Header (4 KB)                          │
 * │            │ - Version info, CRC, signature                     │
 * ├─────────────────────────────────────────────────────────────────┤
 * │ 0x08011000 │ Application Firmware (960 KB)                      │
 * │            │ - Main PMU-30 application                          │
 * ├─────────────────────────────────────────────────────────────────┤
 * │ 0x08100000 │ Backup Firmware (960 KB)                           │
 * │            │ - Fallback if update fails                         │
 * ├─────────────────────────────────────────────────────────────────┤
 * │ 0x081F0000 │ Configuration Area (64 KB)                         │
 * │            │ - User settings preserved across updates           │
 * └─────────────────────────────────────────────────────────────────┘
 *
 * External Flash (W25Q512JV - 64 MB):
 *
 * ┌─────────────────────────────────────────────────────────────────┐
 * │ 0x00000000 │ Firmware Update Buffer (1 MB)                      │
 * │            │ - Temporary storage for OTA downloads              │
 * ├─────────────────────────────────────────────────────────────────┤
 * │ 0x00100000 │ Configuration Backup (256 KB)                      │
 * │            │ - JSON configuration storage                       │
 * ├─────────────────────────────────────────────────────────────────┤
 * │ 0x00140000 │ Data Logging (62+ MB)                              │
 * │            │ - High-speed data logging                          │
 * └─────────────────────────────────────────────────────────────────┘
 *
 ******************************************************************************
 */

#ifndef PMU_BOOTLOADER_H
#define PMU_BOOTLOADER_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "pmu_hal.h"
#include <stdint.h>
#include <stdbool.h>

/* Exported types ------------------------------------------------------------*/

/**
 * @brief Bootloader status codes
 */
typedef enum {
    PMU_BOOT_OK = 0,              /**< Operation successful */
    PMU_BOOT_ERROR,               /**< Generic error */
    PMU_BOOT_ERROR_CRC,           /**< CRC check failed */
    PMU_BOOT_ERROR_SIGNATURE,     /**< Signature verification failed */
    PMU_BOOT_ERROR_VERSION,       /**< Version check failed */
    PMU_BOOT_ERROR_FLASH,         /**< Flash operation failed */
    PMU_BOOT_ERROR_NO_APP,        /**< No valid application found */
    PMU_BOOT_ERROR_TIMEOUT,       /**< Operation timeout */
    PMU_BOOT_UPDATE_REQUIRED,     /**< Update pending in external flash */
    PMU_BOOT_UPDATE_IN_PROGRESS   /**< Update is being applied */
} PMU_Boot_Status_t;

/**
 * @brief Boot reason (why bootloader was entered)
 */
typedef enum {
    PMU_BOOT_REASON_POWER_ON = 0, /**< Normal power-on reset */
    PMU_BOOT_REASON_WATCHDOG,     /**< Watchdog reset */
    PMU_BOOT_REASON_UPDATE,       /**< Update request from application */
    PMU_BOOT_REASON_INVALID_APP,  /**< Application failed verification */
    PMU_BOOT_REASON_BUTTON,       /**< Boot button held during power-on */
    PMU_BOOT_REASON_CRASH         /**< Application crashed (HardFault) */
} PMU_Boot_Reason_t;

/**
 * @brief Firmware header structure (stored at APP_HEADER_ADDRESS)
 */
typedef struct __attribute__((packed)) {
    uint32_t magic;               /**< Magic number (0x504D5530 = "PMU0") */
    uint32_t version_major;       /**< Major version */
    uint32_t version_minor;       /**< Minor version */
    uint32_t version_patch;       /**< Patch version */
    uint32_t build_number;        /**< Build number */
    uint32_t build_timestamp;     /**< Unix timestamp of build */
    uint32_t app_size;            /**< Application size in bytes */
    uint32_t app_crc32;           /**< CRC32 of application code */
    uint32_t vector_table_addr;   /**< Vector table address */
    uint32_t entry_point;         /**< Entry point address */
    uint8_t  signature[64];       /**< Ed25519 signature (optional) */
    uint8_t  reserved[128];       /**< Reserved for future use */
    uint32_t header_crc32;        /**< CRC32 of header (excluding this field) */
} PMU_Firmware_Header_t;

/**
 * @brief Bootloader shared data (in backup SRAM, survives reset)
 */
typedef struct __attribute__((packed)) {
    uint32_t magic;               /**< Magic number (0x424F4F54 = "BOOT") */
    uint32_t boot_reason;         /**< Boot reason code */
    uint32_t update_requested;    /**< Update request flag */
    uint32_t app_boot_count;      /**< Consecutive boot attempts */
    uint32_t last_crash_addr;     /**< Address of last HardFault */
    uint32_t flags;               /**< Misc flags */
    uint32_t checksum;            /**< Simple checksum for validation */
} PMU_Boot_SharedData_t;

/**
 * @brief Bootloader state
 */
typedef struct {
    PMU_Boot_Status_t status;
    PMU_Boot_Reason_t reason;
    PMU_Firmware_Header_t* active_header;
    PMU_Firmware_Header_t* backup_header;
    bool update_available;
    bool signature_verified;
    uint32_t update_progress;
} PMU_Bootloader_State_t;

/* Exported constants --------------------------------------------------------*/

/* Flash memory layout - internal flash (2 MB) */
#define PMU_FLASH_BASE            0x08000000UL
#define PMU_FLASH_SIZE            (2 * 1024 * 1024)  /* 2 MB */
#define PMU_FLASH_SECTOR_SIZE     (128 * 1024)       /* 128 KB sectors on STM32H7 */

/* Bootloader region */
#define PMU_BOOTLOADER_ADDRESS    0x08000000UL
#define PMU_BOOTLOADER_SIZE       (64 * 1024)        /* 64 KB */

/* Application header (contains version, CRC, signature) */
#define PMU_APP_HEADER_ADDRESS    0x08010000UL
#define PMU_APP_HEADER_SIZE       (4 * 1024)         /* 4 KB */

/* Main application region */
#define PMU_APP_ADDRESS           0x08011000UL
#define PMU_APP_SIZE              (960 * 1024)       /* 960 KB */
#define PMU_APP_END               (PMU_APP_ADDRESS + PMU_APP_SIZE)

/* Backup application region (for rollback) */
#define PMU_BACKUP_ADDRESS        0x08100000UL
#define PMU_BACKUP_SIZE           (960 * 1024)       /* 960 KB */

/* Configuration storage (preserved across updates) */
#define PMU_CONFIG_ADDRESS        0x081F0000UL
#define PMU_CONFIG_SIZE           (64 * 1024)        /* 64 KB */

/* External flash layout (W25Q512JV - 64 MB) */
#define PMU_EXT_UPDATE_ADDRESS    0x00000000UL
#define PMU_EXT_UPDATE_SIZE       (1024 * 1024)      /* 1 MB for OTA buffer */
#define PMU_EXT_CONFIG_ADDRESS    0x00100000UL
#define PMU_EXT_CONFIG_SIZE       (256 * 1024)       /* 256 KB for config backup */
#define PMU_EXT_LOG_ADDRESS       0x00140000UL
#define PMU_EXT_LOG_SIZE          (63 * 1024 * 1024) /* 63 MB for logging */

/* Magic numbers */
#define PMU_FW_MAGIC              0x504D5530UL       /* "PMU0" */
#define PMU_BOOT_MAGIC            0x424F4F54UL       /* "BOOT" */
#define PMU_UPDATE_MAGIC          0x55504454UL       /* "UPDT" */

/* Backup SRAM address (survives reset) */
#define PMU_BACKUP_SRAM_BASE      0x38800000UL       /* BKPSRAM on STM32H7 */
#define PMU_BOOT_SHARED_DATA_ADDR PMU_BACKUP_SRAM_BASE

/* Boot button GPIO (optional - for manual bootloader entry) */
#define PMU_BOOT_BUTTON_PORT      GPIOA
#define PMU_BOOT_BUTTON_PIN       GPIO_PIN_0

/* Timeout values */
#define PMU_BOOT_TIMEOUT_MS       5000               /* 5 second boot timeout */
#define PMU_UPDATE_TIMEOUT_MS     30000              /* 30 second update timeout */
#define PMU_MAX_BOOT_ATTEMPTS     3                  /* Max consecutive boot failures */

/* CRC polynomial (CRC-32 IEEE 802.3) */
#define PMU_CRC32_POLYNOMIAL      0xEDB88320UL
#define PMU_CRC32_INITIAL         0xFFFFFFFFUL

/* Exported macros -----------------------------------------------------------*/

/**
 * @brief Check if address is in application region
 */
#define IS_APP_ADDRESS(addr) \
    ((addr) >= PMU_APP_ADDRESS && (addr) < PMU_APP_END)

/**
 * @brief Check if address is in bootloader region
 */
#define IS_BOOTLOADER_ADDRESS(addr) \
    ((addr) >= PMU_BOOTLOADER_ADDRESS && (addr) < (PMU_BOOTLOADER_ADDRESS + PMU_BOOTLOADER_SIZE))

/**
 * @brief Get firmware version as single uint32_t
 */
#define FW_VERSION_PACK(major, minor, patch) \
    (((major) << 24) | ((minor) << 16) | (patch))

/* Exported functions --------------------------------------------------------*/

/*---------------------------------------------------------------------------*/
/* Initialization and Main Functions                                         */
/*---------------------------------------------------------------------------*/

/**
 * @brief Initialize bootloader
 * @note  Called at system startup before main application
 * @retval Boot status
 */
PMU_Boot_Status_t PMU_Bootloader_Init(void);

/**
 * @brief Run bootloader main logic
 * @note  Checks for updates, validates app, and either jumps to app or stays in bootloader
 * @retval Boot status
 */
PMU_Boot_Status_t PMU_Bootloader_Run(void);

/**
 * @brief Get bootloader state
 * @retval Pointer to bootloader state
 */
PMU_Bootloader_State_t* PMU_Bootloader_GetState(void);

/*---------------------------------------------------------------------------*/
/* Application Management                                                     */
/*---------------------------------------------------------------------------*/

/**
 * @brief Validate application firmware
 * @param header_addr Address of firmware header
 * @param verify_signature Whether to check Ed25519 signature
 * @retval Boot status
 */
PMU_Boot_Status_t PMU_Bootloader_ValidateApp(uint32_t header_addr, bool verify_signature);

/**
 * @brief Jump to application
 * @param app_address Application address (vector table location)
 * @note  This function does not return
 */
void PMU_Bootloader_JumpToApp(uint32_t app_address) __attribute__((noreturn));

/**
 * @brief Get active firmware header
 * @retval Pointer to firmware header, or NULL if invalid
 */
PMU_Firmware_Header_t* PMU_Bootloader_GetActiveHeader(void);

/**
 * @brief Get backup firmware header
 * @retval Pointer to firmware header, or NULL if no backup
 */
PMU_Firmware_Header_t* PMU_Bootloader_GetBackupHeader(void);

/*---------------------------------------------------------------------------*/
/* Firmware Update                                                            */
/*---------------------------------------------------------------------------*/

/**
 * @brief Check if firmware update is available in external flash
 * @retval true if update available, false otherwise
 */
bool PMU_Bootloader_IsUpdateAvailable(void);

/**
 * @brief Apply pending firmware update
 * @note  Copies from external flash to internal flash
 * @retval Boot status
 */
PMU_Boot_Status_t PMU_Bootloader_ApplyUpdate(void);

/**
 * @brief Write update chunk to external flash buffer
 * @param offset Offset within update buffer
 * @param data Data to write
 * @param length Data length
 * @retval Boot status
 */
PMU_Boot_Status_t PMU_Bootloader_WriteUpdateChunk(uint32_t offset, const uint8_t* data, uint32_t length);

/**
 * @brief Mark update as complete and ready to apply
 * @param total_size Total firmware size
 * @param crc32 Expected CRC32 of firmware
 * @retval Boot status
 */
PMU_Boot_Status_t PMU_Bootloader_FinalizeUpdate(uint32_t total_size, uint32_t crc32);

/**
 * @brief Cancel pending update
 * @retval Boot status
 */
PMU_Boot_Status_t PMU_Bootloader_CancelUpdate(void);

/**
 * @brief Rollback to backup firmware
 * @note  Use if new firmware fails to boot
 * @retval Boot status
 */
PMU_Boot_Status_t PMU_Bootloader_Rollback(void);

/*---------------------------------------------------------------------------*/
/* Boot Control                                                               */
/*---------------------------------------------------------------------------*/

/**
 * @brief Request system reboot into bootloader mode
 * @param reason Reason for reboot
 * @retval Boot status
 */
PMU_Boot_Status_t PMU_Bootloader_RequestReboot(PMU_Boot_Reason_t reason);

/**
 * @brief Request firmware update (sets flag for bootloader)
 * @note  Called from application to trigger update on next boot
 * @retval Boot status
 */
PMU_Boot_Status_t PMU_Bootloader_RequestUpdate(void);

/**
 * @brief Get boot reason
 * @retval Boot reason code
 */
PMU_Boot_Reason_t PMU_Bootloader_GetBootReason(void);

/**
 * @brief Get shared data structure (survives reset)
 * @retval Pointer to shared data in backup SRAM
 */
PMU_Boot_SharedData_t* PMU_Bootloader_GetSharedData(void);

/*---------------------------------------------------------------------------*/
/* Utility Functions                                                          */
/*---------------------------------------------------------------------------*/

/**
 * @brief Calculate CRC32 of memory region
 * @param data Pointer to data
 * @param length Data length
 * @retval CRC32 value
 */
uint32_t PMU_Bootloader_CalculateCRC32(const uint8_t* data, uint32_t length);

/**
 * @brief Erase internal flash sector
 * @param sector_address Sector address
 * @retval Boot status
 */
PMU_Boot_Status_t PMU_Bootloader_EraseFlashSector(uint32_t sector_address);

/**
 * @brief Write to internal flash
 * @param address Flash address
 * @param data Data to write
 * @param length Data length (must be multiple of 32 bytes on STM32H7)
 * @retval Boot status
 */
PMU_Boot_Status_t PMU_Bootloader_WriteFlash(uint32_t address, const uint8_t* data, uint32_t length);

/**
 * @brief Read from flash memory
 * @param address Flash address
 * @param data Buffer to read into
 * @param length Data length
 * @retval Boot status
 */
PMU_Boot_Status_t PMU_Bootloader_ReadFlash(uint32_t address, uint8_t* data, uint32_t length);

/**
 * @brief Get firmware version string
 * @param header Firmware header
 * @param buffer Output buffer
 * @param buffer_size Buffer size
 * @retval Number of characters written
 */
int PMU_Bootloader_GetVersionString(const PMU_Firmware_Header_t* header, char* buffer, size_t buffer_size);

#ifdef __cplusplus
}
#endif

#endif /* PMU_BOOTLOADER_H */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
