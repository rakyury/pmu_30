/**
 ******************************************************************************
 * @file           : pmu_spi.c
 * @brief          : SPI Driver for PROFET Diagnostics Implementation
 * @author         : R2 m-sport
 * @date           : 2025-12-22
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2025 R2 m-sport.
 * All rights reserved.
 *
 * Hardware Configuration:
 * - SPI2: External ADC for current sensing (ADS8688 or similar)
 * - SPI3: External ADC for status sensing
 * - GPIO: Analog multiplexer control (CD74HC4067)
 *
 * Current Sensing Architecture:
 * - 2x 16-channel external ADC (ADS8688) for 32 channels
 * - Each PROFET IS pin connected through sense resistor to ADC
 * - 16-bit resolution provides 0.1mA accuracy
 *
 * Multiplexer Architecture (alternative):
 * - 2x CD74HC4067 16-channel analog multiplexers
 * - Connected to MCU internal ADC channels
 * - SPI/GPIO controlled channel selection
 *
 ******************************************************************************
 */

/* Includes ------------------------------------------------------------------*/
#include "pmu_spi.h"
#include "stm32h7xx_hal.h"
#include <string.h>

/* Private typedef -----------------------------------------------------------*/

/**
 * @brief ADS8688 command codes
 */
typedef enum {
    ADS8688_CMD_NO_OP       = 0x0000,
    ADS8688_CMD_STDBY       = 0x8200,
    ADS8688_CMD_PWR_DN      = 0x8300,
    ADS8688_CMD_RST         = 0x8500,
    ADS8688_CMD_AUTO_RST    = 0xA000,
    ADS8688_CMD_MAN_CH_0    = 0xC000,
    ADS8688_CMD_MAN_CH_1    = 0xC400,
    ADS8688_CMD_MAN_CH_2    = 0xC800,
    ADS8688_CMD_MAN_CH_3    = 0xCC00,
    ADS8688_CMD_MAN_CH_4    = 0xD000,
    ADS8688_CMD_MAN_CH_5    = 0xD400,
    ADS8688_CMD_MAN_CH_6    = 0xD800,
    ADS8688_CMD_MAN_CH_7    = 0xDC00,
    ADS8688_CMD_MAN_AUX     = 0xE000
} ADS8688_Command_t;

/**
 * @brief ADS8688 register addresses
 */
typedef enum {
    ADS8688_REG_AUTO_SEQ_EN    = 0x01,
    ADS8688_REG_CH_PWR_DN      = 0x02,
    ADS8688_REG_FEATURE_SELECT = 0x03,
    ADS8688_REG_CH0_INPUT_RANGE = 0x05,
    ADS8688_REG_CH1_INPUT_RANGE = 0x06,
    /* ... up to CH7 */
    ADS8688_REG_CMD_READBACK   = 0x3F
} ADS8688_Register_t;

/**
 * @brief SPI device state
 */
typedef struct {
    SPI_HandleTypeDef* hspi;
    GPIO_TypeDef* cs_port;
    uint16_t cs_pin;
    uint8_t is_initialized;
    uint8_t error_count;
} PMU_SPI_DeviceState_t;

/* Private define ------------------------------------------------------------*/

/* ADS8688 input range options */
#define ADS8688_RANGE_PM_2_5VREF    0x00    /* ±2.5 × VREF */
#define ADS8688_RANGE_PM_1_25VREF   0x01    /* ±1.25 × VREF */
#define ADS8688_RANGE_PM_0_625VREF  0x02    /* ±0.625 × VREF */
#define ADS8688_RANGE_0_2_5VREF     0x05    /* 0 to 2.5 × VREF */
#define ADS8688_RANGE_0_1_25VREF    0x06    /* 0 to 1.25 × VREF */

/* Pin definitions for analog multiplexer control (CD74HC4067) */
#define MUX_S0_PORT     GPIOD
#define MUX_S0_PIN      GPIO_PIN_0
#define MUX_S1_PORT     GPIOD
#define MUX_S1_PIN      GPIO_PIN_1
#define MUX_S2_PORT     GPIOD
#define MUX_S2_PIN      GPIO_PIN_2
#define MUX_S3_PORT     GPIOD
#define MUX_S3_PIN      GPIO_PIN_3
#define MUX_EN_PORT     GPIOD
#define MUX_EN_PIN      GPIO_PIN_4

