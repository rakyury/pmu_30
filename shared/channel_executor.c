/**
 * @file channel_executor.c
 * @brief Channel Executor Implementation
 */

#include "channel_executor.h"
#include <string.h>

/*============================================================================
 * Executor Initialization
 *============================================================================*/

void Exec_Init(
    ExecContext_t* ctx,
    Exec_GetValueFunc get_value,
    Exec_SetValueFunc set_value,
    void* user_data
)
{
    if (!ctx) return;

    memset(ctx, 0, sizeof(ExecContext_t));
    ctx->get_value = get_value;
    ctx->set_value = set_value;
    ctx->user_data = user_data;
}

void Exec_UpdateTime(ExecContext_t* ctx, uint32_t now_ms)
{
    if (!ctx) return;

    ctx->dt_ms = (ctx->last_ms > 0) ? (now_ms - ctx->last_ms) : 0;
    ctx->last_ms = ctx->now_ms;
    ctx->now_ms = now_ms;
}

/*============================================================================
 * Helper: Get Input Values
 *============================================================================*/

static int32_t get_input(ExecContext_t* ctx, uint16_t channel_id)
{
    /* Channel ID 0 is invalid (reserved), treat same as CH_REF_NONE */
    if (!ctx || !ctx->get_value || channel_id == CH_REF_NONE || channel_id == 0) {
        return 0;
    }
    return ctx->get_value(channel_id, ctx->user_data);
}

static void get_inputs(
    ExecContext_t* ctx,
    const uint16_t* input_ids,
    uint8_t count,
    int32_t* values
)
{
    for (uint8_t i = 0; i < count && i < EXEC_MAX_INPUTS; i++) {
        values[i] = get_input(ctx, input_ids[i]);
    }
}

/*============================================================================
 * Logic Execution
 *============================================================================*/

int32_t Exec_Logic(
    ExecContext_t* ctx,
    const CfgLogic_t* config
)
{
    if (!ctx || !config) return 0;

    int32_t inputs[EXEC_MAX_INPUTS];
    get_inputs(ctx, config->inputs, config->input_count, inputs);

    int32_t result;

    switch (config->operation) {
        case LOGIC_OP_AND:
            result = Logic_AND(inputs, config->input_count);
            break;

        case LOGIC_OP_OR:
            result = Logic_OR(inputs, config->input_count);
            break;

        case LOGIC_OP_XOR:
            result = Logic_XOR(inputs, config->input_count);
            break;

        case LOGIC_OP_NAND:
            result = Logic_NAND(inputs, config->input_count);
            break;

        case LOGIC_OP_NOR:
            result = Logic_NOR(inputs, config->input_count);
            break;

        case LOGIC_OP_IS_TRUE:
            result = Logic_IsTrue(inputs[0]);
            break;

        case LOGIC_OP_IS_FALSE:
            result = Logic_IsFalse(inputs[0]);
            break;

        case LOGIC_OP_GT:
            result = Logic_GT(inputs[0], config->compare_value);
            break;

        case LOGIC_OP_GTE:
            result = Logic_GTE(inputs[0], config->compare_value);
            break;

        case LOGIC_OP_LT:
            result = Logic_LT(inputs[0], config->compare_value);
            break;

        case LOGIC_OP_LTE:
            result = Logic_LTE(inputs[0], config->compare_value);
            break;

        case LOGIC_OP_EQ:
            result = Logic_EQ(inputs[0], config->compare_value);
            break;

        case LOGIC_OP_NEQ:
            result = Logic_NEQ(inputs[0], config->compare_value);
            break;

        case LOGIC_OP_RANGE:
            result = Logic_InRange(inputs[0], inputs[1], config->compare_value);
            break;

        default:
            result = 0;
            break;
    }

    return config->invert_output ? !result : result;
}

/*============================================================================
 * Math Execution
 *============================================================================*/

