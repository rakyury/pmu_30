/**
 ******************************************************************************
 * @file           : pmu_config_storage.c
 * @brief          : Configuration Storage Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * Implements persistent storage for system configuration and JSON data.
 * Uses wear leveling and CRC validation for reliability.
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_config_storage.h"
#include "pmu_flash.h"
#include "pmu_bootloader.h"
#include <string.h>
#include <stdio.h>

/* Private typedef -----------------------------------------------------------*/

/**
 * @brief JSON slot header
 */
typedef struct __attribute__((packed)) {
    uint32_t magic;               /* PMU_JSON_MAGIC */
    uint32_t json_size;           /* Size of JSON data */
    uint32_t json_crc32;          /* CRC32 of JSON data */
    uint32_t write_count;         /* Slot write counter */
    uint32_t timestamp;           /* Write timestamp */
    uint32_t header_crc32;        /* CRC32 of this header */
} PMU_JSON_Header_t;

/* Private define ------------------------------------------------------------*/
#define FLASH_PROGRAM_SIZE        32      /* STM32H7 flash program size */
#define JSON_HEADER_SIZE          sizeof(PMU_JSON_Header_t)

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_System_Config_t system_config;
static PMU_Storage_Stats_t storage_stats;
static bool storage_initialized = false;
static uint8_t active_json_slot = 0;

/* CRC32 lookup table */
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
static void Storage_InitDefaults(void);
static PMU_Storage_Status_t Storage_LoadFromInternal(void);
static PMU_Storage_Status_t Storage_SaveToInternal(void);
static bool Storage_ValidateJSONSlot(uint8_t slot);
static uint32_t Storage_GetJSONSlotAddress(uint8_t slot);
static void Storage_SelectActiveJSONSlot(void);

/* Private user code ---------------------------------------------------------*/

/**
 * @brief Initialize configuration storage
 */
PMU_Storage_Status_t PMU_Storage_Init(void)
{
    PMU_Storage_Status_t status;

    /* Clear statistics */
    memset(&storage_stats, 0, sizeof(storage_stats));

    /* Try to load system configuration from internal flash */
    status = Storage_LoadFromInternal();

    if (status != PMU_STORAGE_OK) {
        /* No valid configuration found - initialize defaults */
        Storage_InitDefaults();

        /* Save defaults to internal flash */
        status = Storage_SaveToInternal();
        if (status != PMU_STORAGE_OK) {
            /* Failed to save defaults - continue anyway with RAM config */
        }
    }

    /* Select active JSON slot in external flash */
    Storage_SelectActiveJSONSlot();

    /* Increment power-on counter */
    PMU_Storage_IncrementPowerOn();

    storage_initialized = true;
    return PMU_STORAGE_OK;
}

/**
 * @brief Check if storage contains valid configuration
 */
bool PMU_Storage_HasValidConfig(void)
{
    PMU_Config_Header_t* header = (PMU_Config_Header_t*)PMU_CONFIG_INT_ADDRESS;

    if (header->magic != PMU_CONFIG_MAGIC) {
        return false;
    }

    /* Verify header CRC */
    uint32_t header_crc = PMU_Storage_CalculateCRC32(
        (const uint8_t*)header,
        sizeof(PMU_Config_Header_t) - sizeof(uint32_t)
    );

    return (header_crc == header->header_crc32);
}

/**
 * @brief Load system configuration from internal flash
 */
PMU_Storage_Status_t PMU_Storage_LoadSystemConfig(PMU_System_Config_t* config)
{
    if (config == NULL) {
        return PMU_STORAGE_ERROR;
    }

    if (!storage_initialized) {
        return PMU_STORAGE_ERROR;
    }

    memcpy(config, &system_config, sizeof(PMU_System_Config_t));
    storage_stats.read_count++;

    return PMU_STORAGE_OK;
}

/**
 * @brief Save system configuration to internal flash
 */
