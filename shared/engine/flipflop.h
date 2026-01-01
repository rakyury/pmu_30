/**
 * @file flipflop.h
 * @brief Logic Engine - Flip-Flops and Latches (Pure Functions)
 *
 * Digital flip-flop and latch implementations with external state.
 * All state is passed as parameters, no global variables.
 *
 * Supported types:
 * - SR Latch (Set-Reset)
 * - D Flip-Flop (Data)
 * - T Flip-Flop (Toggle)
 * - JK Flip-Flop
 *
 * @note Part of the Logic Engine abstraction layer.
 *       Can run on embedded systems or desktop without hardware.
 */

#ifndef LOGIC_ENGINE_FLIPFLOP_H
#define LOGIC_ENGINE_FLIPFLOP_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/*============================================================================
 * Flip-Flop Types
 *============================================================================*/

typedef enum {
    FF_TYPE_SR = 0,         /**< SR Latch (Set-Reset) */
    FF_TYPE_D,              /**< D Flip-Flop (edge-triggered) */
    FF_TYPE_T,              /**< T Flip-Flop (toggle) */
    FF_TYPE_JK,             /**< JK Flip-Flop */
    FF_TYPE_SR_LATCH,       /**< SR Latch (level-sensitive) */
    FF_TYPE_D_LATCH,        /**< D Latch (level-sensitive) */
} FlipFlopType_t;

/*============================================================================
 * Flip-Flop State
 *============================================================================*/

/**
 * Generic flip-flop state.
 */
typedef struct {
    uint8_t q;              /**< Output Q (0 or 1) */
    uint8_t last_clk;       /**< Last clock state (for edge detection) */
    uint8_t initialized;    /**< State initialized */
} FlipFlop_State_t;

/*============================================================================
 * SR Latch Functions
 *============================================================================*/

/**
 * Initialize flip-flop state.
 */
void FF_Init(FlipFlop_State_t* state);

/**
 * Reset flip-flop to known state.
 *
 * @param state     Flip-flop state
 * @param q_value   Initial Q value (0 or 1)
 */
void FF_Reset(FlipFlop_State_t* state, uint8_t q_value);

/**
 * Update SR Latch (level-sensitive).
 *
 * Truth table:
 *   S=0, R=0: Q unchanged (hold)
 *   S=0, R=1: Q = 0 (reset)
 *   S=1, R=0: Q = 1 (set)
 *   S=1, R=1: Invalid (Q = 0 in this impl)
 *
 * @param state     Flip-flop state (modified)
 * @param set       Set input (non-zero = active)
 * @param reset     Reset input (non-zero = active)
 * @return Q output (0 or 1)
 */
int32_t SR_Latch_Update(FlipFlop_State_t* state, int32_t set, int32_t reset);

/**
 * Update SR Latch with priority.
 *
 * @param state         Flip-flop state (modified)
 * @param set           Set input
 * @param reset         Reset input
 * @param reset_priority If true, reset wins when both active
 * @return Q output
 */
int32_t SR_Latch_Priority(FlipFlop_State_t* state, int32_t set, int32_t reset,
                          bool reset_priority);

/*============================================================================
 * D Flip-Flop Functions
 *============================================================================*/

/**
 * Update D Flip-Flop (edge-triggered).
 * Captures D input on rising edge of clock.
 *
 * @param state     Flip-flop state (modified)
 * @param d         Data input
 * @param clk       Clock input
 * @return Q output
 */
int32_t D_FlipFlop_Update(FlipFlop_State_t* state, int32_t d, int32_t clk);

/**
 * Update D Latch (level-sensitive).
 * Transparent when enable is high, holds when low.
 *
 * @param state     Flip-flop state (modified)
 * @param d         Data input
 * @param enable    Enable input
 * @return Q output
 */
int32_t D_Latch_Update(FlipFlop_State_t* state, int32_t d, int32_t enable);

/*============================================================================
 * T Flip-Flop Functions
 *============================================================================*/

/**
 * Update T Flip-Flop (Toggle).
 * Toggles output on rising edge when T=1.
 *
 * @param state     Flip-flop state (modified)
 * @param t         Toggle input
 * @param clk       Clock input
 * @return Q output
 */
int32_t T_FlipFlop_Update(FlipFlop_State_t* state, int32_t t, int32_t clk);

/**
 * Simple toggle on rising edge.
 * Toggles output on every rising edge of input.
 *
 * @param state     Flip-flop state (modified)
 * @param trigger   Trigger input
 * @return Q output
 */
int32_t Toggle_Update(FlipFlop_State_t* state, int32_t trigger);

/*============================================================================
 * JK Flip-Flop Functions
 *============================================================================*/

/**
 * Update JK Flip-Flop (edge-triggered).
 *
 * Truth table (on clock rising edge):
 *   J=0, K=0: Q unchanged (hold)
 *   J=0, K=1: Q = 0 (reset)
 *   J=1, K=0: Q = 1 (set)
 *   J=1, K=1: Q = !Q (toggle)
 *
 * @param state     Flip-flop state (modified)
 * @param j         J input
 * @param k         K input
 * @param clk       Clock input
 * @return Q output
 */
int32_t JK_FlipFlop_Update(FlipFlop_State_t* state,
                           int32_t j, int32_t k, int32_t clk);

/*============================================================================
 * Helper Functions
 *============================================================================*/

/**
 * Get Q output.
 */
int32_t FF_GetQ(const FlipFlop_State_t* state);

/**
 * Get Q-bar output (inverted Q).
 */
int32_t FF_GetQBar(const FlipFlop_State_t* state);

/**
 * Detect rising edge.
 *
 * @param last_state    Pointer to last state (modified)
 * @param current       Current input value
 * @return 1 if rising edge detected, 0 otherwise
 */
int32_t DetectRisingEdge(uint8_t* last_state, int32_t current);

/**
 * Detect falling edge.
 *
 * @param last_state    Pointer to last state (modified)
 * @param current       Current input value
 * @return 1 if falling edge detected, 0 otherwise
 */
int32_t DetectFallingEdge(uint8_t* last_state, int32_t current);

/**
 * Detect any edge (rising or falling).
 *
 * @param last_state    Pointer to last state (modified)
 * @param current       Current input value
 * @return 1 if any edge detected, 0 otherwise
 */
int32_t DetectAnyEdge(uint8_t* last_state, int32_t current);

#ifdef __cplusplus
}
#endif

#endif /* LOGIC_ENGINE_FLIPFLOP_H */
