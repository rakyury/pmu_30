/**
 ******************************************************************************
 * @file           : channel_example.c
 * @brief          : Channel Abstraction Usage Examples v2.0
 * @author         : R2 m-sport
 * @date           : 2025-12-29
 ******************************************************************************
 * @attention
 *
 * Updated to use PMU_ChannelClass_t enum and new APIs:
 * - PMU_Channel_UpdateValue() for setting input channel values
 * - PMU_Channel_GenerateID() for dynamic channel allocation
 * - PMU_Channel_GetIndexByID() for string-to-ID lookup
 * - Output sub-channels (status, current, voltage, active, duty)
 * - Constant channels (zero, one)
 *
 ******************************************************************************
 */

#include "pmu_channel.h"
#include <stdio.h>

/**
 * Example 1: Register physical channels
 *
 * Physical channels map to real hardware I/O:
 * - Inputs: ADC (0-5V), digital (on/off), frequency
 * - Outputs: PROFET power switches, PWM, H-bridges
 */
void Example1_RegisterPhysicalChannels(void)
{
    PMU_Channel_t channel;

    /* Register analog input (brake pressure sensor)
     * Channel ID 0-99 are reserved for physical inputs */
    channel = (PMU_Channel_t){
        .channel_id = 0,
        .hw_class = PMU_CHANNEL_CLASS_INPUT_ANALOG,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_VOLTAGE,
        .physical_index = 0,  /* ADC channel 0 */
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 5000,    /* 0-5000 mV */
        .name = "Brake_Pressure",
        .unit = "mV"
    };
    PMU_Channel_Register(&channel);

    /* Register digital input (steering wheel button) */
    channel = (PMU_Channel_t){
        .channel_id = 5,
        .hw_class = PMU_CHANNEL_CLASS_INPUT_DIGITAL,
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

    /* Register frequency input (wheel speed sensor) */
    channel = (PMU_Channel_t){
        .channel_id = 10,
        .hw_class = PMU_CHANNEL_CLASS_INPUT_FREQUENCY,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_INT,
        .physical_index = 0,  /* Frequency input 0 */
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 10000,   /* 0-10000 Hz */
        .name = "Wheel_Speed_FL",
        .unit = "Hz"
    };
    PMU_Channel_Register(&channel);

    /* Register power output (fuel pump)
     * Channel ID 100-199 are reserved for physical outputs */
    channel = (PMU_Channel_t){
        .channel_id = 100,
        .hw_class = PMU_CHANNEL_CLASS_OUTPUT_POWER,
        .direction = PMU_CHANNEL_DIR_OUTPUT,
        .format = PMU_CHANNEL_FORMAT_PERCENT,
        .physical_index = 0,  /* PROFET channel 0 */
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 1000,    /* 0-1000 = 0.0-100.0% */
        .name = "Fuel_Pump",
        .unit = "%"
    };
    PMU_Channel_Register(&channel);

    /* Register PWM output (cooling fan) */
    channel = (PMU_Channel_t){
        .channel_id = 105,
        .hw_class = PMU_CHANNEL_CLASS_OUTPUT_PWM,
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
        .hw_class = PMU_CHANNEL_CLASS_OUTPUT_HBRIDGE,
        .direction = PMU_CHANNEL_DIR_OUTPUT,
        .format = PMU_CHANNEL_FORMAT_SIGNED,
        .physical_index = 0,  /* H-bridge 0 */
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = -1000,   /* -1000 = 100% reverse */
        .max_value = 1000,    /* +1000 = 100% forward */
        .name = "Window_Motor",
        .unit = "%"
    };
    PMU_Channel_Register(&channel);
}

/**
 * Example 2: Register virtual channels
 *
 * Virtual channels are software-based (no physical hardware):
 * - Virtual inputs: CAN bus signals, calculated values
 * - Virtual outputs: Logic functions, lookup tables, PID controllers
 *
 * Channel ID 200-999 are reserved for virtual channels
 */
void Example2_RegisterVirtualChannels(void)
{
    PMU_Channel_t channel;

    /* CAN input - engine RPM */
    channel = (PMU_Channel_t){
        .channel_id = 250,
        .hw_class = PMU_CHANNEL_CLASS_INPUT_CAN,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_INT,
        .physical_index = 0,  /* CAN message index */
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 9000,
        .name = "Engine_RPM",
        .unit = "rpm"
    };
    PMU_Channel_Register(&channel);

    /* Calculated value - total power consumption */
    channel = (PMU_Channel_t){
        .channel_id = 260,
        .hw_class = PMU_CHANNEL_CLASS_INPUT_CALCULATED,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_INT,
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
        .hw_class = PMU_CHANNEL_CLASS_OUTPUT_FUNCTION,
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

    /* Lookup table - fan curve */
    channel = (PMU_Channel_t){
        .channel_id = 310,
        .hw_class = PMU_CHANNEL_CLASS_OUTPUT_TABLE,
        .direction = PMU_CHANNEL_DIR_OUTPUT,
        .format = PMU_CHANNEL_FORMAT_PERCENT,
        .physical_index = 0,  /* Table index */
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 1000,
        .name = "Fan_Curve",
        .unit = "%"
    };
    PMU_Channel_Register(&channel);

    /* PID controller - idle valve control */
    channel = (PMU_Channel_t){
        .channel_id = 350,
        .hw_class = PMU_CHANNEL_CLASS_OUTPUT_PID,
        .direction = PMU_CHANNEL_DIR_OUTPUT,
        .format = PMU_CHANNEL_FORMAT_PERCENT,
        .physical_index = 0,  /* PID controller index */
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 1000,
        .name = "Idle_Valve_PID",
        .unit = "%"
    };
    PMU_Channel_Register(&channel);

    /* Constant number - fixed reference value */
    channel = (PMU_Channel_t){
        .channel_id = 400,
        .hw_class = PMU_CHANNEL_CLASS_OUTPUT_NUMBER,
        .direction = PMU_CHANNEL_DIR_OUTPUT,
        .format = PMU_CHANNEL_FORMAT_INT,
        .physical_index = 0,
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 850,         /* Fixed RPM target */
        .min_value = 0,
        .max_value = 9000,
        .name = "Idle_Target_RPM",
        .unit = "rpm"
    };
    PMU_Channel_Register(&channel);

    /* CAN output - transmit brake status */
    channel = (PMU_Channel_t){
        .channel_id = 500,
        .hw_class = PMU_CHANNEL_CLASS_OUTPUT_CAN,
        .direction = PMU_CHANNEL_DIR_OUTPUT,
        .format = PMU_CHANNEL_FORMAT_BOOLEAN,
        .physical_index = 0,  /* CAN TX message index */
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 1,
        .name = "CAN_Brake_Active",
        .unit = ""
    };
    PMU_Channel_Register(&channel);
}

/**
 * Example 3: Read channel values
 */
void Example3_ReadChannels(void)
{
    /* Read physical input by ID */
    int32_t brake_pressure = PMU_Channel_GetValue(0);
    printf("Brake pressure: %ld mV\n", brake_pressure);

    /* Read by name */
    const PMU_Channel_t* ch = PMU_Channel_GetByName("Engine_RPM");
    if (ch) {
        int32_t rpm = PMU_Channel_GetValue(ch->channel_id);
        printf("Engine RPM: %ld rpm\n", rpm);
    }

    /* Read system channels (ECUMaster compatible: pmuX.*) */
    int32_t battery_v = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
    int32_t total_i = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_TOTAL_I);
    int32_t mcu_temp = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_MCU_TEMP);
    int32_t board_temp_l = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BOARD_TEMP_L);
    int32_t board_temp_r = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BOARD_TEMP_R);

    printf("Battery: %ld mV, Current: %ld mA\n", battery_v, total_i);
    printf("MCU Temp: %ld C, Board L: %ld C, Board R: %ld C\n",
           mcu_temp, board_temp_l, board_temp_r);

    /* Read system status */
    int32_t uptime = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_UPTIME);
    int32_t status = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_STATUS);
    printf("Uptime: %ld s, Status: 0x%lX\n", uptime, status);

    /* Read constant channels */
    int32_t zero = PMU_Channel_GetValue(PMU_CHANNEL_CONST_ZERO);
    int32_t one = PMU_Channel_GetValue(PMU_CHANNEL_CONST_ONE);
    printf("Constants: zero=%ld, one=%ld\n", zero, one);
}