PMU_Storage_Status_t PMU_Storage_SaveSystemConfig(const PMU_System_Config_t* config)
{
    if (config == NULL) {
        return PMU_STORAGE_ERROR;
    }

    /* Copy to RAM first */
    memcpy(&system_config, config, sizeof(PMU_System_Config_t));

    /* Save to internal flash */
    PMU_Storage_Status_t status = Storage_SaveToInternal();

    if (status == PMU_STORAGE_OK) {
        storage_stats.write_count++;
        storage_stats.internal_writes++;
    }

    return status;
}

/**
 * @brief Reset system configuration to defaults
 */
PMU_Storage_Status_t PMU_Storage_ResetSystemConfig(void)
{
    Storage_InitDefaults();
    return Storage_SaveToInternal();
}

/**
 * @brief Get pointer to current system configuration
 */
const PMU_System_Config_t* PMU_Storage_GetSystemConfig(void)
{
    return &system_config;
}

/**
 * @brief Load JSON configuration from external flash
 */
PMU_Storage_Status_t PMU_Storage_LoadJSON(char* buffer, uint32_t buffer_size, uint32_t* actual_size)
{
    if (buffer == NULL || actual_size == NULL) {
        return PMU_STORAGE_ERROR;
    }

    PMU_JSON_Header_t header;
    uint32_t slot_addr = Storage_GetJSONSlotAddress(active_json_slot);

    /* Read header */
    if (PMU_Flash_Read(slot_addr, (uint8_t*)&header, sizeof(header)) != PMU_FLASH_OK) {
        return PMU_STORAGE_ERROR_FLASH;
    }

    /* Validate header */
    if (header.magic != PMU_JSON_MAGIC) {
        return PMU_STORAGE_ERROR_NOT_FOUND;
    }

    if (header.json_size > PMU_CONFIG_JSON_MAX_SIZE || header.json_size > buffer_size) {
        return PMU_STORAGE_ERROR_SIZE;
    }

    /* Read JSON data */
    if (PMU_Flash_Read(slot_addr + JSON_HEADER_SIZE, (uint8_t*)buffer, header.json_size) != PMU_FLASH_OK) {
        return PMU_STORAGE_ERROR_FLASH;
    }

    /* Verify CRC */
    uint32_t json_crc = PMU_Storage_CalculateCRC32((const uint8_t*)buffer, header.json_size);
    if (json_crc != header.json_crc32) {
        return PMU_STORAGE_ERROR_CRC;
    }

    *actual_size = header.json_size;
    storage_stats.read_count++;

    return PMU_STORAGE_OK;
}

/**
 * @brief Save JSON configuration to external flash
 */
PMU_Storage_Status_t PMU_Storage_SaveJSON(const char* json, uint32_t json_size)
{
    if (json == NULL || json_size == 0) {
        return PMU_STORAGE_ERROR;
    }

    if (json_size > PMU_CONFIG_JSON_MAX_SIZE) {
        return PMU_STORAGE_ERROR_SIZE;
    }

    /* Use alternate slot (wear leveling) */
    uint8_t new_slot = (active_json_slot == 0) ? 1 : 0;
    uint32_t slot_addr = Storage_GetJSONSlotAddress(new_slot);

    /* Prepare header */
    PMU_JSON_Header_t header = {0};
    header.magic = PMU_JSON_MAGIC;
    header.json_size = json_size;
    header.json_crc32 = PMU_Storage_CalculateCRC32((const uint8_t*)json, json_size);
    header.write_count = storage_stats.external_writes + 1;
    header.timestamp = 0;  /* TODO: Get RTC time */
    header.header_crc32 = PMU_Storage_CalculateCRC32(
        (const uint8_t*)&header,
        sizeof(header) - sizeof(uint32_t)
    );

    /* Erase slot (128 KB = 32 sectors of 4 KB each) */
    for (uint32_t offset = 0; offset < PMU_CONFIG_SLOT_SIZE; offset += 4096) {
        if (PMU_Flash_EraseSector(slot_addr + offset) != PMU_FLASH_OK) {
            return PMU_STORAGE_ERROR_FLASH;
        }
    }

    /* Write header */
    if (PMU_Flash_Write(slot_addr, (const uint8_t*)&header, sizeof(header)) != PMU_FLASH_OK) {
        return PMU_STORAGE_ERROR_FLASH;
    }

    /* Write JSON data */
    if (PMU_Flash_Write(slot_addr + JSON_HEADER_SIZE, (const uint8_t*)json, json_size) != PMU_FLASH_OK) {
        return PMU_STORAGE_ERROR_FLASH;
    }

    /* Switch to new slot */
    active_json_slot = new_slot;
    storage_stats.write_count++;
    storage_stats.external_writes++;

    return PMU_STORAGE_OK;
}

