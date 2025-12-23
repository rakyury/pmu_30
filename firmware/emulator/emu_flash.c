/**
 ******************************************************************************
 * @file           : emu_flash.c
 * @brief          : Emulated Flash Driver for PMU-30 Emulator
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * This module emulates W25Q512JV SPI Flash and STM32H7 internal flash
 * using files for persistent storage.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_flash.h"
#include "pmu_bootloader.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Only compile for emulator */
#ifdef PMU_EMULATOR

/* Private define ------------------------------------------------------------*/
#define EMU_FLASH_FILE          "emu_flash.bin"
#define EMU_INTERNAL_FLASH_FILE "emu_internal_flash.bin"
#define EMU_FLASH_SIZE          (64 * 1024 * 1024)  /* 64 MB external */
#define EMU_INTERNAL_SIZE       (2 * 1024 * 1024)   /* 2 MB internal */

/* Private variables ---------------------------------------------------------*/
static PMU_Flash_Stats_t flash_stats = {0};
static bool flash_initialized = false;

/* Private function prototypes -----------------------------------------------*/
static void Flash_EnsureFileExists(const char* filename, size_t size);
static FILE* Flash_OpenFile(const char* filename, const char* mode);

/* ==========================================================================
 * External Flash (W25Q512JV) Emulation - pmu_flash.h interface
 * ========================================================================== */

/**
 * @brief Initialize flash driver
 */
PMU_Flash_Status_t PMU_Flash_Init(void)
{
    Flash_EnsureFileExists(EMU_FLASH_FILE, EMU_FLASH_SIZE);
    flash_initialized = true;
    printf("[EMU_FLASH] External flash initialized (file: %s)\n", EMU_FLASH_FILE);
    return PMU_FLASH_OK;
}

/**
 * @brief Get flash information
 */
PMU_Flash_Status_t PMU_Flash_GetInfo(PMU_Flash_Info_t* info)
{
    if (!info) return PMU_FLASH_ERROR;

    info->manufacturer_id = 0xEF;  /* Winbond */
    info->memory_type = 0x40;      /* W25Q series */
    info->capacity = 0x20;         /* 512 Mbit */
    info->jedec_id = W25Q512_JEDEC_ID;
    info->unique_id = 0x454D554C41544F52ULL;  /* "EMULATOR" */
    info->total_size = W25Q_FLASH_SIZE;

    return PMU_FLASH_OK;
}

/**
 * @brief Read data from flash
 */
PMU_Flash_Status_t PMU_Flash_Read(uint32_t address, uint8_t* data, uint32_t length)
{
    if (!data || address + length > EMU_FLASH_SIZE) {
        return PMU_FLASH_ERROR;
    }

    FILE* f = Flash_OpenFile(EMU_FLASH_FILE, "rb");
    if (!f) return PMU_FLASH_ERROR;

    fseek(f, address, SEEK_SET);
    size_t read = fread(data, 1, length, f);
    fclose(f);

    if (read != length) {
        /* Fill unread portion with 0xFF (erased state) */
        memset(data + read, 0xFF, length - read);
    }

    flash_stats.read_count++;
    flash_stats.bytes_read += length;

    return PMU_FLASH_OK;
}

/**
 * @brief Write data to flash
 */
PMU_Flash_Status_t PMU_Flash_Write(uint32_t address, const uint8_t* data, uint32_t length)
{
    if (!data || address + length > EMU_FLASH_SIZE) {
        return PMU_FLASH_ERROR;
    }

    /* Read existing data */
    uint8_t* buffer = (uint8_t*)malloc(length);
    if (!buffer) return PMU_FLASH_ERROR;

    FILE* f = Flash_OpenFile(EMU_FLASH_FILE, "r+b");
    if (!f) {
        free(buffer);
        return PMU_FLASH_ERROR;
    }

    /* Read current content */
    fseek(f, address, SEEK_SET);
    fread(buffer, 1, length, f);

    /* Flash write: can only change 1->0, simulate by AND operation */
    for (uint32_t i = 0; i < length; i++) {
        buffer[i] &= data[i];
    }

    /* Write back */
    fseek(f, address, SEEK_SET);
    fwrite(buffer, 1, length, f);
    fclose(f);
    free(buffer);

    flash_stats.write_count++;
    flash_stats.bytes_written += length;

    return PMU_FLASH_OK;
}

/**
 * @brief Erase sector (4KB)
 */
PMU_Flash_Status_t PMU_Flash_EraseSector(uint32_t address)
{
    /* Align to sector boundary */
    address = (address / W25Q_SECTOR_SIZE) * W25Q_SECTOR_SIZE;

    if (address + W25Q_SECTOR_SIZE > EMU_FLASH_SIZE) {
        return PMU_FLASH_ERROR;
    }

    FILE* f = Flash_OpenFile(EMU_FLASH_FILE, "r+b");
    if (!f) return PMU_FLASH_ERROR;

    /* Fill sector with 0xFF (erased state) */
    uint8_t erase_buffer[W25Q_SECTOR_SIZE];
    memset(erase_buffer, 0xFF, W25Q_SECTOR_SIZE);

    fseek(f, address, SEEK_SET);
    fwrite(erase_buffer, 1, W25Q_SECTOR_SIZE, f);
    fclose(f);

    flash_stats.erase_count++;

    return PMU_FLASH_OK;
}

