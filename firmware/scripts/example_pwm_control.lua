--[[
    PMU-30 PWM Control Example

    This script demonstrates PWM output control:
    - Reading analog input (potentiometer)
    - Scaling input to PWM duty cycle
    - Controlling fan speed based on temperature
--]]

-- Configuration
local INPUT_POT = 1         -- Potentiometer on ADC1
local INPUT_TEMP_SENSOR = 2 -- Temperature sensor on ADC2
local OUTPUT_FAN = 10       -- Fan output on channel 10

-- Temperature thresholds (ADC values)
local TEMP_LOW = 1000       -- ~30°C
local TEMP_HIGH = 3000      -- ~70°C

function control_fan()
    -- Read temperature sensor
    local temp_adc = getInput(INPUT_TEMP_SENSOR)

    -- Calculate fan speed based on temperature
    local fan_pwm = 0

    if temp_adc < TEMP_LOW then
        -- Temperature OK - fan off
        fan_pwm = 0
    elseif temp_adc > TEMP_HIGH then
        -- Too hot - full speed
        fan_pwm = 100
    else
        -- Linear interpolation
        fan_pwm = ((temp_adc - TEMP_LOW) * 100) / (TEMP_HIGH - TEMP_LOW)
    end

    -- Apply PWM to fan output
    setOutput(OUTPUT_FAN, 1, fan_pwm)

    -- Log status every 100 calls
    local count = getVirtual(99)
    if count >= 100 then
        log(string.format("Temp ADC: %d, Fan PWM: %d%%", temp_adc, fan_pwm))
        setVirtual(99, 0)
    else
        setVirtual(99, count + 1)
    end
end

-- Run control loop
control_fan()
