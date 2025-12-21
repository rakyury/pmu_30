/**
 ******************************************************************************
 * @file           : pmu_flash.c
 * @brief          : W25Q512JV SPI Flash Driver Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 * W25Q512JV SPI Flash Driver for high-speed data logging
 * Supports DMA transfers for maximum throughput
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_flash.h"
#include <string.h>

/* Private typedef -----------------------------------------------------------*/

/* Private define ------------------------------------------------------------*/
#define FLASH_CS_LOW()     HAL_GPIO_WritePin(FLASH_CS_GPIO_Port, FLASH_CS_Pin, GPIO_PIN_RESET)
#define FLASH_CS_HIGH()    HAL_GPIO_WritePin(FLASH_CS_GPIO_Port, FLASH_CS_Pin, GPIO_PIN_SET)

#define FLASH_SPI_TIMEOUT  1000  /* SPI timeout in ms */

/* Private macro -------------------------------------------------------------*/

/* Private variables ---------------------------------------------------------*/
static PMU_Flash_Info_t flash_info = {0};
static PMU_Flash_Stats_t flash_stats = {0};
static bool flash_initialized = false;

#ifndef UNIT_TEST
extern SPI_HandleTypeDef hspi1;  /* SPI1 for external flash */

/* GPIO definitions for flash CS pin */
static GPIO_TypeDef* FLASH_CS_GPIO_Port = GPIOA;
static uint16_t FLASH_CS_Pin = GPIO_PIN_4;  /* Example: PA4 for CS */
#endif

/* Private function prototypes -----------------------------------------------*/
static PMU_Flash_Status_t Flash_SendCommand(uint8_t cmd);
static PMU_Flash_Status_t Flash_SendCommandWithAddress(uint8_t cmd, uint32_t address);
static PMU_Flash_Status_t Flash_ReadData(uint8_t* data, uint32_t length);
static PMU_Flash_Status_t Flash_WriteData(const uint8_t* data, uint32_t length);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize flash driver
 */
PMU_Flash_Status_t PMU_Flash_Init(void)
{
#ifdef UNIT_TEST
    flash_initialized = true;
    flash_info.manufacturer_id = W25Q512_MANUFACTURER_ID;
    flash_info.memory_type = W25Q512_MEMORY_TYPE;
    flash_info.capacity = W25Q512_CAPACITY;
    flash_info.total_size = FLASH_SIZE;
    return PMU_FLASH_OK;
#else

    /* Initialize SPI peripheral */
    hspi1.Instance = SPI1;
    hspi1.Init.Mode = SPI_MODE_MASTER;
    hspi1.Init.Direction = SPI_DIRECTION_2LINES;
    hspi1.Init.DataSize = SPI_DATASIZE_8BIT;
    hspi1.Init.CLKPolarity = SPI_POLARITY_LOW;
    hspi1.Init.CLKPhase = SPI_PHASE_1EDGE;
    hspi1.Init.NSS = SPI_NSS_SOFT;
    hspi1.Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_4;  /* 200MHz/4 = 50MHz */
    hspi1.Init.FirstBit = SPI_FIRSTBIT_MSB;
    hspi1.Init.TIMode = SPI_TIMODE_DISABLE;
    hspi1.Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
    hspi1.Init.NSSPMode = SPI_NSS_PULSE_DISABLE;

    if (HAL_SPI_Init(&hspi1) != HAL_OK) {
        return PMU_FLASH_ERROR;
    }

    /* Initialize CS pin */
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin = FLASH_CS_Pin;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    HAL_GPIO_Init(FLASH_CS_GPIO_Port, &GPIO_InitStruct);

    FLASH_CS_HIGH();  /* CS idle high */

    /* Small delay for flash power-up */
    HAL_Delay(10);

    /* Reset flash device */
    PMU_Flash_Reset();
    HAL_Delay(1);

    /* Read and verify JEDEC ID */
    PMU_Flash_Status_t status = PMU_Flash_GetInfo(&flash_info);
    if (status != PMU_FLASH_OK) {
        return status;
    }

    /* Verify chip ID */
    if (flash_info.manufacturer_id != W25Q512_MANUFACTURER_ID ||
        flash_info.memory_type != W25Q512_MEMORY_TYPE) {
        return PMU_FLASH_ERROR_ID;
    }

    flash_info.total_size = FLASH_SIZE;
    flash_initialized = true;

    /* Clear statistics */
    memset(&flash_stats, 0, sizeof(flash_stats));

    return PMU_FLASH_OK;
#endif
}

