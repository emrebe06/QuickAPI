#include "quick_http.h"

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <cstring>
#include <string>

namespace {
constexpr size_t npos = static_cast<size_t>(-1);

std::string upper(const char* value) {
    std::string out = value == nullptr ? "" : value;
    std::transform(out.begin(), out.end(), out.begin(), [](unsigned char ch) { return static_cast<char>(std::toupper(ch)); });
    return out;
}

quickapi_string_view view(const char* data, size_t start, size_t end) {
    if (!data || end < start) {
        return quickapi_string_view_make(nullptr, 0);
    }
    return quickapi_string_view_make(data + start, end - start);
}

quickapi_http_request_parse parse_error(quickapi_status_code code, const char* message) {
    quickapi_http_request_parse request{};
    request.ok = 0;
    request.result = quickapi_result_error(code, message);
    return request;
}

size_t find_crlf(const char* data, size_t size, size_t start) {
    if (!data || start >= size) {
        return npos;
    }
    for (size_t i = start; i + 1 < size; ++i) {
        if (data[i] == '\r' && data[i + 1] == '\n') {
            return i;
        }
    }
    return npos;
}

size_t find_header_end(const char* data, size_t size) {
    if (!data || size < 4) {
        return npos;
    }
    for (size_t i = 0; i + 3 < size; ++i) {
        if (data[i] == '\r' && data[i + 1] == '\n' && data[i + 2] == '\r' && data[i + 3] == '\n') {
            return i;
        }
    }
    return npos;
}

size_t find_char(const char* data, size_t start, size_t end, char needle) {
    for (size_t i = start; i < end; ++i) {
        if (data[i] == needle) {
            return i;
        }
    }
    return npos;
}

bool view_iequals(quickapi_string_view value, const char* text) {
    if (!text) {
        return value.size == 0;
    }
    size_t len = std::strlen(text);
    if (value.size != len || !value.data) {
        return false;
    }
    for (size_t i = 0; i < len; ++i) {
        if (std::tolower(static_cast<unsigned char>(value.data[i])) != std::tolower(static_cast<unsigned char>(text[i]))) {
            return false;
        }
    }
    return true;
}

bool view_contains_ci(quickapi_string_view value, const char* needle) {
    if (!value.data || !needle || !*needle) {
        return false;
    }
    size_t needle_len = std::strlen(needle);
    if (needle_len > value.size) {
        return false;
    }
    for (size_t i = 0; i + needle_len <= value.size; ++i) {
        bool ok = true;
        for (size_t j = 0; j < needle_len; ++j) {
            if (std::tolower(static_cast<unsigned char>(value.data[i + j])) != std::tolower(static_cast<unsigned char>(needle[j]))) {
                ok = false;
                break;
            }
        }
        if (ok) {
            return true;
        }
    }
    return false;
}

quickapi_string_view trim_view(const char* data, size_t start, size_t end) {
    while (start < end && (data[start] == ' ' || data[start] == '\t')) {
        ++start;
    }
    while (end > start && (data[end - 1] == ' ' || data[end - 1] == '\t')) {
        --end;
    }
    return view(data, start, end);
}

size_t parse_size(quickapi_string_view value) {
    if (!value.data || value.size == 0) {
        return 0;
    }
    size_t result = 0;
    for (size_t i = 0; i < value.size; ++i) {
        unsigned char ch = static_cast<unsigned char>(value.data[i]);
        if (!std::isdigit(ch)) {
            return 0;
        }
        size_t digit = static_cast<size_t>(ch - '0');
        if (result > (static_cast<size_t>(-1) - digit) / 10) {
            return 0;
        }
        result = result * 10 + digit;
    }
    return result;
}

int supported_method_view(quickapi_string_view method) {
    if (!method.data || method.size == 0 || method.size > 8) {
        return 0;
    }
    char buffer[9] = {};
    std::memcpy(buffer, method.data, method.size);
    return quickapi_http_method_supported(buffer);
}
}

const char* quickapi_http_status_code_name(int status) {
    switch (status) {
        case 200: return "OK";
        case 201: return "CREATED";
        case 202: return "ACCEPTED";
        case 204: return "NO_CONTENT";
        case 400: return "BAD_REQUEST";
        case 401: return "UNAUTHORIZED";
        case 402: return "PAYMENT_REQUIRED";
        case 403: return "FORBIDDEN";
        case 404: return "NOT_FOUND";
        case 405: return "METHOD_NOT_ALLOWED";
        case 409: return "CONFLICT";
        case 413: return "PAYLOAD_TOO_LARGE";
        case 415: return "UNSUPPORTED_MEDIA_TYPE";
        case 422: return "VALIDATION_ERROR";
        case 429: return "TOO_MANY_REQUESTS";
        case 500: return "INTERNAL_SERVER_ERROR";
        case 502: return "BAD_GATEWAY";
        case 503: return "SERVICE_UNAVAILABLE";
        case 504: return "GATEWAY_TIMEOUT";
        default: return "UNKNOWN";
    }
}

