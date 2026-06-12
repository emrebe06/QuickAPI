#ifndef QUICKAPI_NATIVE_LOADER_H
#define QUICKAPI_NATIVE_LOADER_H

#include "../core/quick_core.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef const char* (*quickapi_native_json_fn)(const char* json_input);

QUICKAPI_EXPORT void* quickapi_native_open(const char* library_path);
QUICKAPI_EXPORT void quickapi_native_close(void* handle);
QUICKAPI_EXPORT quickapi_native_json_fn quickapi_native_symbol(void* handle, const char* symbol);
QUICKAPI_EXPORT const char* quickapi_native_last_error(void);

#ifdef __cplusplus
}
#endif

#endif
