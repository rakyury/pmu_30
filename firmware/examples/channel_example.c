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
 * Пример 1: Регистрация физических каналов
 */
void Example1_RegisterPhysicalChannels(void)
{
    PMU_Channel_t channel;

    /* Регистрация аналогового входа (датчик давления тормозов) */
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

    /* Регистрация цифрового входа (кнопка на руле) */
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

    /* Регистрация силового выхода (топливный насос) */
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

    /* Регистрация PWM выхода (вентилятор) */
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

    /* Регистрация H-bridge (стеклоподъемник) */
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
 * Пример 2: Регистрация виртуальных каналов
 */
void Example2_RegisterVirtualChannels(void)
{
    PMU_Channel_t channel;

    /* CAN вход - обороты двигателя */
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

    /* Вычисляемое значение - мощность */
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

    /* Логическая функция - сигнализация перегрева */
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

    /* PID регулятор */
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
 * Пример 3: Чтение значений каналов
 */
void Example3_ReadChannels(void)
{
    /* Чтение по ID */
    int32_t brake_pressure = PMU_Channel_GetValue(0);
    printf("Brake pressure: %ld bar\n", brake_pressure);

    /* Чтение по имени */
    const PMU_Channel_t* ch = PMU_Channel_GetByName("Engine_RPM");
    if (ch) {
        int32_t rpm = PMU_Channel_GetValue(ch->channel_id);
        printf("Engine RPM: %ld rpm\n", rpm);
    }

    /* Чтение системных значений */
    int32_t battery_v = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
    int32_t total_i = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_TOTAL_I);
    int32_t temp = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_MCU_TEMP);

    printf("Battery: %ld mV, Current: %ld mA, Temp: %ld C\n",
           battery_v, total_i, temp);
}

/**
 * Пример 4: Управление выходами
 */
void Example4_SetOutputs(void)
{
    /* Включить топливный насос на 100% */
    PMU_Channel_SetValue(100, 1000);  /* Fuel_Pump = 100% */

    /* Установить вентилятор на 50% */
    PMU_Channel_SetValue(105, 500);   /* Cooling_Fan = 50% */

    /* Стеклоподъемник вверх (70%) */
    PMU_Channel_SetValue(150, 700);   /* Window_Motor = +70% (forward) */

    /* Стеклоподъемник вниз (70%) */
    PMU_Channel_SetValue(150, -700);  /* Window_Motor = -70% (reverse) */

    /* Остановить стеклоподъемник */
    PMU_Channel_SetValue(150, 0);     /* Window_Motor = 0% (coast) */
}

/**
 * Пример 5: Логическая функция с каналами
 */
void Example5_LogicFunction(void)
{
    /* Включить вентилятор, если температура > 80°C ИЛИ давление > 3 бар */
    int32_t temp = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_MCU_TEMP);
    int32_t pressure = PMU_Channel_GetValue(0);  /* Brake_Pressure */

    bool fan_on = (temp > 80) || (pressure > 3000);

    /* Установить вентилятор */
    PMU_Channel_SetValue(105, fan_on ? 1000 : 0);

    /* Установить сигнализацию перегрева */
    PMU_Channel_SetValue(300, temp > 100 ? 1 : 0);
}

/**
 * Пример 6: Автоматическое управление (PID)
 */
void Example6_PIDControl(void)
{
    /* Целевая температура 75°C */
    const int32_t target_temp = 75;

    /* Текущая температура */
    int32_t current_temp = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_MCU_TEMP);

    /* Ошибка */
    int32_t error = target_temp - current_temp;

    /* Простой P-регулятор (для примера) */
    int32_t fan_speed = error * 10;  /* Kp = 10 */

    /* Ограничение 0-100% */
    if (fan_speed < 0) fan_speed = 0;
    if (fan_speed > 1000) fan_speed = 1000;

    /* Установить скорость вентилятора */
    PMU_Channel_SetValue(105, fan_speed);

    /* Или использовать встроенный PID канал */
    PMU_Channel_SetValue(350, fan_speed);
}

/**
 * Пример 7: Получение информации о канале
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
 * Пример 8: Список всех каналов
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

    /* Статистика */
    const PMU_ChannelStats_t* stats = PMU_Channel_GetStats();
    printf("\nStatistics:\n");
    printf("  Total:    %d\n", stats->total_channels);
    printf("  Inputs:   %d\n", stats->input_channels);
    printf("  Outputs:  %d\n", stats->output_channels);
    printf("  Physical: %d\n", stats->physical_channels);
    printf("  Virtual:  %d\n", stats->virtual_channels);
}

/**
 * Пример 9: Включение/выключение каналов
 */
void Example9_EnableDisable(void)
{
    /* Отключить топливный насос */
    PMU_Channel_SetEnabled(100, false);

    /* Проверка */
    int32_t value = PMU_Channel_GetValue(100);
    printf("Fuel pump (disabled): %ld\n", value);  /* Вернет 0 */

    /* Снова включить */
    PMU_Channel_SetEnabled(100, true);
    PMU_Channel_SetValue(100, 1000);  /* Теперь работает */
}

/**
 * Пример 10: Вычисление мощности из виртуального канала
 */
void Example10_CalculatedPower(void)
{
    /* Напряжение и ток - системные каналы */
    int32_t voltage_mv = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_BATTERY_V);
    int32_t current_ma = PMU_Channel_GetValue(PMU_CHANNEL_SYSTEM_TOTAL_I);

    /* P = V × I (в мВт, затем в Вт) */
    int32_t power_w = (voltage_mv * current_ma) / 1000000;

    /* Записать в виртуальный канал "Total_Power" */
    /* (предполагается, что логика обновляет канал 260) */

    printf("Power: %ld W (V=%ld mV, I=%ld mA)\n",
           power_w, voltage_mv, current_ma);
}

/**
 * Главная функция примеров
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
