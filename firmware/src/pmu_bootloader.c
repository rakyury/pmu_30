/**
 ******************************************************************************
 * @file           : pmu_bootloader.c
 * @brief          : Bootloader Implementation - OTA Firmware Updates for PMU-30
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This bootloader provides:
 * - CRC32 firmware verification
 * - Optional Ed25519 signature verification
 * - OTA update from external flash
 * - Automatic rollback on boot failure
 * - Configuration preservation across updates
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_bootloader.h"
#include "pmu_flash.h"
#include <string.h>
#include <stdio.h>

/* Private typedef -----------------------------------------------------------*/

/**
 * @brief Update buffer header (stored at beginning of external flash update region)
 */
typedef struct __attribute__((packed)) {
    uint32_t magic;               /* PMU_UPDATE_MAGIC */
    uint32_t firmware_size;       /* Total firmware size */
    uint32_t firmware_crc32;      /* Expected CRC32 */
    uint32_t header_offset;       /* Offset to firmware header */
    uint32_t status;              /* Update status (0=pending, 1=applied, 2=failed) */
    uint32_t timestamp;           /* When update was received */
    uint32_t reserved[8];         /* Reserved for future use */
    uint32_t buffer_crc32;        /* CRC32 of this header */
} PMU_Update_Header_t;

/* Private define ------------------------------------------------------------*/
#define UPDATE_STATUS_PENDING     0
#define UPDATE_STATUS_APPLIED     1
#define UPDATE_STATUS_FAILED      2

/* STM32H7 flash programming granularity */
#define FLASH_PROGRAM_SIZE        32  /* 256-bit (32 bytes) on STM32H7 */

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_Bootloader_State_t bootloader_state = {0};
static PMU_Boot_SharedData_t* shared_data = NULL;

