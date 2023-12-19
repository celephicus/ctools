#ifndef REGS_LOCAL_H__
#define REGS_LOCAL_H__

// Define version of NV data. If you change the schema or the implementation, increment the number to force any existing
// EEPROM to flag as corrupt. Also increment to force the default values to be set for testing.
const uint16_t REGS_DEF_VERSION = 2;

/* [[[ Definition start...
FLAGS [fmt=hex] "Various flags.
	A register with a number of boolean flags that represent various conditions. They may be set only at at startup, or as the
	result of various conditions."
- DC_LOW [bit=0] "External DC power volts low.
	The DC volts supplying power to the slave from the bus cable is low indicating a possible problem."
- SW_RUN [bit=1] "RUN button active."
- SW_DIR [bit=2] "DIR button active."
- REM1_RUN [bit=3] "REM1 RUN active."
- REM1_DIR [bit=4] "REM1 DIR active."
- REM2_RUN [bit=5] "REM2 RUN active."
- REM2_DIR [bit=6] "REM2 DIR active."
- ESTOP [bit=7] "E-stop active."
- MOTOR_DIR_REVERSE [bit=8] "Holds fwd/reverse state of motor."
- EEPROM_READ_BAD_0 [bit=13] "EEPROM bank 0 corrupt.
	EEPROM bank 0 corrupt. If bank 1 is corrupt too then a default set of values has been written. Flag written at startup only."
- EEPROM_READ_BAD_1 [bit=14] "EEPROM bank 1 corrupt.
	EEPROM bank 1 corrupt. If bank 0 is corrupt too then a default set of values has been written. Flag written at startup only."
- WATCHDOG_RESTART [bit=15] "Device has restarted from a watchdog timeout."
RESTART [fmt=hex] "MCUSR in low byte, wdog in high byte.
	The processor MCUSR register is copied into the low byte. The watchdog reset source is copied to the high byte. For details
	refer to devWatchdogInit()."
ADC_VOLTS_MON_DC "Raw ADC (unscaled) voltage on DC input."
VOLTS_MON_DC "DC input volts /mV."
RELAYS [fmt=hex] "Relay state, updated at 10/s rate from this register"
- RUN   [bit=0] "Run relay, full motor current."
- START [bit=1] "Start relay, via soft-start resistor."
- DIR_1 [bit=2] "0 for FWD, 1 for REV."
- DIR_2 [bit=3] "1 for FWD, 2 for REV."
MOTOR_RUN_DOWN_DURATION [nv default=1000] "Time in ms to allow motor to run down after stopping."
MOTOR_SOFT_START_DURATION [nv default=500] "Time in ms for motor soft start."
ENABLES [nv fmt=hex] "Non-volatile enable flags.
	A number of flags that are rarely written by the code, but control the behaviour of the system."
- DUMP_REGS [bit=0] "Enable regs dump to console.
	If set then registers are dumped at a set rate."
- DUMP_REGS_FAST [bit=1] "Dump regs at 5/s rather than 1/s."
- TRACE_FORMAT_BINARY [bit=13] "Dump trace in binary format."
- TRACE_FORMAT_CONCISE [bit=14] "Dump trace in concise text format."
>>>  Definition end, declaration start... */

// Declare the indices to the registers.
enum {
    REGS_IDX_FLAGS = 0,
    REGS_IDX_RESTART = 1,
    REGS_IDX_ADC_VOLTS_MON_DC = 2,
    REGS_IDX_VOLTS_MON_DC = 3,
    REGS_IDX_RELAYS = 4,
    REGS_IDX_MOTOR_RUN_DOWN_DURATION = 5,
    REGS_IDX_MOTOR_SOFT_START_DURATION = 6,
    REGS_IDX_ENABLES = 7,
    COUNT_REGS = 8
};

// Define the start of the NV regs. The region is from this index up to the end of the register array.
#define REGS_START_NV_IDX REGS_IDX_MOTOR_RUN_DOWN_DURATION

// Define default values for the NV segment.
#define REGS_NV_DEFAULT_VALS 1000, 500, 0

// Define how to format the reg when printing.
#define REGS_FORMAT_DEF CFMT_X, CFMT_X, CFMT_U, CFMT_U, CFMT_X, CFMT_U, CFMT_U, CFMT_X

// Flags/masks for register FLAGS.
enum {
    	REGS_FLAGS_MASK_DC_LOW = (int)0x1,
    	REGS_FLAGS_MASK_SW_RUN = (int)0x2,
    	REGS_FLAGS_MASK_SW_DIR = (int)0x4,
    	REGS_FLAGS_MASK_REM1_RUN = (int)0x8,
    	REGS_FLAGS_MASK_REM1_DIR = (int)0x10,
    	REGS_FLAGS_MASK_REM2_RUN = (int)0x20,
    	REGS_FLAGS_MASK_REM2_DIR = (int)0x40,
    	REGS_FLAGS_MASK_ESTOP = (int)0x80,
    	REGS_FLAGS_MASK_MOTOR_DIR_REVERSE = (int)0x100,
    	REGS_FLAGS_MASK_EEPROM_READ_BAD_0 = (int)0x2000,
    	REGS_FLAGS_MASK_EEPROM_READ_BAD_1 = (int)0x4000,
    	REGS_FLAGS_MASK_WATCHDOG_RESTART = (int)0x8000,
};

// Flags/masks for register RELAYS.
enum {
    	REGS_RELAYS_MASK_RUN = (int)0x1,
    	REGS_RELAYS_MASK_START = (int)0x2,
    	REGS_RELAYS_MASK_DIR_1 = (int)0x4,
    	REGS_RELAYS_MASK_DIR_2 = (int)0x8,
};

