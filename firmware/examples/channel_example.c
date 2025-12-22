/**
 ******************************************************************************
 * @file           : channel_example.c
 * @brief          : Channel Abstraction Usage Examples
 * @author         : R2 m-sport
 * @date           : 2025-12-21
 ******************************************************************************
 */

#include "pmu_channel.h"
#include <stdio.h>

/**
 * Example 1: Register physical channels
 */
void Example1_RegisterPhysicalChannels(void)
{
    PMU_Channel_t channel;

    /* Register analog input (brake pressure sensor) */
    channel = (PMU_Channel_t){
        .channel_id = 0,
        .type = PMU_CHANNEL_INPUT_ANALOG,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_RAW,
        .physical_index = 0,  /* ADC channel 0 */
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 1023,
        .name = "Brake_Pressure",
        .unit = "bar"
    };
    PMU_Channel_Register(&channel);

    /* Register digital input (steering wheel button) */
    channel = (PMU_Channel_t){
        .channel_id = 5,
        .type = PMU_CHANNEL_INPUT_DIGITAL,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_BOOLEAN,
        .physical_index = 5,
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 1,
        .name = "Steering_Button_OK",
        .unit = ""
    };
    PMU_Channel_Register(&channel);

    /* Register power output (fuel pump) */
    channel = (PMU_Channel_t){
        .channel_id = 100,
        .type = PMU_CHANNEL_OUTPUT_POWER,
        .direction = PMU_CHANNEL_DIR_OUTPUT,
        .format = PMU_CHANNEL_FORMAT_PERCENT,
        .physical_index = 0,  /* PROFET channel 0 */
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 1000,
        .name = "Fuel_Pump",
        .unit = "%"
    };
    PMU_Channel_Register(&channel);

    /* Register PWM output (cooling fan) */
    channel = (PMU_Channel_t){
        .channel_id = 105,
        .type = PMU_CHANNEL_OUTPUT_PWM,
        .direction = PMU_CHANNEL_DIR_OUTPUT,
        .format = PMU_CHANNEL_FORMAT_PERCENT,
        .physical_index = 5,  /* PROFET channel 5 */
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 1000,
        .name = "Cooling_Fan",
        .unit = "%"
    };
    PMU_Channel_Register(&channel);

    /* Register H-bridge (window motor) */
    channel = (PMU_Channel_t){
        .channel_id = 150,
        .type = PMU_CHANNEL_OUTPUT_HBRIDGE,
        .direction = PMU_CHANNEL_DIR_OUTPUT,
        .format = PMU_CHANNEL_FORMAT_SIGNED,
        .physical_index = 0,  /* H-bridge 0 */
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = -1000,
        .max_value = 1000,
        .name = "Window_Motor",
        .unit = "%"
    };
    PMU_Channel_Register(&channel);
}

/**
 * Example 2: Register virtual channels
 */
void Example2_RegisterVirtualChannels(void)
{
    PMU_Channel_t channel;

    /* CAN input - engine RPM */
    channel = (PMU_Channel_t){
        .channel_id = 250,
        .type = PMU_CHANNEL_INPUT_CAN,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_RAW,
        .physical_index = 0,
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 9000,
        .name = "Engine_RPM",
        .unit = "rpm"
    };
    PMU_Channel_Register(&channel);

    /* Calculated value - power */
    channel = (PMU_Channel_t){
        .channel_id = 260,
        .type = PMU_CHANNEL_INPUT_CALCULATED,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_RAW,
        .physical_index = 0,
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 100000,
        .name = "Total_Power",
        .unit = "W"
    };
    PMU_Channel_Register(&channel);

    /* Logic function - overheat warning */
    channel = (PMU_Channel_t){
        .channel_id = 300,
        .type = PMU_CHANNEL_OUTPUT_FUNCTION,
        .direction = PMU_CHANNEL_DIR_OUTPUT,
        .format = PMU_CHANNEL_FORMAT_BOOLEAN,
        .physical_index = 0,
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 1,
        .name = "Overheat_Warning",
        .unit = ""
    };
    PMU_Channel_Register(&channel);

    /* PID controller */
    channel = (PMU_Channel_t){
        .channel_id = 350,
        .type = PMU_CHANNEL_OUTPUT_PID,
        .direction = PMU_CHANNEL_DIR_OUTPUT,
        .format = PMU_CHANNEL_FORMAT_PERCENT,
        .physical_index = 0,
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 1000,
        .name = "Fan_PID_Controller",
        .unit = "%"
    };
    PMU_Channel_Register(&channel);
}