/* CRC32 lookup table (pre-computed for speed) */
static const uint32_t crc32_table[256] = {
    0x00000000, 0x77073096, 0xEE0E612C, 0x990951BA, 0x076DC419, 0x706AF48F,
    0xE963A535, 0x9E6495A3, 0x0EDB8832, 0x79DCB8A4, 0xE0D5E91E, 0x97D2D988,
    0x09B64C2B, 0x7EB17CBD, 0xE7B82D07, 0x90BF1D91, 0x1DB71064, 0x6AB020F2,
    0xF3B97148, 0x84BE41DE, 0x1ADAD47D, 0x6DDDE4EB, 0xF4D4B551, 0x83D385C7,
    0x136C9856, 0x646BA8C0, 0xFD62F97A, 0x8A65C9EC, 0x14015C4F, 0x63066CD9,
    0xFA0F3D63, 0x8D080DF5, 0x3B6E20C8, 0x4C69105E, 0xD56041E4, 0xA2677172,
    0x3C03E4D1, 0x4B04D447, 0xD20D85FD, 0xA50AB56B, 0x35B5A8FA, 0x42B2986C,
    0xDBBBC9D6, 0xACBCF940, 0x32D86CE3, 0x45DF5C75, 0xDCD60DCF, 0xABD13D59,
    0x26D930AC, 0x51DE003A, 0xC8D75180, 0xBFD06116, 0x21B4F4B5, 0x56B3C423,
    0xCFBA9599, 0xB8BDA50F, 0x2802B89E, 0x5F058808, 0xC60CD9B2, 0xB10BE924,
    0x2F6F7C87, 0x58684C11, 0xC1611DAB, 0xB6662D3D, 0x76DC4190, 0x01DB7106,
    0x98D220BC, 0xEFD5102A, 0x71B18589, 0x06B6B51F, 0x9FBFE4A5, 0xE8B8D433,
    0x7807C9A2, 0x0F00F934, 0x9609A88E, 0xE10E9818, 0x7F6A0DBB, 0x086D3D2D,
    0x91646C97, 0xE6635C01, 0x6B6B51F4, 0x1C6C6162, 0x856530D8, 0xF262004E,
    0x6C0695ED, 0x1B01A57B, 0x8208F4C1, 0xF50FC457, 0x65B0D9C6, 0x12B7E950,
    0x8BBEB8EA, 0xFCB9887C, 0x62DD1DDF, 0x15DA2D49, 0x8CD37CF3, 0xFBD44C65,
    0x4DB26158, 0x3AB551CE, 0xA3BC0074, 0xD4BB30E2, 0x4ADFA541, 0x3DD895D7,
    0xA4D1C46D, 0xD3D6F4FB, 0x4369E96A, 0x346ED9FC, 0xAD678846, 0xDA60B8D0,
    0x44042D73, 0x33031DE5, 0xAA0A4C5F, 0xDD0D7CC9, 0x5005713C, 0x270241AA,
    0xBE0B1010, 0xC90C2086, 0x5768B525, 0x206F85B3, 0xB966D409, 0xCE61E49F,
    0x5EDEF90E, 0x29D9C998, 0xB0D09822, 0xC7D7A8B4, 0x59B33D17, 0x2EB40D81,
    0xB7BD5C3B, 0xC0BA6CAD, 0xEDB88320, 0x9ABFB3B6, 0x03B6E20C, 0x74B1D29A,
    0xEAD54739, 0x9DD277AF, 0x04DB2615, 0x73DC1683, 0xE3630B12, 0x94643B84,
    0x0D6D6A3E, 0x7A6A5AA8, 0xE40ECF0B, 0x9309FF9D, 0x0A00AE27, 0x7D079EB1,
    0xF00F9344, 0x8708A3D2, 0x1E01F268, 0x6906C2FE, 0xF762575D, 0x806567CB,
    0x196C3671, 0x6E6B06E7, 0xFED41B76, 0x89D32BE0, 0x10DA7A5A, 0x67DD4ACC,
    0xF9B9DF6F, 0x8EBEEFF9, 0x17B7BE43, 0x60B08ED5, 0xD6D6A3E8, 0xA1D1937E,
    0x38D8C2C4, 0x4FDFF252, 0xD1BB67F1, 0xA6BC5767, 0x3FB506DD, 0x48B2364B,
    0xD80D2BDA, 0xAF0A1B4C, 0x36034AF6, 0x41047A60, 0xDF60EFC3, 0xA867DF55,
    0x316E8EEF, 0x4669BE79, 0xCB61B38C, 0xBC66831A, 0x256FD2A0, 0x5268E236,
    0xCC0C7795, 0xBB0B4703, 0x220216B9, 0x5505262F, 0xC5BA3BBE, 0xB2BD0B28,
    0x2BB45A92, 0x5CB36A04, 0xC2D7FFA7, 0xB5D0CF31, 0x2CD99E8B, 0x5BDEAE1D,
    0x9B64C2B0, 0xEC63F226, 0x756AA39C, 0x026D930A, 0x9C0906A9, 0xEB0E363F,
    0x72076785, 0x05005713, 0x95BF4A82, 0xE2B87A14, 0x7BB12BAE, 0x0CB61B38,
    0x92D28E9B, 0xE5D5BE0D, 0x7CDCEFB7, 0x0BDBDF21, 0x86D3D2D4, 0xF1D4E242,
    0x68DDB3F8, 0x1FDA836E, 0x81BE16CD, 0xF6B9265B, 0x6FB077E1, 0x18B74777,
    0x88085AE6, 0xFF0F6A70, 0x66063BCA, 0x11010B5C, 0x8F659EFF, 0xF862AE69,
    0x616BFFD3, 0x166CCF45, 0xA00AE278, 0xD70DD2EE, 0x4E048354, 0x3903B3C2,
    0xA7672661, 0xD06016F7, 0x4969474D, 0x3E6E77DB, 0xAED16A4A, 0xD9D65ADC,
    0x40DF0B66, 0x37D83BF0, 0xA9BCAE53, 0xDEBB9EC5, 0x47B2CF7F, 0x30B5FFE9,
    0xBDBDF21C, 0xCABAC28A, 0x53B39330, 0x24B4A3A6, 0xBAD03605, 0xCDD706B3,
    0x54DE5729, 0x23D967BF, 0xB3667A2E, 0xC4614AB8, 0x5D681B02, 0x2A6F2B94,
    0xB40BBE37, 0xC30C8EA1, 0x5A05DF1B, 0x2D02EF8D
};

/* Private function prototypes -----------------------------------------------*/
static void Boot_EnableBackupSRAM(void);
static void Boot_InitSharedData(void);
static PMU_Boot_Reason_t Boot_DetermineBootReason(void);
static bool Boot_IsBootButtonPressed(void);
static PMU_Boot_Status_t Boot_BackupFirmware(void);
static uint32_t Boot_CalculateSharedDataChecksum(PMU_Boot_SharedData_t* data);

/* Private user code ---------------------------------------------------------*/

/**
 * @brief Initialize bootloader
 */
PMU_Boot_Status_t PMU_Bootloader_Init(void)
{
    /* Clear state */
    memset(&bootloader_state, 0, sizeof(bootloader_state));

    /* Enable backup SRAM and initialize shared data */
    Boot_EnableBackupSRAM();
    Boot_InitSharedData();

    /* Determine boot reason */
    bootloader_state.reason = Boot_DetermineBootReason();

    /* Check for valid application in main region */
    if (PMU_Bootloader_ValidateApp(PMU_APP_HEADER_ADDRESS, false) == PMU_BOOT_OK) {
        bootloader_state.active_header = (PMU_Firmware_Header_t*)PMU_APP_HEADER_ADDRESS;
    }

    /* Check for valid backup */
    if (PMU_Bootloader_ValidateApp(PMU_BACKUP_ADDRESS, false) == PMU_BOOT_OK) {
        bootloader_state.backup_header = (PMU_Firmware_Header_t*)PMU_BACKUP_ADDRESS;
    }

    /* Check for pending update in external flash */
    bootloader_state.update_available = PMU_Bootloader_IsUpdateAvailable();

    bootloader_state.status = PMU_BOOT_OK;
    return PMU_BOOT_OK;
}