/**
 * Example 4: Read output sub-channels (ECUMaster compatible: pmuX.oY.*)
 *
 * Each physical output has associated read-only sub-channels:
 * - Status: Fault/OK status bits
 * - Current: Measured current in mA
 * - Voltage: Measured voltage in mV
 * - Active: Whether output is currently active (0/1)
 * - Duty: Current duty cycle (0-1000)
 */
void Example4_ReadOutputSubChannels(void)
{
    /* Output index 0 = Fuel Pump (channel 100) */
    uint8_t output_idx = 0;

    int32_t status = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_STATUS_BASE + output_idx);
    int32_t current = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_CURRENT_BASE + output_idx);
    int32_t voltage = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_VOLTAGE_BASE + output_idx);
    int32_t active = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_ACTIVE_BASE + output_idx);
    int32_t duty = PMU_Channel_GetValue(PMU_CHANNEL_OUTPUT_DUTY_BASE + output_idx);

    printf("Output %d (Fuel Pump):\n", output_idx);
    printf("  Status: 0x%lX\n", status);
    printf("  Current: %ld mA\n", current);
    printf("  Voltage: %ld mV\n", voltage);
    printf("  Active: %s\n", active ? "Yes" : "No");
    printf("  Duty: %ld.%ld%%\n", duty / 10, duty % 10);

    /* Read analog input sub-channel (voltage) */
    uint8_t analog_idx = 0;
    int32_t analog_voltage = PMU_Channel_GetValue(PMU_CHANNEL_ANALOG_VOLTAGE_BASE + analog_idx);
    printf("Analog %d voltage: %ld mV\n", analog_idx, analog_voltage);
}

