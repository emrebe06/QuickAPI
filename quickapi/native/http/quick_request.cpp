#include "quick_request.h"
#include "quick_http.h"

#include <cstring>
#include <string>

namespace {
size_t cstr_len(const char* value) {
    return value ? std::strlen(value) : 0;
}
}

quickapi_request_view quickapi_request_view_make(
    const char* method,
    const char* path,
    const char* query,
    const char* body,
    const char* ip
) {
    quickapi_request_view request;
    request.method = quickapi_string_view_make(method, cstr_len(method));
    request.path = quickapi_string_view_make(path, cstr_len(path));
    request.query = quickapi_string_view_make(query, cstr_len(query));
    request.body = quickapi_string_view_make(body, cstr_len(body));
    request.ip = quickapi_string_view_make(ip, cstr_len(ip));
    return request;
}

int quickapi_request_view_valid(quickapi_request_view request) {
    if (!request.method.data || !request.path.data || request.path.size == 0) {
        return 0;
    }
    return quickapi_http_method_supported(std::string(request.method.data, request.method.size).c_str());
}

size_t quickapi_request_view_body_size(quickapi_request_view request) {
    return request.body.size;
}

size_t quickapi_request_view_path_depth(quickapi_request_view request) {
    if (!request.path.data || request.path.size == 0) {
        return 0;
    }
    size_t depth = 0;
    int in_segment = 0;
    for (size_t i = 0; i < request.path.size; ++i) {
        char ch = request.path.data[i];
        if (ch == '/') {
            in_segment = 0;
        } else if (!in_segment) {
            in_segment = 1;
            depth += 1;
        }
    }
    return depth;
}