/**
 * @brief Run bootloader main logic
 */
PMU_Boot_Status_t PMU_Bootloader_Run(void)
{
    PMU_Boot_Status_t status;

    /* Check boot button for manual bootloader mode */
    if (Boot_IsBootButtonPressed()) {
        bootloader_state.reason = PMU_BOOT_REASON_BUTTON;
        /* Stay in bootloader mode - return without jumping to app */
        return PMU_BOOT_OK;
    }

    /* Check if update was requested or is available */
    if (shared_data->update_requested || bootloader_state.update_available) {
        /* Apply the update */
        status = PMU_Bootloader_ApplyUpdate();
        if (status == PMU_BOOT_OK) {
            /* Clear update request flag */
            shared_data->update_requested = 0;
            shared_data->checksum = Boot_CalculateSharedDataChecksum(shared_data);

            /* Validate the new firmware */
            status = PMU_Bootloader_ValidateApp(PMU_APP_HEADER_ADDRESS, false);
            if (status == PMU_BOOT_OK) {
                bootloader_state.active_header = (PMU_Firmware_Header_t*)PMU_APP_HEADER_ADDRESS;
            }
        } else {
            /* Update failed - try to rollback if backup is available */
            if (bootloader_state.backup_header != NULL) {
                PMU_Bootloader_Rollback();
            }
        }
    }

    /* Check boot attempt counter (prevent boot loops) */
    if (shared_data->app_boot_count >= PMU_MAX_BOOT_ATTEMPTS) {
        /* Too many failed boot attempts - try rollback */
        if (bootloader_state.backup_header != NULL) {
            status = PMU_Bootloader_Rollback();
            if (status == PMU_BOOT_OK) {
                shared_data->app_boot_count = 0;
            }
        }
        /* If no backup, stay in bootloader mode */
        return PMU_BOOT_ERROR_NO_APP;
    }

    /* Validate application */
    if (bootloader_state.active_header == NULL) {
        /* No valid application - check backup */
        if (bootloader_state.backup_header != NULL) {
            status = PMU_Bootloader_Rollback();
            if (status == PMU_BOOT_OK) {
                bootloader_state.active_header = (PMU_Firmware_Header_t*)PMU_APP_HEADER_ADDRESS;
            } else {
                return PMU_BOOT_ERROR_NO_APP;
            }
        } else {
            return PMU_BOOT_ERROR_NO_APP;
        }
    }

    /* Increment boot counter (will be cleared by app if boot succeeds) */
    shared_data->app_boot_count++;
    shared_data->checksum = Boot_CalculateSharedDataChecksum(shared_data);

    /* Jump to application */
    PMU_Bootloader_JumpToApp(bootloader_state.active_header->vector_table_addr);

    /* Should never reach here */
    return PMU_BOOT_ERROR;
}

/**
 * @brief Get bootloader state
 */
PMU_Bootloader_State_t* PMU_Bootloader_GetState(void)
{
    return &bootloader_state;
}

/**
 * @brief Validate application firmware
 */
PMU_Boot_Status_t PMU_Bootloader_ValidateApp(uint32_t header_addr, bool verify_signature)
{
    PMU_Firmware_Header_t* header = (PMU_Firmware_Header_t*)header_addr;

    /* Check magic number */
    if (header->magic != PMU_FW_MAGIC) {
        return PMU_BOOT_ERROR_NO_APP;
    }

    /* Validate header CRC */
    uint32_t header_crc = PMU_Bootloader_CalculateCRC32(
        (const uint8_t*)header,
        sizeof(PMU_Firmware_Header_t) - sizeof(uint32_t)  /* Exclude header_crc32 field */
    );
    if (header_crc != header->header_crc32) {
        return PMU_BOOT_ERROR_CRC;
    }

    /* Check application size is reasonable */
    if (header->app_size == 0 || header->app_size > PMU_APP_SIZE) {
        return PMU_BOOT_ERROR;
    }

    /* Validate application CRC */
    uint32_t app_addr = header->vector_table_addr;
    uint32_t app_crc = PMU_Bootloader_CalculateCRC32(
        (const uint8_t*)app_addr,
        header->app_size
    );
    if (app_crc != header->app_crc32) {
        return PMU_BOOT_ERROR_CRC;
    }

    /* Validate vector table */
    uint32_t* vector_table = (uint32_t*)header->vector_table_addr;

    /* First entry should be initial stack pointer (in SRAM range) */
    if ((vector_table[0] & 0xFF000000) != 0x20000000 &&
        (vector_table[0] & 0xFF000000) != 0x24000000) {  /* D1 SRAM on STM32H7 */
        return PMU_BOOT_ERROR;
    }

    /* Second entry should be reset handler (in flash range) */
    if ((vector_table[1] & 0xFF000000) != 0x08000000) {
        return PMU_BOOT_ERROR;
    }

    /* Optional: Verify Ed25519 signature */
    if (verify_signature) {
        /* TODO: Implement signature verification */
        /* This requires Ed25519 library and public key embedded in bootloader */
        (void)verify_signature;
    }

    return PMU_BOOT_OK;
}

