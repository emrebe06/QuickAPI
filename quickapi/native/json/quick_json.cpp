#include "quick_json.h"

#include <sstream>
#include <string>

namespace {
thread_local std::string quick_json_buffer;

const char* safe(const char* value, const char* fallback = "") {
    return value == nullptr ? fallback : value;
}

std::string escape_json(const char* raw) {
    std::ostringstream out;
    const char* value = safe(raw);
    for (const unsigned char* p = reinterpret_cast<const unsigned char*>(value); *p; ++p) {
        switch (*p) {
            case '\\': out << "\\\\"; break;
            case '"': out << "\\\""; break;
            case '\b': out << "\\b"; break;
            case '\f': out << "\\f"; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default:
                if (*p < 0x20) {
                    out << "\\u00";
                    const char* hex = "0123456789abcdef";
                    out << hex[*p >> 4] << hex[*p & 0x0f];
                } else {
                    out << static_cast<char>(*p);
                }
        }
    }
    return out.str();
}
}

const char* quickapi_json_escape(const char* value) {
    quick_json_buffer = escape_json(value);
    return quick_json_buffer.c_str();
}

const char* quickapi_json_ok(int status, const char* code, const char* message, const char* data_json) {
    quick_json_buffer =
        "{\"ok\":true,\"status\":" + std::to_string(status) +
        ",\"code\":\"" + escape_json(safe(code, "OK")) +
        "\",\"message\":\"" + escape_json(safe(message, "Success")) +
        "\",\"data\":" + std::string(safe(data_json, "null")) +
        ",\"error\":null,\"meta\":{\"engine\":\"quickapi_native\"}}";
    return quick_json_buffer.c_str();
}

const char* quickapi_json_error(
    int status,
    const char* code,
    const char* message,
    const char* error_type,
    const char* detail_json
) {
    quick_json_buffer =
        "{\"ok\":false,\"status\":" + std::to_string(status) +
        ",\"code\":\"" + escape_json(safe(code, "INTERNAL_SERVER_ERROR")) +
        "\",\"message\":\"" + escape_json(safe(message, "Internal server error")) +
        "\",\"data\":null,\"error\":{\"type\":\"" + escape_json(safe(error_type, "api_error")) +
        "\",\"detail\":" + std::string(safe(detail_json, "null")) +
        "},\"meta\":{\"engine\":\"quickapi_native\"}}";
    return quick_json_buffer.c_str();
}
