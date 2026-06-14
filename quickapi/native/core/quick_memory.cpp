#include "quick_memory.h"

#include <cstdlib>
#include <cstring>
#include <new>

struct quickapi_arena {
    unsigned char* data;
    size_t capacity;
    size_t used;
    size_t high_watermark;
    size_t allocation_count;
};

namespace {
bool is_power_of_two(size_t value) {
    return value != 0 && (value & (value - 1)) == 0;
}

bool align_up(size_t value, size_t alignment, size_t* out) {
    if (alignment == 0) {
        alignment = sizeof(void*);
    }
    if (!is_power_of_two(alignment)) {
        return false;
    }
    size_t remainder = value % alignment;
    if (remainder == 0) {
        *out = value;
        return true;
    }
    size_t delta = alignment - remainder;
    if (value > static_cast<size_t>(-1) - delta) {
        return false;
    }
    *out = value + delta;
    return true;
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
    arena->high_watermark = 0;
    arena->allocation_count = 0;
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
    arena->high_watermark = 0;
    arena->allocation_count = 0;
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
    arena->allocation_count = 0;
}

quickapi_result quickapi_arena_alloc(quickapi_arena* arena, size_t size, size_t alignment) {
    if (!arena || !arena->data || size == 0) {
        return quickapi_result_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid arena allocation");
    }
    size_t offset = 0;
    if (!align_up(arena->used, alignment, &offset)) {
        return quickapi_result_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid arena alignment");
    }
    if (offset > arena->capacity || size > arena->capacity - offset) {
        return quickapi_result_error(QUICKAPI_ERROR_LIMIT_EXCEEDED, "arena capacity exceeded");
    }
    arena->used = offset + size;
    if (arena->used > arena->high_watermark) {
        arena->high_watermark = arena->used;
    }
    arena->allocation_count += 1;
    return quickapi_result_ok(offset);
}

quickapi_result quickapi_arena_alloc_zeroed(quickapi_arena* arena, size_t size, size_t alignment) {
    quickapi_result result = quickapi_arena_alloc(arena, size, alignment);
    if (!result.ok) {
        return result;
    }
    void* ptr = quickapi_arena_ptr(arena, result.value);
    if (!ptr) {
        return quickapi_result_error(QUICKAPI_ERROR_INTERNAL, "arena pointer lookup failed");
    }
    std::memset(ptr, 0, size);
    return result;
}

size_t quickapi_arena_used(const quickapi_arena* arena) {
    return arena ? arena->used : 0;
}

size_t quickapi_arena_capacity(const quickapi_arena* arena) {
    return arena ? arena->capacity : 0;
}

size_t quickapi_arena_remaining(const quickapi_arena* arena) {
    if (!arena || arena->used > arena->capacity) {
        return 0;
    }
    return arena->capacity - arena->used;
}

size_t quickapi_arena_high_watermark(const quickapi_arena* arena) {
    return arena ? arena->high_watermark : 0;
}

size_t quickapi_arena_allocation_count(const quickapi_arena* arena) {
    return arena ? arena->allocation_count : 0;
}

void* quickapi_arena_ptr(quickapi_arena* arena, size_t offset) {
    if (!arena || !arena->data || offset >= arena->capacity) {
        return nullptr;
    }
    return arena->data + offset;
}

void* quickapi_arena_alloc_ptr(quickapi_arena* arena, size_t size, size_t alignment) {
    quickapi_result result = quickapi_arena_alloc(arena, size, alignment);
    if (!result.ok) {
        return nullptr;
    }
    return quickapi_arena_ptr(arena, result.value);
}
