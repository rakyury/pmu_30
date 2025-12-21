--[[
******************************************************************************
* @file           : lua_examples.lua
* @brief          : PMU-30 Lua Scripting Examples
* @author         : R2 m-sport
* @date           : 2025-12-21
******************************************************************************
* @attention
*
* These examples demonstrate the PMU-30 Lua API for:
* - Channel access and manipulation
* - Logic function creation
* - System monitoring
* - Custom control algorithms
*
******************************************************************************
]]

-- ============================================================================
-- Example 1: Simple channel read/write
-- ============================================================================

function example1_channel_access()
    -- Read analog input (brake pressure sensor on channel 0)
    local brake_pressure = channel.get(0)
    print("Brake pressure: " .. brake_pressure .. " bar")

    -- Write to output channel (fuel pump on channel 100)
    if brake_pressure > 5000 then
        channel.set(100, 1000)  -- Turn on at 100%
    else
        channel.set(100, 0)      -- Turn off
    end

    -- Get channel info
    local info = channel.info(0)
    if info then
        print("Channel name: " .. info.name)
        print("Min: " .. info.min .. ", Max: " .. info.max)
        print("Unit: " .. info.unit)
    end
end

-- ============================================================================
-- Example 2: Find channel by name
-- ============================================================================

function example2_find_channel()
    -- Find channel by name instead of ID
    local rpm_ch = channel.find("Engine_RPM")

    if rpm_ch then
        local rpm = channel.get(rpm_ch)
        print("Engine RPM: " .. rpm)

        -- Rev limiter at 9000 RPM
        if rpm > 9000 then
            local ignition_ch = channel.find("Ignition_Cut")
            if ignition_ch then
                channel.set(ignition_ch, 1)  -- Cut ignition
            end
        end
    end
end

-- ============================================================================
-- Example 3: Create logic function (temperature-based fan control)
-- ============================================================================

function example3_logic_function()
    -- Create hysteresis function for cooling fan
    -- ON at 85°C, OFF at 75°C
    local temp_ch = channel.find("Engine_Temp")
    local fan_ch = channel.find("Cooling_Fan")

    if temp_ch and fan_ch then
        local func_id = logic.hysteresis(fan_ch, temp_ch, 85, 75)
        print("Created hysteresis function ID: " .. func_id)
    end
end

-- ============================================================================
-- Example 4: PID controller for boost pressure
-- ============================================================================

function example4_pid_controller()
    -- Create PID controller for boost control
    -- Target: 1.5 bar
    -- Kp=2.0, Ki=0.5, Kd=0.1

    local boost_sensor = channel.find("Boost_Pressure")
    local wastegate = channel.find("Wastegate_PWM")

    if boost_sensor and wastegate then
        local pid_id = logic.pid(
            wastegate,      -- Output channel
            boost_sensor,   -- Input channel (process variable)
            1500,           -- Setpoint (1.5 bar = 1500 mbar)
            2.0,            -- Kp
            0.5,            -- Ki
            0.1             -- Kd
        )
        print("Created PID controller ID: " .. pid_id)
    end
end

-- ============================================================================
-- Example 5: Mathematical operations
-- ============================================================================

function example5_math_operations()
    -- Calculate power: P = V * I
    local voltage_ch = 1000  -- System voltage channel
    local current_ch = 1001  -- System current channel
    local power_ch = 200     -- Virtual channel for power result

    -- Create multiply function (voltage * current / 1000 = power in Watts)
    local func_id = logic.multiply(power_ch, voltage_ch, current_ch)

    -- Read calculated power
    local power = channel.get(power_ch)
    print("Total power: " .. power .. " W")
end

-- ============================================================================
-- Example 6: Comparison and conditional logic
-- ============================================================================

function example6_comparison()
    -- Create comparison: if oil_pressure < 20, turn on warning light
    local oil_pressure = channel.find("Oil_Pressure")
    local warning_light = channel.find("Oil_Warning_LED")

    if oil_pressure and warning_light then
        -- Create "less than" comparison
        local func_id = logic.compare(warning_light, oil_pressure, 20, "<")
        print("Created oil pressure warning function ID: " .. func_id)
    end
end

-- ============================================================================
-- Example 7: Complex control algorithm (launch control)
-- ============================================================================

function example7_launch_control()
    -- Launch control: limit RPM when clutch is engaged and vehicle speed is low

    local rpm = channel.get(channel.find("Engine_RPM"))
    local speed = channel.get(channel.find("Vehicle_Speed"))
    local clutch = channel.get(channel.find("Clutch_Switch"))
    local launch_button = channel.get(channel.find("Launch_Button"))

    -- Launch control conditions:
    -- - Launch button pressed
    -- - Clutch engaged
    -- - Speed < 5 km/h
    -- - RPM limit at 4000

    if launch_button == 1 and clutch == 1 and speed < 5 then
        if rpm > 4000 then
            -- Cut ignition/fuel
            channel.set(channel.find("Ignition_Cut"), 1)
        else
            channel.set(channel.find("Ignition_Cut"), 0)
        end
    else
        -- Launch control not active
        channel.set(channel.find("Ignition_Cut"), 0)
    end