/* Private macro -------------------------------------------------------------*/

#define SPI_SELECT(dev)     HAL_GPIO_WritePin(spi_devices[dev].cs_port, spi_devices[dev].cs_pin, GPIO_PIN_RESET)
#define SPI_DESELECT(dev)   HAL_GPIO_WritePin(spi_devices[dev].cs_port, spi_devices[dev].cs_pin, GPIO_PIN_SET)

/* Private variables ---------------------------------------------------------*/

static SPI_HandleTypeDef hspi2;     /* SPI2 for current ADC */
static SPI_HandleTypeDef hspi3;     /* SPI3 for status ADC */

static PMU_SPI_DeviceState_t spi_devices[PMU_SPI_DEV_COUNT] = {
    /* Current ADC - SPI2 */
    {.hspi = &hspi2, .cs_port = GPIOB, .cs_pin = GPIO_PIN_12, .is_initialized = 0, .error_count = 0},
    /* Status ADC - SPI3 */
    {.hspi = &hspi3, .cs_port = GPIOA, .cs_pin = GPIO_PIN_15, .is_initialized = 0, .error_count = 0},
    /* MUX Control - GPIO only, no SPI */
    {.hspi = NULL, .cs_port = NULL, .cs_pin = 0, .is_initialized = 0, .error_count = 0},
    /* Future diagnostic IC */
    {.hspi = NULL, .cs_port = NULL, .cs_pin = 0, .is_initialized = 0, .error_count = 0}
};

static PMU_SPI_DiagData_t diag_data;
static PMU_SPI_Status_t current_status = PMU_SPI_STATUS_OK;
static uint8_t mux_current_channel = 0;

/* Channel configurations */
static PMU_SPI_ADC_Channel_t channel_configs[32];

/* Private function prototypes -----------------------------------------------*/

static HAL_StatusTypeDef SPI_InitPeripheral(SPI_HandleTypeDef* hspi, SPI_TypeDef* instance);
static HAL_StatusTypeDef SPI_InitGPIO(void);
static HAL_StatusTypeDef ADS8688_Init(PMU_SPI_Device_t device);
static HAL_StatusTypeDef ADS8688_WriteReg(PMU_SPI_Device_t device, uint8_t reg, uint8_t value);
static HAL_StatusTypeDef ADS8688_ReadReg(PMU_SPI_Device_t device, uint8_t reg, uint8_t* value);
static HAL_StatusTypeDef ADS8688_ReadChannel(PMU_SPI_Device_t device, uint8_t channel, uint16_t* value);
static HAL_StatusTypeDef ADS8688_AutoScan(PMU_SPI_Device_t device, uint16_t* buffer, uint8_t num_channels);
static uint32_t ConvertCurrentRaw(uint16_t raw_value, uint8_t channel);
static int16_t ConvertTemperatureRaw(uint16_t raw_value, uint8_t channel);

/* Exported functions --------------------------------------------------------*/

/**
 * @brief Initialize SPI diagnostic interface
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_Init(void)
{
    HAL_StatusTypeDef status = HAL_OK;

    /* Clear diagnostic data */
    memset(&diag_data, 0, sizeof(diag_data));

    /* Initialize default channel configurations */
    for (uint8_t i = 0; i < 32; i++) {
        channel_configs[i].channel = i % 16;
        channel_configs[i].gain = 1;
        channel_configs[i].offset_cal = 0;
        channel_configs[i].scale_factor = 1.0f;
    }

