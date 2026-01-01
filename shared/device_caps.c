/**
 * @file device_caps.c
 * @brief PMU-30 Device Capabilities Implementation
 */

#include "device_caps.h"
#include <string.h>

/*============================================================================
 * Caps_Init - Initialize capabilities for device type
 *============================================================================*/

void Caps_Init(DeviceCaps_t* caps, DeviceType_t device_type)
{
    if (!caps) return;

    memset(caps, 0, sizeof(DeviceCaps_t));

    caps->magic = CAPS_MAGIC;
    caps->version = CAPS_VERSION;
    caps->device_type = (uint8_t)device_type;

    switch (device_type) {
        case DEVICE_TYPE_PMU30:
            /* Full PMU-30 hardware */
            caps->hw_revision = 1;
            caps->hw_flags =
                CAPS_HAS_PROFET | CAPS_HAS_HBRIDGE |
                CAPS_HAS_ADC | CAPS_HAS_DIN | CAPS_HAS_FREQ | CAPS_HAS_PWM |
                CAPS_HAS_CAN1 | CAPS_HAS_CAN2 | CAPS_HAS_CAN3 | CAPS_HAS_CAN4 |
                CAPS_HAS_LIN |
                CAPS_HAS_WIFI | CAPS_HAS_BLUETOOTH |
                CAPS_HAS_SDCARD | CAPS_HAS_USB |
                CAPS_HAS_RTC | CAPS_HAS_EEPROM | CAPS_HAS_FLASH_EXT;

            caps->sw_flags =
                CAPS_SW_PID | CAPS_SW_TABLES_2D | CAPS_SW_TABLES_3D |
                CAPS_SW_LOGIC | CAPS_SW_TIMERS | CAPS_SW_FILTERS | CAPS_SW_MATH |
                CAPS_SW_LUA | CAPS_SW_DATALOG | CAPS_SW_BLINKMARINE |
                CAPS_SW_WIPER_PARK | CAPS_SW_CAN_STREAM;

            caps->profet_count = 30;
            caps->hbridge_count = 4;
            caps->adc_count = 20;
            caps->din_count = 20;
            caps->freq_count = 4;
            caps->pwm_count = 8;
            caps->can_count = 4;
            caps->lin_count = 1;
            caps->dac_count = 2;
            caps->dout_count = 4;

            caps->max_channels = 256;
            caps->max_logic = 32;
            caps->max_timers = 16;
            caps->max_tables = 32;

            caps->flash_size_kb = 2048;
            caps->ram_size_kb = 512;

            caps->max_current_ma = 100000;  /* 100A total */
            caps->per_channel_ma = 20000;   /* 20A per channel */
            caps->hbridge_current_ma = 30000; /* 30A per H-Bridge */
            break;

        case DEVICE_TYPE_NUCLEO_F446:
            /* Nucleo-F446RE - minimal hardware */
            caps->hw_revision = 1;
            caps->hw_flags =
                CAPS_HAS_ADC | CAPS_HAS_DIN | CAPS_HAS_DOUT |
                CAPS_HAS_PWM | CAPS_HAS_CAN1 |
                CAPS_HAS_USB;

            caps->sw_flags =
                CAPS_SW_LOGIC | CAPS_SW_TIMERS |
                CAPS_SW_TABLES_2D;

            caps->profet_count = 0;
            caps->hbridge_count = 0;
            caps->adc_count = 8;
            caps->din_count = 8;
            caps->freq_count = 2;
            caps->pwm_count = 4;
            caps->can_count = 1;
            caps->lin_count = 0;
            caps->dac_count = 2;
            caps->dout_count = 8;

            caps->max_channels = 64;
            caps->max_logic = 8;
            caps->max_timers = 4;
            caps->max_tables = 8;

            caps->flash_size_kb = 512;
            caps->ram_size_kb = 128;

            caps->max_current_ma = 0;  /* No power outputs */
            caps->per_channel_ma = 0;
            caps->hbridge_current_ma = 0;
            break;

        case DEVICE_TYPE_EMULATOR:
            /* Emulator - full software features */
            caps->hw_revision = 0;
            caps->hw_flags =
                CAPS_HAS_PROFET | CAPS_HAS_HBRIDGE |
                CAPS_HAS_ADC | CAPS_HAS_DIN | CAPS_HAS_FREQ | CAPS_HAS_PWM |
                CAPS_HAS_CAN1 | CAPS_HAS_CAN2 |
                CAPS_HAS_USB;

            caps->sw_flags =
                CAPS_SW_PID | CAPS_SW_TABLES_2D | CAPS_SW_TABLES_3D |
                CAPS_SW_LOGIC | CAPS_SW_TIMERS | CAPS_SW_FILTERS | CAPS_SW_MATH |
                CAPS_SW_DATALOG | CAPS_SW_BLINKMARINE |
                CAPS_SW_WIPER_PARK | CAPS_SW_CAN_STREAM;

            caps->profet_count = 30;
            caps->hbridge_count = 4;
            caps->adc_count = 20;
            caps->din_count = 20;
            caps->freq_count = 4;
            caps->pwm_count = 8;
            caps->can_count = 2;
            caps->lin_count = 0;
            caps->dac_count = 0;
            caps->dout_count = 0;

            caps->max_channels = 256;
            caps->max_logic = 32;
            caps->max_timers = 16;
            caps->max_tables = 32;

            caps->flash_size_kb = 8192;  /* Virtual */
            caps->ram_size_kb = 1024;    /* Virtual */

            caps->max_current_ma = 100000;
            caps->per_channel_ma = 20000;
            caps->hbridge_current_ma = 30000;
            break;

        default:
            caps->device_type = DEVICE_TYPE_UNKNOWN;
            break;
    }
}
