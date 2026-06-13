#ifndef QUICKAPI_MEMORY_H
#define QUICKAPI_MEMORY_H

#include <stddef.h>
#include "quick_core.h"
#include "quick_result.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct quickapi_arena quickapi_arena;

QUICKAPI_EXPORT quickapi_arena* quickapi_arena_create(size_t capacity);
QUICKAPI_EXPORT void quickapi_arena_destroy(quickapi_arena* arena);
QUICKAPI_EXPORT void quickapi_arena_reset(quickapi_arena* arena);
QUICKAPI_EXPORT quickapi_result quickapi_arena_alloc(quickapi_arena* arena, size_t size, size_t alignment);
QUICKAPI_EXPORT size_t quickapi_arena_used(const quickapi_arena* arena);
QUICKAPI_EXPORT size_t quickapi_arena_capacity(const quickapi_arena* arena);
QUICKAPI_EXPORT void* quickapi_arena_ptr(quickapi_arena* arena, size_t offset);

#ifdef __cplusplus
}
#endif

#endif