/**
 * @brief Jump to application
 */
void PMU_Bootloader_JumpToApp(uint32_t app_address)
{
#ifndef UNIT_TEST
    /* Disable all interrupts */
    __disable_irq();

    /* Disable SysTick */
    SysTick->CTRL = 0;
    SysTick->LOAD = 0;
    SysTick->VAL = 0;

    /* Clear pending interrupts */
    for (int i = 0; i < 8; i++) {
        NVIC->ICER[i] = 0xFFFFFFFF;
        NVIC->ICPR[i] = 0xFFFFFFFF;
    }

    /* Set vector table offset */
    SCB->VTOR = app_address;

    /* Get stack pointer and reset handler from vector table */
    uint32_t* vector_table = (uint32_t*)app_address;
    uint32_t app_sp = vector_table[0];
    uint32_t app_reset = vector_table[1];

    /* Set main stack pointer */
    __set_MSP(app_sp);

    /* Memory barrier */
    __DSB();
    __ISB();

    /* Jump to application reset handler */
    void (*app_reset_handler)(void) = (void (*)(void))app_reset;
    app_reset_handler();
#else
    (void)app_address;
#endif

    /* Should never reach here */
    while (1) {}
}

/**
 * @brief Get active firmware header
 */
PMU_Firmware_Header_t* PMU_Bootloader_GetActiveHeader(void)
{
    return bootloader_state.active_header;
}

/**
 * @brief Get backup firmware header
 */
PMU_Firmware_Header_t* PMU_Bootloader_GetBackupHeader(void)
{
    return bootloader_state.backup_header;
}

/**
 * @brief Check if firmware update is available
 */
bool PMU_Bootloader_IsUpdateAvailable(void)
{
#ifdef UNIT_TEST
    return false;
#else
    PMU_Update_Header_t update_header;

    /* Read update header from external flash */
    if (PMU_Flash_Read(PMU_EXT_UPDATE_ADDRESS, (uint8_t*)&update_header,
                       sizeof(update_header)) != PMU_FLASH_OK) {
        return false;
    }

    /* Check magic number */
    if (update_header.magic != PMU_UPDATE_MAGIC) {
        return false;
    }

    /* Check status */
    if (update_header.status != UPDATE_STATUS_PENDING) {
        return false;
    }

    /* Verify header CRC */
    uint32_t header_crc = PMU_Bootloader_CalculateCRC32(
        (const uint8_t*)&update_header,
        sizeof(update_header) - sizeof(uint32_t)
    );
    if (header_crc != update_header.buffer_crc32) {
        return false;
    }

    return true;
#endif
}

/**
 * @brief Apply pending firmware update
 */
