#include "quick_listener.h"

#include "quick_http.h"
#include "../security/quick_security.h"

#include <cstring>
#include <string>

namespace {
thread_local std::string quick_listener_handler;
thread_local std::string quick_listener_path;

quickapi_listener_exchange exchange_error(
    quickapi_response_writer* writer,
    int status,
    const char* code,
    const char* message,
    int keep_alive,
    unsigned int security_flags = 0
) {
    quickapi_listener_exchange exchange{};
    exchange.ok = 0;
    exchange.status = status;
    exchange.result = quickapi_result_error(status >= 500 ? QUICKAPI_ERROR_INTERNAL : QUICKAPI_ERROR_INVALID_ARGUMENT, message);
    exchange.security_flags = security_flags;
    if (writer) {
        quickapi_response_writer_error_json(writer, status, code, message, keep_alive);
        exchange.response_size = quickapi_response_writer_size(writer);
    }
    return exchange;
}

std::string view_to_string(quickapi_string_view view) {
    if (!view.data || view.size == 0) {
        return "";
    }
    return std::string(view.data, view.size);
}

std::string json_escape(const std::string& value) {
    std::string out;
    out.reserve(value.size() + 8);
    for (char ch : value) {
        switch (ch) {
        case '\\':
            out += "\\\\";
            break;
        case '"':
            out += "\\\"";
            break;
        case '\n':
            out += "\\n";
            break;
        case '\r':
            out += "\\r";
            break;
        case '\t':
            out += "\\t";
            break;
        default:
            out.push_back(ch);
            break;
        }
    }
    return out;
}
}

quickapi_listener_exchange quickapi_listener_handle_json(
    quickapi_router_t router,
    const char* raw_request,
    size_t raw_request_size,
    quickapi_response_writer* writer,
    size_t max_body_size
) {
    if (!router || !raw_request || raw_request_size == 0 || !writer) {
        return exchange_error(writer, 500, "NATIVE_LISTENER_ERROR", "Invalid listener input", 0);
    }

    quickapi_response_writer_reset(writer);
    quickapi_http_request_parse parsed = quickapi_http_parse_request(raw_request, raw_request_size, 96, max_body_size);
    if (!parsed.ok) {
        int status = parsed.result.code == QUICKAPI_ERROR_LIMIT_EXCEEDED ? 413 : 400;
        return exchange_error(writer, status, quickapi_http_status_code_name(status), quickapi_http_parse_error(parsed), 0);
    }

    quickapi_string_view content_type = quickapi_http_header_value(parsed, "Content-Type");
    std::string method = view_to_string(parsed.method);
    std::string path = view_to_string(parsed.path);
    std::string body = view_to_string(parsed.body);
    std::string content_type_text = view_to_string(content_type);
    int keep_alive = quickapi_http_request_should_keep_alive(parsed);

    unsigned int flags = quickapi_security_fast_scan(
        method.c_str(),
        path.c_str(),
        content_type_text.c_str(),
        parsed.body.size,
        max_body_size ? max_body_size : 1024 * 1024,
        body.c_str()
    );
    if (flags != 0) {
        return exchange_error(writer, 400, "BAD_REQUEST", "Suspicious or invalid native HTTP request", keep_alive, flags);
    }

    const char* handler = quickapi_router_match(router, method.c_str(), path.c_str());
    if (!handler) {
        return exchange_error(writer, 404, "NOT_FOUND", "Native route not found", keep_alive);
    }

    quick_listener_handler = handler;
    quick_listener_path = path;
    std::string payload = "{\"handler\":\"";
    payload += json_escape(quick_listener_handler);
    payload += "\",\"path\":\"";
    payload += json_escape(quick_listener_path);
    payload += "\",\"body_bytes\":";
    payload += std::to_string(parsed.body.size);
    payload += "}";

    std::string response = "{\"ok\":true,\"status\":200,\"code\":\"OK\",\"message\":\"Native listener exchange accepted\",\"data\":";
    response += payload;
    response += ",\"error\":null,\"meta\":{\"engine\":\"quickapi-native\"}}";
    quickapi_result write = quickapi_response_writer_json(writer, 200, response.c_str(), keep_alive);

    quickapi_listener_exchange exchange{};
    exchange.ok = write.ok;
    exchange.status = write.ok ? 200 : 500;
    exchange.result = write;
    exchange.handler = quickapi_string_view_make(quick_listener_handler.c_str(), quick_listener_handler.size());
    exchange.path = quickapi_string_view_make(quick_listener_path.c_str(), quick_listener_path.size());
    exchange.response_size = quickapi_response_writer_size(writer);
    exchange.security_flags = 0;
    return exchange;
}
