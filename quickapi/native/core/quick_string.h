#ifndef QUICKAPI_STRING_H
#define QUICKAPI_STRING_H

#include <stddef.h>
#include "quick_core.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct quickapi_string_view {
    const char* data;
    size_t size;
} quickapi_string_view;

QUICKAPI_EXPORT quickapi_string_view quickapi_string_view_make(const char* data, size_t size);
QUICKAPI_EXPORT quickapi_string_view quickapi_string_view_from_cstr(const char* data);
QUICKAPI_EXPORT int quickapi_string_view_equals(quickapi_string_view left, quickapi_string_view right);
QUICKAPI_EXPORT int quickapi_string_view_contains(quickapi_string_view haystack, quickapi_string_view needle);

#ifdef __cplusplus
}
#endif

#endif