/**
 * @brief Erase 64KB block
 */
PMU_Flash_Status_t PMU_Flash_EraseBlock64K(uint32_t address)
{
    /* Align to block boundary */
    address = (address / W25Q_BLOCK_SIZE_64K) * W25Q_BLOCK_SIZE_64K;

    if (address + W25Q_BLOCK_SIZE_64K > EMU_FLASH_SIZE) {
        return PMU_FLASH_ERROR;
    }

    FILE* f = Flash_OpenFile(EMU_FLASH_FILE, "r+b");
    if (!f) return PMU_FLASH_ERROR;

    /* Fill block with 0xFF */
    uint8_t* erase_buffer = (uint8_t*)malloc(W25Q_BLOCK_SIZE_64K);
    if (!erase_buffer) {
        fclose(f);
        return PMU_FLASH_ERROR;
    }

    memset(erase_buffer, 0xFF, W25Q_BLOCK_SIZE_64K);
    fseek(f, address, SEEK_SET);
    fwrite(erase_buffer, 1, W25Q_BLOCK_SIZE_64K, f);
    fclose(f);
    free(erase_buffer);

    flash_stats.erase_count++;

    return PMU_FLASH_OK;
}

/**
 * @brief Erase entire chip
 */
PMU_Flash_Status_t PMU_Flash_EraseChip(void)
{
    FILE* f = Flash_OpenFile(EMU_FLASH_FILE, "wb");
    if (!f) return PMU_FLASH_ERROR;

    /* Write 0xFF for entire flash */
    uint8_t erase_buffer[4096];
    memset(erase_buffer, 0xFF, sizeof(erase_buffer));

    for (size_t i = 0; i < EMU_FLASH_SIZE; i += sizeof(erase_buffer)) {
        fwrite(erase_buffer, 1, sizeof(erase_buffer), f);
    }

    fclose(f);

    flash_stats.erase_count++;
    printf("[EMU_FLASH] Chip erased\n");

    return PMU_FLASH_OK;
}

/**
 * @brief Check if flash is busy
 */
bool PMU_Flash_IsBusy(void)
{
    return false;  /* Emulator is never busy */
}

/**
 * @brief Wait until flash is ready
 */
PMU_Flash_Status_t PMU_Flash_WaitReady(uint32_t timeout_ms)
{
    (void)timeout_ms;
    return PMU_FLASH_OK;
}

/**
 * @brief Enable write operations
 */
PMU_Flash_Status_t PMU_Flash_WriteEnable(void)
{
    return PMU_FLASH_OK;
}

/**
 * @brief Disable write operations
 */
PMU_Flash_Status_t PMU_Flash_WriteDisable(void)
{
    return PMU_FLASH_OK;
}

/**
 * @brief Read status register
 */
PMU_Flash_Status_t PMU_Flash_ReadStatus(uint8_t reg_num, uint8_t* status)
{
    if (!status) return PMU_FLASH_ERROR;
    *status = 0x00;  /* Ready, write disabled */
    (void)reg_num;
    return PMU_FLASH_OK;
}

/**
 * @brief Power down flash
 */
PMU_Flash_Status_t PMU_Flash_PowerDown(void)
{
    return PMU_FLASH_OK;
}

/**
 * @brief Wake up flash
 */
PMU_Flash_Status_t PMU_Flash_WakeUp(void)
{
    return PMU_FLASH_OK;
}

/**
 * @brief Reset flash device
 */
PMU_Flash_Status_t PMU_Flash_Reset(void)
{
    return PMU_FLASH_OK;
}

/**
 * @brief Get flash statistics
 */
PMU_Flash_Stats_t* PMU_Flash_GetStats(void)
{
    return &flash_stats;
}

/**
 * @brief Clear flash statistics
 */
void PMU_Flash_ClearStats(void)
{
    memset(&flash_stats, 0, sizeof(flash_stats));
}

/* ==========================================================================
 * Internal Flash (STM32H7) Emulation - pmu_bootloader.h interface
 * ========================================================================== */

/**
 * @brief Erase internal flash sector
 */