/**
 * @brief Get JSON configuration size
 */
PMU_Storage_Status_t PMU_Storage_GetJSONSize(uint32_t* size)
{
    if (size == NULL) {
        return PMU_STORAGE_ERROR;
    }

    PMU_JSON_Header_t header;
    uint32_t slot_addr = Storage_GetJSONSlotAddress(active_json_slot);

    /* Read header */
    if (PMU_Flash_Read(slot_addr, (uint8_t*)&header, sizeof(header)) != PMU_FLASH_OK) {
        return PMU_STORAGE_ERROR_FLASH;
    }

    if (header.magic != PMU_JSON_MAGIC) {
        *size = 0;
        return PMU_STORAGE_ERROR_NOT_FOUND;
    }

    *size = header.json_size;
    return PMU_STORAGE_OK;
}

/**
 * @brief Clear JSON configuration
 */
PMU_Storage_Status_t PMU_Storage_ClearJSON(void)
{
    /* Erase both slots */
    for (uint8_t slot = 0; slot < 2; slot++) {
        uint32_t slot_addr = Storage_GetJSONSlotAddress(slot);

        for (uint32_t offset = 0; offset < PMU_CONFIG_SLOT_SIZE; offset += 4096) {
            if (PMU_Flash_EraseSector(slot_addr + offset) != PMU_FLASH_OK) {
                return PMU_STORAGE_ERROR_FLASH;
            }
        }
    }

    active_json_slot = 0;
    return PMU_STORAGE_OK;
}

/**
 * @brief Perform factory reset
 */
PMU_Storage_Status_t PMU_Storage_FactoryReset(bool keep_calibration)
{
    PMU_System_Config_t backup;

    /* Backup calibration if requested */
    if (keep_calibration) {
        memcpy(backup.adc_offset, system_config.adc_offset, sizeof(system_config.adc_offset));
        memcpy(backup.adc_gain, system_config.adc_gain, sizeof(system_config.adc_gain));
        backup.vbat_calibration = system_config.vbat_calibration;
        backup.temp_offset = system_config.temp_offset;
    }

    /* Reset to defaults */
    Storage_InitDefaults();

    /* Restore calibration if requested */
    if (keep_calibration) {
        memcpy(system_config.adc_offset, backup.adc_offset, sizeof(system_config.adc_offset));
        memcpy(system_config.adc_gain, backup.adc_gain, sizeof(system_config.adc_gain));
        system_config.vbat_calibration = backup.vbat_calibration;
        system_config.temp_offset = backup.temp_offset;
    }

    /* Save system config */
    PMU_Storage_Status_t status = Storage_SaveToInternal();
    if (status != PMU_STORAGE_OK) {
        return status;
    }

    /* Clear JSON */
    return PMU_Storage_ClearJSON();
}

/**
 * @brief Export configuration to buffer
 */
