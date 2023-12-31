// This file is autogenerated from `../tst/event.local.src'. Do not edit, your changes will be lost!

#ifndef F_EVENT_LOCAL_H__
#define F_EVENT_LOCAL_H__

// Event IDs
enum {
    EV_SAMPLE_1 = 0,                    // Frobs the foo.
    EV_SAMPLE_2 = 1,                    // Frobs the foo some more.
    COUNT_EV = 2,                       // Total number of events defined.
};

// Multi event counts.

// Size of trace mask in bytes.
#define EVENT_TRACE_MASK_SIZE 2

// Trace mask default.
#define EVENT_DECLARE_TRACE_MASK_DEFAULT() static const uint8_t TRACE_MASK_DEFAULT[] PROGMEM = {    \
    0x01                                                                                            \
}

// Trace mask all.
#define EVENT_DECLARE_TRACE_MASK_ALL() static const uint8_t TRACE_MASK_ALL[] PROGMEM = {            \
    0x03                                                                                            \
}

// Trace mask debug.
#define EVENT_DECLARE_TRACE_MASK_DEBUG() static const uint8_t TRACE_MASK_DEBUG[] PROGMEM = {        \
    0x02                                                                                            \
}

// Event Names.
#define EVENT_DECLARE_EVENT_NAMES()                                                     \
 static const char EVENT_NAMES_0[] PROGMEM = "SAMPLE_1";                                \
 static const char EVENT_NAMES_1[] PROGMEM = "SAMPLE_2";                                \
                                                                                        \
 static const char* const EVENT_NAMES[] PROGMEM = {                                     \
   EVENT_NAMES_0,                                                                       \
   EVENT_NAMES_1,                                                                       \
 }

// Event Descriptions.
#define EVENT_DECLARE_EVENT_DESCS()                                                                                                         \
 static const char EVENT_DESCS_0[] PROGMEM = "Frobs the foo.";                                                                              \
 static const char EVENT_DESCS_1[] PROGMEM = "Frobs the foo some more.";                                                                    \
                                                                                                                                            \
 static const char* const EVENT_DESCS[] PROGMEM = {                                                                                         \
   EVENT_DESCS_0,                                                                                                                           \
   EVENT_DESCS_1,                                                                                                                           \
 }


#endif   // F_EVENT_LOCAL_H__