/**
 * Example 3: Read channel values
 */
void Example3_ReadChannels(void)
{
    /* Read by ID */
    int32_t brake_pressure = PMU_Channel_GetValue(0);
    printf("Brake pressure: %ld bar\n", brake_pressure);

    /* Read by name */
    const PMU_Channel_t* ch = PMU_Channel_GetByName("Engine_RPM");
    if (ch) {
        int32_t rpm = PMU_Channel_GetValue(ch->channel_id);
        printf("Engine RPM: %ld rpm\n", rpm);
    }

    /* Read system values */
    int32_t battery_v = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
    int32_t total_i = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_TOTAL_I);
    int32_t temp = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_MCU_TEMP);

    printf("Battery: %ld mV, Current: %ld mA, Temp: %ld C\n",
           battery_v, total_i, temp);
}

/**
 * Example 4: Control outputs
 */
void Example4_SetOutputs(void)
{
    /* Enable fuel pump at 100% */
    PMU_Channel_SetValue(100, 1000);  /* Fuel_Pump = 100% */

    /* Set cooling fan to 50% */
    PMU_Channel_SetValue(105, 500);   /* Cooling_Fan = 50% */

    /* Window motor up (70%) */
    PMU_Channel_SetValue(150, 700);   /* Window_Motor = +70% (forward) */

    /* Window motor down (70%) */
    PMU_Channel_SetValue(150, -700);  /* Window_Motor = -70% (reverse) */

    /* Stop window motor */
    PMU_Channel_SetValue(150, 0);     /* Window_Motor = 0% (coast) */
}

/**
 * Example 5: Logic function with channels
 */
void Example5_LogicFunction(void)
{
    /* Enable fan if temperature > 80°C OR pressure > 3 bar */
    int32_t temp = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_MCU_TEMP);
    int32_t pressure = PMU_Channel_GetValue(0);  /* Brake_Pressure */

    bool fan_on = (temp > 80) || (pressure > 3000);

    /* Set cooling fan */
    PMU_Channel_SetValue(105, fan_on ? 1000 : 0);

    /* Set overheat warning */
    PMU_Channel_SetValue(300, temp > 100 ? 1 : 0);
}

/**
 * Example 6: Automatic control (PID)
 */
void Example6_PIDControl(void)
{
    /* Target temperature 75°C */
    const int32_t target_temp = 75;

    /* Current temperature */
    int32_t current_temp = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_MCU_TEMP);

    /* Error */
    int32_t error = target_temp - current_temp;

    /* Simple P-controller (for example) */
    int32_t fan_speed = error * 10;  /* Kp = 10 */

    /* Limit 0-100% */
    if (fan_speed < 0) fan_speed = 0;
    if (fan_speed > 1000) fan_speed = 1000;

    /* Set fan speed */
    PMU_Channel_SetValue(105, fan_speed);

    /* Or use built-in PID channel */
    PMU_Channel_SetValue(350, fan_speed);
}

/**
 * Example 7: Get channel information
 */
void Example7_GetChannelInfo(void)
{
    const PMU_Channel_t* info = PMU_Channel_GetInfo(100);
    if (info) {
        printf("Channel Info:\n");
        printf("  ID:        %d\n", info->channel_id);
        printf("  Name:      %s\n", info->name);
        printf("  Type:      0x%02X\n", info->type);
        printf("  Direction: %d\n", info->direction);
        printf("  Format:    %d\n", info->format);
        printf("  Value:     %ld %s\n", info->value, info->unit);
        printf("  Range:     %ld - %ld\n", info->min_value, info->max_value);
        printf("  Flags:     0x%02X\n", info->flags);
        printf("  Enabled:   %s\n", (info->flags & PMU_CHANNEL_FLAG_ENABLED) ? "Yes" : "No");
    }
}