#ifndef UNIT_TEST
    /* Initialize GPIO for CS pins and MUX control */
    status = SPI_InitGPIO();
    if (status != HAL_OK) {
        return status;
    }

    /* Initialize SPI2 for current ADC */
    status = SPI_InitPeripheral(&hspi2, SPI2);
    if (status != HAL_OK) {
        return status;
    }
    spi_devices[PMU_SPI_DEV_ADC_CURRENT].is_initialized = 1;

    /* Initialize SPI3 for status ADC */
    status = SPI_InitPeripheral(&hspi3, SPI3);
    if (status != HAL_OK) {
        return status;
    }
    spi_devices[PMU_SPI_DEV_ADC_STATUS].is_initialized = 1;

    /* Initialize ADS8688 ADCs */
    status = ADS8688_Init(PMU_SPI_DEV_ADC_CURRENT);
    if (status != HAL_OK) {
        return status;
    }

    status = ADS8688_Init(PMU_SPI_DEV_ADC_STATUS);
    if (status != HAL_OK) {
        return status;
    }

    /* Initialize MUX control */
    spi_devices[PMU_SPI_DEV_MUX_CTRL].is_initialized = 1;
    PMU_SPI_SetMuxChannel(0);
#endif

    current_status = PMU_SPI_STATUS_OK;
    return HAL_OK;
}

/**
 * @brief Deinitialize SPI diagnostic interface
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_DeInit(void)
{
#ifndef UNIT_TEST
    HAL_SPI_DeInit(&hspi2);
    HAL_SPI_DeInit(&hspi3);
#endif

    for (uint8_t i = 0; i < PMU_SPI_DEV_COUNT; i++) {
        spi_devices[i].is_initialized = 0;
    }

    return HAL_OK;
}

/**
 * @brief Update all diagnostic channels
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_Update(void)
{
    HAL_StatusTypeDef status = HAL_OK;

#ifndef UNIT_TEST
    /* Read all current sense channels */
    if (spi_devices[PMU_SPI_DEV_ADC_CURRENT].is_initialized) {
        status = ADS8688_AutoScan(PMU_SPI_DEV_ADC_CURRENT,
                                   diag_data.current_raw,
                                   PMU_SPI_ADC_CHANNELS);
        if (status != HAL_OK) {
            spi_devices[PMU_SPI_DEV_ADC_CURRENT].error_count++;
            current_status = PMU_SPI_STATUS_ERROR;
        }

        /* Read second ADC for channels 16-31 if needed */
        /* For now, using single ADC with multiplexer for extended channels */
    }

    /* Read all status channels */
    if (spi_devices[PMU_SPI_DEV_ADC_STATUS].is_initialized) {
        status = ADS8688_AutoScan(PMU_SPI_DEV_ADC_STATUS,
                                   diag_data.status_raw,
                                   PMU_SPI_ADC_CHANNELS);
        if (status != HAL_OK) {
            spi_devices[PMU_SPI_DEV_ADC_STATUS].error_count++;
            current_status = PMU_SPI_STATUS_ERROR;
        }
    }
#endif

    /* Convert raw values to engineering units */
    for (uint8_t ch = 0; ch < 32; ch++) {
        /* Convert current */
        diag_data.current_mA[ch] = ConvertCurrentRaw(diag_data.current_raw[ch], ch);

        /* Convert temperature */
        diag_data.temperature_C[ch] = ConvertTemperatureRaw(diag_data.status_raw[ch], ch);

        /* Update fault flags based on measurements */
        diag_data.fault_flags[ch] = 0;

        /* Overcurrent detection (>42A) */
        if (diag_data.current_mA[ch] > 42000) {
            diag_data.fault_flags[ch] |= 0x01;
        }

        /* Overtemperature detection (>140°C) */
        if (diag_data.temperature_C[ch] > 140) {
            diag_data.fault_flags[ch] |= 0x02;
        }

        /* Open load detection (<50mA when expected ON) */
        if (diag_data.current_mA[ch] < 50 && diag_data.current_raw[ch] < 100) {
            diag_data.fault_flags[ch] |= 0x08;
        }
    }

    /* Update timestamp */
    diag_data.last_update_tick = HAL_GetTick();

    if (current_status != PMU_SPI_STATUS_ERROR) {
        current_status = PMU_SPI_STATUS_OK;
    }

    return status;
}

