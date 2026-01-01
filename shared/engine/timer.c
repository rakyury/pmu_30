/**
 * @file timer.c
 * @brief Logic Engine - Timer Functions Implementation
 */

#include "timer.h"
#include <string.h>

/*============================================================================
 * Edge Detection Helper
 *============================================================================*/

static bool detect_edge(uint8_t* last_state, int32_t current, uint8_t edge_type)
{
    bool current_high = (current != 0);
    bool last_high = (*last_state != 0);
    bool triggered = false;

    switch (edge_type) {
        case 0:  /* Level - trigger while high */
            triggered = current_high;
            break;
        case 1:  /* Rising edge */
            triggered = current_high && !last_high;
            break;
        case 2:  /* Falling edge */
            triggered = !current_high && last_high;
            break;
        case 3:  /* Both edges */
            triggered = current_high != last_high;
            break;
    }

    *last_state = current_high ? 1 : 0;
    return triggered;
}

/*============================================================================
 * Timer Functions
 *============================================================================*/

void Timer_Init(Timer_State_t* state)
{
    if (!state) return;
    memset(state, 0, sizeof(Timer_State_t));
    state->state = TIMER_STATE_IDLE;
}

void Timer_Reset(Timer_State_t* state)
{
    if (!state) return;
    state->state = TIMER_STATE_IDLE;
    state->output = 0;
    state->elapsed_ms = 0;
    state->start_time_ms = 0;
    state->blink_phase = 0;
}

int32_t Timer_Update(Timer_State_t* state, const Timer_Config_t* config,
                     int32_t trigger, uint32_t now_ms)
{
    if (!state || !config) return 0;

    bool edge_triggered = detect_edge(&state->last_trigger, trigger, config->start_edge);

    switch (state->state) {
        case TIMER_STATE_IDLE:
            /* Waiting for trigger */
            if (edge_triggered || (config->start_edge == 0 && trigger != 0)) {
                state->state = TIMER_STATE_RUNNING;
                state->start_time_ms = now_ms;
                state->elapsed_ms = 0;
                state->blink_phase = 0;

                /* Immediate output based on mode */
                switch (config->mode) {
                    case TIMER_MODE_DELAY_ON:
                        state->output = 0;  /* Will turn ON after delay */
                        break;
                    case TIMER_MODE_DELAY_OFF:
                    case TIMER_MODE_PULSE:
                    case TIMER_MODE_ONESHOT:
                    case TIMER_MODE_RETRIGGERABLE:
                    case TIMER_MODE_MONOSTABLE:
                        state->output = 1;  /* Immediately ON */
                        break;
                    case TIMER_MODE_BLINK:
                        state->output = 1;  /* Start with ON */
                        break;
                }
            }
            break;

        case TIMER_STATE_RUNNING:
            /* Update elapsed time */
            state->elapsed_ms = now_ms - state->start_time_ms;

            /* Handle retriggerable mode */
            if (config->mode == TIMER_MODE_RETRIGGERABLE && edge_triggered) {
                state->start_time_ms = now_ms;
                state->elapsed_ms = 0;
            }

            /* Check for expiration */
            if (state->elapsed_ms >= config->duration_ms) {
                switch (config->mode) {
                    case TIMER_MODE_DELAY_ON:
                        state->output = 1;
                        state->state = TIMER_STATE_EXPIRED;
                        break;

                    case TIMER_MODE_DELAY_OFF:
                        state->output = 0;
                        state->state = TIMER_STATE_EXPIRED;
                        break;

                    case TIMER_MODE_PULSE:
                    case TIMER_MODE_ONESHOT:
                    case TIMER_MODE_RETRIGGERABLE:
                    case TIMER_MODE_MONOSTABLE:
                        state->output = 0;
                        state->state = TIMER_STATE_EXPIRED;
                        break;

                    case TIMER_MODE_BLINK:
                        /* Blink continues until trigger goes low */
                        break;
                }
            }

            /* Handle blink mode */
            if (config->mode == TIMER_MODE_BLINK) {
                uint32_t blink_period = config->blink_on_ms + config->blink_off_ms;
                if (blink_period > 0) {
                    uint32_t phase_time = state->elapsed_ms % blink_period;
                    state->output = (phase_time < config->blink_on_ms) ? 1 : 0;
                }

                /* Stop blinking when trigger goes low (level mode) */
                if (config->start_edge == 0 && trigger == 0) {
                    state->output = 0;
                    state->state = TIMER_STATE_IDLE;
                }
            }
            break;

        case TIMER_STATE_EXPIRED:
            /* Check for auto-reset or new trigger */
            if (config->auto_reset) {
                if (config->start_edge == 0) {
                    /* Level mode: reset when trigger goes low */
                    if (trigger == 0) {
                        Timer_Reset(state);
                    }
                } else {
                    /* Edge mode: auto-reset immediately */
                    Timer_Reset(state);
                }
            } else if (config->mode == TIMER_MODE_MONOSTABLE) {
                /* Monostable auto-resets */
                Timer_Reset(state);
            }
            /* Oneshot stays expired until manual reset */
            break;

        case TIMER_STATE_PAUSED:
            /* Do nothing while paused */
            break;
    }

    return state->output;
}

void Timer_Pause(Timer_State_t* state, uint32_t now_ms)
{
    if (!state || state->state != TIMER_STATE_RUNNING) return;

    state->pause_time_ms = now_ms;
    state->state = TIMER_STATE_PAUSED;
}

void Timer_Resume(Timer_State_t* state, uint32_t now_ms)
{
    if (!state || state->state != TIMER_STATE_PAUSED) return;

    /* Adjust start time to account for pause duration */
    uint32_t pause_duration = now_ms - state->pause_time_ms;
    state->start_time_ms += pause_duration;
    state->state = TIMER_STATE_RUNNING;
}

uint32_t Timer_GetRemaining(const Timer_State_t* state, const Timer_Config_t* config)
{
    if (!state || !config) return 0;

    if (state->state != TIMER_STATE_RUNNING) return 0;

    if (state->elapsed_ms >= config->duration_ms) return 0;

    return config->duration_ms - state->elapsed_ms;
}

uint32_t Timer_GetElapsed(const Timer_State_t* state)
{
    return state ? state->elapsed_ms : 0;
}

bool Timer_IsRunning(const Timer_State_t* state)
{
    return state && state->state == TIMER_STATE_RUNNING;
}

bool Timer_IsExpired(const Timer_State_t* state)
{
    return state && state->state == TIMER_STATE_EXPIRED;
}