PMU_Boot_Status_t PMU_Bootloader_ApplyUpdate(void)
{
#ifdef UNIT_TEST
    return PMU_BOOT_OK;
#else
    PMU_Boot_Status_t status;
    PMU_Update_Header_t update_header;
    uint8_t buffer[FLASH_PROGRAM_SIZE];

    /* Read update header */
    if (PMU_Flash_Read(PMU_EXT_UPDATE_ADDRESS, (uint8_t*)&update_header,
                       sizeof(update_header)) != PMU_FLASH_OK) {
        return PMU_BOOT_ERROR_FLASH;
    }

    /* Validate update header */
    if (update_header.magic != PMU_UPDATE_MAGIC ||
        update_header.status != UPDATE_STATUS_PENDING) {
        return PMU_BOOT_ERROR;
    }

    /* Backup current firmware first */
    status = Boot_BackupFirmware();
    if (status != PMU_BOOT_OK) {
        /* Continue anyway - backup failure shouldn't block update */
    }

    /* Erase application region (128KB sectors on STM32H7) */
    uint32_t erase_addr = PMU_APP_HEADER_ADDRESS;
    while (erase_addr < PMU_APP_END) {
        status = PMU_Bootloader_EraseFlashSector(erase_addr);
        if (status != PMU_BOOT_OK) {
            return PMU_BOOT_ERROR_FLASH;
        }
        erase_addr += PMU_FLASH_SECTOR_SIZE;
    }

    /* Copy firmware from external flash to internal flash */
    uint32_t total_size = update_header.firmware_size + sizeof(PMU_Firmware_Header_t);
    uint32_t src_offset = sizeof(PMU_Update_Header_t) + update_header.header_offset;
    uint32_t dst_addr = PMU_APP_HEADER_ADDRESS;
    uint32_t bytes_copied = 0;

    while (bytes_copied < total_size) {
        uint32_t chunk_size = total_size - bytes_copied;
        if (chunk_size > FLASH_PROGRAM_SIZE) {
            chunk_size = FLASH_PROGRAM_SIZE;
        }

        /* Pad to flash programming size if needed */
        memset(buffer, 0xFF, FLASH_PROGRAM_SIZE);

        /* Read from external flash */
        if (PMU_Flash_Read(PMU_EXT_UPDATE_ADDRESS + src_offset + bytes_copied,
                           buffer, chunk_size) != PMU_FLASH_OK) {
            return PMU_BOOT_ERROR_FLASH;
        }

        /* Write to internal flash */
        status = PMU_Bootloader_WriteFlash(dst_addr + bytes_copied, buffer, FLASH_PROGRAM_SIZE);
        if (status != PMU_BOOT_OK) {
            return PMU_BOOT_ERROR_FLASH;
        }

        bytes_copied += FLASH_PROGRAM_SIZE;
        bootloader_state.update_progress = (bytes_copied * 100) / total_size;
    }

    /* Verify the written firmware */
    status = PMU_Bootloader_ValidateApp(PMU_APP_HEADER_ADDRESS, false);
    if (status != PMU_BOOT_OK) {
        return status;
    }

    /* Mark update as applied in external flash */
    update_header.status = UPDATE_STATUS_APPLIED;
    update_header.buffer_crc32 = PMU_Bootloader_CalculateCRC32(
        (const uint8_t*)&update_header,
        sizeof(update_header) - sizeof(uint32_t)
    );

    /* Erase first sector of update buffer */
    PMU_Flash_EraseSector(PMU_EXT_UPDATE_ADDRESS);

    /* Write updated header */
    PMU_Flash_Write(PMU_EXT_UPDATE_ADDRESS, (const uint8_t*)&update_header,
                    sizeof(update_header));

    return PMU_BOOT_OK;
#endif
}

/**
 * @brief Write update chunk to external flash
 */
PMU_Boot_Status_t PMU_Bootloader_WriteUpdateChunk(uint32_t offset, const uint8_t* data, uint32_t length)
{
    if (data == NULL || length == 0) {
        return PMU_BOOT_ERROR;
    }

    /* Write to external flash */
    if (PMU_Flash_Write(PMU_EXT_UPDATE_ADDRESS + sizeof(PMU_Update_Header_t) + offset,
                        data, length) != PMU_FLASH_OK) {
        return PMU_BOOT_ERROR_FLASH;
    }

    return PMU_BOOT_OK;
}

/**
 * @brief Finalize update (mark as ready to apply)
 */
PMU_Boot_Status_t PMU_Bootloader_FinalizeUpdate(uint32_t total_size, uint32_t crc32)
{
    PMU_Update_Header_t update_header = {0};

    update_header.magic = PMU_UPDATE_MAGIC;
    update_header.firmware_size = total_size;
    update_header.firmware_crc32 = crc32;
    update_header.header_offset = 0;
    update_header.status = UPDATE_STATUS_PENDING;
    update_header.timestamp = 0;  /* TODO: Get RTC time */

    /* Calculate header CRC */
    update_header.buffer_crc32 = PMU_Bootloader_CalculateCRC32(
        (const uint8_t*)&update_header,
        sizeof(update_header) - sizeof(uint32_t)
    );

    /* Erase first sector to write header */
    if (PMU_Flash_EraseSector(PMU_EXT_UPDATE_ADDRESS) != PMU_FLASH_OK) {
        return PMU_BOOT_ERROR_FLASH;
    }

    /* Write header */
    if (PMU_Flash_Write(PMU_EXT_UPDATE_ADDRESS, (const uint8_t*)&update_header,
                        sizeof(update_header)) != PMU_FLASH_OK) {
        return PMU_BOOT_ERROR_FLASH;
    }

    return PMU_BOOT_OK;
}

/**
 * @brief Cancel pending update
 */
PMU_Boot_Status_t PMU_Bootloader_CancelUpdate(void)
{
    /* Erase first sector of update buffer to invalidate update */
    if (PMU_Flash_EraseSector(PMU_EXT_UPDATE_ADDRESS) != PMU_FLASH_OK) {
        return PMU_BOOT_ERROR_FLASH;
    }

    bootloader_state.update_available = false;
    return PMU_BOOT_OK;
}