/**
 * @brief Read single ADC channel
 * @param device SPI device
 * @param channel ADC channel number
 * @param value Pointer to store result
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_ReadADC(PMU_SPI_Device_t device, uint8_t channel, uint16_t* value)
{
    if (device >= PMU_SPI_DEV_COUNT || value == NULL) {
        return HAL_ERROR;
    }

    if (!spi_devices[device].is_initialized) {
        return HAL_ERROR;
    }

#ifdef UNIT_TEST
    *value = 0;
    return HAL_OK;
#else
    return ADS8688_ReadChannel(device, channel, value);
#endif
}

/**
 * @brief Read all ADC channels in sequence
 * @param device SPI device
 * @param buffer Buffer for results
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_ReadAllChannels(PMU_SPI_Device_t device, uint16_t* buffer)
{
    if (device >= PMU_SPI_DEV_COUNT || buffer == NULL) {
        return HAL_ERROR;
    }

    if (!spi_devices[device].is_initialized) {
        return HAL_ERROR;
    }

#ifdef UNIT_TEST
    memset(buffer, 0, PMU_SPI_ADC_CHANNELS * sizeof(uint16_t));
    return HAL_OK;
#else
    return ADS8688_AutoScan(device, buffer, PMU_SPI_ADC_CHANNELS);
#endif
}

/**
 * @brief Get current measurement for PROFET channel
 * @param channel PROFET channel (0-29)
 * @retval Current in mA
 */
uint32_t PMU_SPI_GetCurrent(uint8_t channel)
{
    if (channel >= 32) {
        return 0;
    }
    return diag_data.current_mA[channel];
}

/**
 * @brief Get temperature for PROFET channel
 * @param channel PROFET channel (0-29)
 * @retval Temperature in degrees C
 */
int16_t PMU_SPI_GetTemperature(uint8_t channel)
{
    if (channel >= 32) {
        return 0;
    }
    return diag_data.temperature_C[channel];
}

/**
 * @brief Get raw ADC value for channel
 * @param channel PROFET channel (0-29)
 * @param type 0=current, 1=status
 * @retval Raw ADC value
 */
uint16_t PMU_SPI_GetRawValue(uint8_t channel, uint8_t type)
{
    if (channel >= 32) {
        return 0;
    }

    if (type == 0) {
        return diag_data.current_raw[channel];
    } else {
        return diag_data.status_raw[channel];
    }
}

/**
 * @brief Get diagnostic data structure
 * @retval Pointer to diagnostic data
 */
PMU_SPI_DiagData_t* PMU_SPI_GetDiagData(void)
{
    return &diag_data;
}