/**
 * @brief Read flash information
 */
PMU_Flash_Status_t PMU_Flash_GetInfo(PMU_Flash_Info_t* info)
{
    if (!info) {
        return PMU_FLASH_ERROR;
    }

#ifdef UNIT_TEST
    memcpy(info, &flash_info, sizeof(PMU_Flash_Info_t));
    return PMU_FLASH_OK;
#else

    uint8_t jedec_data[3] = {0};

    /* Read JEDEC ID (Manufacturer, Memory Type, Capacity) */
    FLASH_CS_LOW();

    uint8_t cmd = W25Q_CMD_JEDEC_ID;
    if (HAL_SPI_Transmit(&hspi1, &cmd, 1, FLASH_SPI_TIMEOUT) != HAL_OK) {
        FLASH_CS_HIGH();
        return PMU_FLASH_ERROR;
    }

    if (HAL_SPI_Receive(&hspi1, jedec_data, 3, FLASH_SPI_TIMEOUT) != HAL_OK) {
        FLASH_CS_HIGH();
        return PMU_FLASH_ERROR;
    }

    FLASH_CS_HIGH();

    info->manufacturer_id = jedec_data[0];
    info->memory_type = jedec_data[1];
    info->capacity = jedec_data[2];
    info->jedec_id = (jedec_data[0] << 16) | (jedec_data[1] << 8) | jedec_data[2];

    /* Read Unique ID (64-bit) */
    uint8_t unique_id_data[8] = {0};

    FLASH_CS_LOW();
    cmd = W25Q_CMD_READ_UNIQUE_ID;
    if (HAL_SPI_Transmit(&hspi1, &cmd, 1, FLASH_SPI_TIMEOUT) != HAL_OK) {
        FLASH_CS_HIGH();
        return PMU_FLASH_ERROR;
    }

    /* Send 4 dummy bytes */
    uint8_t dummy[4] = {0xFF, 0xFF, 0xFF, 0xFF};
    HAL_SPI_Transmit(&hspi1, dummy, 4, FLASH_SPI_TIMEOUT);

    if (HAL_SPI_Receive(&hspi1, unique_id_data, 8, FLASH_SPI_TIMEOUT) != HAL_OK) {
        FLASH_CS_HIGH();
        return PMU_FLASH_ERROR;
    }

    FLASH_CS_HIGH();

    /* Convert to 64-bit unique ID */
    info->unique_id = 0;
    for (int i = 0; i < 8; i++) {
        info->unique_id |= ((uint64_t)unique_id_data[i]) << (56 - i * 8);
    }

    return PMU_FLASH_OK;
#endif
}

/**
 * @brief Read data from flash
 */
PMU_Flash_Status_t PMU_Flash_Read(uint32_t address, uint8_t* data, uint32_t length)
{
    if (!data || length == 0 || address + length > FLASH_SIZE) {
        return PMU_FLASH_ERROR;
    }

#ifdef UNIT_TEST
    /* For unit tests, return dummy data */
    memset(data, 0xFF, length);
    flash_stats.read_count++;
    flash_stats.bytes_read += length;
    return PMU_FLASH_OK;
#else

    /* Wait until flash is ready */
    if (PMU_Flash_WaitReady(FLASH_TIMEOUT_MS) != PMU_FLASH_OK) {
        return PMU_FLASH_TIMEOUT;
    }

    FLASH_CS_LOW();

    /* Send Fast Read command with 24-bit address */
    uint8_t cmd_addr[5];
    cmd_addr[0] = W25Q_CMD_FAST_READ;
    cmd_addr[1] = (address >> 16) & 0xFF;
    cmd_addr[2] = (address >> 8) & 0xFF;
    cmd_addr[3] = address & 0xFF;
    cmd_addr[4] = 0xFF;  /* Dummy byte for fast read */

    if (HAL_SPI_Transmit(&hspi1, cmd_addr, 5, FLASH_SPI_TIMEOUT) != HAL_OK) {
        FLASH_CS_HIGH();
        flash_stats.error_count++;
        return PMU_FLASH_ERROR;
    }

    /* Read data */
    if (HAL_SPI_Receive(&hspi1, data, length, FLASH_TIMEOUT_MS) != HAL_OK) {
        FLASH_CS_HIGH();
        flash_stats.error_count++;
        return PMU_FLASH_ERROR;
    }

    FLASH_CS_HIGH();

    flash_stats.read_count++;
    flash_stats.bytes_read += length;

    return PMU_FLASH_OK;
#endif
}