int32_t Exec_Math(
    ExecContext_t* ctx,
    const CfgMath_t* config
)
{
    if (!ctx || !config) return 0;

    int32_t inputs[EXEC_MAX_INPUTS];
    get_inputs(ctx, config->inputs, config->input_count, inputs);

    int32_t result;

    switch (config->operation) {
        case MATH_OP_ADD:
            result = Math_Add(inputs, config->input_count);
            break;

        case MATH_OP_SUB:
            result = Math_Sub(inputs[0], inputs[1]);
            break;

        case MATH_OP_MUL:
            result = Math_Mul(inputs[0], inputs[1]);
            break;

        case MATH_OP_DIV:
            result = Math_Div(inputs[0], inputs[1]);
            break;

        case MATH_OP_MOD:
            result = Math_Mod(inputs[0], inputs[1]);
            break;

        case MATH_OP_ABS:
            result = Math_Abs(inputs[0]);
            break;

        case MATH_OP_NEG:
            result = Math_Neg(inputs[0]);
            break;

        case MATH_OP_MIN:
            result = Math_Min(inputs, config->input_count);
            break;

        case MATH_OP_MAX:
            result = Math_Max(inputs, config->input_count);
            break;

        case MATH_OP_AVG:
            result = Math_Avg(inputs, config->input_count);
            break;

        case MATH_OP_CLAMP:
            result = Math_Clamp(inputs[0], config->min_value, config->max_value);
            break;

        case MATH_OP_MAP:
            /* Map from input range to output range */
            result = Math_Map(inputs[0], inputs[1], inputs[2],
                              config->min_value, config->max_value);
            break;

        case MATH_OP_SCALE:
            result = Math_Scale(inputs[0], config->scale_num, config->scale_den);
            break;

        default:
            result = inputs[0];
            break;
    }

    /* Apply output clamping */
    result = Math_Clamp(result, config->min_value, config->max_value);

    /* Apply output scaling */
    if (config->scale_den != 0 && config->scale_den != 1) {
        result = Math_Scale(result, config->scale_num, config->scale_den);
    }

    return result;
}

/*============================================================================
 * Timer Execution
 *============================================================================*/

int32_t Exec_Timer(
    ExecContext_t* ctx,
    Timer_State_t* state,
    const CfgTimer_t* config
)
{
    if (!ctx || !state || !config) return 0;

    int32_t trigger = get_input(ctx, config->trigger_id);

    /* Convert CfgTimer to Timer_Config_t */
    Timer_Config_t timer_cfg = {
        .mode = config->mode,
        .start_edge = config->trigger_mode,
        .auto_reset = config->auto_reset,
        .reserved = 0,
        .duration_ms = config->delay_ms,
        .blink_on_ms = config->on_time_ms,
        .blink_off_ms = config->off_time_ms
    };

    return Timer_Update(state, &timer_cfg, trigger, ctx->now_ms);
}

/*============================================================================
 * PID Execution
 *============================================================================*/

int32_t Exec_PID(
    ExecContext_t* ctx,
    PID_State_t* state,
    const CfgPid_t* config
)
{
    if (!ctx || !state || !config) return 0;

    int32_t setpoint = get_input(ctx, config->setpoint_id);
    int32_t feedback = get_input(ctx, config->feedback_id);

    /* Convert CfgPid to PID_Config_t */
    PID_Config_t pid_cfg = {
        .kp = config->kp,
        .ki = config->ki,
        .kd = config->kd,
        .scale = PID_DEFAULT_SCALE,
        .output_min = config->output_min,
        .output_max = config->output_max,
        .integral_min = config->integral_min,
        .integral_max = config->integral_max,
        .deadband = config->deadband,
        .d_on_measurement = config->d_on_measurement,
        .reset_integral_on_setpoint = 0
    };

    return PID_Update(state, &pid_cfg, setpoint, feedback, ctx->dt_ms);
}

/*============================================================================
 * Filter Execution
 *============================================================================*/

