/* This file is auto-generated. Do not edit. */

/* Verbatim `include' code. */
#include <Arduino.h>

#include "project_config.h"
#include "utils.h"
#include "regs.h"
#include "event.h"
#include "driver.h"
#include "console.h"
#include "app.h"
/* Verbatim `include' code ends. */

#include "sm_main.autogen.h"

/* Context type declaration */
typedef struct {
    uint8_t state_;
} smk_context_sm_main_t;

static smk_context_sm_main_t context;

#define PROP(member_) (context.member_)

/* Verbatim `code' code. */
// Timeouts.
static constexpr uint16_t MOTOR_STOP_DURATION_MS    = 1000U;
static constexpr uint16_t RLY_OPERATE_DELAY_MS      = 200U;

// Timers
enum {
    TIMER_MOTOR_STOP,
};
constexpr uint8_t EV_TIMEOUT_MOTOR_STOP = EVENT_MK_TIMER_EVENT_ID(TIMER_MOTOR_STOP);

static bool is_timer_valid(t_event& ev) {
    return event_p8(ev) == eventSmTimerCookie(event_id(ev)-EV_TIMEOUT_0);
}

static bool is_dir_rev() { return regsFlags() & REGS_FLAGS_MASK_MOTOR_DIR_REVERSE; }
static void update_dir_indicator(uint16_t flash) {
    driverIndicatorSet(DRIVER_INDICATOR_DIR, 
      is_dir_rev() ? DRIVER_INDICATOR_COLOUR_RED : DRIVER_INDICATOR_COLOUR_GREEN, flash);
}

// We abstract run relay control to a few states.
enum { RST_STOP, RST_START, RST_RUN_START, RST_RUN, };
static void set_run_relay(uint8_t st) {
    constexpr uint16_t M = REGS_RELAYS_MASK_RUN|REGS_RELAYS_MASK_START;
    switch (st) {
    case RST_STOP:  driverRelayWrite(M, 0U); break;
    case RST_START: driverRelayWrite(M, REGS_RELAYS_MASK_START); break;
    case RST_RUN_START: driverRelayWrite(M, REGS_RELAYS_MASK_START|REGS_RELAYS_MASK_RUN); break;
    case RST_RUN: driverRelayWrite(M, REGS_RELAYS_MASK_RUN); break;
    }
}
/* Verbatim `code' code ends. */