/**
 * @brief Set analog multiplexer channel
 * @param mux_channel Multiplexer channel (0-15)
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_SetMuxChannel(uint8_t mux_channel)
{
    if (mux_channel > 15) {
        return HAL_ERROR;
    }

#ifndef UNIT_TEST
    /* Set multiplexer address bits (S0-S3) */
    HAL_GPIO_WritePin(MUX_S0_PORT, MUX_S0_PIN, (mux_channel & 0x01) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(MUX_S1_PORT, MUX_S1_PIN, (mux_channel & 0x02) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(MUX_S2_PORT, MUX_S2_PIN, (mux_channel & 0x04) ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(MUX_S3_PORT, MUX_S3_PIN, (mux_channel & 0x08) ? GPIO_PIN_SET : GPIO_PIN_RESET);

    /* Enable multiplexer */
    HAL_GPIO_WritePin(MUX_EN_PORT, MUX_EN_PIN, GPIO_PIN_SET);

    /* Small delay for MUX settling */
    for (volatile int i = 0; i < 100; i++);
#endif

    mux_current_channel = mux_channel;
    return HAL_OK;
}

/**
 * @brief Configure ADC channel
 * @param device SPI device
 * @param channel Channel number
 * @param config Channel configuration
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_ConfigureChannel(PMU_SPI_Device_t device,
                                            uint8_t channel,
                                            PMU_SPI_ADC_Channel_t* config)
{
    if (device >= PMU_SPI_DEV_COUNT || channel >= 32 || config == NULL) {
        return HAL_ERROR;
    }

    /* Store configuration */
    uint8_t idx = (device == PMU_SPI_DEV_ADC_STATUS) ? channel + 16 : channel;
    if (idx < 32) {
        memcpy(&channel_configs[idx], config, sizeof(PMU_SPI_ADC_Channel_t));
    }

#ifndef UNIT_TEST
    /* Configure ADC channel input range */
    if (spi_devices[device].is_initialized && channel < 8) {
        return ADS8688_WriteReg(device,
                                 ADS8688_REG_CH0_INPUT_RANGE + channel,
                                 ADS8688_RANGE_0_2_5VREF);
    }
#endif

    return HAL_OK;
}

/**
 * @brief Calibrate ADC offset
 * @param device SPI device
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_CalibrateOffset(PMU_SPI_Device_t device)
{
    if (device >= PMU_SPI_DEV_COUNT) {
        return HAL_ERROR;
    }

    if (!spi_devices[device].is_initialized) {
        return HAL_ERROR;
    }

    /* Read all channels with no load for offset calibration */
    uint16_t cal_buffer[16];

#ifndef UNIT_TEST
    HAL_StatusTypeDef status = ADS8688_AutoScan(device, cal_buffer, PMU_SPI_ADC_CHANNELS);
    if (status != HAL_OK) {
        return status;
    }
#else
    memset(cal_buffer, 0, sizeof(cal_buffer));
#endif

    /* Store offset values */
    for (uint8_t ch = 0; ch < 16; ch++) {
        uint8_t idx = (device == PMU_SPI_DEV_ADC_STATUS) ? ch + 16 : ch;
        if (idx < 32) {
            channel_configs[idx].offset_cal = cal_buffer[ch];
        }
    }

    return HAL_OK;
}

/**
 * @brief Check SPI communication status
 * @retval PMU_SPI_Status_t
 */
PMU_SPI_Status_t PMU_SPI_GetStatus(void)
{
    return current_status;
}

/**
 * @brief Reset SPI interface after error
 * @retval HAL status
 */
HAL_StatusTypeDef PMU_SPI_Reset(void)
{
#ifndef UNIT_TEST
    /* Reset SPI peripherals */
    HAL_SPI_DeInit(&hspi2);
    HAL_SPI_DeInit(&hspi3);

    /* Reinitialize */
    SPI_InitPeripheral(&hspi2, SPI2);
    SPI_InitPeripheral(&hspi3, SPI3);

    /* Reinitialize ADCs */
    ADS8688_Init(PMU_SPI_DEV_ADC_CURRENT);
    ADS8688_Init(PMU_SPI_DEV_ADC_STATUS);
#endif

    /* Clear error counts */
    for (uint8_t i = 0; i < PMU_SPI_DEV_COUNT; i++) {
        spi_devices[i].error_count = 0;
    }

    diag_data.comm_error_count = 0;
    current_status = PMU_SPI_STATUS_OK;

    return HAL_OK;
}

/* Private functions ---------------------------------------------------------*/

/**
 * @brief Initialize SPI peripheral
 * @param hspi SPI handle
 * @param instance SPI instance (SPI2 or SPI3)
 * @retval HAL status
 */
