#!/usr/bin/bash

set -e
cp sm_main.autogen.cpp.golden sm_main.autogen.cpp
cp sm_main.autogen.h.golden sm_main.autogen.h

# -f static -O1 
../smk/smk.py -D "RESET_EVENT_NAME=EV_SM_RESET" -D "EVENT_ACCESSOR=event_id(ev)" \
	-D "CHANGE_STATE_HOOK=eventPublish(EV_DEBUG_SM_STATE_CHANGE, 0, st_)" -v -O2 -o sm_main.autogen.cpp sm_main.xml 

echo
diff -s sm_main.autogen.h sm_main.autogen.h.golden
diff -s sm_main.autogen.cpp sm_main.autogen.cpp.golden
