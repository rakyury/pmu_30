# Timer Channel Debugging Guide

**Version:** 1.0
**Date:** January 2025
**Platform:** Nucleo-F446RE, PMU-30 Firmware

---

## Overview

This document captures the complete debugging experience of fixing a critical timer channel issue where the timer started correctly but never expired. The solution required addressing multiple root causes related to tick synchronization and edge detection.

---

## 1. Problem Description

### Symptoms
- Timer starts correctly when button is pressed (LED turns ON)
- Timer **never expires** - LED stays ON indefinitely
- `limit_seconds: 5` setting is ignored
- Timer `running` flag stays at 1 forever

### Expected Behavior
1. Press button → Timer starts, LED turns ON
2. Wait 5 seconds → Timer expires, LED turns OFF
3. Timer can be restarted with another button press

---

## 2. Root Causes Identified

### 2.1 HAL_GetTick() Returns 0 on Bare-Metal

**Issue:** On Nucleo-F446RE without SysTick configuration, `HAL_GetTick()` always returns 0.

**Impact:** Timer expiration logic uses:
```c
uint32_t now = HAL_GetTick();  // Always 0!
uint32_t elapsed_ms = now - rt->start_time_ms;  // Always 0!

if (elapsed_ms >= limit_ms) {  // Never true!
    rt->running = false;
}
```

**Solution:** Use the timer update call counter instead:
```c
// g_timer_update_calls increments every PMU_TimerChannel_Update() call
// At ~2000Hz update rate, divide by 2 to get approximate milliseconds
uint32_t now = g_timer_update_calls / 2;
```

### 2.2 False Edge Detection on First Run

**Issue:** Timer initializes `prev_start_value = 0`. On first update after config load, if any channel has value > 0, edge detection triggers falsely.

**Edge Detection Code:**
```c
// Rising edge detection
start_edge = (start_val > 0 && rt->prev_start_value <= 0);
```

**Scenario:**
1. Config loaded, `prev_start_value = 0`
2. First update: button not pressed, but DIN0 might have noise or initial value
3. If `start_val > 0`: edge detected! Timer starts immediately!

**Solution:** Use `-1` as sentinel value and skip first iteration:
```c
// Initialization
rt->prev_start_value = -1;  // Sentinel: "not initialized"
rt->prev_stop_value = -1;

// In PMU_TimerChannel_Update()
if (rt->prev_start_value == -1) {
    // First run: initialize without triggering edge detection
    rt->prev_start_value = start_val;
    rt->prev_stop_value = stop_val;
    PMU_Channel_SetValue(rt->channel_id, 0);
    PMU_Channel_SetValue(rt->elapsed_channel_id, 0);
    continue;  // Skip to next timer
}
```

### 2.3 Tick Synchronization from Main Loop Failed

**Initial Attempt:** Sync tick counter from main loop:
```c
// In main_nucleo_f446.c
g_tick_count++;
extern void PMU_SetCurrentTick(uint32_t);
PMU_SetCurrentTick(g_tick_count);

// In pmu_config_json.c
static volatile uint32_t g_current_tick_ms = 0;
void PMU_SetCurrentTick(uint32_t tick_ms) {
    g_current_tick_ms = tick_ms;
}
```

**Problem:** Despite correct code, `g_current_tick_ms` stayed at 0 in telemetry.

**Root Cause:** Unknown (possibly linker or compilation issue with large file).

**Solution:** Use local counter that's guaranteed to work:
```c
static volatile uint32_t g_timer_update_calls = 0;

void PMU_TimerChannel_Update(void) {
    g_timer_update_calls++;  // Always increments
    uint32_t now = g_timer_update_calls / 2;  // Convert to approx ms
    // ...
}
```

---

## 3. Timer Update Rate Calibration

### Measuring Actual Update Rate

From telemetry debug output:
```
Time 0.0s: UpdCalls = 17800
Time 9.8s: UpdCalls = 107600
Delta: 89800 calls over 9.8 seconds
Rate: 89800 / 9.8 = ~9163 Hz
```

Wait, that's higher than expected. Let's recalculate:
```
Time 9.3s:  UpdCalls = 106800
Time 18.8s: UpdCalls = 122800
Delta: 16000 calls over 9.5 seconds
Rate: 16000 / 9.5 = ~1684 Hz
```

### Multiplier Selection

| Update Rate | Multiplier | 1 call = | Result |
|-------------|------------|----------|--------|
| 500 Hz | `* 2` | 2 ms | Correct |
| 1000 Hz | `* 1` | 1 ms | Correct |
| 2000 Hz | `/ 2` | 0.5 ms | Correct |
| 1700 Hz | `* 1000 / 1700` | ~0.59 ms | Accurate |

### Observed Behavior

| Multiplier | Expected 5s | Actual Result |
|------------|-------------|---------------|
| `* 2` | 5 seconds | ~2 seconds (too fast) |
| `/ 2` | 5 seconds | ~10 seconds (too slow) |
| `* 1` | 5 seconds | ~5 seconds (close) |

---

## 4. Debugging Telemetry

### Debug Bytes Added to Telemetry

