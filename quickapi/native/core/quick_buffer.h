#ifndef QUICKAPI_BUFFER_H
#define QUICKAPI_BUFFER_H

#include <stddef.h>
#include "quick_core.h"
#include "quick_result.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct quickapi_buffer quickapi_buffer;

QUICKAPI_EXPORT quickapi_buffer* quickapi_buffer_create(size_t initial_capacity, size_t max_capacity);
QUICKAPI_EXPORT void quickapi_buffer_destroy(quickapi_buffer* buffer);
QUICKAPI_EXPORT void quickapi_buffer_clear(quickapi_buffer* buffer);
QUICKAPI_EXPORT quickapi_result quickapi_buffer_reserve(quickapi_buffer* buffer, size_t needed);
QUICKAPI_EXPORT quickapi_result quickapi_buffer_append(quickapi_buffer* buffer, const char* data, size_t size);
QUICKAPI_EXPORT quickapi_result quickapi_buffer_append_cstr(quickapi_buffer* buffer, const char* data);
QUICKAPI_EXPORT quickapi_result quickapi_buffer_append_char(quickapi_buffer* buffer, char ch);
QUICKAPI_EXPORT const char* quickapi_buffer_data(const quickapi_buffer* buffer);
QUICKAPI_EXPORT size_t quickapi_buffer_size(const quickapi_buffer* buffer);
QUICKAPI_EXPORT size_t quickapi_buffer_capacity(const quickapi_buffer* buffer);
QUICKAPI_EXPORT size_t quickapi_buffer_max_capacity(const quickapi_buffer* buffer);
QUICKAPI_EXPORT size_t quickapi_buffer_remaining(const quickapi_buffer* buffer);

#ifdef __cplusplus
}
#endif

#endif