/**
 * Example 5: Control outputs
 */
void Example5_SetOutputs(void)
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
 * Example 6: Update input channel values
 *
 * Use PMU_Channel_UpdateValue() to sync hardware input states.
 * Unlike PMU_Channel_SetValue(), this works for INPUT channels.
 */
void Example6_UpdateInputValues(void)
{
    /* Simulate ADC reading update */
    int32_t adc_reading = 2500;  /* 2500 mV from ADC */
    PMU_Channel_UpdateValue(0, adc_reading);  /* Brake_Pressure */

    /* Update digital input state */
    PMU_Channel_UpdateValue(5, 1);  /* Steering_Button_OK = pressed */

    /* Update CAN input from received message */
    int32_t engine_rpm = 3500;
    PMU_Channel_UpdateValue(250, engine_rpm);  /* Engine_RPM */

    /* Update calculated value */
    int32_t voltage_mv = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
    int32_t current_ma = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_TOTAL_I);
    int32_t power_w = (voltage_mv * current_ma) / 1000000;
    PMU_Channel_UpdateValue(260, power_w);  /* Total_Power */
}

/**
 * Example 7: Logic function with channels
 */
void Example7_LogicFunction(void)
{
    /* Enable fan if temperature > 80C OR pressure > 3V */
    int32_t temp = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_MCU_TEMP);
    int32_t pressure = PMU_Channel_GetValue(0);  /* Brake_Pressure in mV */

    bool fan_on = (temp > 80) || (pressure > 3000);

    /* Set cooling fan */
    PMU_Channel_SetValue(105, fan_on ? 1000 : 0);

    /* Set overheat warning */
    PMU_Channel_SetValue(300, temp > 100 ? 1 : 0);
}

/**
 * Example 8: Get channel by string ID
 *
 * PMU_Channel_GetIndexByID() converts string names to numeric IDs.
 * Useful for config parsing where channels are referenced by name.
 */
void Example8_GetChannelByString(void)
{
    /* Look up channel by name string */
    uint16_t id = PMU_Channel_GetIndexByID("Fuel_Pump");
    if (id != 0xFFFF) {
        printf("Found 'Fuel_Pump' at channel ID %d\n", id);
        int32_t value = PMU_Channel_GetValue(id);
        printf("Current value: %ld\n", value);
    } else {
        printf("Channel 'Fuel_Pump' not found\n");
    }

    /* Also works with system channel names */
    id = PMU_Channel_GetIndexByID("pmu.battery");  /* ECUMaster alias */
    if (id != 0xFFFF) {
        printf("System battery voltage channel: %d\n", id);
    }
}

/**
 * Example 9: Generate dynamic channel IDs
 *
 * PMU_Channel_GenerateID() allocates unique IDs for runtime channels.
 */
void Example9_DynamicChannels(void)
{
    /* Generate unique IDs for dynamically created channels */
    uint16_t dynamic_id1 = PMU_Channel_GenerateID();
    uint16_t dynamic_id2 = PMU_Channel_GenerateID();

    printf("Generated dynamic IDs: %d, %d\n", dynamic_id1, dynamic_id2);

    /* Create runtime channel with generated ID */
    PMU_Channel_t channel = {
        .channel_id = dynamic_id1,
        .hw_class = PMU_CHANNEL_CLASS_INPUT_CALCULATED,
        .direction = PMU_CHANNEL_DIR_INPUT,
        .format = PMU_CHANNEL_FORMAT_INT,
        .physical_index = 0,
        .flags = PMU_CHANNEL_FLAG_ENABLED,
        .value = 0,
        .min_value = 0,
        .max_value = 65535,
        .name = "Dynamic_Counter",
        .unit = ""
    };
    PMU_Channel_Register(&channel);
}

