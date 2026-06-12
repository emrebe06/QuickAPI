#ifndef QUICKAPI_JSON_H
#define QUICKAPI_JSON_H

#include "../core/quick_core.h"

#ifdef __cplusplus
extern "C" {
#endif

QUICKAPI_EXPORT const char* quickapi_json_escape(const char* value);
QUICKAPI_EXPORT const char* quickapi_json_ok(int status, const char* code, const char* message, const char* data_json);
QUICKAPI_EXPORT const char* quickapi_json_error(
    int status,
    const char* code,
    const char* message,
    const char* error_type,
    const char* detail_json
);

#ifdef __cplusplus
}
#endif

#endif