PMU_Storage_Status_t PMU_Storage_ExportConfig(uint8_t* buffer, uint32_t buffer_size, uint32_t* actual_size)
{
    if (buffer == NULL || actual_size == NULL) {
        return PMU_STORAGE_ERROR;
    }

    uint32_t required_size = sizeof(PMU_System_Config_t) + 8;  /* Config + size header + CRC */

    if (buffer_size < required_size) {
        return PMU_STORAGE_ERROR_SIZE;
    }

    /* Write size header */
    uint32_t config_size = sizeof(PMU_System_Config_t);
    memcpy(buffer, &config_size, 4);

    /* Write configuration */
    memcpy(buffer + 4, &system_config, sizeof(PMU_System_Config_t));

    /* Write CRC */
    uint32_t crc = PMU_Storage_CalculateCRC32(buffer + 4, sizeof(PMU_System_Config_t));
    memcpy(buffer + 4 + sizeof(PMU_System_Config_t), &crc, 4);

    *actual_size = required_size;
    return PMU_STORAGE_OK;
}

/**
 * @brief Import configuration from buffer
 */
PMU_Storage_Status_t PMU_Storage_ImportConfig(const uint8_t* buffer, uint32_t buffer_size)
{
    if (buffer == NULL) {
        return PMU_STORAGE_ERROR;
    }

    uint32_t required_size = sizeof(PMU_System_Config_t) + 8;
    if (buffer_size < required_size) {
        return PMU_STORAGE_ERROR_SIZE;
    }

    /* Read size header */
    uint32_t config_size;
    memcpy(&config_size, buffer, 4);

    if (config_size != sizeof(PMU_System_Config_t)) {
        return PMU_STORAGE_ERROR_VERSION;
    }

    /* Verify CRC */
    uint32_t stored_crc;
    memcpy(&stored_crc, buffer + 4 + config_size, 4);

    uint32_t calc_crc = PMU_Storage_CalculateCRC32(buffer + 4, config_size);
    if (calc_crc != stored_crc) {
        return PMU_STORAGE_ERROR_CRC;
    }

    /* Import configuration */
    memcpy(&system_config, buffer + 4, sizeof(PMU_System_Config_t));

    /* Save to flash */
    return Storage_SaveToInternal();
}

/**
 * @brief Get storage statistics
 */
PMU_Storage_Stats_t* PMU_Storage_GetStats(void)
{
    return &storage_stats;
}

/**
 * @brief Increment power-on counter
 */
void PMU_Storage_IncrementPowerOn(void)
{
    system_config.power_on_count++;
    /* Don't save immediately to reduce flash wear */
}

/**
 * @brief Update runtime counter
 */
void PMU_Storage_UpdateRuntime(void)
{
    system_config.runtime_hours++;
    /* Save periodically to preserve runtime data */
    Storage_SaveToInternal();
}

/**
 * @brief Log a fault event
 */
void PMU_Storage_LogFault(uint32_t fault_code)
{
    system_config.fault_count++;
    system_config.last_fault_code = fault_code;
    /* Save immediately for fault logging */
    Storage_SaveToInternal();
}

/**
 * @brief Calculate CRC32
 */
uint32_t PMU_Storage_CalculateCRC32(const uint8_t* data, uint32_t length)
{
    uint32_t crc = PMU_CONFIG_CRC_INIT;

    for (uint32_t i = 0; i < length; i++) {
        uint8_t index = (uint8_t)((crc ^ data[i]) & 0xFF);
        crc = (crc >> 8) ^ crc32_table[index];
    }

    return crc ^ PMU_CONFIG_CRC_INIT;
}

/*---------------------------------------------------------------------------*/
/* Private Functions                                                          */
/*---------------------------------------------------------------------------*/

/**
 * @brief Initialize configuration to defaults
 */