end

-- ============================================================================
-- Example 8: Traction control (basic)
-- ============================================================================

function example8_traction_control()
    -- Simple traction control: compare front and rear wheel speeds

    local front_left = channel.get(channel.find("Wheel_Speed_FL"))
    local front_right = channel.get(channel.find("Wheel_Speed_FR"))
    local rear_left = channel.get(channel.find("Wheel_Speed_RL"))
    local rear_right = channel.get(channel.find("Wheel_Speed_RR"))

    -- Calculate average speeds
    local front_avg = (front_left + front_right) / 2
    local rear_avg = (rear_left + rear_right) / 2

    -- If rear wheels spin 10% faster than front, reduce power
    local slip_threshold = front_avg * 1.1

    if rear_avg > slip_threshold then
        -- Reduce throttle by 20%
        local throttle = channel.get(channel.find("Throttle_Position"))
        local reduced = throttle * 0.8
        channel.set(channel.find("Throttle_Output"), reduced)

        -- Turn on TC indicator
        channel.set(channel.find("TC_Indicator"), 1)
    else
        -- No traction control intervention
        local throttle = channel.get(channel.find("Throttle_Position"))
        channel.set(channel.find("Throttle_Output"), throttle)
        channel.set(channel.find("TC_Indicator"), 0)
    end
end

-- ============================================================================
-- Example 9: System monitoring and telemetry
-- ============================================================================

function example9_system_monitor()
    -- Monitor system health and report

    local voltage = system.voltage()
    local current = system.current()
    local temp = system.temperature()
    local uptime = system.uptime()

    print("=== System Status ===")
    print("Voltage: " .. voltage .. " mV")
    print("Current: " .. current .. " mA")
    print("Temperature: " .. temp .. " °C")
    print("Uptime: " .. (uptime / 1000) .. " seconds")

    -- Check for warnings
    if voltage < 11000 then
        print("WARNING: Low battery voltage!")
        channel.set(channel.find("Battery_Warning"), 1)
    end

    if temp > 85 then
        print("WARNING: High MCU temperature!")
        channel.set(channel.find("Temp_Warning"), 1)
    end

    if current > 50000 then
        print("WARNING: High current draw!")
    end
end

-- ============================================================================
-- Example 10: Periodic execution (main loop)
-- ============================================================================

function main()
    -- This function is called periodically by the PMU-30 firmware

    -- Run system monitoring every cycle
    example9_system_monitor()

    -- Run traction control if enabled
    local tc_enabled = channel.get(channel.find("TC_Enable"))
    if tc_enabled == 1 then
        example8_traction_control()
    end

    -- Run launch control
    example7_launch_control()

    -- Small delay to prevent CPU overload
    sleep(10)
end

-- ============================================================================
-- Example 11: List all channels
-- ============================================================================

function example11_list_channels()
    local channels = channel.list()

    print("=== Channel List ===")
    for i, ch in ipairs(channels) do
        print(i .. ": " .. ch.name .. " = " .. ch.value)
    end
end

-- ============================================================================
-- Example 12: Advanced math (gear calculation)
-- ============================================================================

function example12_gear_calculation()
    -- Calculate current gear based on engine RPM and vehicle speed

    local rpm = channel.get(channel.find("Engine_RPM"))
    local speed = channel.get(channel.find("Vehicle_Speed"))

    if speed > 0 and rpm > 0 then
        -- Simple gear detection based on RPM/speed ratio
        local ratio = rpm / speed

        local gear = 0
        if ratio > 200 and ratio < 250 then gear = 1
        elseif ratio > 150 and ratio < 200 then gear = 2
        elseif ratio > 100 and ratio < 150 then gear = 3
        elseif ratio > 70 and ratio < 100 then gear = 4
        elseif ratio > 50 and ratio < 70 then gear = 5
        elseif ratio > 35 and ratio < 50 then gear = 6
        end

        -- Write calculated gear to virtual channel
        channel.set(channel.find("Current_Gear"), gear)
        print("Calculated gear: " .. gear)
    end
end

-- ============================================================================
-- Run examples
-- ============================================================================

print("=== PMU-30 Lua Examples ===")
print("Running examples...")

-- Run individual examples (comment out as needed)
-- example1_channel_access()
-- example2_find_channel()
-- example3_logic_function()
-- example4_pid_controller()
-- example5_math_operations()
-- example6_comparison()
-- example11_list_channels()
-- example12_gear_calculation()

-- Start main loop
-- main()

print("Examples completed!")

--[[
******************************************************************************
END OF FILE
******************************************************************************
]]
