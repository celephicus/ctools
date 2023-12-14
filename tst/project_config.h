// project-config.h -- Project configuration file. 

#ifndef PROJECT_CONFIG_H__
#define PROJECT_CONFIG_H__


// Version info, set by manual editing. 
#define CFG_VER_MAJOR 0   
#define CFG_VER_MINOR 0

// Build number incremented with each build by cfg-set-build.py script. 
#define CFG_BUILD_NUMBER 343

	// Timestamp in ISO8601 format set by cfg-set-build.py script.
 	#define CFG_BUILD_TIMESTAMP "20231215T095039"

// Do not edit below this line......

// Macro tricks to get symbols with build info
#define CFG_STRINGIFY2(x) #x
#define CFG_STRINGIFY(x) CFG_STRINGIFY2(x)

// Build number as a string.
#define CFG_BUILD_NUMBER_STR CFG_STRINGIFY(CFG_BUILD_NUMBER)

// This should not be touched.
#define CFG_BUILD_TIMESTAMP_2 CFG_BUILD_TIMESTAMP

#endif		// PROJECT_CONFIG_H__	
