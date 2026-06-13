#ifndef QUICKAPI_RESULT_H
#define QUICKAPI_RESULT_H

#include <stddef.h>
#include "quick_core.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum quickapi_status_code {
    QUICKAPI_OK = 0,
    QUICKAPI_ERROR_INVALID_ARGUMENT = 1,
    QUICKAPI_ERROR_OUT_OF_MEMORY = 2,
    QUICKAPI_ERROR_LIMIT_EXCEEDED = 3,
    QUICKAPI_ERROR_NOT_FOUND = 4,
    QUICKAPI_ERROR_IO = 5,
    QUICKAPI_ERROR_CANCELLED = 6,
    QUICKAPI_ERROR_INTERNAL = 99
} quickapi_status_code;

typedef struct quickapi_result {
    int ok;
    quickapi_status_code code;
    size_t value;
    const char* message;
} quickapi_result;

static inline quickapi_result quickapi_result_ok(size_t value) {
    quickapi_result result;
    result.ok = 1;
    result.code = QUICKAPI_OK;
    result.value = value;
    result.message = "ok";
    return result;
}

static inline quickapi_result quickapi_result_error(quickapi_status_code code, const char* message) {
    quickapi_result result;
    result.ok = 0;
    result.code = code;
    result.value = 0;
    result.message = message;
    return result;
}

QUICKAPI_EXPORT const char* quickapi_result_code_name(int code);

#ifdef __cplusplus
}
#endif

#endif