PMU_Boot_Status_t PMU_Bootloader_EraseFlashSector(uint32_t address)
{
    Flash_EnsureFileExists(EMU_INTERNAL_FLASH_FILE, EMU_INTERNAL_SIZE);

    /* STM32H7 has 128KB sectors */
    uint32_t sector_size = 128 * 1024;
    address = (address / sector_size) * sector_size;

    /* Map internal flash address (0x08000000+) to file offset */
    uint32_t offset = address;
    if (address >= 0x08000000) {
        offset = address - 0x08000000;
    }

    if (offset + sector_size > EMU_INTERNAL_SIZE) {
        return PMU_BOOT_ERROR_FLASH;
    }

    FILE* f = Flash_OpenFile(EMU_INTERNAL_FLASH_FILE, "r+b");
    if (!f) return PMU_BOOT_ERROR_FLASH;

    /* Fill sector with 0xFF */
    uint8_t* erase_buffer = (uint8_t*)malloc(sector_size);
    if (!erase_buffer) {
        fclose(f);
        return PMU_BOOT_ERROR_FLASH;
    }

    memset(erase_buffer, 0xFF, sector_size);
    fseek(f, offset, SEEK_SET);
    fwrite(erase_buffer, 1, sector_size, f);
    fclose(f);
    free(erase_buffer);

    return PMU_BOOT_OK;
}

/**
 * @brief Write to internal flash
 */
PMU_Boot_Status_t PMU_Bootloader_WriteFlash(uint32_t address, const uint8_t* data, uint32_t length)
{
    Flash_EnsureFileExists(EMU_INTERNAL_FLASH_FILE, EMU_INTERNAL_SIZE);

    /* Map internal flash address to file offset */
    uint32_t offset = address;
    if (address >= 0x08000000) {
        offset = address - 0x08000000;
    }

    if (offset + length > EMU_INTERNAL_SIZE) {
        return PMU_BOOT_ERROR_FLASH;
    }

    FILE* f = Flash_OpenFile(EMU_INTERNAL_FLASH_FILE, "r+b");
    if (!f) return PMU_BOOT_ERROR_FLASH;

    /* Read current content */
    uint8_t* buffer = (uint8_t*)malloc(length);
    if (!buffer) {
        fclose(f);
        return PMU_BOOT_ERROR_FLASH;
    }

    fseek(f, offset, SEEK_SET);
    fread(buffer, 1, length, f);

    /* Flash write: can only change 1->0 */
    for (uint32_t i = 0; i < length; i++) {
        buffer[i] &= data[i];
    }

    /* Write back */
    fseek(f, offset, SEEK_SET);
    fwrite(buffer, 1, length, f);
    fclose(f);
    free(buffer);

    return PMU_BOOT_OK;
}

/**
 * @brief Read from internal flash
 */
PMU_Boot_Status_t PMU_Bootloader_ReadFlash(uint32_t address, uint8_t* data, uint32_t length)
{
    Flash_EnsureFileExists(EMU_INTERNAL_FLASH_FILE, EMU_INTERNAL_SIZE);

    /* Map internal flash address to file offset */
    uint32_t offset = address;
    if (address >= 0x08000000) {
        offset = address - 0x08000000;
    }

    if (offset + length > EMU_INTERNAL_SIZE) {
        return PMU_BOOT_ERROR_FLASH;
    }

    FILE* f = Flash_OpenFile(EMU_INTERNAL_FLASH_FILE, "rb");
    if (!f) return PMU_BOOT_ERROR_FLASH;

    fseek(f, offset, SEEK_SET);
    size_t read = fread(data, 1, length, f);
    fclose(f);

    if (read != length) {
        memset(data + read, 0xFF, length - read);
    }

    return PMU_BOOT_OK;
}

/* ==========================================================================
 * Private Functions
 * ========================================================================== */

/**
 * @brief Ensure flash file exists with correct size
 */
static void Flash_EnsureFileExists(const char* filename, size_t size)
{
    FILE* f = fopen(filename, "rb");
    if (f) {
        /* Check size */
        fseek(f, 0, SEEK_END);
        size_t current_size = ftell(f);
        fclose(f);

        if (current_size >= size) {
            return;  /* File exists and is correct size */
        }
    }

    /* Create new file filled with 0xFF */
    f = fopen(filename, "wb");
    if (!f) {
        printf("[EMU_FLASH] ERROR: Cannot create %s\n", filename);
        return;
    }

    uint8_t buffer[4096];
    memset(buffer, 0xFF, sizeof(buffer));

    for (size_t i = 0; i < size; i += sizeof(buffer)) {
        size_t chunk = (size - i < sizeof(buffer)) ? (size - i) : sizeof(buffer);
        fwrite(buffer, 1, chunk, f);
    }

    fclose(f);
    printf("[EMU_FLASH] Created %s (%zu bytes)\n", filename, size);
}

/**
 * @brief Open flash file
 */
static FILE* Flash_OpenFile(const char* filename, const char* mode)
{
    FILE* f = fopen(filename, mode);
    if (!f) {
        /* Try to create if opening for read */
        if (strcmp(filename, EMU_FLASH_FILE) == 0) {
            Flash_EnsureFileExists(EMU_FLASH_FILE, EMU_FLASH_SIZE);
        } else {
            Flash_EnsureFileExists(EMU_INTERNAL_FLASH_FILE, EMU_INTERNAL_SIZE);
        }
        f = fopen(filename, mode);
    }
    return f;
}

#endif /* PMU_EMULATOR */

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