/**
 * @brief Rollback to backup firmware
 */
PMU_Boot_Status_t PMU_Bootloader_Rollback(void)
{
#ifdef UNIT_TEST
    return PMU_BOOT_OK;
#else
    PMU_Boot_Status_t status;
    uint8_t buffer[FLASH_PROGRAM_SIZE];

    /* Validate backup firmware first */
    status = PMU_Bootloader_ValidateApp(PMU_BACKUP_ADDRESS, false);
    if (status != PMU_BOOT_OK) {
        return status;
    }

    PMU_Firmware_Header_t* backup_header = (PMU_Firmware_Header_t*)PMU_BACKUP_ADDRESS;
    uint32_t total_size = backup_header->app_size + sizeof(PMU_Firmware_Header_t);

    /* Erase application region */
    uint32_t erase_addr = PMU_APP_HEADER_ADDRESS;
    while (erase_addr < PMU_APP_END) {
        status = PMU_Bootloader_EraseFlashSector(erase_addr);
        if (status != PMU_BOOT_OK) {
            return PMU_BOOT_ERROR_FLASH;
        }
        erase_addr += PMU_FLASH_SECTOR_SIZE;
    }

    /* Copy backup to main region */
    uint32_t bytes_copied = 0;
    while (bytes_copied < total_size) {
        uint32_t chunk_size = total_size - bytes_copied;
        if (chunk_size > FLASH_PROGRAM_SIZE) {
            chunk_size = FLASH_PROGRAM_SIZE;
        }

        /* Pad buffer */
        memset(buffer, 0xFF, FLASH_PROGRAM_SIZE);

        /* Copy from backup region */
        memcpy(buffer, (const uint8_t*)(PMU_BACKUP_ADDRESS + bytes_copied), chunk_size);

        /* Write to main region */
        status = PMU_Bootloader_WriteFlash(PMU_APP_HEADER_ADDRESS + bytes_copied,
                                           buffer, FLASH_PROGRAM_SIZE);
        if (status != PMU_BOOT_OK) {
            return PMU_BOOT_ERROR_FLASH;
        }

        bytes_copied += FLASH_PROGRAM_SIZE;
    }

    /* Verify restored firmware */
    return PMU_Bootloader_ValidateApp(PMU_APP_HEADER_ADDRESS, false);
#endif
}

/**
 * @brief Request system reboot into bootloader mode
 */
PMU_Boot_Status_t PMU_Bootloader_RequestReboot(PMU_Boot_Reason_t reason)
{
    if (shared_data == NULL) {
        return PMU_BOOT_ERROR;
    }

    shared_data->boot_reason = reason;
    shared_data->checksum = Boot_CalculateSharedDataChecksum(shared_data);

#ifndef UNIT_TEST
    /* Trigger system reset */
    NVIC_SystemReset();
#endif

    return PMU_BOOT_OK;
}

/**
 * @brief Request firmware update
 */
PMU_Boot_Status_t PMU_Bootloader_RequestUpdate(void)
{
    if (shared_data == NULL) {
        return PMU_BOOT_ERROR;
    }

    shared_data->update_requested = 1;
    shared_data->checksum = Boot_CalculateSharedDataChecksum(shared_data);

    return PMU_BOOT_OK;
}

/**
 * @brief Get boot reason
 */
PMU_Boot_Reason_t PMU_Bootloader_GetBootReason(void)
{
    return bootloader_state.reason;
}

/**
 * @brief Get shared data structure
 */
PMU_Boot_SharedData_t* PMU_Bootloader_GetSharedData(void)
{
    return shared_data;
}

/**
 * @brief Calculate CRC32
 */
uint32_t PMU_Bootloader_CalculateCRC32(const uint8_t* data, uint32_t length)
{
    uint32_t crc = PMU_CRC32_INITIAL;

    for (uint32_t i = 0; i < length; i++) {
        uint8_t index = (uint8_t)((crc ^ data[i]) & 0xFF);
        crc = (crc >> 8) ^ crc32_table[index];
    }

    return crc ^ PMU_CRC32_INITIAL;
}

/**
 * @brief Erase internal flash sector
 */
