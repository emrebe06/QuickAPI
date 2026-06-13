#ifndef QUICKAPI_ISOLATE_H
#define QUICKAPI_ISOLATE_H

#include "../core/quick_core.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct quickapi_isolate_spec {
    const char* executable;
    const char* working_directory;
    unsigned int timeout_ms;
    unsigned int memory_limit_mb;
} quickapi_isolate_spec;

QUICKAPI_EXPORT int quickapi_isolate_spec_valid(quickapi_isolate_spec spec);
QUICKAPI_EXPORT const char* quickapi_isolate_plan(quickapi_isolate_spec spec);

#ifdef __cplusplus
}
#endif

#endif