/**
 * @brief Write data to flash (page program)
 */
PMU_Flash_Status_t PMU_Flash_Write(uint32_t address, const uint8_t* data, uint32_t length)
{
    if (!data || length == 0 || address + length > FLASH_SIZE) {
        return PMU_FLASH_ERROR;
    }

#ifdef UNIT_TEST
    flash_stats.write_count++;
    flash_stats.bytes_written += length;
    return PMU_FLASH_OK;
#else

    uint32_t bytes_written = 0;

    while (bytes_written < length) {
        /* Calculate bytes to write in this page (max 256, page-aligned) */
        uint32_t current_addr = address + bytes_written;
        uint32_t page_offset = current_addr % FLASH_PAGE_SIZE;
        uint32_t bytes_to_write = FLASH_PAGE_SIZE - page_offset;

        if (bytes_to_write > (length - bytes_written)) {
            bytes_to_write = length - bytes_written;
        }

        /* Wait until flash is ready */
        if (PMU_Flash_WaitReady(FLASH_TIMEOUT_MS) != PMU_FLASH_OK) {
            return PMU_FLASH_TIMEOUT;
        }

        /* Enable write */
        if (PMU_Flash_WriteEnable() != PMU_FLASH_OK) {
            flash_stats.error_count++;
            return PMU_FLASH_ERROR;
        }

        /* Send Page Program command */
        FLASH_CS_LOW();

        uint8_t cmd_addr[4];
        cmd_addr[0] = W25Q_CMD_PAGE_PROGRAM;
        cmd_addr[1] = (current_addr >> 16) & 0xFF;
        cmd_addr[2] = (current_addr >> 8) & 0xFF;
        cmd_addr[3] = current_addr & 0xFF;

        if (HAL_SPI_Transmit(&hspi1, cmd_addr, 4, FLASH_SPI_TIMEOUT) != HAL_OK) {
            FLASH_CS_HIGH();
            flash_stats.error_count++;
            return PMU_FLASH_ERROR;
        }

        /* Write data */
        if (HAL_SPI_Transmit(&hspi1, (uint8_t*)(data + bytes_written),
                             bytes_to_write, FLASH_TIMEOUT_MS) != HAL_OK) {
            FLASH_CS_HIGH();
            flash_stats.error_count++;
            return PMU_FLASH_ERROR;
        }

        FLASH_CS_HIGH();

        /* Wait for programming to complete */
        if (PMU_Flash_WaitReady(FLASH_PROGRAM_PAGE_MS) != PMU_FLASH_OK) {
            return PMU_FLASH_TIMEOUT;
        }

        bytes_written += bytes_to_write;
    }

    flash_stats.write_count++;
    flash_stats.bytes_written += length;

    return PMU_FLASH_OK;
#endif
}

/**
 * @brief Erase sector (4KB)
 */
PMU_Flash_Status_t PMU_Flash_EraseSector(uint32_t address)
{
    if (address >= FLASH_SIZE) {
        return PMU_FLASH_ERROR;
    }

    /* Align to sector boundary */
    address &= ~(FLASH_SECTOR_SIZE - 1);

#ifdef UNIT_TEST
    flash_stats.erase_count++;
    return PMU_FLASH_OK;
#else

    /* Wait until flash is ready */
    if (PMU_Flash_WaitReady(FLASH_TIMEOUT_MS) != PMU_FLASH_OK) {
        return PMU_FLASH_TIMEOUT;
    }

    /* Enable write */
    if (PMU_Flash_WriteEnable() != PMU_FLASH_OK) {
        return PMU_FLASH_ERROR;
    }

    /* Send Sector Erase command */
    if (Flash_SendCommandWithAddress(W25Q_CMD_SECTOR_ERASE, address) != PMU_FLASH_OK) {
        flash_stats.error_count++;
        return PMU_FLASH_ERROR;
    }

    /* Wait for erase to complete */
    if (PMU_Flash_WaitReady(FLASH_ERASE_SECTOR_MS) != PMU_FLASH_OK) {
        return PMU_FLASH_TIMEOUT;
    }

    flash_stats.erase_count++;

    return PMU_FLASH_OK;
#endif
}

