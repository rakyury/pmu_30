--[[
    PMU-30 Basic Lua Script Example

    This script demonstrates basic PMU API usage:
    - Reading inputs
    - Controlling outputs
    - Using virtual channels
    - Logging
--]]

-- Constants
local INPUT_BUTTON = 0
local OUTPUT_LED = 5
local VIRT_COUNTER = 0

-- Main function (called periodically)
function main()
    -- Read button input (ADC channel 0)
    local button_value = getInput(INPUT_BUTTON)

    -- Check if button is pressed (>2.5V = >2048 ADC)
    if button_value > 2048 then
        -- Turn on LED output
        setOutput(OUTPUT_LED, 1, 0)

        -- Increment counter in virtual channel
        local count = getVirtual(VIRT_COUNTER)
        setVirtual(VIRT_COUNTER, count + 1)

        -- Log event
        log("Button pressed! Count: " .. tostring(count + 1))
    else
        -- Turn off LED
        setOutput(OUTPUT_LED, 0, 0)
    end
end

-- Auto-run main function
main()