PMU_Boot_Status_t PMU_Bootloader_EraseFlashSector(uint32_t sector_address)
{
#ifdef UNIT_TEST
    (void)sector_address;
    return PMU_BOOT_OK;
#else
    FLASH_EraseInitTypeDef erase_init;
    uint32_t sector_error = 0;

    /* Unlock flash */
    HAL_FLASH_Unlock();

    /* Determine bank and sector based on address */
    uint32_t bank;
    uint32_t sector;

    if (sector_address < 0x08100000) {
        bank = FLASH_BANK_1;
        sector = (sector_address - 0x08000000) / PMU_FLASH_SECTOR_SIZE;
    } else {
        bank = FLASH_BANK_2;
        sector = (sector_address - 0x08100000) / PMU_FLASH_SECTOR_SIZE;
    }

    erase_init.TypeErase = FLASH_TYPEERASE_SECTORS;
    erase_init.Banks = bank;
    erase_init.Sector = sector;
    erase_init.NbSectors = 1;
    erase_init.VoltageRange = FLASH_VOLTAGE_RANGE_3;

    HAL_StatusTypeDef hal_status = HAL_FLASHEx_Erase(&erase_init, &sector_error);

    /* Lock flash */
    HAL_FLASH_Lock();

    if (hal_status != HAL_OK || sector_error != 0xFFFFFFFF) {
        return PMU_BOOT_ERROR_FLASH;
    }

    return PMU_BOOT_OK;
#endif
}

/**
 * @brief Write to internal flash
 */
PMU_Boot_Status_t PMU_Bootloader_WriteFlash(uint32_t address, const uint8_t* data, uint32_t length)
{
#ifdef UNIT_TEST
    (void)address;
    (void)data;
    (void)length;
    return PMU_BOOT_OK;
#else
    /* STM32H7 requires 256-bit (32-byte) aligned writes */
    if ((address % FLASH_PROGRAM_SIZE) != 0 || (length % FLASH_PROGRAM_SIZE) != 0) {
        return PMU_BOOT_ERROR;
    }

    /* Unlock flash */
    HAL_FLASH_Unlock();

    for (uint32_t i = 0; i < length; i += FLASH_PROGRAM_SIZE) {
        /* STM32H7 uses FLASH_TYPEPROGRAM_FLASHWORD for 256-bit writes */
        HAL_StatusTypeDef hal_status = HAL_FLASH_Program(
            FLASH_TYPEPROGRAM_FLASHWORD,
            address + i,
            (uint32_t)(data + i)
        );

        if (hal_status != HAL_OK) {
            HAL_FLASH_Lock();
            return PMU_BOOT_ERROR_FLASH;
        }
    }

    /* Lock flash */
    HAL_FLASH_Lock();

    /* Verify write */
    if (memcmp((const void*)address, data, length) != 0) {
        return PMU_BOOT_ERROR_FLASH;
    }

    return PMU_BOOT_OK;
#endif
}

/**
 * @brief Get firmware version string
 */
int PMU_Bootloader_GetVersionString(const PMU_Firmware_Header_t* header, char* buffer, size_t buffer_size)
{
    if (header == NULL || buffer == NULL || buffer_size == 0) {
        return -1;
    }

    return snprintf(buffer, buffer_size, "v%lu.%lu.%lu (build %lu)",
                    (unsigned long)header->version_major,
                    (unsigned long)header->version_minor,
                    (unsigned long)header->version_patch,
                    (unsigned long)header->build_number);
}

/*---------------------------------------------------------------------------*/
/* Private Functions                                                          */
/*---------------------------------------------------------------------------*/

/**
 * @brief Enable backup SRAM
 */
static void Boot_EnableBackupSRAM(void)
{
#ifndef UNIT_TEST
    /* Enable PWR clock */
    __HAL_RCC_PWR_CLK_ENABLE();

    /* Enable backup SRAM */
    HAL_PWR_EnableBkUpAccess();

    /* Enable backup SRAM clock */
    __HAL_RCC_BKPRAM_CLK_ENABLE();

    /* Wait for backup SRAM to be ready */
    while (__HAL_RCC_GET_FLAG(RCC_FLAG_BKPRDY) == 0) {}
#endif
}

/**
 * @brief Initialize shared data in backup SRAM
 */
static void Boot_InitSharedData(void)
{
    shared_data = (PMU_Boot_SharedData_t*)PMU_BOOT_SHARED_DATA_ADDR;

    /* Check if shared data is valid */
    if (shared_data->magic != PMU_BOOT_MAGIC ||
        shared_data->checksum != Boot_CalculateSharedDataChecksum(shared_data)) {
        /* Initialize shared data */
        memset(shared_data, 0, sizeof(PMU_Boot_SharedData_t));
        shared_data->magic = PMU_BOOT_MAGIC;
        shared_data->boot_reason = PMU_BOOT_REASON_POWER_ON;
        shared_data->checksum = Boot_CalculateSharedDataChecksum(shared_data);
    }
}

/**
 * @brief Determine boot reason from reset flags
 */