const char* quickapi_http_status_message(int status) {
    switch (status) {
        case 200: return "OK";
        case 201: return "Created";
        case 202: return "Accepted";
        case 204: return "No content";
        case 400: return "Bad request";
        case 401: return "Unauthorized";
        case 402: return "Payment required";
        case 403: return "Forbidden";
        case 404: return "Not found";
        case 405: return "Method not allowed";
        case 409: return "Conflict";
        case 413: return "Payload too large";
        case 415: return "Unsupported media type";
        case 422: return "Validation error";
        case 429: return "Too many requests";
        case 500: return "Internal server error";
        case 502: return "Bad gateway";
        case 503: return "Service unavailable";
        case 504: return "Gateway timeout";
        default: return "Unknown";
    }
}

int quickapi_http_method_supported(const char* method) {
    std::string value = upper(method);
    return value == "GET" || value == "POST" || value == "PUT" || value == "PATCH" || value == "DELETE" || value == "OPTIONS" || value == "HEAD";
}

quickapi_http_request_parse quickapi_http_parse_request(const char* data, size_t size, size_t max_headers, size_t max_body_size) {
    if (!data || size == 0) {
        return parse_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "empty http request");
    }
    if (max_headers == 0) {
        max_headers = 64;
    }
    if (max_body_size == 0) {
        max_body_size = 1024 * 1024;
    }

    size_t header_end = find_header_end(data, size);
    if (header_end == npos) {
        return parse_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "http headers are incomplete");
    }

    size_t line_end = find_crlf(data, size, 0);
    if (line_end == npos || line_end == 0) {
        return parse_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid request line");
    }

    size_t method_end = find_char(data, 0, line_end, ' ');
    if (method_end == npos) {
        return parse_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "request method is missing");
    }
    size_t target_start = method_end + 1;
    size_t target_end = find_char(data, target_start, line_end, ' ');
    if (target_end == npos || target_end == target_start) {
        return parse_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "request target is missing");
    }
    size_t version_start = target_end + 1;
    if (version_start >= line_end) {
        return parse_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "http version is missing");
    }

    quickapi_http_request_parse request{};
    request.method = view(data, 0, method_end);
    request.target = view(data, target_start, target_end);
    request.version = view(data, version_start, line_end);
    if (!supported_method_view(request.method)) {
        return parse_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "unsupported http method");
    }

    size_t query_marker = find_char(data, target_start, target_end, '?');
    if (query_marker == npos) {
        request.path = request.target;
        request.query = quickapi_string_view_make(nullptr, 0);
    } else {
        request.path = view(data, target_start, query_marker);
        request.query = view(data, query_marker + 1, target_end);
    }
    if (!request.path.data || request.path.size == 0 || request.path.data[0] != '/') {
        return parse_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "request path must start with slash");
    }

    request.headers = view(data, line_end + 2, header_end);
    request.header_count = 0;
    request.content_length = 0;
    request.keep_alive = view_contains_ci(request.version, "HTTP/1.1") ? 1 : 0;

    size_t cursor = line_end + 2;
    while (cursor < header_end) {
        size_t end = find_crlf(data, size, cursor);
        if (end == npos || end > header_end) {
            return parse_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "invalid header line");
        }
        if (end == cursor) {
            break;
        }
        if (++request.header_count > max_headers) {
            return parse_error(QUICKAPI_ERROR_LIMIT_EXCEEDED, "too many headers");
        }
        size_t colon = find_char(data, cursor, end, ':');
        if (colon == npos || colon == cursor) {
            return parse_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "malformed header");
        }
        quickapi_string_view key = trim_view(data, cursor, colon);
        quickapi_string_view value = trim_view(data, colon + 1, end);
        if (view_iequals(key, "Content-Length")) {
            request.content_length = parse_size(value);
        } else if (view_iequals(key, "Connection")) {
            if (view_contains_ci(value, "close")) {
                request.keep_alive = 0;
            } else if (view_contains_ci(value, "keep-alive")) {
                request.keep_alive = 1;
            }
        }
        cursor = end + 2;
    }

    if (request.content_length > max_body_size) {
        return parse_error(QUICKAPI_ERROR_LIMIT_EXCEEDED, "http body exceeds max_body_size");
    }
    size_t body_start = header_end + 4;
    if (body_start > size || request.content_length > size - body_start) {
        return parse_error(QUICKAPI_ERROR_INVALID_ARGUMENT, "http body is incomplete");
    }
    request.body = view(data, body_start, body_start + request.content_length);
    request.result = quickapi_result_ok(body_start + request.content_length);
    request.ok = 1;
    return request;
}

quickapi_string_view quickapi_http_header_value(quickapi_http_request_parse request, const char* name) {
    if (!request.headers.data || !name) {
        return quickapi_string_view_make(nullptr, 0);
    }
    const char* data = request.headers.data;
    size_t cursor = 0;
    while (cursor < request.headers.size) {
        size_t line_end = cursor;
        while (line_end + 1 < request.headers.size && !(data[line_end] == '\r' && data[line_end + 1] == '\n')) {
            ++line_end;
        }
        size_t colon = find_char(data, cursor, line_end, ':');
        if (colon != npos) {
            quickapi_string_view key = trim_view(data, cursor, colon);
            if (view_iequals(key, name)) {
                return trim_view(data, colon + 1, line_end);
            }
        }
        cursor = line_end + 2;
    }
    return quickapi_string_view_make(nullptr, 0);
}

int quickapi_http_request_should_keep_alive(quickapi_http_request_parse request) {
    return request.ok && request.keep_alive;
}

const char* quickapi_http_parse_error(quickapi_http_request_parse request) {
    if (request.ok) {
        return "";
    }
    return request.result.message ? request.result.message : "http parse error";
}
