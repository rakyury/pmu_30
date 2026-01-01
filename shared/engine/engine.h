/**
 * @file engine.h
 * @brief Logic Engine - Master Header
 *
 * Single include for all Logic Engine components.
 * All functions are pure (or use external state) and can run
 * on embedded systems or desktop without hardware dependencies.
 *
 * Components:
 *   - logic.h      : Boolean logic operations (AND, OR, XOR, comparisons)
 *   - math_ops.h   : Math operations (Add, Mul, Map, Clamp, etc.)
 *   - timer.h      : Timer functions (delay, pulse, blink)
 *   - table.h      : 2D/3D lookup tables with interpolation
 *   - switch.h     : Switch/selector functions
 *   - counter.h    : Counter with inc/dec/reset
 *   - pid.h        : PID controller
 *   - filter.h     : Signal filters (SMA, EMA, LPF, median, etc.)
 *   - flipflop.h   : Flip-flops and latches (SR, D, T, JK)
 *   - hysteresis.h : Hysteresis comparator / Schmitt trigger
 *
 * Design Principles:
 *   1. Pure functions - no side effects, output depends only on inputs
 *   2. External state - stateful functions take state pointer as parameter
 *   3. No hardware dependencies - can run in desktop simulation
 *   4. No dynamic allocation - all memory is caller-managed
 *   5. Fixed-point arithmetic - integer math for embedded systems
 *
 * Usage Example:
 * @code
 *   #include "engine.h"
 *
 *   // Pure logic function
 *   int32_t inputs[] = {1, 0, 1};
 *   int32_t result = Logic_AND(inputs, 3);  // returns 0
 *
 *   // Stateful timer
 *   Timer_State_t timer_state;
 *   Timer_Config_t timer_cfg = { .mode = TIMER_MODE_DELAY_ON, .delay_ms = 1000 };
 *   Timer_Init(&timer_state);
 *   int32_t output = Timer_Update(&timer_state, &timer_cfg, trigger, now_ms);
 *
 *   // PID controller
 *   PID_State_t pid_state;
 *   PID_Config_t pid_cfg = PID_DefaultConfig(1000, 100, 50, 0, 10000);
 *   PID_Init(&pid_state);
 *   int32_t control = PID_Update(&pid_state, &pid_cfg, setpoint, measurement, dt_ms);
 * @endcode
 *
 * @version 1.0
 * @date January 2026
 */

#ifndef LOGIC_ENGINE_H
#define LOGIC_ENGINE_H

/* Core logic operations */
#include "logic.h"

/* Math operations */
#include "math_ops.h"

/* Timer functions */
#include "timer.h"

/* Lookup tables */
#include "table.h"

/* Switch/selector */
#include "switch.h"

/* Counter */
#include "counter.h"

/* PID controller */
#include "pid.h"

/* Signal filters */
#include "filter.h"

/* Flip-flops and latches */
#include "flipflop.h"

/* Hysteresis comparator */
#include "hysteresis.h"

#endif /* LOGIC_ENGINE_H */