/**
 * @brief Erase 64KB block
 */
PMU_Flash_Status_t PMU_Flash_EraseBlock64K(uint32_t address)
{
    if (address >= FLASH_SIZE) {
        return PMU_FLASH_ERROR;
    }

    /* Align to block boundary */
    address &= ~(FLASH_BLOCK_SIZE_64K - 1);

#ifdef UNIT_TEST
    flash_stats.erase_count++;
    return PMU_FLASH_OK;
#else

    /* Wait until flash is ready */
    if (PMU_Flash_WaitReady(FLASH_TIMEOUT_MS) != PMU_FLASH_OK) {
        return PMU_FLASH_TIMEOUT;
    }

    /* Enable write */
    if (PMU_Flash_WriteEnable() != PMU_FLASH_OK) {
        return PMU_FLASH_ERROR;
    }

    /* Send Block Erase command */
    if (Flash_SendCommandWithAddress(W25Q_CMD_BLOCK_ERASE_64K, address) != PMU_FLASH_OK) {
        flash_stats.error_count++;
        return PMU_FLASH_ERROR;
    }

    /* Wait for erase to complete */
    if (PMU_Flash_WaitReady(FLASH_ERASE_BLOCK_MS) != PMU_FLASH_OK) {
        return PMU_FLASH_TIMEOUT;
    }

    flash_stats.erase_count++;

    return PMU_FLASH_OK;
#endif
}

/**
 * @brief Erase entire chip
 */
PMU_Flash_Status_t PMU_Flash_EraseChip(void)
{
#ifdef UNIT_TEST
    flash_stats.erase_count++;
    return PMU_FLASH_OK;
#else

    /* Wait until flash is ready */
    if (PMU_Flash_WaitReady(FLASH_TIMEOUT_MS) != PMU_FLASH_OK) {
        return PMU_FLASH_TIMEOUT;
    }

    /* Enable write */
    if (PMU_Flash_WriteEnable() != PMU_FLASH_OK) {
        return PMU_FLASH_ERROR;
    }

    /* Send Chip Erase command */
    if (Flash_SendCommand(W25Q_CMD_CHIP_ERASE) != PMU_FLASH_OK) {
        flash_stats.error_count++;
        return PMU_FLASH_ERROR;
    }

    /* Wait for erase to complete (can take several minutes!) */
    if (PMU_Flash_WaitReady(FLASH_ERASE_CHIP_MS) != PMU_FLASH_OK) {
        return PMU_FLASH_TIMEOUT;
    }

    flash_stats.erase_count++;

    return PMU_FLASH_OK;
#endif
}

/**
 * @brief Check if flash is busy
 */
bool PMU_Flash_IsBusy(void)
{
#ifdef UNIT_TEST
    return false;
#else
    uint8_t status = 0;

    if (PMU_Flash_ReadStatus(1, &status) != PMU_FLASH_OK) {
        return true;  /* Assume busy on error */
    }

    return (status & W25Q_SR_BUSY) != 0;
#endif
}

/**
 * @brief Wait until flash is ready
 */
PMU_Flash_Status_t PMU_Flash_WaitReady(uint32_t timeout_ms)
{
#ifdef UNIT_TEST
    return PMU_FLASH_OK;
#else
    uint32_t start_time = HAL_GetTick();

    while (PMU_Flash_IsBusy()) {
        if ((HAL_GetTick() - start_time) > timeout_ms) {
            return PMU_FLASH_TIMEOUT;
        }
        /* Small delay to reduce SPI traffic */
        HAL_Delay(1);
    }

    return PMU_FLASH_OK;
#endif
}

/**
 * @brief Enable write operations
 */
PMU_Flash_Status_t PMU_Flash_WriteEnable(void)
{
#ifdef UNIT_TEST
    return PMU_FLASH_OK;
#else
    return Flash_SendCommand(W25Q_CMD_WRITE_ENABLE);
#endif
}

/**
 * @brief Disable write operations
 */
PMU_Flash_Status_t PMU_Flash_WriteDisable(void)
{
#ifdef UNIT_TEST
    return PMU_FLASH_OK;
#else
    return Flash_SendCommand(W25Q_CMD_WRITE_DISABLE);
#endif
}

