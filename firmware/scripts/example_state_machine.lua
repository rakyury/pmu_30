--[[
    PMU-30 State Machine Example

    This script implements a simple state machine for:
    - Engine start sequence
    - Safety interlocks
    - Sequential output activation
--]]

-- States
local STATE_IDLE = 0
local STATE_PRIMING = 1
local STATE_CRANKING = 2
local STATE_RUNNING = 3
local STATE_ERROR = 4

-- Outputs
local OUT_FUEL_PUMP = 0
local OUT_STARTER = 1
local OUT_IGNITION = 2
local OUT_ALARM = 3

-- Inputs
local IN_START_BUTTON = 0
local IN_ENGINE_RPM = 1
local IN_OIL_PRESSURE = 2

-- Virtual channels for state
local VIRT_STATE = 0
local VIRT_TIMER = 1

-- Configuration
local PRIME_TIME = 50       -- 500ms at 100Hz
local CRANK_TIMEOUT = 300   -- 3 seconds

function engine_control()
    local state = getVirtual(VIRT_STATE)
    local timer = getVirtual(VIRT_TIMER)

    local start_button = getInput(IN_START_BUTTON)
    local rpm = getInput(IN_ENGINE_RPM)
    local oil_pressure = getInput(IN_OIL_PRESSURE)

    -- State machine
    if state == STATE_IDLE then
        -- All outputs off
        setOutput(OUT_FUEL_PUMP, 0, 0)
        setOutput(OUT_STARTER, 0, 0)
        setOutput(OUT_IGNITION, 0, 0)
        setOutput(OUT_ALARM, 0, 0)

        -- Check for start request
        if start_button > 2048 then
            log("Start requested - entering PRIMING")
            setVirtual(VIRT_STATE, STATE_PRIMING)
            setVirtual(VIRT_TIMER, 0)
        end

    elseif state == STATE_PRIMING then
        -- Turn on fuel pump
        setOutput(OUT_FUEL_PUMP, 1, 0)

        -- Wait for prime time
        timer = timer + 1
        setVirtual(VIRT_TIMER, timer)

        if timer >= PRIME_TIME then
            log("Priming complete - CRANKING")
            setVirtual(VIRT_STATE, STATE_CRANKING)
            setVirtual(VIRT_TIMER, 0)
        end

    elseif state == STATE_CRANKING then
        -- Fuel pump and ignition on
        setOutput(OUT_FUEL_PUMP, 1, 0)
        setOutput(OUT_IGNITION, 1, 0)

        -- Engage starter
        setOutput(OUT_STARTER, 1, 0)

        timer = timer + 1
        setVirtual(VIRT_TIMER, timer)

        -- Check if engine started (RPM > threshold)
        if rpm > 500 then
            log("Engine started - RUNNING")
            setVirtual(VIRT_STATE, STATE_RUNNING)
            setVirtual(VIRT_TIMER, 0)
        elseif timer >= CRANK_TIMEOUT then
            log("Crank timeout - ERROR")
            setVirtual(VIRT_STATE, STATE_ERROR)
        end

    elseif state == STATE_RUNNING then
        -- Normal operation
        setOutput(OUT_FUEL_PUMP, 1, 0)
        setOutput(OUT_IGNITION, 1, 0)
        setOutput(OUT_STARTER, 0, 0)

        -- Safety check - oil pressure
        if oil_pressure < 500 then
            timer = timer + 1
            setVirtual(VIRT_TIMER, timer)

            if timer > 100 then  -- 1 second
                log("Low oil pressure - ERROR")
                setVirtual(VIRT_STATE, STATE_ERROR)
            end
        else
            setVirtual(VIRT_TIMER, 0)
        end

        -- Check for shutdown
        if start_button < 1000 and rpm < 300 then
            log("Shutdown - IDLE")
            setVirtual(VIRT_STATE, STATE_IDLE)
        end

    elseif state == STATE_ERROR then
        -- Error state - shut down and alarm
        setOutput(OUT_FUEL_PUMP, 0, 0)
        setOutput(OUT_STARTER, 0, 0)
        setOutput(OUT_IGNITION, 0, 0)
        setOutput(OUT_ALARM, 1, 0)

        -- Blink alarm
        timer = timer + 1
        setVirtual(VIRT_TIMER, timer)
        if timer % 20 == 0 then  -- Toggle every 200ms
            local alarm_state = getVirtual(10)
            setOutput(OUT_ALARM, 1 - alarm_state, 0)
            setVirtual(10, 1 - alarm_state)
        end
    end
end

-- Run engine control
engine_control()