// Flags/masks for register ENABLES.
enum {
    	REGS_ENABLES_MASK_DUMP_REGS = (int)0x1,
    	REGS_ENABLES_MASK_DUMP_REGS_FAST = (int)0x2,
    	REGS_ENABLES_MASK_TRACE_FORMAT_BINARY = (int)0x2000,
    	REGS_ENABLES_MASK_TRACE_FORMAT_CONCISE = (int)0x4000,
};

// Declare an array of names for each register.
#define DECLARE_REGS_NAMES()                                                            \
 static const char REGS_NAMES_0[] PROGMEM = "FLAGS";                                    \
 static const char REGS_NAMES_1[] PROGMEM = "RESTART";                                  \
 static const char REGS_NAMES_2[] PROGMEM = "ADC_VOLTS_MON_DC";                         \
 static const char REGS_NAMES_3[] PROGMEM = "VOLTS_MON_DC";                             \
 static const char REGS_NAMES_4[] PROGMEM = "RELAYS";                                   \
 static const char REGS_NAMES_5[] PROGMEM = "MOTOR_RUN_DOWN_DURATION";                  \
 static const char REGS_NAMES_6[] PROGMEM = "MOTOR_SOFT_START_DURATION";                \
 static const char REGS_NAMES_7[] PROGMEM = "ENABLES";                                  \
                                                                                        \
 static const char* const REGS_NAMES[] PROGMEM = {                                      \
   REGS_NAMES_0,                                                                        \
   REGS_NAMES_1,                                                                        \
   REGS_NAMES_2,                                                                        \
   REGS_NAMES_3,                                                                        \
   REGS_NAMES_4,                                                                        \
   REGS_NAMES_5,                                                                        \
   REGS_NAMES_6,                                                                        \
   REGS_NAMES_7,                                                                        \
 }

// Declare an array of description text for each register.
#define DECLARE_REGS_DESCRS()                                                           \
 static const char REGS_DESCRS_0[] PROGMEM = "Various flags.";                          \
 static const char REGS_DESCRS_1[] PROGMEM = "MCUSR in low byte, wdog in high byte.";   \
 static const char REGS_DESCRS_2[] PROGMEM = "Raw ADC (unscaled) voltage on DC input."; \
 static const char REGS_DESCRS_3[] PROGMEM = "DC input volts /mV.";                     \
 static const char REGS_DESCRS_4[] PROGMEM = "Relay state, updated at 10/s rate from this register.";\
 static const char REGS_DESCRS_5[] PROGMEM = "Time in ms to allow motor to run down after stopping.";\
 static const char REGS_DESCRS_6[] PROGMEM = "Time in ms for motor soft start.";        \
 static const char REGS_DESCRS_7[] PROGMEM = "Non-volatile enable flags.";              \
                                                                                        \
 static const char* const REGS_DESCRS[] PROGMEM = {                                     \
   REGS_DESCRS_0,                                                                       \
   REGS_DESCRS_1,                                                                       \
   REGS_DESCRS_2,                                                                       \
   REGS_DESCRS_3,                                                                       \
   REGS_DESCRS_4,                                                                       \
   REGS_DESCRS_5,                                                                       \
   REGS_DESCRS_6,                                                                       \
   REGS_DESCRS_7,                                                                       \
 }

// Declare a multiline string description of the fields.
#define DECLARE_REGS_HELPS()                                                            \
 static const char REGS_HELPS[] PROGMEM =                                               \
    "\nFlags:"                                                                          \
    "\n DC_LOW: 0 (External DC power volts low.)"                                       \
    "\n SW_RUN: 1 (RUN button active.)"                                                 \
    "\n SW_DIR: 2 (DIR button active.)"                                                 \
    "\n REM1_RUN: 3 (REM1 RUN active.)"                                                 \
    "\n REM1_DIR: 4 (REM1 DIR active.)"                                                 \
    "\n REM2_RUN: 5 (REM2 RUN active.)"                                                 \
    "\n REM2_DIR: 6 (REM2 DIR active.)"                                                 \
    "\n ESTOP: 7 (E-stop active.)"                                                      \
    "\n MOTOR_DIR_REVERSE: 8 (Holds fwd/reverse state of motor.)"                       \
    "\n EEPROM_READ_BAD_0: 13 (EEPROM bank 0 corrupt.)"                                 \
    "\n EEPROM_READ_BAD_1: 14 (EEPROM bank 1 corrupt.)"                                 \
    "\n WATCHDOG_RESTART: 15 (Device has restarted from a watchdog timeout.)"           \
    "\nRelays:"                                                                         \
    "\n RUN: 0 (Run relay, full motor current.)"                                        \
    "\n START: 1 (Start relay, via soft-start resistor.)"                               \
    "\n DIR_1: 2 (0 for FWD, 1 for REV.)"                                               \
    "\n DIR_2: 3 (1 for FWD, 2 for REV.)"                                               \
    "\nEnables:"                                                                        \
    "\n DUMP_REGS: 0 (Enable regs dump to console.)"                                    \
    "\n DUMP_REGS_FAST: 1 (Dump regs at 5/s rather than 1/s.)"                          \
    "\n TRACE_FORMAT_BINARY: 13 (Dump trace in binary format.)"                         \
    "\n TRACE_FORMAT_CONCISE: 14 (Dump trace in concise text format.)"                  \

// ]]] Declarations end

#endif // REGS_LOCAL_H__