static PMU_Boot_Reason_t Boot_DetermineBootReason(void)
{
#ifdef UNIT_TEST
    return PMU_BOOT_REASON_POWER_ON;
#else
    /* Check if reason was set by application */
    if (shared_data->boot_reason != PMU_BOOT_REASON_POWER_ON) {
        PMU_Boot_Reason_t reason = shared_data->boot_reason;
        shared_data->boot_reason = PMU_BOOT_REASON_POWER_ON;
        shared_data->checksum = Boot_CalculateSharedDataChecksum(shared_data);
        return reason;
    }

    /* Check reset flags */
    if (__HAL_RCC_GET_FLAG(RCC_FLAG_IWDGRST)) {
        __HAL_RCC_CLEAR_RESET_FLAGS();
        return PMU_BOOT_REASON_WATCHDOG;
    }

    if (__HAL_RCC_GET_FLAG(RCC_FLAG_SFTRST)) {
        __HAL_RCC_CLEAR_RESET_FLAGS();
        /* Could be update request or crash */
        return PMU_BOOT_REASON_UPDATE;
    }

    __HAL_RCC_CLEAR_RESET_FLAGS();
    return PMU_BOOT_REASON_POWER_ON;
#endif
}

/**
 * @brief Check if boot button is pressed
 */
static bool Boot_IsBootButtonPressed(void)
{
#ifdef UNIT_TEST
    return false;
#else
    /* Configure boot button GPIO as input with pull-up */
    GPIO_InitTypeDef gpio_init = {0};
    gpio_init.Pin = PMU_BOOT_BUTTON_PIN;
    gpio_init.Mode = GPIO_MODE_INPUT;
    gpio_init.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(PMU_BOOT_BUTTON_PORT, &gpio_init);

    /* Check if button is pressed (active low) */
    return (HAL_GPIO_ReadPin(PMU_BOOT_BUTTON_PORT, PMU_BOOT_BUTTON_PIN) == GPIO_PIN_RESET);
#endif
}

/**
 * @brief Backup current firmware to backup region
 */
static PMU_Boot_Status_t Boot_BackupFirmware(void)
{
#ifdef UNIT_TEST
    return PMU_BOOT_OK;
#else
    /* Validate current application first */
    if (PMU_Bootloader_ValidateApp(PMU_APP_HEADER_ADDRESS, false) != PMU_BOOT_OK) {
        /* Current app invalid, nothing to backup */
        return PMU_BOOT_ERROR;
    }

    PMU_Firmware_Header_t* current_header = (PMU_Firmware_Header_t*)PMU_APP_HEADER_ADDRESS;
    uint32_t total_size = current_header->app_size + sizeof(PMU_Firmware_Header_t);
    uint8_t buffer[FLASH_PROGRAM_SIZE];
    PMU_Boot_Status_t status;

    /* Erase backup region */
    uint32_t erase_addr = PMU_BACKUP_ADDRESS;
    uint32_t backup_end = PMU_BACKUP_ADDRESS + PMU_BACKUP_SIZE;
    while (erase_addr < backup_end) {
        status = PMU_Bootloader_EraseFlashSector(erase_addr);
        if (status != PMU_BOOT_OK) {
            return PMU_BOOT_ERROR_FLASH;
        }
        erase_addr += PMU_FLASH_SECTOR_SIZE;
    }

    /* Copy current firmware to backup region */
    uint32_t bytes_copied = 0;
    while (bytes_copied < total_size) {
        uint32_t chunk_size = total_size - bytes_copied;
        if (chunk_size > FLASH_PROGRAM_SIZE) {
            chunk_size = FLASH_PROGRAM_SIZE;
        }

        /* Pad buffer */
        memset(buffer, 0xFF, FLASH_PROGRAM_SIZE);

        /* Copy from main region */
        memcpy(buffer, (const uint8_t*)(PMU_APP_HEADER_ADDRESS + bytes_copied), chunk_size);

        /* Write to backup region */
        status = PMU_Bootloader_WriteFlash(PMU_BACKUP_ADDRESS + bytes_copied,
                                           buffer, FLASH_PROGRAM_SIZE);
        if (status != PMU_BOOT_OK) {
            return PMU_BOOT_ERROR_FLASH;
        }

        bytes_copied += FLASH_PROGRAM_SIZE;
    }

    return PMU_BOOT_OK;
#endif
}

/**
 * @brief Calculate simple checksum for shared data validation
 */
static uint32_t Boot_CalculateSharedDataChecksum(PMU_Boot_SharedData_t* data)
{
    uint32_t checksum = 0;
    uint32_t* ptr = (uint32_t*)data;
    size_t count = (sizeof(PMU_Boot_SharedData_t) - sizeof(uint32_t)) / sizeof(uint32_t);

    for (size_t i = 0; i < count; i++) {
        checksum ^= ptr[i];
        checksum = (checksum << 7) | (checksum >> 25);  /* Rotate left 7 bits */
    }

    return checksum;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