static HAL_StatusTypeDef SPI_InitPeripheral(SPI_HandleTypeDef* hspi, SPI_TypeDef* instance)
{
#ifdef UNIT_TEST
    return HAL_OK;
#else
    hspi->Instance = instance;
    hspi->Init.Mode = SPI_MODE_MASTER;
    hspi->Init.Direction = SPI_DIRECTION_2LINES;
    hspi->Init.DataSize = SPI_DATASIZE_16BIT;
    hspi->Init.CLKPolarity = SPI_POLARITY_LOW;      /* CPOL = 0 for ADS8688 */
    hspi->Init.CLKPhase = SPI_PHASE_1EDGE;          /* CPHA = 0 for ADS8688 */
    hspi->Init.NSS = SPI_NSS_SOFT;
    hspi->Init.BaudRatePrescaler = SPI_BAUDRATEPRESCALER_16;  /* ~12.5MHz @ 200MHz APB */
    hspi->Init.FirstBit = SPI_FIRSTBIT_MSB;
    hspi->Init.TIMode = SPI_TIMODE_DISABLE;
    hspi->Init.CRCCalculation = SPI_CRCCALCULATION_DISABLE;
    hspi->Init.CRCPolynomial = 7;
    hspi->Init.NSSPMode = SPI_NSS_PULSE_DISABLE;
    hspi->Init.NSSPolarity = SPI_NSS_POLARITY_LOW;
    hspi->Init.FifoThreshold = SPI_FIFO_THRESHOLD_01DATA;
    hspi->Init.TxCRCInitializationPattern = SPI_CRC_INITIALIZATION_ALL_ZERO_PATTERN;
    hspi->Init.RxCRCInitializationPattern = SPI_CRC_INITIALIZATION_ALL_ZERO_PATTERN;
    hspi->Init.MasterSSIdleness = SPI_MASTER_SS_IDLENESS_00CYCLE;
    hspi->Init.MasterInterDataIdleness = SPI_MASTER_INTERDATA_IDLENESS_00CYCLE;
    hspi->Init.MasterReceiverAutoSusp = SPI_MASTER_RX_AUTOSUSP_DISABLE;
    hspi->Init.MasterKeepIOState = SPI_MASTER_KEEP_IO_STATE_ENABLE;
    hspi->Init.IOSwap = SPI_IO_SWAP_DISABLE;

    return HAL_SPI_Init(hspi);
#endif
}

/**
 * @brief Initialize GPIO pins for SPI and MUX control
 * @retval HAL status
 */
static HAL_StatusTypeDef SPI_InitGPIO(void)
{
#ifdef UNIT_TEST
    return HAL_OK;
#else
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* Enable GPIO clocks */
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    /* Configure CS pins as outputs (active low) */
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;

    /* SPI2 CS - PB12 */
    GPIO_InitStruct.Pin = GPIO_PIN_12;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_12, GPIO_PIN_SET);  /* Deselect */

    /* SPI3 CS - PA15 */
    GPIO_InitStruct.Pin = GPIO_PIN_15;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
    HAL_GPIO_WritePin(GPIOA, GPIO_PIN_15, GPIO_PIN_SET);  /* Deselect */

    /* MUX control pins - PD0-PD4 */
    GPIO_InitStruct.Pin = GPIO_PIN_0 | GPIO_PIN_1 | GPIO_PIN_2 | GPIO_PIN_3 | GPIO_PIN_4;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);
    HAL_GPIO_WritePin(GPIOD, GPIO_PIN_0 | GPIO_PIN_1 | GPIO_PIN_2 | GPIO_PIN_3, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(GPIOD, GPIO_PIN_4, GPIO_PIN_SET);  /* Enable MUX */

    return HAL_OK;
#endif
}

/**
 * @brief Initialize ADS8688 ADC
 * @param device SPI device
 * @retval HAL status
 */
static HAL_StatusTypeDef ADS8688_Init(PMU_SPI_Device_t device)
{
#ifdef UNIT_TEST
    return HAL_OK;
#else
    HAL_StatusTypeDef status;
    uint8_t tx_data[4];
    uint8_t rx_data[4];

    /* Reset device */
    SPI_SELECT(device);

    tx_data[0] = (ADS8688_CMD_RST >> 8) & 0xFF;
    tx_data[1] = ADS8688_CMD_RST & 0xFF;

    status = HAL_SPI_TransmitReceive(spi_devices[device].hspi, tx_data, rx_data, 2, PMU_SPI_TIMEOUT_MS);

    SPI_DESELECT(device);

    if (status != HAL_OK) {
        return status;
    }

    /* Small delay after reset */
    HAL_Delay(1);

    /* Enable all channels for auto-sequence */
    status = ADS8688_WriteReg(device, ADS8688_REG_AUTO_SEQ_EN, 0xFF);
    if (status != HAL_OK) {
        return status;
    }

    /* Set input range for all channels (0 to 2.5×VREF = 0-10.24V) */
    for (uint8_t ch = 0; ch < 8; ch++) {
        status = ADS8688_WriteReg(device, ADS8688_REG_CH0_INPUT_RANGE + ch, ADS8688_RANGE_0_2_5VREF);
        if (status != HAL_OK) {
            return status;
        }
    }

    /* Enable auto-reset mode */
    SPI_SELECT(device);

    tx_data[0] = (ADS8688_CMD_AUTO_RST >> 8) & 0xFF;
    tx_data[1] = ADS8688_CMD_AUTO_RST & 0xFF;

    status = HAL_SPI_TransmitReceive(spi_devices[device].hspi, tx_data, rx_data, 2, PMU_SPI_TIMEOUT_MS);

    SPI_DESELECT(device);

    return status;
#endif
}