static void Storage_InitDefaults(void)
{
    memset(&system_config, 0, sizeof(system_config));

    /* Device identification */
    system_config.device_id = 0;
    strncpy(system_config.serial_number, "PMU30-UNSET", sizeof(system_config.serial_number) - 1);
    strncpy(system_config.device_name, "PMU-30 Racing Controller", sizeof(system_config.device_name) - 1);

    /* Hardware configuration */
    system_config.hw_revision = 1;
    system_config.profet_count = 30;
    system_config.hbridge_count = 4;
    system_config.analog_input_count = 20;
    system_config.digital_input_count = 8;
    system_config.can_bus_count = 2;

    /* ADC calibration - default to unity gain, zero offset */
    for (int i = 0; i < 20; i++) {
        system_config.adc_offset[i] = 0;
        system_config.adc_gain[i] = 1000;  /* 1.000 × */
    }
    system_config.vbat_calibration = 1000;
    system_config.temp_offset = 0;

    /* Protection thresholds */
    system_config.voltage_min_mv = 6000;     /* 6V */
    system_config.voltage_max_mv = 22000;    /* 22V */
    system_config.temp_warning_c = 100;      /* 100°C */
    system_config.temp_critical_c = 125;     /* 125°C */
    system_config.max_current_ma = 1200000;  /* 1200A total */

    /* System settings */
    system_config.update_rate_hz = 1000;     /* 1 kHz */
    system_config.logging_rate_hz = 500;     /* 500 Hz */
    system_config.can1_bitrate_idx = 3;      /* 500 kbps */
    system_config.can2_bitrate_idx = 3;      /* 500 kbps */
    system_config.can1_fd_enabled = 1;
    system_config.can2_fd_enabled = 1;

    /* Statistics - preserved if already set */
    /* power_on_count, runtime_hours, fault_count are kept */
}

/**
 * @brief Load configuration from internal flash
 */
static PMU_Storage_Status_t Storage_LoadFromInternal(void)
{
#ifdef UNIT_TEST
    Storage_InitDefaults();
    return PMU_STORAGE_OK;
#else
    PMU_Config_Header_t* header = (PMU_Config_Header_t*)PMU_CONFIG_INT_ADDRESS;

    /* Check magic */
    if (header->magic != PMU_CONFIG_MAGIC) {
        return PMU_STORAGE_ERROR_NOT_FOUND;
    }

    /* Verify header CRC */
    uint32_t header_crc = PMU_Storage_CalculateCRC32(
        (const uint8_t*)header,
        sizeof(PMU_Config_Header_t) - sizeof(uint32_t)
    );
    if (header_crc != header->header_crc32) {
        return PMU_STORAGE_ERROR_CRC;
    }

    /* Check version compatibility */
    if (header->version_major != PMU_CONFIG_VERSION_MAJOR) {
        return PMU_STORAGE_ERROR_VERSION;
    }

    /* Check data size */
    if (header->data_size != sizeof(PMU_System_Config_t)) {
        return PMU_STORAGE_ERROR_VERSION;
    }

    /* Read configuration data */
    uint8_t* config_addr = (uint8_t*)(PMU_CONFIG_INT_ADDRESS + PMU_CONFIG_HEADER_SIZE);
    memcpy(&system_config, config_addr, sizeof(PMU_System_Config_t));

    /* Verify data CRC */
    uint32_t data_crc = PMU_Storage_CalculateCRC32(
        (const uint8_t*)&system_config,
        sizeof(PMU_System_Config_t)
    );
    if (data_crc != header->data_crc32) {
        return PMU_STORAGE_ERROR_CRC;
    }

    return PMU_STORAGE_OK;
#endif
}

/**
 * @brief Save configuration to internal flash
 */