/**
 * Example 8: List all channels
 */
void Example8_ListAllChannels(void)
{
    PMU_Channel_t channels[100];
    uint16_t count = PMU_Channel_List(channels, 100);

    printf("Total channels: %d\n", count);
    printf("%-5s %-20s %-10s %-10s %s\n",
           "ID", "Name", "Type", "Value", "Unit");
    printf("-------------------------------------------------------------\n");

    for (uint16_t i = 0; i < count; i++) {
        const char* type_str;

        if (PMU_Channel_IsInput(channels[i].type)) {
            type_str = PMU_Channel_IsVirtual(channels[i].type) ? "Virt In" : "Phys In";
        } else {
            type_str = PMU_Channel_IsVirtual(channels[i].type) ? "Virt Out" : "Phys Out";
        }

        printf("%-5d %-20s %-10s %-10ld %s\n",
               channels[i].channel_id,
               channels[i].name,
               type_str,
               channels[i].value,
               channels[i].unit);
    }

    /* Statistics */
    const PMU_ChannelStats_t* stats = PMU_Channel_GetStats();
    printf("\nStatistics:\n");
    printf("  Total:    %d\n", stats->total_channels);
    printf("  Inputs:   %d\n", stats->input_channels);
    printf("  Outputs:  %d\n", stats->output_channels);
    printf("  Physical: %d\n", stats->physical_channels);
    printf("  Virtual:  %d\n", stats->virtual_channels);
}

/**
 * Example 9: Enable/Disable channels
 */
void Example9_EnableDisable(void)
{
    /* Disable fuel pump */
    PMU_Channel_SetEnabled(100, false);

    /* Check */
    int32_t value = PMU_Channel_GetValue(100);
    printf("Fuel pump (disabled): %ld\n", value);  /* Returns 0 */

    /* Enable again */
    PMU_Channel_SetEnabled(100, true);
    PMU_Channel_SetValue(100, 1000);  /* Now it works */
}

/**
 * Example 10: Calculate power from virtual channel
 */
void Example10_CalculatedPower(void)
{
    /* Voltage and current - system channels */
    int32_t voltage_mv = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
    int32_t current_ma = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_TOTAL_I);

    /* P = V × I (in mW, then W) */
    int32_t power_w = (voltage_mv * current_ma) / 1000000;

    /* Write to virtual channel "Total_Power" */
    /* (assuming logic updates channel 260) */

    printf("Power: %ld W (V=%ld mV, I=%ld mA)\n",
           power_w, voltage_mv, current_ma);
}

/**
 * Main examples function
 */
void RunChannelExamples(void)
{
    printf("=== PMU-30 Channel Abstraction Examples ===\n\n");

    printf("Example 1: Registering physical channels...\n");
    Example1_RegisterPhysicalChannels();

    printf("\nExample 2: Registering virtual channels...\n");
    Example2_RegisterVirtualChannels();

    printf("\nExample 3: Reading channels...\n");
    Example3_ReadChannels();

    printf("\nExample 4: Setting outputs...\n");
    Example4_SetOutputs();

    printf("\nExample 5: Logic function...\n");
    Example5_LogicFunction();

    printf("\nExample 6: PID control...\n");
    Example6_PIDControl();

    printf("\nExample 7: Getting channel info...\n");
    Example7_GetChannelInfo();

    printf("\nExample 8: Listing all channels...\n");
    Example8_ListAllChannels();

    printf("\nExample 9: Enable/Disable...\n");
    Example9_EnableDisable();

    printf("\nExample 10: Calculated power...\n");
    Example10_CalculatedPower();

    printf("\n=== Examples completed ===\n");
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