/**
 * @brief Write ADS8688 register
 * @param device SPI device
 * @param reg Register address
 * @param value Value to write
 * @retval HAL status
 */
static HAL_StatusTypeDef ADS8688_WriteReg(PMU_SPI_Device_t device, uint8_t reg, uint8_t value)
{
#ifdef UNIT_TEST
    return HAL_OK;
#else
    uint8_t tx_data[4];
    uint8_t rx_data[4];
    HAL_StatusTypeDef status;

    /* Write command: address (7 bits) + W bit (1) + data (8 bits) */
    tx_data[0] = (reg << 1) | 0x01;  /* Address + Write bit */
    tx_data[1] = value;

    SPI_SELECT(device);
    status = HAL_SPI_TransmitReceive(spi_devices[device].hspi, tx_data, rx_data, 2, PMU_SPI_TIMEOUT_MS);
    SPI_DESELECT(device);

    return status;
#endif
}

/**
 * @brief Read ADS8688 register
 * @param device SPI device
 * @param reg Register address
 * @param value Pointer to store value
 * @retval HAL status
 */
static HAL_StatusTypeDef ADS8688_ReadReg(PMU_SPI_Device_t device, uint8_t reg, uint8_t* value)
{
#ifdef UNIT_TEST
    *value = 0;
    return HAL_OK;
#else
    uint8_t tx_data[4];
    uint8_t rx_data[4];
    HAL_StatusTypeDef status;

    /* Read command: address (7 bits) + R bit (0) */
    tx_data[0] = (reg << 1);  /* Address + Read bit */
    tx_data[1] = 0x00;

    SPI_SELECT(device);
    status = HAL_SPI_TransmitReceive(spi_devices[device].hspi, tx_data, rx_data, 2, PMU_SPI_TIMEOUT_MS);
    SPI_DESELECT(device);

    if (status == HAL_OK) {
        *value = rx_data[1];
    }

    return status;
#endif
}

/**
 * @brief Read single ADS8688 channel
 * @param device SPI device
 * @param channel Channel number (0-7)
 * @param value Pointer to store result
 * @retval HAL status
 */
static HAL_StatusTypeDef ADS8688_ReadChannel(PMU_SPI_Device_t device, uint8_t channel, uint16_t* value)
{
#ifdef UNIT_TEST
    *value = 0;
    return HAL_OK;
#else
    uint16_t tx_data;
    uint16_t rx_data;
    HAL_StatusTypeDef status;

    if (channel > 7) {
        return HAL_ERROR;
    }

    /* Manual channel select command */
    tx_data = ADS8688_CMD_MAN_CH_0 + (channel << 10);

    SPI_SELECT(device);
    status = HAL_SPI_TransmitReceive(spi_devices[device].hspi,
                                      (uint8_t*)&tx_data,
                                      (uint8_t*)&rx_data,
                                      1, PMU_SPI_TIMEOUT_MS);
    SPI_DESELECT(device);

    if (status != HAL_OK) {
        return status;
    }

    /* Second transaction to read result */
    tx_data = ADS8688_CMD_NO_OP;

    SPI_SELECT(device);
    status = HAL_SPI_TransmitReceive(spi_devices[device].hspi,
                                      (uint8_t*)&tx_data,
                                      (uint8_t*)&rx_data,
                                      1, PMU_SPI_TIMEOUT_MS);
    SPI_DESELECT(device);

    if (status == HAL_OK) {
        *value = rx_data;
    }

    return status;
#endif
}

