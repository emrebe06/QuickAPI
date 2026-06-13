#include "quick_memory.h"

#include <cstdlib>
#include <cstring>
#include <new>

struct quickapi_arena {
    unsigned char* data;
    size_t capacity;
    size_t used;
};

namespace {
size_t align_up(size_t value, size_t alignment) {
    if (alignment == 0) {
        alignment = sizeof(void*);
    }
    size_t remainder = value % alignment;
    if (remainder == 0) {
        return value;
    }
    return value + (alignment - remainder);
}
}

const char* quickapi_result_code_name(int code) {
    switch (code) {
        case QUICKAPI_OK: return "OK";
        case QUICKAPI_ERROR_INVALID_ARGUMENT: return "INVALID_ARGUMENT";
        case QUICKAPI_ERROR_OUT_OF_MEMORY: return "OUT_OF_MEMORY";
        case QUICKAPI_ERROR_LIMIT_EXCEEDED: return "LIMIT_EXCEEDED";
        case QUICKAPI_ERROR_NOT_FOUND: return "NOT_FOUND";
        case QUICKAPI_ERROR_IO: return "IO_ERROR";
        case QUICKAPI_ERROR_CANCELLED: return "CANCELLED";
        default: return "INTERNAL_ERROR";
    }
}

quickapi_arena* quickapi_arena_create(size_t capacity) {
    if (capacity == 0) {
        return nullptr;
    }
    quickapi_arena* arena = new (std::nothrow) quickapi_arena;
    if (!arena) {
        return nullptr;
    }
    arena->data = static_cast<unsigned char*>(std::calloc(capacity, 1));
    if (!arena->data) {
        delete arena;
        return nullptr;
    }
    arena->capacity = capacity;
    arena->used = 0;
    return arena;
}

void quickapi_arena_destroy(quickapi_arena* arena) {
    if (!arena) {
        return;
    }
    std::free(arena->data);
    arena->data = nullptr;
    arena->capacity = 0;
    arena->used = 0;
    delete arena;
}

void quickapi_arena_reset(quickapi_arena* arena) {
    if (!arena) {
        return;
    }
    if (arena->data && arena->capacity) {
        std::memset(arena->data, 0, arena->capacity);
    }
    arena->used = 0;
}

quickapi_result quickapi_arena_alloc(quickapi_arena* arena, size_t size, size_t alignment) {
    if (!arena || !arena->data || size == 0) {
        return quickapi_result_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid arena allocation");
    }
    size_t offset = align_up(arena->used, alignment);
    if (offset > arena->capacity || size > arena->capacity - offset) {
        return quickapi_result_error(QUICKAPI_ERROR_LIMIT_EXCEEDED, "arena capacity exceeded");
    }
    arena->used = offset + size;
    return quickapi_result_ok(offset);
}

size_t quickapi_arena_used(const quickapi_arena* arena) {
    return arena ? arena->used : 0;
}

size_t quickapi_arena_capacity(const quickapi_arena* arena) {
    return arena ? arena->capacity : 0;
}

void* quickapi_arena_ptr(quickapi_arena* arena, size_t offset) {
    if (!arena || !arena->data || offset >= arena->capacity) {
        return nullptr;
    }
    return arena->data + offset;
}