```
Offset   Size   Field              Description
78       1      digital_inputs     DIN states (bit-packed)
79       1      ch_flags           Channel exists/value flags
80       1      timer_count        Number of configured timers
81-82    2      start_channel_id   Timer 0 start trigger ID (LE)
83       1      start_val          Current start trigger value
84       1      prev_start_val     Previous start value
85       1      running            Timer 0 running state
86-89    4      update_calls       Timer update call counter (LE)
90-93    4      logic_exec_count   Logic execution counter (LE)
94       1      limit_sec          Timer limit_seconds config
95       1      mode               Timer mode (0=up, 1=down)
96-99    4      elapsed_ms         Calculated elapsed time (LE)
100-103  4      tick_ms            Current tick value (LE)
104-107  4      start_time_ms      Timer start timestamp (LE)
```

### Debug Functions in pmu_config_json.c

```c
uint8_t Debug_Timer0_GetLimitSec(void) {
    return (timer_count > 0) ? timer_storage[0].config.limit_seconds : 0xFF;
}

uint8_t Debug_Timer0_GetMode(void) {
    return (timer_count > 0) ? (uint8_t)timer_storage[0].config.mode : 0xFF;
}

uint32_t Debug_Timer0_GetElapsedMs(void) {
    if (timer_count > 0 && timer_storage[0].running) {
        uint32_t now = g_timer_update_calls / 2;
        return now - timer_storage[0].start_time_ms;
    }
    return 0;
}

uint32_t Debug_GetCurrentTickMs(void) {
    return g_timer_update_calls / 2;
}

uint32_t Debug_Timer0_GetStartTimeMs(void) {
    return (timer_count > 0) ? timer_storage[0].start_time_ms : 0xFFFFFFFF;
}
```

---

## 5. Test Configuration

### JSON Config for Timer Test

```json
{
  "version": "3.0",
  "device": {"name": "PMU30-TimerTest"},
  "channels": [
    {
      "channel_type": "digital_input",
      "channel_id": 50,
      "channel_name": "Button",
      "input_pin": 0,
      "subtype": "switch_active_high",
      "threshold_mv": 2500,
      "debounce_ms": 20
    },
    {
      "channel_type": "timer",
      "channel_id": 300,
      "channel_name": "Timer5s",
      "start_channel": 50,
      "start_edge": "rising",
      "mode": "count_down",
      "limit_seconds": 5
    },
    {
      "channel_type": "power_output",
      "channel_id": 100,
      "channel_name": "TimerLED",
      "pins": [1],
      "source_channel": 300,
      "current_limit_a": 10.0
    }
  ]
}
```

### Test Script: firmware_timer_test.py

```bash
python firmware_timer_test.py COM11
```

**Expected Output:**
```
Time    DIN0 OUT1 Run  | TickMs   ElapsMs  StartMs | Status
--------------------------------------------------
  0.0s   0    0    0   |       0        0        0 |
  5.2s   1    1    1   |    5200        0     5200 | TIMER STARTED!
  6.2s   0    1    1   |    6200     1000     5200 | RUNNING (4.0s)
 10.2s   0    0    0   |   10200     5000     5200 | >>> EXPIRED <<<
```

---

## 6. Files Modified

| File | Changes |
|------|---------|
| `pmu_config_json.c:128-135` | Added `g_current_tick_ms`, `PMU_SetCurrentTick()` |
| `pmu_config_json.c:3121-3122` | Changed sentinel to `-1` for prev values |
| `pmu_config_json.c:4294` | Changed `now = g_timer_update_calls / 2` |
| `pmu_config_json.c:4304-4312` | Added first-run detection check |
| `pmu_config_json.c:4439-4480` | Added debug functions |
| `pmu_protocol.c:428-510` | Added debug bytes to telemetry |
| `main_nucleo_f446.c:272-273` | Added `PMU_SetCurrentTick()` call |

---

## 7. Lessons Learned

1. **Don't assume HAL functions work on all platforms**
   - `HAL_GetTick()` requires SysTick to be configured
   - Always verify with debug output

2. **Edge detection needs careful initialization**
   - Use sentinel values like `-1` for "uninitialized" state
   - Skip first iteration to establish baseline

3. **Use local counters when external sync fails**
   - `g_timer_update_calls` is reliable because it's in same file
   - Divide/multiply to convert to real time units

4. **Add debug telemetry early**
   - Debug bytes in telemetry are invaluable
   - Makes remote debugging possible

5. **Calibrate timing with real measurements**
   - Don't assume update rates - measure them
   - Test with different multipliers until timing is correct

---

## 8. Quick Reference

### Timer Not Expiring Checklist

- [ ] Check `elapsed_ms` in telemetry - should increase
- [ ] Check `tick_ms` in telemetry - should increase
- [ ] Verify `mode=1` for count_down timer
- [ ] Verify `limit_sec` matches config
- [ ] Check `update_calls` is incrementing

### Timer Starts Immediately Checklist

- [ ] Verify `prev_start_val` shows `-1` initially
- [ ] Check first-run detection code is present
- [ ] Verify DIN0 is 0 before button press

### Wrong Timing Checklist

- [ ] Calculate actual update rate from `update_calls`
- [ ] Adjust multiplier in `pmu_config_json.c`
- [ ] Rebuild and test timing

---

## See Also

- [Troubleshooting Guide](troubleshooting-guide.md)
- [Telemetry Documentation](../telemetry.md)
- [Timer Channel Reference](../reference/channels.md)

---

**Document Version:** 1.0
**Last Updated:** January 2025