/**
 * @brief Auto-scan all ADS8688 channels
 * @param device SPI device
 * @param buffer Buffer for results
 * @param num_channels Number of channels to read
 * @retval HAL status
 */
static HAL_StatusTypeDef ADS8688_AutoScan(PMU_SPI_Device_t device, uint16_t* buffer, uint8_t num_channels)
{
#ifdef UNIT_TEST
    memset(buffer, 0, num_channels * sizeof(uint16_t));
    return HAL_OK;
#else
    HAL_StatusTypeDef status;
    uint16_t tx_data;
    uint16_t rx_data;

    /* Trigger auto-sequence */
    tx_data = ADS8688_CMD_AUTO_RST;

    SPI_SELECT(device);
    status = HAL_SPI_TransmitReceive(spi_devices[device].hspi,
                                      (uint8_t*)&tx_data,
                                      (uint8_t*)&rx_data,
                                      1, PMU_SPI_TIMEOUT_MS);
    SPI_DESELECT(device);

    if (status != HAL_OK) {
        return status;
    }

    /* Read all channels in sequence */
    for (uint8_t ch = 0; ch < num_channels && ch < 16; ch++) {
        tx_data = ADS8688_CMD_NO_OP;

        SPI_SELECT(device);
        status = HAL_SPI_TransmitReceive(spi_devices[device].hspi,
                                          (uint8_t*)&tx_data,
                                          (uint8_t*)&rx_data,
                                          1, PMU_SPI_TIMEOUT_MS);
        SPI_DESELECT(device);

        if (status != HAL_OK) {
            return status;
        }

        buffer[ch] = rx_data;
    }

    return HAL_OK;
#endif
}

/**
 * @brief Convert raw ADC value to current in mA
 * @param raw_value Raw ADC value (16-bit)
 * @param channel Channel number
 * @retval Current in mA
 */
static uint32_t ConvertCurrentRaw(uint16_t raw_value, uint8_t channel)
{
    /* Apply offset calibration */
    int32_t corrected = (int32_t)raw_value - (int32_t)channel_configs[channel].offset_cal;
    if (corrected < 0) corrected = 0;

    /* Convert ADC value to voltage
     * 16-bit ADC, 4.096V reference
     * Voltage = (raw / 65535) × 4096 mV
     */
    uint32_t voltage_uV = ((uint32_t)corrected * 4096000UL) / 65535;

    /* Convert voltage to current
     * IS voltage = (I_load / kILIS) × R_sense
     * I_load = (V_sense × kILIS) / R_sense
     *
     * With R_sense = 1kΩ, kILIS = 4700:
     * I_load (mA) = V_sense (µV) × 4700 / 1000000
     */
    uint32_t current_mA = (voltage_uV * PMU_SPI_KILIS_RATIO) / (PMU_SPI_SENSE_RESISTOR_OHM * 1000);

    /* Apply channel-specific scale factor */
    current_mA = (uint32_t)((float)current_mA * channel_configs[channel].scale_factor);

    return current_mA;
}

/**
 * @brief Convert raw ADC value to temperature in °C
 * @param raw_value Raw ADC value (16-bit)
 * @param channel Channel number
 * @retval Temperature in °C
 */
static int16_t ConvertTemperatureRaw(uint16_t raw_value, uint8_t channel)
{
    /* Convert ADC value to voltage
     * 16-bit ADC, 4.096V reference
     */
    uint32_t voltage_mV = ((uint32_t)raw_value * 4096) / 65535;

    /* BTS7008 status pin temperature sensing
     * Typical: V_ST ≈ 1.0V @ 25°C
     * Temperature coefficient: ~6mV/°C
     *
     * Temp(°C) = (V_ST - 1000mV) / 6mV + 25°C
     */
    int32_t temp_C = ((int32_t)voltage_mV - 1000) / 6 + 25;

    /* Clamp to reasonable range */
    if (temp_C < -40) temp_C = -40;
    if (temp_C > 175) temp_C = 175;

    return (int16_t)temp_C;
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
