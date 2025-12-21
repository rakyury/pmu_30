--[[
    PMU-30 CAN Processing Example

    This script demonstrates CAN message processing:
    - Reading CAN data from virtual channels
    - Processing vehicle data
    - Controlling outputs based on CAN signals
--]]

-- CAN virtual channels (configured via DBC)
local CAN_ENGINE_RPM = 100
local CAN_VEHICLE_SPEED = 101
local CAN_COOLANT_TEMP = 102
local CAN_THROTTLE_POS = 103

-- Outputs
local OUT_SHIFT_LIGHT = 15
local OUT_LAUNCH_CONTROL = 16
local OUT_TRACTION_CONTROL = 17

-- Configuration
local SHIFT_RPM = 6500
local LAUNCH_RPM_MIN = 3000
local LAUNCH_RPM_MAX = 5000
local TRACTION_SPEED_LIMIT = 80  -- km/h

function process_can_data()
    -- Read CAN signals from virtual channels
    local rpm = getVirtual(CAN_ENGINE_RPM)
    local speed = getVirtual(CAN_VEHICLE_SPEED)
    local coolant = getVirtual(CAN_COOLANT_TEMP)
    local throttle = getVirtual(CAN_THROTTLE_POS)

    -- Shift light control
    if rpm > SHIFT_RPM then
        setOutput(OUT_SHIFT_LIGHT, 1, 100)  -- Full brightness
    elseif rpm > (SHIFT_RPM - 500) then
        -- Blink when approaching shift point
        local blink = (getVirtual(99) % 10) < 5
        setOutput(OUT_SHIFT_LIGHT, blink and 1 or 0, 100)
    else
        setOutput(OUT_SHIFT_LIGHT, 0, 0)
    end

    -- Launch control (2-step rev limiter)
    if speed < 5 and throttle > 90 then
        -- Vehicle stopped, throttle wide open
        if rpm > LAUNCH_RPM_MAX then
            -- Cut ignition
            setOutput(OUT_LAUNCH_CONTROL, 1, 0)
        elseif rpm < LAUNCH_RPM_MIN then
            -- Restore ignition
            setOutput(OUT_LAUNCH_CONTROL, 0, 0)
        end
    else
        -- Normal operation
        setOutput(OUT_LAUNCH_CONTROL, 0, 0)
    end

    -- Basic traction control
    -- (In real application, would compare wheel speeds)
    if speed < TRACTION_SPEED_LIMIT and throttle > 50 then
        local tc_active = getVirtual(50)
        if rpm > 7000 then
            -- Cut power
            setOutput(OUT_TRACTION_CONTROL, 1, 0)
            setVirtual(50, 1)
        end
    else
        setOutput(OUT_TRACTION_CONTROL, 0, 0)
        setVirtual(50, 0)
    end

    -- Increment counter for timing
    local count = getVirtual(99)
    setVirtual(99, (count + 1) % 1000)

    -- Log every 100 cycles (1 second at 100Hz)
    if count % 100 == 0 then
        log(string.format("RPM:%d Speed:%d Coolant:%d Throttle:%d%%",
            rpm, speed, coolant, throttle))
    end
end

-- Run CAN processing
process_can_data()
