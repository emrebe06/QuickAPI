#include "quick_string.h"

#include <cstring>

quickapi_string_view quickapi_string_view_make(const char* data, size_t size) {
    quickapi_string_view view;
    view.data = data;
    view.size = data ? size : 0;
    return view;
}

quickapi_string_view quickapi_string_view_from_cstr(const char* data) {
    return quickapi_string_view_make(data, data ? std::strlen(data) : 0);
}

int quickapi_string_view_equals(quickapi_string_view left, quickapi_string_view right) {
    if (left.size != right.size) {
        return 0;
    }
    if (left.size == 0) {
        return 1;
    }
    if (!left.data || !right.data) {
        return 0;
    }
    return std::memcmp(left.data, right.data, left.size) == 0 ? 1 : 0;
}

int quickapi_string_view_contains(quickapi_string_view haystack, quickapi_string_view needle) {
    if (!haystack.data || !needle.data || needle.size == 0 || needle.size > haystack.size) {
        return 0;
    }
    for (size_t i = 0; i <= haystack.size - needle.size; ++i) {
        if (std::memcmp(haystack.data + i, needle.data, needle.size) == 0) {
            return 1;
        }
    }
    return 0;
}