/**
 * @brief Read status register
 */
PMU_Flash_Status_t PMU_Flash_ReadStatus(uint8_t reg_num, uint8_t* status)
{
    if (!status || reg_num < 1 || reg_num > 3) {
        return PMU_FLASH_ERROR;
    }

#ifdef UNIT_TEST
    *status = 0x00;  /* Not busy, write enabled */
    return PMU_FLASH_OK;
#else

    uint8_t cmd;
    switch (reg_num) {
        case 1: cmd = W25Q_CMD_READ_STATUS_REG1; break;
        case 2: cmd = W25Q_CMD_READ_STATUS_REG2; break;
        case 3: cmd = W25Q_CMD_READ_STATUS_REG3; break;
        default: return PMU_FLASH_ERROR;
    }

    FLASH_CS_LOW();

    if (HAL_SPI_Transmit(&hspi1, &cmd, 1, FLASH_SPI_TIMEOUT) != HAL_OK) {
        FLASH_CS_HIGH();
        return PMU_FLASH_ERROR;
    }

    if (HAL_SPI_Receive(&hspi1, status, 1, FLASH_SPI_TIMEOUT) != HAL_OK) {
        FLASH_CS_HIGH();
        return PMU_FLASH_ERROR;
    }

    FLASH_CS_HIGH();

    return PMU_FLASH_OK;
#endif
}

/**
 * @brief Power down flash
 */
PMU_Flash_Status_t PMU_Flash_PowerDown(void)
{
#ifdef UNIT_TEST
    return PMU_FLASH_OK;
#else
    return Flash_SendCommand(W25Q_CMD_POWER_DOWN);
#endif
}

/**
 * @brief Wake up flash from power down
 */
PMU_Flash_Status_t PMU_Flash_WakeUp(void)
{
#ifdef UNIT_TEST
    return PMU_FLASH_OK;
#else
    PMU_Flash_Status_t status = Flash_SendCommand(W25Q_CMD_RELEASE_POWER_DOWN);
    HAL_Delay(1);  /* tRES1 = 3µs typical */
    return status;
#endif
}

/**
 * @brief Reset flash device
 */
PMU_Flash_Status_t PMU_Flash_Reset(void)
{
#ifdef UNIT_TEST
    return PMU_FLASH_OK;
#else
    /* Enable Reset */
    if (Flash_SendCommand(W25Q_CMD_ENABLE_RESET) != PMU_FLASH_OK) {
        return PMU_FLASH_ERROR;
    }

    /* Reset Device */
    if (Flash_SendCommand(W25Q_CMD_RESET) != PMU_FLASH_OK) {
        return PMU_FLASH_ERROR;
    }

    HAL_Delay(1);  /* tRST = 30µs typical */

    return PMU_FLASH_OK;
#endif
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

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Send simple command (no address, no data)
 */
static PMU_Flash_Status_t Flash_SendCommand(uint8_t cmd)
{
#ifndef UNIT_TEST
    FLASH_CS_LOW();

    if (HAL_SPI_Transmit(&hspi1, &cmd, 1, FLASH_SPI_TIMEOUT) != HAL_OK) {
        FLASH_CS_HIGH();
        return PMU_FLASH_ERROR;
    }

    FLASH_CS_HIGH();
#else
    (void)cmd;
#endif

    return PMU_FLASH_OK;
}

/**
 * @brief Send command with 24-bit address
 */
static PMU_Flash_Status_t Flash_SendCommandWithAddress(uint8_t cmd, uint32_t address)
{
#ifndef UNIT_TEST
    FLASH_CS_LOW();

    uint8_t cmd_addr[4];
    cmd_addr[0] = cmd;
    cmd_addr[1] = (address >> 16) & 0xFF;
    cmd_addr[2] = (address >> 8) & 0xFF;
    cmd_addr[3] = address & 0xFF;

    if (HAL_SPI_Transmit(&hspi1, cmd_addr, 4, FLASH_SPI_TIMEOUT) != HAL_OK) {
        FLASH_CS_HIGH();
        return PMU_FLASH_ERROR;
    }

    FLASH_CS_HIGH();
#else
    (void)cmd;
    (void)address;
#endif

    return PMU_FLASH_OK;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