/**
 * Example 10: Get channel information
 */
void Example10_GetChannelInfo(void)
{
    const PMU_Channel_t* info = PMU_Channel_GetInfo(100);
    if (info) {
        printf("Channel Info:\n");
        printf("  ID:        %d\n", info->channel_id);
        printf("  Name:      %s\n", info->name);
        printf("  HW Class:  0x%02X\n", info->hw_class);
        printf("  Direction: %d\n", info->direction);
        printf("  Format:    %d\n", info->format);
        printf("  Value:     %ld %s\n", info->value, info->unit);
        printf("  Range:     %ld - %ld\n", info->min_value, info->max_value);
        printf("  Flags:     0x%02X\n", info->flags);
        printf("  Enabled:   %s\n", (info->flags & PMU_CHANNEL_FLAG_ENABLED) ? "Yes" : "No");
        printf("  Inverted:  %s\n", (info->flags & PMU_CHANNEL_FLAG_INVERTED) ? "Yes" : "No");
        printf("  Fault:     %s\n", (info->flags & PMU_CHANNEL_FLAG_FAULT) ? "Yes" : "No");
        printf("  Override:  %s\n", (info->flags & PMU_CHANNEL_FLAG_OVERRIDE) ? "Yes" : "No");
    }
}

/**
 * Example 11: List all channels
 */
void Example11_ListAllChannels(void)
{
    PMU_Channel_t channels[100];
    uint16_t count = PMU_Channel_List(channels, 100);

    printf("Total channels: %d\n", count);
    printf("%-5s %-20s %-12s %-10s %s\n",
           "ID", "Name", "Type", "Value", "Unit");
    printf("-------------------------------------------------------------\n");

    for (uint16_t i = 0; i < count; i++) {
        const char* type_str;

        /* Classify by hardware class */
        if (PMU_Channel_IsInput(channels[i].hw_class)) {
            type_str = PMU_Channel_IsVirtual(channels[i].hw_class) ? "Virt In" : "Phys In";
        } else {
            type_str = PMU_Channel_IsVirtual(channels[i].hw_class) ? "Virt Out" : "Phys Out";
        }

        printf("%-5d %-20s %-12s %-10ld %s\n",
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
 * Example 12: Enable/Disable channels
 */
void Example12_EnableDisable(void)
{
    /* Disable fuel pump */
    PMU_Channel_SetEnabled(100, false);

    /* Check - disabled channels return 0 */
    int32_t value = PMU_Channel_GetValue(100);
    printf("Fuel pump (disabled): %ld\n", value);  /* Returns 0 */

    /* Enable again */
    PMU_Channel_SetEnabled(100, true);
    PMU_Channel_SetValue(100, 1000);  /* Now it works */

    value = PMU_Channel_GetValue(100);
    printf("Fuel pump (enabled): %ld\n", value);  /* Returns 1000 */
}

/**
 * Main examples function
 */
void RunChannelExamples(void)
{
    printf("=== PMU-30 Channel Abstraction Examples v2.0 ===\n\n");

    printf("Example 1: Registering physical channels...\n");
    Example1_RegisterPhysicalChannels();

    printf("\nExample 2: Registering virtual channels...\n");
    Example2_RegisterVirtualChannels();

    printf("\nExample 3: Reading channels...\n");
    Example3_ReadChannels();

    printf("\nExample 4: Reading output sub-channels...\n");
    Example4_ReadOutputSubChannels();

    printf("\nExample 5: Setting outputs...\n");
    Example5_SetOutputs();

    printf("\nExample 6: Updating input values...\n");
    Example6_UpdateInputValues();

    printf("\nExample 7: Logic function...\n");
    Example7_LogicFunction();

    printf("\nExample 8: Get channel by string...\n");
    Example8_GetChannelByString();

    printf("\nExample 9: Dynamic channels...\n");
    Example9_DynamicChannels();

    printf("\nExample 10: Getting channel info...\n");
    Example10_GetChannelInfo();

    printf("\nExample 11: Listing all channels...\n");
    Example11_ListAllChannels();

    printf("\nExample 12: Enable/Disable...\n");
    Example12_EnableDisable();

    printf("\n=== Examples completed ===\n");
}

/************************ (C) COPYRIGHT R2 m-sport *****END OF FILE****/