int32_t Exec_Filter(
    ExecContext_t* ctx,
    ChannelState_t* state,
    const CfgFilter_t* config
)
{
    if (!ctx || !state || !config) return 0;

    int32_t input = get_input(ctx, config->input_id);

    switch (config->filter_type) {
        case FILTER_TYPE_SMA: {
            SMA_Config_t cfg = { .window_size = config->window_size };
            return SMA_Update(&state->sma, &cfg, input);
        }

        case FILTER_TYPE_EMA: {
            EMA_Config_t cfg = { .alpha = config->alpha };
            return EMA_Update(&state->ema, &cfg, input);
        }

        case FILTER_TYPE_LOWPASS: {
            LPF_Config_t cfg = {
                .time_constant_ms = config->time_constant_ms,
                .scale = 1000
            };
            return LPF_Update(&state->lpf, &cfg, input, ctx->dt_ms);
        }

        case FILTER_TYPE_MEDIAN: {
            Median_Config_t cfg = { .window_size = config->window_size };
            return Median_Update(&state->median, &cfg, input);
        }

        case FILTER_TYPE_RATE_LIMIT: {
            RateLimiter_Config_t cfg = {
                .rise_rate = config->time_constant_ms,  /* Reuse field */
                .fall_rate = config->time_constant_ms
            };
            return RateLimiter_Update(&state->rate_limiter, &cfg, input, ctx->dt_ms);
        }

        case FILTER_TYPE_DEBOUNCE: {
            Debounce_Config_t cfg = {
                .debounce_ms = config->time_constant_ms,
                .hysteresis = 0
            };
            return Debounce_Update(&state->debounce, &cfg, input, ctx->dt_ms);
        }

        default:
            return input;
    }
}

/*============================================================================
 * Table 2D Execution
 *============================================================================*/

int32_t Exec_Table2D(
    ExecContext_t* ctx,
    const CfgTable2D_t* config
)
{
    if (!ctx || !config) return 0;

    int32_t input = get_input(ctx, config->input_id);

    /* Build Table2D_t from config */
    Table2D_t table = {
        .count = config->point_count,
        .reserved = {0, 0, 0}
    };

    /* Copy values (int16 to int32) */
    for (uint8_t i = 0; i < config->point_count && i < TABLE_2D_MAX_POINTS; i++) {
        table.x[i] = config->x_values[i];
        table.y[i] = config->y_values[i];
    }

    return Table2D_Lookup(&table, input);
}

/*============================================================================
 * Switch Execution
 *============================================================================*/

int32_t Exec_Switch(
    ExecContext_t* ctx,
    const CfgSwitch_t* config
)
{
    if (!ctx || !config) return config->default_value;

    int32_t selector = get_input(ctx, config->selector_id);

    /* Mode 2: index-based selection */
    if (config->mode == 2) {
        if (selector >= 0 && selector < config->case_count) {
            return config->cases[selector].result;
        }
        return config->default_value;
    }

    /* Mode 0: value match, Mode 1: range match */
    for (uint8_t i = 0; i < config->case_count; i++) {
        if (config->mode == 0) {
            /* Exact match */
            if (selector == config->cases[i].match_value) {
                return config->cases[i].result;
            }
        } else {
            /* Range match */
            if (selector >= config->cases[i].match_value &&
                selector <= config->cases[i].max_value) {
                return config->cases[i].result;
            }
        }
    }

    return config->default_value;
}

/*============================================================================
 * Counter Execution
 *============================================================================*/

int32_t Exec_Counter(
    ExecContext_t* ctx,
    Counter_State_t* state,
    const CfgCounter_t* config
)
{
    if (!ctx || !state || !config) return 0;

    int32_t inc_trigger = get_input(ctx, config->inc_trigger_id);
    int32_t dec_trigger = get_input(ctx, config->dec_trigger_id);
    int32_t reset_trigger = get_input(ctx, config->reset_trigger_id);

    Counter_Config_t counter_cfg = {
        .initial_value = config->initial_value,
        .min_value = config->min_value,
        .max_value = config->max_value,
        .step = config->step,
        .wrap = config->wrap,
        .edge_mode = config->edge_mode
    };

    return Counter_Update(state, &counter_cfg, inc_trigger, dec_trigger, reset_trigger);
}