void smk_process_sm_main(t_event ev) {
    if (EV_SM_RESET == event_id(ev)) {
        eventPublish(EV_DEBUG_SM_STATE_CHANGE, 0, ST_SM_MAIN_STOPPING); PROP(state_) = ST_SM_MAIN_STOPPING;
            update_dir_indicator(DRIVER_INDICATOR_FLASH_SOLID);
            if (regsFlags() & REGS_FLAGS_MASK_ESTOP)
                    eventPublishEvFront(EV_SW_ESTOP);
            set_run_relay(RST_STOP);
            driverIndicatorSet(DRIVER_INDICATOR_RUN, DRIVER_INDICATOR_COLOUR_BLUE, DRIVER_INDICATOR_FLASH_VFAST);
            eventSmTimerStart(TIMER_MOTOR_STOP, REGS[REGS_IDX_MOTOR_RUN_DOWN_DURATION]/CFG_EVENT_TIMER_PERIOD_MS);
        return;
    }

    switch(context.state_) {
    default:
        break;
    
    case ST_SM_MAIN_STOPPING:
        switch(event_id(ev)) {
        case EV_SW_ESTOP:
            T000:
        if(event_p8(ev) == EV_P8_SW_CLICK) {
            set_run_relay(RST_STOP);
            driverIndicatorSet(DRIVER_INDICATOR_RUN, DRIVER_INDICATOR_COLOUR_RED, DRIVER_INDICATOR_FLASH_FAST);
            update_dir_indicator(DRIVER_INDICATOR_FLASH_FAST);
            eventPublish(EV_DEBUG_SM_STATE_CHANGE, 0, ST_SM_MAIN_ESTOP); PROP(state_) = ST_SM_MAIN_ESTOP;
        }
        break;
        case EV_TIMEOUT_MOTOR_STOP:
        if(is_timer_valid(ev)) {
            set_run_relay(RST_STOP);
            driverRelayWrite(REGS_RELAYS_MASK_DIR_1|REGS_RELAYS_MASK_DIR_2, 0U);
            driverIndicatorSet(DRIVER_INDICATOR_RUN, DRIVER_INDICATOR_COLOUR_OFF, DRIVER_INDICATOR_FLASH_SOLID);
            eventPublish(EV_DEBUG_SM_STATE_CHANGE, 0, ST_SM_MAIN_STOP); PROP(state_) = ST_SM_MAIN_STOP;
        }
        break;
    }
    break;
    case ST_SM_MAIN_STOP:
        switch(event_id(ev)) {
        case EV_SW_ESTOP:
            goto T000;
        case EV_SW_DIR:
            T001:
        if(event_p8(ev) == EV_P8_SW_CLICK) {
            regsToggleMaskFlags(REGS_FLAGS_MASK_MOTOR_DIR_REVERSE);
            update_dir_indicator(DRIVER_INDICATOR_FLASH_SOLID);
        }
        break;
        case EV_REM1_DIR:
            goto T001;
        case EV_REM2_DIR:
            goto T001;
        case EV_SW_RUN:
            T002:
        if(event_p8(ev) == EV_P8_SW_CLICK) {
            driverRelayWrite(REGS_RELAYS_MASK_DIR_1|REGS_RELAYS_MASK_DIR_2, 
                      is_dir_rev() ? REGS_RELAYS_MASK_DIR_2 : REGS_RELAYS_MASK_DIR_1);
            eventSmTimerStart(TIMER_MOTOR_STOP, RLY_OPERATE_DELAY_MS/CFG_EVENT_TIMER_PERIOD_MS);
            eventPublish(EV_DEBUG_SM_STATE_CHANGE, 0, ST_SM_MAIN_SET_DIR); PROP(state_) = ST_SM_MAIN_SET_DIR;
        }
        break;
        case EV_REM1_RUN:
            goto T002;
        case EV_REM2_RUN:
            goto T002;
    }
    break;
    case ST_SM_MAIN_SET_DIR:
        switch(event_id(ev)) {
        case EV_SW_ESTOP:
            goto T000;
        case EV_TIMEOUT_MOTOR_STOP:
        if(is_timer_valid(ev)) {
            set_run_relay(RST_START);
            driverIndicatorSet(DRIVER_INDICATOR_RUN, DRIVER_INDICATOR_COLOUR_BLUE, DRIVER_INDICATOR_FLASH_VFAST);
            eventSmTimerStart(TIMER_MOTOR_STOP, REGS[REGS_IDX_MOTOR_SOFT_START_DURATION]/CFG_EVENT_TIMER_PERIOD_MS);
            eventPublish(EV_DEBUG_SM_STATE_CHANGE, 0, ST_SM_MAIN_START); PROP(state_) = ST_SM_MAIN_START;
        }
        break;
        case EV_SW_DIR:
            T003:
        if(event_p8(ev) == EV_P8_SW_CLICK) {
            set_run_relay(RST_STOP);
            driverIndicatorSet(DRIVER_INDICATOR_RUN, DRIVER_INDICATOR_COLOUR_BLUE, DRIVER_INDICATOR_FLASH_VFAST);
            eventSmTimerStart(TIMER_MOTOR_STOP, REGS[REGS_IDX_MOTOR_RUN_DOWN_DURATION]/CFG_EVENT_TIMER_PERIOD_MS);
            eventPublish(EV_DEBUG_SM_STATE_CHANGE, 0, ST_SM_MAIN_STOPPING); PROP(state_) = ST_SM_MAIN_STOPPING;
        }
        break;
        case EV_REM1_DIR:
            goto T003;
        case EV_REM2_DIR:
            goto T003;
        case EV_SW_RUN:
            goto T003;
        case EV_REM1_RUN:
            goto T003;
        case EV_REM2_RUN:
            goto T003;
    }
    break;
    case ST_SM_MAIN_START:
        switch(event_id(ev)) {
        case EV_SW_ESTOP:
            goto T000;
        case EV_TIMEOUT_MOTOR_STOP:
        if(is_timer_valid(ev)) {
            set_run_relay(RST_RUN_START);
            eventSmTimerStart(TIMER_MOTOR_STOP, RLY_OPERATE_DELAY_MS/CFG_EVENT_TIMER_PERIOD_MS);
            eventPublish(EV_DEBUG_SM_STATE_CHANGE, 0, ST_SM_MAIN_RUN); PROP(state_) = ST_SM_MAIN_RUN;
        }
        break;
        case EV_SW_DIR:
            goto T003;
        case EV_REM1_DIR:
            goto T003;
        case EV_REM2_DIR:
            goto T003;
        case EV_SW_RUN:
            goto T003;
        case EV_REM1_RUN:
            goto T003;
        case EV_REM2_RUN:
            goto T003;
    }
    break;
    case ST_SM_MAIN_RUN:
        switch(event_id(ev)) {
        case EV_SW_ESTOP:
            goto T000;
        case EV_TIMEOUT_MOTOR_STOP:
        if(is_timer_valid(ev)) {
            set_run_relay(RST_RUN);
            driverIndicatorSet(DRIVER_INDICATOR_RUN, DRIVER_INDICATOR_COLOUR_BLUE, DRIVER_INDICATOR_FLASH_SOLID);
        }
        break;
        case EV_SW_DIR:
            goto T003;
        case EV_REM1_DIR:
            goto T003;
        case EV_REM2_DIR:
            goto T003;
        case EV_SW_RUN:
            goto T003;
        case EV_REM1_RUN:
            goto T003;
        case EV_REM2_RUN:
            goto T003;
    }
    break;
    case ST_SM_MAIN_ESTOP:
        switch(event_id(ev)) {
        case EV_SW_ESTOP:
        if(event_p8(ev) == EV_P8_SW_RELEASE) {
            update_dir_indicator(DRIVER_INDICATOR_FLASH_SOLID);
            if (regsFlags() & REGS_FLAGS_MASK_ESTOP)
                eventPublishEvFront(EV_SW_ESTOP);
            set_run_relay(RST_STOP);
            driverIndicatorSet(DRIVER_INDICATOR_RUN, DRIVER_INDICATOR_COLOUR_BLUE, DRIVER_INDICATOR_FLASH_VFAST);
            eventSmTimerStart(TIMER_MOTOR_STOP, REGS[REGS_IDX_MOTOR_RUN_DOWN_DURATION]/CFG_EVENT_TIMER_PERIOD_MS);
            eventPublish(EV_DEBUG_SM_STATE_CHANGE, 0, ST_SM_MAIN_STOPPING); PROP(state_) = ST_SM_MAIN_STOPPING;
        }
        break;
    }
    break;
    }
}

static const uint8_t is_in_data[] = {
    0x01, 0x03, 0x05, 0x09, 0x19, 0x29, 0x49, 0x80
};

bool smk_is_in_sm_main(uint8_t state) {
    return !!(is_in_data[(context.state_ * 1) + state/8] & (1 << state%8));
}

/* EOF */
