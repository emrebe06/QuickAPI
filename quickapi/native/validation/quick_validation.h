#ifndef QUICKAPI_VALIDATION_H
#define QUICKAPI_VALIDATION_H

#include <stddef.h>
#include "../core/quick_core.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum quickapi_validation_flags {
    QUICKAPI_VALIDATION_OK = 0,
    QUICKAPI_VALIDATION_CONTROL_CHARACTER = 1u << 0,
    QUICKAPI_VALIDATION_DEPTH_EXCEEDED = 1u << 1,
    QUICKAPI_VALIDATION_STRING_TOO_LONG = 1u << 2,
    QUICKAPI_VALIDATION_ARRAY_TOO_LONG = 1u << 3,
    QUICKAPI_VALIDATION_OBJECT_TOO_WIDE = 1u << 4,
    QUICKAPI_VALIDATION_UNBALANCED_JSON = 1u << 5,
    QUICKAPI_VALIDATION_SUSPICIOUS_KEY = 1u << 6,
    QUICKAPI_VALIDATION_BINARY_PAYLOAD = 1u << 7
} quickapi_validation_flags;

QUICKAPI_EXPORT unsigned int quickapi_validation_payload_flags(
    const char* payload,
    size_t payload_size,
    size_t max_depth,
    size_t max_string_length,
    size_t max_array_length,
    size_t max_object_keys
);

QUICKAPI_EXPORT const char* quickapi_validation_payload_json(
    const char* payload,
    size_t payload_size,
    size_t max_depth,
    size_t max_string_length,
    size_t max_array_length,
    size_t max_object_keys
);

QUICKAPI_EXPORT const char* quickapi_validation_flags_json(unsigned int flags);

#ifdef __cplusplus
}
#endif

#endif