static PMU_Storage_Status_t Storage_SaveToInternal(void)
{
#ifdef UNIT_TEST
    return PMU_STORAGE_OK;
#else
    /* Prepare header */
    PMU_Config_Header_t header = {0};
    header.magic = PMU_CONFIG_MAGIC;
    header.version_major = PMU_CONFIG_VERSION_MAJOR;
    header.version_minor = PMU_CONFIG_VERSION_MINOR;
    header.data_size = sizeof(PMU_System_Config_t);
    header.data_crc32 = PMU_Storage_CalculateCRC32(
        (const uint8_t*)&system_config,
        sizeof(PMU_System_Config_t)
    );
    header.write_count = storage_stats.internal_writes + 1;
    header.timestamp = 0;  /* TODO: Get RTC time */
    header.slot_active = active_json_slot;
    header.header_crc32 = PMU_Storage_CalculateCRC32(
        (const uint8_t*)&header,
        sizeof(header) - sizeof(uint32_t)
    );

    /* Erase configuration sector (128 KB on STM32H7) */
    if (PMU_Bootloader_EraseFlashSector(PMU_CONFIG_INT_ADDRESS) != PMU_BOOT_OK) {
        return PMU_STORAGE_ERROR_FLASH;
    }

    /* Write header */
    if (PMU_Bootloader_WriteFlash(PMU_CONFIG_INT_ADDRESS, (const uint8_t*)&header, 32) != PMU_BOOT_OK) {
        return PMU_STORAGE_ERROR_FLASH;
    }

    /* Pad header to 256 bytes for alignment */
    uint8_t padding[224] = {0xFF};
    if (PMU_Bootloader_WriteFlash(PMU_CONFIG_INT_ADDRESS + 32, padding, 224) != PMU_BOOT_OK) {
        return PMU_STORAGE_ERROR_FLASH;
    }

    /* Write configuration data (pad to 32-byte boundary) */
    uint32_t config_size = sizeof(PMU_System_Config_t);
    uint32_t padded_size = ((config_size + 31) / 32) * 32;
    uint8_t config_buffer[4096];  /* Must be large enough for padded config */

    memset(config_buffer, 0xFF, padded_size);
    memcpy(config_buffer, &system_config, sizeof(PMU_System_Config_t));

    if (PMU_Bootloader_WriteFlash(PMU_CONFIG_INT_ADDRESS + PMU_CONFIG_HEADER_SIZE,
                                   config_buffer, padded_size) != PMU_BOOT_OK) {
        return PMU_STORAGE_ERROR_FLASH;
    }

    return PMU_STORAGE_OK;
#endif
}

/**
 * @brief Validate JSON slot
 */
static bool Storage_ValidateJSONSlot(uint8_t slot)
{
    PMU_JSON_Header_t header;
    uint32_t slot_addr = Storage_GetJSONSlotAddress(slot);

    if (PMU_Flash_Read(slot_addr, (uint8_t*)&header, sizeof(header)) != PMU_FLASH_OK) {
        return false;
    }

    if (header.magic != PMU_JSON_MAGIC) {
        return false;
    }

    /* Verify header CRC */
    uint32_t header_crc = PMU_Storage_CalculateCRC32(
        (const uint8_t*)&header,
        sizeof(header) - sizeof(uint32_t)
    );

    return (header_crc == header.header_crc32);
}

/**
 * @brief Get JSON slot address
 */
static uint32_t Storage_GetJSONSlotAddress(uint8_t slot)
{
    return (slot == 0) ? PMU_CONFIG_SLOT_0 : PMU_CONFIG_SLOT_1;
}

/**
 * @brief Select active JSON slot (most recently written valid slot)
 */
static void Storage_SelectActiveJSONSlot(void)
{
    bool slot0_valid = Storage_ValidateJSONSlot(0);
    bool slot1_valid = Storage_ValidateJSONSlot(1);

    if (!slot0_valid && !slot1_valid) {
        active_json_slot = 0;
        return;
    }

    if (slot0_valid && !slot1_valid) {
        active_json_slot = 0;
        return;
    }

    if (!slot0_valid && slot1_valid) {
        active_json_slot = 1;
        return;
    }

    /* Both valid - select one with higher write count */
    PMU_JSON_Header_t header0, header1;
    PMU_Flash_Read(PMU_CONFIG_SLOT_0, (uint8_t*)&header0, sizeof(header0));
    PMU_Flash_Read(PMU_CONFIG_SLOT_1, (uint8_t*)&header1, sizeof(header1));

    active_json_slot = (header1.write_count > header0.write_count) ? 1 : 0;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