/*============================================================================
 * Hysteresis Execution
 *============================================================================*/

int32_t Exec_Hysteresis(
    ExecContext_t* ctx,
    Hysteresis_State_t* state,
    const CfgHysteresis_t* config
)
{
    if (!ctx || !state || !config) return 0;

    int32_t input = get_input(ctx, config->input_id);

    Hysteresis_Config_t hyst_cfg = {
        .threshold_high = config->threshold_high,
        .threshold_low = config->threshold_low,
        .invert = config->invert
    };

    return Hysteresis_Update(state, &hyst_cfg, input);
}

/*============================================================================
 * Process Any Channel
 *============================================================================*/

int32_t Exec_ProcessChannel(
    ExecContext_t* ctx,
    ChannelRuntime_t* runtime
)
{
    if (!ctx || !runtime) return 0;

    runtime->prev_value = runtime->value;
    int32_t result = runtime->value;

    switch (runtime->type) {
        case CH_TYPE_LOGIC:
            if (runtime->config) {
                result = Exec_Logic(ctx, (CfgLogic_t*)runtime->config);
            }
            break;

        case CH_TYPE_MATH:
            if (runtime->config) {
                result = Exec_Math(ctx, (CfgMath_t*)runtime->config);
            }
            break;

        case CH_TYPE_TIMER:
            if (runtime->config) {
                result = Exec_Timer(ctx, &runtime->state.timer,
                                    (CfgTimer_t*)runtime->config);
            }
            break;

        case CH_TYPE_PID:
            if (runtime->config) {
                result = Exec_PID(ctx, &runtime->state.pid,
                                  (CfgPid_t*)runtime->config);
            }
            break;

        case CH_TYPE_FILTER:
            if (runtime->config) {
                result = Exec_Filter(ctx, &runtime->state,
                                     (CfgFilter_t*)runtime->config);
            }
            break;

        case CH_TYPE_TABLE_2D:
            if (runtime->config) {
                result = Exec_Table2D(ctx, (CfgTable2D_t*)runtime->config);
            }
            break;

        case CH_TYPE_SWITCH:
            if (runtime->config) {
                result = Exec_Switch(ctx, (CfgSwitch_t*)runtime->config);
            }
            break;

        case CH_TYPE_NUMBER:
            /* Number channels just hold their value */
            if (runtime->config) {
                CfgNumber_t* num_cfg = (CfgNumber_t*)runtime->config;
                if (!num_cfg->readonly) {
                    /* Value can be modified externally */
                    result = runtime->value;
                } else {
                    result = num_cfg->value;
                }
            }
            break;

        default:
            /* Input/output channels are handled by hardware layer */
            break;
    }

    runtime->value = result;
    return result;
}

/*============================================================================
 * State Initialization
 *============================================================================*/

void Exec_InitChannelState(ChannelRuntime_t* runtime, ChannelType_t type)
{
    if (!runtime) return;

    memset(&runtime->state, 0, sizeof(ChannelState_t));
    runtime->type = type;

    switch (type) {
        case CH_TYPE_TIMER:
            Timer_Init(&runtime->state.timer);
            break;

        case CH_TYPE_PID:
            PID_Init(&runtime->state.pid);
            break;

        case CH_TYPE_FILTER:
            /* Initialized when first used based on filter_type */
            break;

        default:
            break;
    }
}

void Exec_ResetChannelState(ChannelRuntime_t* runtime)
{
    if (!runtime) return;

    switch (runtime->type) {
        case CH_TYPE_TIMER:
            Timer_Reset(&runtime->state.timer);
            break;

        case CH_TYPE_PID:
            PID_Reset(&runtime->state.pid);
            break;

        case CH_TYPE_FILTER:
            memset(&runtime->state, 0, sizeof(ChannelState_t));
            break;

        default:
            break;
    }

    runtime->value = 0;
    runtime->prev_value = 0;
}
