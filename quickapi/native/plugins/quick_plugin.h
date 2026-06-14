#ifndef QUICKAPI_PLUGIN_H
#define QUICKAPI_PLUGIN_H

#include <stddef.h>
#include "../core/quick_core.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum quickapi_plugin_permission {
    QUICKAPI_PLUGIN_FILE_READ = 1u << 0,
    QUICKAPI_PLUGIN_FILE_WRITE = 1u << 1,
    QUICKAPI_PLUGIN_NETWORK = 1u << 2,
    QUICKAPI_PLUGIN_SHELL = 1u << 3,
    QUICKAPI_PLUGIN_LLM = 1u << 4,
    QUICKAPI_PLUGIN_DATABASE = 1u << 5,
    QUICKAPI_PLUGIN_AUTOMATION = 1u << 6
} quickapi_plugin_permission;

typedef struct quickapi_plugin_manifest {
    const char* name;
    const char* version;
    unsigned int permissions;
    unsigned int max_runtime_ms;
    unsigned int max_memory_mb;
} quickapi_plugin_manifest;

QUICKAPI_EXPORT unsigned int quickapi_plugin_permission_from_name(const char* name);
QUICKAPI_EXPORT int quickapi_plugin_manifest_valid(quickapi_plugin_manifest manifest);
QUICKAPI_EXPORT const char* quickapi_plugin_manifest_json(quickapi_plugin_manifest manifest);
QUICKAPI_EXPORT int quickapi_plugin_permission_allowed(unsigned int granted, unsigned int required);

#ifdef __cplusplus
}
#endif

#endif
