#include "quick_buffer.h"

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <new>

struct quickapi_buffer {
    char* data;
    size_t size;
    size_t capacity;
    size_t max_capacity;
};

namespace {
int ensure_capacity(quickapi_buffer* buffer, size_t needed) {
    if (!buffer || !buffer->data) {
        return 0;
    }
    if (needed <= buffer->capacity) {
        return 1;
    }
    if (needed > buffer->max_capacity) {
        return 0;
    }
    size_t doubled = buffer->capacity > static_cast<size_t>(-1) / 2
        ? buffer->max_capacity
        : buffer->capacity * 2;
    size_t next = std::max(doubled, needed);
    next = std::min(next, buffer->max_capacity);
    if (next == static_cast<size_t>(-1)) {
        return 0;
    }
    char* data = static_cast<char*>(std::realloc(buffer->data, next + 1));
    if (!data) {
        return 0;
    }
    buffer->data = data;
    buffer->capacity = next;
    return 1;
}
}

quickapi_buffer* quickapi_buffer_create(size_t initial_capacity, size_t max_capacity) {
    if (max_capacity == 0) {
        return nullptr;
    }
    if (max_capacity == static_cast<size_t>(-1)) {
        return nullptr;
    }
    if (initial_capacity == 0) {
        initial_capacity = 256;
    }
    if (initial_capacity > max_capacity) {
        initial_capacity = max_capacity;
    }
    quickapi_buffer* buffer = new (std::nothrow) quickapi_buffer;
    if (!buffer) {
        return nullptr;
    }
    buffer->data = static_cast<char*>(std::calloc(initial_capacity + 1, 1));
    if (!buffer->data) {
        delete buffer;
        return nullptr;
    }
    buffer->size = 0;
    buffer->capacity = initial_capacity;
    buffer->max_capacity = max_capacity;
    return buffer;
}

void quickapi_buffer_destroy(quickapi_buffer* buffer) {
    if (!buffer) {
        return;
    }
    std::free(buffer->data);
    buffer->data = nullptr;
    buffer->size = 0;
    buffer->capacity = 0;
    buffer->max_capacity = 0;
    delete buffer;
}

void quickapi_buffer_clear(quickapi_buffer* buffer) {
    if (!buffer || !buffer->data) {
        return;
    }
    buffer->size = 0;
    buffer->data[0] = '\0';
}

quickapi_result quickapi_buffer_reserve(quickapi_buffer* buffer, size_t needed) {
    if (!buffer || !buffer->data) {
        return quickapi_result_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid buffer reserve");
    }
    if (needed > buffer->max_capacity) {
        return quickapi_result_error(QUICKAPI_ERROR_LIMIT_EXCEEDED, "buffer reserve exceeds max capacity");
    }
    if (!ensure_capacity(buffer, needed)) {
        return quickapi_result_error(QUICKAPI_ERROR_OUT_OF_MEMORY, "buffer reserve allocation failed");
    }
    return quickapi_result_ok(buffer->capacity);
}

quickapi_result quickapi_buffer_append(quickapi_buffer* buffer, const char* data, size_t size) {
    if (!buffer || !buffer->data || (!data && size > 0)) {
        return quickapi_result_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid buffer append");
    }
    if (size == 0) {
        return quickapi_result_ok(buffer->size);
    }
    if (buffer->size > buffer->max_capacity || size > buffer->max_capacity - buffer->size) {
        return quickapi_result_error(QUICKAPI_ERROR_LIMIT_EXCEEDED, "buffer capacity exceeded");
    }
    size_t needed = buffer->size + size;
    if (!ensure_capacity(buffer, needed)) {
        return quickapi_result_error(QUICKAPI_ERROR_OUT_OF_MEMORY, "buffer allocation failed");
    }
    std::memcpy(buffer->data + buffer->size, data, size);
    buffer->size += size;
    buffer->data[buffer->size] = '\0';
    return quickapi_result_ok(buffer->size);
}

quickapi_result quickapi_buffer_append_cstr(quickapi_buffer* buffer, const char* data) {
    return quickapi_buffer_append(buffer, data, data ? std::strlen(data) : 0);
}

quickapi_result quickapi_buffer_append_char(quickapi_buffer* buffer, char ch) {
    return quickapi_buffer_append(buffer, &ch, 1);
}

const char* quickapi_buffer_data(const quickapi_buffer* buffer) {
    return buffer && buffer->data ? buffer->data : "";
}

size_t quickapi_buffer_size(const quickapi_buffer* buffer) {
    return buffer ? buffer->size : 0;
}

size_t quickapi_buffer_capacity(const quickapi_buffer* buffer) {
    return buffer ? buffer->capacity : 0;
}

size_t quickapi_buffer_max_capacity(const quickapi_buffer* buffer) {
    return buffer ? buffer->max_capacity : 0;
}

size_t quickapi_buffer_remaining(const quickapi_buffer* buffer) {
    if (!buffer || buffer->size > buffer->max_capacity) {
        return 0;
    }
    return buffer->max_capacity - buffer->size;
}
